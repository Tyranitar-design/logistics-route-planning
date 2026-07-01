import importlib
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _build_client(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app, db
    from app.models import DataImportBatch, ShipmentFact, User, Vehicle

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "dispatch-orchestration-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        batch = DataImportBatch(
            dataset_source="unit-test",
            source_filename="dispatch.csv",
            quality_status="ready",
            raw_record_count=2,
            fact_record_count=2,
        )
        db.session.add(batch)
        db.session.flush()

        db.session.add_all([
            Vehicle(
                plate_number="京A10001",
                vehicle_type="truck",
                load_capacity=30,
                volume_capacity=90,
                capacity=30,
                status="available",
            ),
            Vehicle(
                plate_number="京A10002",
                vehicle_type="truck",
                load_capacity=30,
                volume_capacity=90,
                capacity=30,
                status="available",
            ),
        ])
        db.session.add_all([
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHP-DISPATCH-001",
                external_order_id="ORD-DISPATCH-001",
                customer_name_masked="客户甲",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="天津",
                destination_city_std="天津",
                origin_lng=116.4074,
                origin_lat=39.9042,
                destination_lng=117.2,
                destination_lat=39.1333,
                geo_status="resolved",
                cargo_type="普货",
                standard_status="assigned",
                weight_kg=12000,
                volume_m3=20,
                freight=500,
            ),
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHP-DISPATCH-002",
                external_order_id="ORD-DISPATCH-002",
                customer_name_masked="客户乙",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="石家庄",
                destination_city_std="石家庄",
                origin_lng=116.4074,
                origin_lat=39.9042,
                destination_lng=114.5149,
                destination_lat=38.0428,
                geo_status="resolved",
                cargo_type="普货",
                standard_status="assigned",
                weight_kg=15000,
                volume_m3=25,
                freight=650,
            ),
        ])
        db.session.commit()

    client = app.test_client()
    login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_response.get_json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}, app


def test_dispatch_health_prefers_layered_facts_when_orders_empty(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    response = client.get("/api/dispatch/health", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data_source"] == "shipment_fact"
    assert payload["order_sources"]["shipment_facts"]["total"] == 2
    assert payload["vehicle_source"]["available_vehicles"] == 2
    assert payload["diagnostics"]["order_count"] == 2


def test_smart_dispatch_generates_plans_from_shipment_facts(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    response = client.post(
        "/api/dispatch/smart",
        headers=headers,
        json={
            "algorithm": "balanced",
            "limit": 10,
            "max_orders_per_vehicle": 2,
            "use_precise_distance": False,
            "weights": {"cost": 0.4, "time": 0.3, "satisfaction": 0.3},
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data_source"] == "shipment_fact"
    assert payload["summary"]["assigned_orders"] == 2
    assert payload["summary"]["total_orders_assigned"] == 2
    assert payload["plans"]
    plan = payload["plans"][0]
    assert plan["route_legs"]
    assert plan["route_legs"][0]["path_source"] == "dispatch_order_origin_destination_leg"
    assert plan["route_legs"][0]["distance_source"] == "haversine_corrected"
    assert plan["route_truth"]["path_source"] == "dispatch_assignment_sequence"
    assert plan["route_truth"]["leg_count"] >= 1
    assert plan["route_truth"]["distance_source_counts"]["haversine_corrected"] >= 1
    assert plan["route_truth"]["provider_status_counts"]["degraded"] >= 1
    assert payload["summary"]["route_truth"]["leg_count"] == 2
    assert payload["route_truth"]["estimated_leg_count"] == 2
    assert payload["diagnostics"]["order_count"] == 2
    assert payload["ai_shadow"]["mode"] == "shadow"
    assert payload["distance_source"] == "haversine_corrected"
    assert payload["authenticity_level"].startswith("B")
    assert payload["scenario_id"]


def test_apply_persisted_dispatch_scenario(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    ).get_json()

    response = client.post(
        "/api/dispatch/apply",
        headers=headers,
        json={"scenario_id": preview["scenario_id"]},
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["assignments_updated"] == 2

    detail = client.get(f"/api/dispatch/scenarios/{preview['scenario_id']}", headers=headers)
    scenario = detail.get_json()["scenario"]
    assert scenario["status"] == "applied"
    assert len(scenario["assignments"]) == 2
    assert scenario["assignments"][0]["diagnostics"]["route_truth"]["leg_count"] >= 1
    assert (
        scenario["assignments"][0]["diagnostics"]["route_truth"]["path_source"]
        == "dispatch_assignment_sequence"
    )


def test_dispatch_preview_can_skip_persisting_scenario(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False, "persist": False},
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["summary"]["assigned_orders"] == 2
    assert "scenario_id" not in payload
    assert "scenario_code" not in payload


def test_dispatch_learning_dataset_from_persisted_scenarios(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.get(
        f"/api/dispatch/learning-dataset?scenario_id={scenario_id}&scenario_limit=10&row_limit=10",
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["dataset_version"] == "rl_shadow_dataset_v1"
    assert payload["mode"] == "shadow_training_dataset"
    assert payload["readiness"]["ready"] is True
    assert payload["summary"]["row_count"] == 2
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["summary"]["route_truth_rows"] == 2
    assert payload["summary"]["distance_source_counts"]["haversine_corrected"] >= 1
    assert payload["target_definition"]["task"] == "dispatch_policy_shadow_ranking"
    assert payload["feature_schema"]
    row = payload["rows"][0]
    assert row["action"]["assign_to_vehicle_id"]
    assert row["scenario_id"] == scenario_id
    assert row["features"]["route_leg_count"] >= 1
    assert row["target"]["target_type"] == "offline_proxy_reward"
    assert row["truth"]["path_source"] == "dispatch_assignment_sequence"
    assert row["truth"]["route_truth"]["path_source"] == "dispatch_assignment_sequence"


def test_dispatch_policy_scorer_compares_shadow_policies(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.get(
        f"/api/dispatch/policy-scorer?scenario_id={scenario_id}&scenario_limit=10&row_limit=10&top_k=2",
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_policy_comparison"
    assert payload["scorer_version"] == "dispatch_policy_shadow_scorer_v1"
    assert payload["dataset_version"] == "rl_shadow_dataset_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["readiness"]["policy_rows"] == 2
    assert payload["best_policy"]["deployable"] is True
    policies = {item["policy_id"]: item for item in payload["policies"]}
    assert "historical_solver_order" in policies
    assert "reward_oracle_upper_bound" in policies
    assert policies["reward_oracle_upper_bound"]["deployable"] is False
    assert policies["historical_solver_order"]["top_k"] == 2
    assert isinstance(policies["historical_solver_order"]["top_actions"], list)
    assert "score_delta_vs_baseline" in policies["balanced_shadow"]
    assert "No business state is mutated" in payload["target_definition"]["scoring_note"]


def test_dispatch_reward_model_trains_shadow_baseline(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.get(
        f"/api/dispatch/reward-model?scenario_id={scenario_id}&scenario_limit=10&row_limit=10&test_ratio=0.5",
        headers=headers,
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_model_training"
    assert payload["model_version"] == "linear_reward_ranker_v1"
    assert payload["dataset_version"] == "rl_shadow_dataset_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["readiness"]["ready"] is True
    assert payload["readiness"]["row_count"] == 2
    assert payload["readiness"]["train_rows"] == 1
    assert payload["readiness"]["test_rows"] == 1
    assert payload["metrics"]["all"]["sample_count"] == 2
    assert "rank_accuracy" in payload["metrics"]
    assert payload["model"]["type"] == "standardized_linear_regression"
    assert payload["model"]["feature_importance"]
    assert payload["predictions"]
    assert payload["truth_contract"]["reward_model"] == "offline shadow learning baseline only"
    assert "shadow ranking only" in payload["model"]["training_note"]


def test_dispatch_redispatch_simulator_scores_disruption_shadow(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]
    detail = client.get(f"/api/dispatch/scenarios/{scenario_id}", headers=headers).get_json()
    vehicle_id = detail["scenario"]["assignments"][0]["vehicle_id"]

    response = client.post(
        "/api/dispatch/redispatch-simulator",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "top_k": 2,
            "delay_minutes": 30,
            "unavailable_vehicle_ids": [vehicle_id],
            "cost_multiplier": 1.2,
            "provider_degradation": True,
            "reliability_drop": 0.2,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_disruption_simulation"
    assert payload["simulator_version"] == "dynamic_redispatch_shadow_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["disruption"]["unavailable_vehicle_ids"] == [vehicle_id]
    assert payload["summary"]["row_count"] == 2
    assert payload["summary"]["held_for_reassignment"] >= 1
    assert payload["summary"]["impacted_assignments"] >= 1
    assert payload["best_policy"]["deployable"] is True
    assert payload["policies"]
    assert payload["impacts"]
    assert any("vehicle_unavailable" in item["impact_flags"] for item in payload["impacts"])
    assert payload["truth_contract"]["mutation"] == "none"
    assert "solver" in payload["summary"]["simulation_note"]


def test_dispatch_redispatch_profiles_use_real_anomaly_signals(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db

        fact = ShipmentFact.query.filter_by(external_order_id="ORD-DISPATCH-001").first()
        fact.standard_status = "exception"
        fact.exception_reason = "unit test carrier disruption"
        fact.freight = 50000
        db.session.commit()

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.post(
        "/api/dispatch/redispatch-profiles",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "anomaly_limit": 20,
            "tasks": ["status", "cost", "delay", "node_congestion"],
            "use_ml": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_disruption_profile_generation"
    assert payload["profile_version"] == "anomaly_driven_redispatch_profiles_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["readiness"]["profile_count"] >= 1
    assert payload["anomaly_summary"]["anomaly_count"] >= 1
    assert payload["profiles"]
    balanced = payload["profiles"][0]
    assert balanced["params"]["top_k"] == 10
    assert "provider_degradation" in balanced["params"]
    assert balanced["evidence"]["anomaly_count"] >= 1
    assert payload["truth_contract"]["mutation"] == "none"


def test_dispatch_redispatch_scenario_generator_scores_historical_disruptions(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db

        fact = ShipmentFact.query.filter_by(external_order_id="ORD-DISPATCH-001").first()
        fact.standard_status = "exception"
        fact.exception_reason = "unit test historical disruption"
        fact.freight = 50000
        db.session.commit()

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.post(
        "/api/dispatch/redispatch-scenario-generator",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "top_k": 2,
            "anomaly_limit": 20,
            "tasks": ["status", "cost", "delay", "node_congestion"],
            "use_ml": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_historical_disruption_generation"
    assert payload["generator_version"] == "historical_disruption_scenario_generator_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["summary"]["generated_scenario_count"] >= 3
    assert payload["summary"]["anomaly_count"] >= 1
    assert payload["readiness"]["generated_scenario_count"] == payload["summary"]["generated_scenario_count"]
    first = payload["generated_scenarios"][0]
    assert first["training_use"] == "dql_dqn_shadow_episode_preset"
    assert first["simulation_summary"]["row_count"] >= 1
    assert first["best_policy"]["deployable"] is True
    assert "simulation_provider_status" in first
    assert payload["truth_contract"]["mutation"] == "none"
    assert "shadow" in payload["truth_contract"]["dql_dqn_boundary"]


def test_dispatch_rl_shadow_runner_builds_q_shadow_benchmark(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db

        fact = ShipmentFact.query.filter_by(external_order_id="ORD-DISPATCH-001").first()
        fact.standard_status = "exception"
        fact.exception_reason = "unit test rl shadow disruption"
        fact.freight = 50000
        db.session.commit()

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.post(
        "/api/dispatch/rl-shadow-runner",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "top_k": 2,
            "anomaly_limit": 20,
            "tasks": ["status", "cost", "delay", "node_congestion"],
            "use_ml": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_rl_evaluation"
    assert payload["runner_version"] == "offline_q_shadow_runner_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["readiness"]["episode_count"] >= 1
    assert payload["summary"]["episode_count"] >= 1
    assert payload["summary"]["action_count"] >= 1
    assert payload["summary"]["deployable"] is False
    assert payload["action_space"]
    assert payload["q_table"]
    assert payload["episode_results"]
    assert payload["episode_results"][0]["selected_action"]
    assert "policy_scores" in payload["episode_results"][0]
    assert payload["truth_contract"]["mutation"] == "none"
    assert payload["truth_contract"]["deployable"] is False
    assert "not a deployed" in payload["truth_contract"]["rl_shadow_runner"]


def test_dispatch_fitted_q_shadow_model_trains_offline_approximator(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db

        fact = ShipmentFact.query.filter_by(external_order_id="ORD-DISPATCH-001").first()
        fact.standard_status = "exception"
        fact.exception_reason = "unit test fitted q shadow disruption"
        fact.freight = 50000
        db.session.commit()

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.post(
        "/api/dispatch/fitted-q-shadow-model",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "top_k": 2,
            "test_ratio": 0.25,
            "anomaly_limit": 20,
            "tasks": ["status", "cost", "delay", "node_congestion"],
            "use_ml": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_fitted_q_shadow_training"
    assert payload["model_version"] == "linear_fitted_q_shadow_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["readiness"]["sample_count"] >= 2
    assert payload["summary"]["deployable"] is False
    assert payload["feature_names"]
    assert payload["metrics"]["all"]["sample_count"] >= 2
    assert "rank_accuracy" in payload["metrics"]
    assert payload["model"]["type"] == "standardized_linear_q_approximator"
    assert payload["model"]["feature_importance"]
    assert payload["recommendations"]
    assert payload["predictions"]
    assert payload["truth_contract"]["mutation"] == "none"
    assert payload["truth_contract"]["deployable"] is False
    assert "fitted-Q" in payload["truth_contract"]["fitted_q_shadow_model"]


def test_dispatch_shadow_benchmark_unifies_ai_shadow_scorecard(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db

        fact = ShipmentFact.query.filter_by(external_order_id="ORD-DISPATCH-001").first()
        fact.standard_status = "exception"
        fact.exception_reason = "unit test shadow benchmark disruption"
        fact.freight = 50000
        db.session.commit()

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.post(
        "/api/dispatch/shadow-benchmark",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "top_k": 2,
            "test_ratio": 0.25,
            "anomaly_limit": 20,
            "tasks": ["status", "cost", "delay", "node_congestion"],
            "use_ml": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_readiness_scorecard"
    assert payload["benchmark_version"] == "dispatch_ai_shadow_benchmark_v1"
    assert payload["filters"]["scenario_ids"] == [scenario_id]
    assert payload["summary"]["component_count"] >= 6
    assert payload["summary"]["gate_count"] >= 6
    assert payload["summary"]["readiness_score"] > 0
    assert payload["summary"]["deployable"] is False
    component_ids = {component["component_id"] for component in payload["components"]}
    assert "learning_dataset" in component_ids
    assert "fitted_q_shadow_model" in component_ids
    gate_ids = {gate["gate_id"] for gate in payload["gates"]}
    assert "non_mutating_shadow_contract" in gate_ids
    assert payload["truth_contract"]["mutation"] == "none"
    assert payload["truth_contract"]["deployable"] is False
    assert "scorecard" in payload["truth_contract"]["shadow_benchmark"]


def test_dispatch_shadow_benchmark_snapshot_exports_audit_payload(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db

        fact = ShipmentFact.query.filter_by(external_order_id="ORD-DISPATCH-001").first()
        fact.standard_status = "exception"
        fact.exception_reason = "unit test shadow snapshot disruption"
        fact.freight = 50000
        db.session.commit()

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert preview.status_code == 200, preview.get_json()
    scenario_id = preview.get_json()["scenario_id"]

    response = client.post(
        "/api/dispatch/shadow-benchmark/snapshot",
        headers=headers,
        json={
            "scenario_id": scenario_id,
            "scenario_limit": 1,
            "row_limit": 10,
            "top_k": 2,
            "test_ratio": 0.25,
            "anomaly_limit": 20,
            "tasks": ["status", "cost", "delay", "node_congestion"],
            "use_ml": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["mode"] == "offline_shadow_benchmark_snapshot_export"
    assert payload["snapshot_version"] == "dispatch_ai_shadow_snapshot_v1"
    assert payload["snapshot"]["snapshot_id"].startswith("dispatch-shadow-")
    assert len(payload["snapshot"]["content_hash"]) == 64
    assert payload["snapshot"]["hash_algorithm"] == "sha256"
    assert payload["snapshot"]["storage"] == "not_persisted"
    assert payload["snapshot"]["mutation"] == "none"
    assert payload["snapshot"]["replay_request"]["endpoint"] == "/api/dispatch/shadow-benchmark"
    assert payload["scorecard"]["benchmark_version"] == "dispatch_ai_shadow_benchmark_v1"
    assert payload["truth_contract"]["mutation"] == "none"
    assert payload["truth_contract"]["deployable"] is False
    assert payload["truth_contract"]["content_hash"] == payload["snapshot"]["content_hash"]


def test_dispatch_capacity_shortage_is_explained(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import Vehicle, db

        Vehicle.query.update({"load_capacity": 1, "volume_capacity": 1})
        db.session.commit()

    response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["assigned_orders"] == 0
    assert payload["summary"]["unassigned_orders"] == 2
    assert payload["unassigned_orders"][0]["reason"]
    assert payload["diagnostics"]["reason_counts"]["capacity_shortage_weight"] == 1


def test_auto_data_source_prefers_shipment_facts_over_legacy_orders(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import Node, Order, db

        pickup = Node(
            name="旧仓库",
            code="LEG-WH",
            type="warehouse",
            city="北京",
            address="北京市旧仓库",
            longitude=116.4074,
            latitude=39.9042,
            status="active",
        )
        delivery = Node(
            name="旧客户",
            code="LEG-CUST",
            type="customer",
            city="天津",
            address="天津市旧客户",
            longitude=117.2,
            latitude=39.1333,
            status="active",
        )
        db.session.add_all([pickup, delivery])
        db.session.flush()
        db.session.add(
            Order(
                order_number="LEGACY-DISPATCH-001",
                customer_name="旧订单客户",
                pickup_node_id=pickup.id,
                delivery_node_id=delivery.id,
                weight=1,
                volume=2,
                priority="normal",
                status="pending",
            )
        )
        db.session.commit()

    auto_response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert auto_response.status_code == 200
    auto_payload = auto_response.get_json()
    assert auto_payload["data_source"] == "shipment_fact"
    assert auto_payload["summary"]["total_orders"] == 2

    legacy_response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "data_source": "orders", "use_precise_distance": False},
    )
    assert legacy_response.status_code == 200
    legacy_payload = legacy_response.get_json()
    assert legacy_payload["data_source"] == "orders"
    assert legacy_payload["summary"]["total_orders"] == 1
