import importlib
import os
import sys
import time
from datetime import datetime, timedelta


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def _build_app(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")
    _clear_logistics_prometheus_collectors()

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    importlib.import_module("app")
    from app import create_app
    from app.models import DataImportBatch, ShipmentFact, Vehicle, db

    app = create_app("testing")

    with app.app_context():
        db.create_all()
        batch = DataImportBatch(
            dataset_source="unit-test",
            source_filename="prediction.csv",
            quality_status="ready",
            raw_record_count=14,
            fact_record_count=14,
        )
        db.session.add(batch)
        db.session.flush()

        base = datetime(2026, 5, 1, 8, 0, 0)
        facts = []
        for idx in range(14):
            shipped_at = base + timedelta(days=idx)
            transit_hours = 16 + (idx % 4) * 3
            eta_hours = 18 + (idx % 3) * 2
            weight = 800 + idx * 25
            freight = 120 + idx * 8
            facts.append(
                ShipmentFact(
                    batch_id=batch.id,
                    external_shipment_id=f"SHP-PRED-{idx:03d}",
                    external_order_id=f"ORD-PRED-{idx:03d}",
                    origin_city_std="广州" if idx % 2 == 0 else "深圳",
                    destination_city_std="上海" if idx % 3 else "杭州",
                    origin_lng=113.2644,
                    origin_lat=23.1291,
                    destination_lng=121.4737 if idx % 3 else 120.1551,
                    destination_lat=31.2304 if idx % 3 else 30.2741,
                    geo_status="resolved",
                    cargo_type="普货" if idx % 2 == 0 else "冷链",
                    logistics_company="测试物流",
                    transport_mode="truck",
                    freight=freight,
                    insurance_amount=freight * 2,
                    standard_status="delivered",
                    shipped_at=shipped_at,
                    eta_at=shipped_at + timedelta(hours=eta_hours),
                    delivered_at=shipped_at + timedelta(hours=transit_hours),
                    signed_at=shipped_at + timedelta(hours=transit_hours + 1),
                    weight_kg=weight,
                    volume_m3=2 + idx * 0.1,
                )
            )
        db.session.add_all(facts)
        db.session.add_all(
            [
                Vehicle(
                    plate_number="粤A-PRED-01",
                    vehicle_type="truck",
                    load_capacity=1.2,
                    volume_capacity=8,
                    capacity=1.2,
                    status="available",
                ),
                Vehicle(
                    plate_number="粤A-PRED-02",
                    vehicle_type="truck",
                    load_capacity=1.4,
                    volume_capacity=9,
                    capacity=1.4,
                    status="available",
                ),
            ]
        )
        db.session.commit()

    return app


def _clear_logistics_prometheus_collectors():
    try:
        from prometheus_client import REGISTRY
    except Exception:
        return

    collector_to_names = getattr(REGISTRY, "_collector_to_names", {})
    for collector, names in list(collector_to_names.items()):
        if any(str(name).startswith("logistics_") for name in names):
            try:
                REGISTRY.unregister(collector)
            except KeyError:
                pass


def test_shipment_prediction_health_uses_real_facts(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().dataset_health()

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["provider_status"] == "ok"
    assert result["fallback_reason"] is None
    assert result["summary"]["total_records"] == 14
    assert result["readiness"]["demand"]["ready"] is True
    assert result["readiness"]["eta"]["ready"] is True
    assert result["readiness"]["delay"]["ready"] is True
    assert result["readiness"]["cost"]["ready"] is True
    assert result["truth_contract"]["path_source"] == "not_route_geometry_prediction_features"


def test_shipment_prediction_baselines_return_metrics_for_phase3_targets(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().evaluate_baselines(
            {"tasks": ["demand", "eta", "delay", "cost"], "horizon_days": 3}
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "explainable_baseline"
    assert set(result["results"]) == {"demand", "eta", "delay", "cost"}

    for task, item in result["results"].items():
        assert item["provider_status"] == "ok", task
        assert item["model_stage"] == "phase3_baseline"
        assert item["data_source"] == "shipment_fact"
        assert item["metrics"]["sample_count"] > 0
        assert item["metrics"]["mae"] is not None
        assert item["metrics"]["rmse"] is not None
        assert item["metrics"]["mape"] is not None

    assert result["results"]["demand"]["forecast"]
    assert result["results"]["delay"]["classification_summary"]["delay_threshold_minutes"] == 15


def test_shipment_prediction_baselines_stream_column_projections(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from sqlalchemy.orm import Query

        from app.services.shipment_prediction_service import ShipmentPredictionService

        def fail_all(self):
            raise AssertionError("baseline evaluation must not load full ORM result sets with Query.all()")

        monkeypatch.setattr(Query, "all", fail_all)

        result = ShipmentPredictionService().evaluate_baselines(
            {"tasks": ["demand", "eta", "delay", "cost"], "horizon_days": 3, "limit": 100}
        )

    assert result["success"] is True
    assert result["provider_status"] == "ok"
    assert result["results"]["eta"]["metrics"]["sample_count"] > 0
    assert result["results"]["delay"]["metrics"]["sample_count"] > 0
    assert result["results"]["cost"]["metrics"]["sample_count"] > 0


def test_shipment_prediction_feature_dataset_exposes_schema_and_targets(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        eta_dataset = ShipmentPredictionService().build_feature_dataset(
            {"task": "eta", "row_limit": 5}
        )
        demand_dataset = ShipmentPredictionService().build_feature_dataset(
            {"task": "demand", "row_limit": 5, "city": "上海"}
        )

    assert eta_dataset["success"] is True
    assert eta_dataset["dataset_name"] == "shipment_fact_eta_features_v1"
    assert eta_dataset["target_definition"]["target_name"] == "actual_transit_hours"
    assert eta_dataset["row_count"] == 14
    assert eta_dataset["returned_rows"] == 5
    assert eta_dataset["truncated"] is True
    assert any(field["name"] == "distance_km" for field in eta_dataset["feature_schema"])
    assert eta_dataset["rows"][0]["target_name"] == "actual_transit_hours"
    assert eta_dataset["summary"]["category_cardinality"]["origin_city"] >= 2

    assert demand_dataset["success"] is True
    assert demand_dataset["target_definition"]["target_name"] == "daily_order_count"
    assert demand_dataset["rows"][0]["city_scope"] == "上海"
    assert any(field["role"] == "time_index" for field in demand_dataset["feature_schema"])


def test_shipment_prediction_time_series_benchmark_reports_dl_readiness(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().evaluate_time_series_benchmark(
            {"task": "demand", "horizon_days": 5, "test_days": 4, "sequence_length": 7}
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "time_series_baseline_benchmark"
    assert result["benchmark_version"] == "shipment_fact_time_series_benchmark_v1"
    assert result["series_summary"]["daily_points"] == 14
    assert result["backtest"]["test_points"] == 4
    assert result["backtest"]["best_model"]["metrics"]["sample_count"] == 4
    assert {item["model_id"] for item in result["backtest"]["models"]} >= {
        "weekday_mean",
        "moving_average_7",
        "seasonal_naive_7",
        "exponential_smoothing_alpha_0_35",
    }
    assert len(result["forecast"]) == 5
    assert result["deep_learning_readiness"]["candidate_models"] == [
        "LSTM",
        "GRU",
        "TemporalFusionTransformer",
    ]
    assert result["deep_learning_readiness"]["training_windows"] == 7
    assert result["truth_contract"]["business_mutation"] == "none"


def test_demand_forecast_explains_insufficient_daily_history_and_hourly_fallback(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.models import ShipmentFact, db
        from app.services.shipment_prediction_service import ShipmentPredictionService

        base = datetime(2026, 5, 1, 0, 0, 0)
        for idx, fact in enumerate(ShipmentFact.query.order_by(ShipmentFact.id.asc())):
            fact.shipped_at = base + timedelta(hours=idx)
        db.session.commit()

        service = ShipmentPredictionService()
        daily = service.forecast_demand(days=3, limit=100, time_granularity="daily")
        auto = service.forecast_demand(days=1, limit=100, time_granularity="auto")

    assert daily["success"] is True
    assert daily["provider_status"] == "degraded"
    assert daily["forecast_status"] == "insufficient_history"
    assert daily["forecast"] == []
    assert daily["series_summary"]["distinct_dates"] == 1

    assert auto["success"] is True
    assert auto["provider_status"] == "degraded"
    assert auto["forecast_status"] == "degraded"
    assert auto["fallback_reason"] == "DEMAND_DAILY_POINTS_INSUFFICIENT_USING_HOURLY_FALLBACK"
    assert auto["time_granularity"] == "hourly"
    assert auto["forecast"]
    assert auto["series_summary"]["time_bucket_points"] >= 14


def test_prediction_timeline_audit_reports_time_field_coverage(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().timeline_audit({"sequence_length": 7})

    assert result["success"] is True
    assert result["audit_version"] == "shipment_timeline_audit_v1"
    assert result["fields"]["shipped_at"]["distinct_dates"] == 14
    assert result["time_fields"]["shipped_at"]["distinct_dates"] == 14
    assert result["recommended"]["series_source"] == "shipped_at"
    assert result["recommended"]["time_granularity"] == "daily"
    assert result["recommended_granularity"] == "daily"
    assert result["training_window_count"] == result["recommended"]["training_windows"]
    assert result["truth_contract"]["timeline_audit"].startswith("real shipment_facts")


def test_prediction_job_returns_quickly_and_completes_shadow_status(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        service = ShipmentPredictionService()
        started = time.perf_counter()
        created = service.create_prediction_job(
            {
                "task": "demand",
                "model_family": "lstm",
                "runtime_profile": "full",
                "limit": 100,
                "horizon_days": 2,
                "test_days": 2,
                "sequence_length": 7,
            },
            app=app,
        )
        elapsed = time.perf_counter() - started
        job_id = created["job"]["job_id"]

    assert created["success"] is True
    assert created["job_id"] == job_id
    assert created["status"] in {"queued", "running"}
    assert created["model_family"] == "lstm"
    assert elapsed < 2.0

    deadline = time.time() + 5
    status = {}
    while time.time() < deadline:
        status = service.prediction_job_status(job_id)
        if status.get("job", {}).get("status") in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert status["success"] is True
    assert status["job"]["status"] == "completed"
    assert status["job"]["result"]["model_stage"] == "deep_shadow_job"
    assert status["job"]["result"]["training_contract"]["business_mutation"] == "none"


def test_shipment_prediction_capacity_gap_forecast_uses_vehicle_capacity(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().forecast_capacity_gap(
            {"horizon_days": 4, "test_days": 3, "sequence_length": 7, "limit": 100}
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "capacity_gap_forecast"
    assert result["forecast_version"] == "shipment_capacity_gap_v1"
    assert result["fleet_capacity"]["available_vehicles"] == 2
    assert result["fleet_capacity"]["total_capacity_weight_kg"] == 2600
    assert len(result["forecast"]) == 4
    assert result["forecast"][0]["capacity_weight_kg"] == 2600
    assert result["models"]["weight"]["metrics"]["sample_count"] > 0
    assert result["deep_learning_readiness"]["candidate_models"] == [
        "LSTM",
        "GRU",
        "TemporalFusionTransformer",
    ]
    assert result["truth_contract"]["business_mutation"] == "none"


def test_shipment_prediction_cost_volatility_forecast_uses_real_freight(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().forecast_cost_volatility(
            {
                "horizon_days": 4,
                "test_days": 3,
                "sequence_length": 7,
                "volatility_window": 5,
                "limit": 100,
            }
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "cost_volatility_forecast"
    assert result["forecast_version"] == "shipment_cost_volatility_v1"
    assert result["summary"]["daily_points"] == 14
    assert len(result["forecast"]) == 4
    assert result["forecast"][0]["predicted_unit_cost_per_kg"] > 0
    assert result["models"]["unit_cost_per_kg"]["metrics"]["sample_count"] > 0
    assert result["deep_learning_readiness"]["candidate_models"] == [
        "LSTM",
        "GRU",
        "TemporalFusionTransformer",
    ]
    assert result["truth_contract"]["business_mutation"] == "none"


def test_shipment_prediction_scorecard_aggregates_readiness(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().prediction_scorecard(
            {"horizon_days": 4, "test_days": 3, "sequence_length": 7, "limit": 100}
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "prediction_readiness_scorecard"
    assert result["scorecard_version"] == "shipment_prediction_scorecard_v1"
    assert result["summary"]["readiness_score"] > 0
    assert {component["id"] for component in result["components"]} >= {
        "data_readiness",
        "baseline_coverage",
        "time_series_readiness",
        "capacity_planning",
        "cost_volatility",
    }
    assert {gate["id"] for gate in result["gates"]} >= {
        "real_data_available",
        "baseline_metrics_available",
        "shadow_boundary_preserved",
    }
    assert result["evidence"]["dataset"]["total_records"] == 14
    assert result["truth_contract"]["business_mutation"] == "none"


def test_shipment_prediction_scorecard_tolerates_insufficient_time_series_backtest(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        result = ShipmentPredictionService().prediction_scorecard(
            {"horizon_days": 4, "test_days": 3, "sequence_length": 7, "limit": 1}
        )

    assert result["success"] is True
    assert result["provider_status"] in {"ok", "degraded"}
    assert result["evidence"]["time_series"]["best_model"] is None
    assert result["truth_contract"]["business_mutation"] == "none"


def test_shipment_prediction_lightweight_model_train_and_evaluate(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_prediction_service import ShipmentPredictionService

        service = ShipmentPredictionService()
        train_result = service.train_model(
            {"task": "eta", "limit": 100, "hash_buckets": 8, "test_ratio": 0.25}
        )
        model_id = train_result["model"]["model_id"]
        status = service.model_status()
        evaluation = service.evaluate_model({"task": "eta", "model_id": model_id, "row_limit": 4})
        prediction = service.predict_with_model({"task": "eta", "model_id": model_id, "row_limit": 3})

    assert train_result["success"] is True
    assert train_result["data_source"] == "shipment_fact"
    assert train_result["model"]["model_type"] == "ridge_feature_hashing_regressor_v1"
    assert train_result["model"]["training_summary"]["row_count"] == 14
    assert train_result["model"]["metrics"]["sample_count"] > 0
    assert train_result["model"]["feature_importance"]
    assert train_result["training_contract"]["business_mutation"] == "none"

    assert status["model_count"] == 1
    assert status["latest_by_task"]["eta"]["model_id"] == model_id

    assert evaluation["provider_status"] == "ok"
    assert evaluation["evaluation"]["metrics"]["sample_count"] == 14
    assert len(evaluation["evaluation"]["prediction_rows"]) == 4
    assert prediction["prediction"]["mutation"] == "none"
    assert len(prediction["prediction"]["rows"]) == 3


def test_ai_prediction_routes_are_available_when_legacy_ml_routes_disabled(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    route_rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/ml/train" not in route_rules
    assert "/api/ai-prediction/health" in route_rules
    assert "/api/ai-prediction/timeline/audit" in route_rules
    assert "/api/ai-prediction/jobs/<job_id>" in route_rules
    assert "/api/ai-prediction/model/train" in route_rules

    health = client.get("/api/ai-prediction/health")
    timeline = client.get("/api/ai-prediction/timeline/audit")
    evaluate = client.post(
        "/api/ai-prediction/baseline/evaluate",
        json={"tasks": ["demand", "eta"], "horizon_days": 2},
    )
    forecast = client.get("/api/ai-prediction/demand/forecast?days=2&city=上海&time_granularity=auto")
    time_series = client.post(
        "/api/ai-prediction/time-series/benchmark",
        json={"task": "demand", "horizon_days": 3, "test_days": 3, "sequence_length": 7},
    )
    capacity_gap = client.post(
        "/api/ai-prediction/capacity-gap/forecast",
        json={"horizon_days": 3, "test_days": 3, "sequence_length": 7},
    )
    cost_volatility = client.post(
        "/api/ai-prediction/cost-volatility/forecast",
        json={"horizon_days": 3, "test_days": 3, "sequence_length": 7},
    )
    scorecard = client.post(
        "/api/ai-prediction/scorecard",
        json={"horizon_days": 3, "test_days": 3, "sequence_length": 7},
    )
    training_dataset = client.post(
        "/api/ai-prediction/training-dataset",
        json={"task": "cost", "row_limit": 3},
    )
    train_model = client.post(
        "/api/ai-prediction/model/train",
        json={"task": "delay", "hash_buckets": 8, "test_ratio": 0.25},
    )
    model_id = train_model.get_json()["model"]["model_id"]
    model_status = client.get("/api/ai-prediction/model/status")
    model_evaluate = client.post(
        "/api/ai-prediction/model/evaluate",
        json={"task": "delay", "model_id": model_id, "row_limit": 2},
    )
    model_predict = client.post(
        "/api/ai-prediction/model/predict",
        json={"task": "delay", "model_id": model_id, "row_limit": 2},
    )
    clamped = client.post(
        "/api/ai-prediction/baseline/evaluate",
        json={
            "tasks": ["demand"],
            "runtime_profile": "interactive",
            "limit": 50000,
        },
    )

    assert health.status_code == 200
    assert health.get_json()["summary"]["total_records"] == 14
    assert timeline.status_code == 200
    assert timeline.get_json()["fields"]["shipped_at"]["distinct_dates"] == 14
    assert evaluate.status_code == 200
    assert evaluate.get_json()["results"]["eta"]["metrics"]["sample_count"] > 0
    assert forecast.status_code == 200
    assert forecast.get_json()["task"] == "demand"
    assert forecast.get_json()["forecast_status"] == "ok"
    assert len(forecast.get_json()["forecast"]) == 2
    assert time_series.status_code == 200
    assert time_series.get_json()["backtest"]["best_model"]["metrics"]["sample_count"] == 3
    assert time_series.get_json()["deep_learning_readiness"]["deployment_boundary"] == "shadow_evaluation_only_until_backtests_beat_classical_baselines"
    assert capacity_gap.status_code == 200
    assert capacity_gap.get_json()["fleet_capacity"]["available_vehicles"] == 2
    assert len(capacity_gap.get_json()["forecast"]) == 3
    assert cost_volatility.status_code == 200
    assert cost_volatility.get_json()["summary"]["daily_points"] == 14
    assert len(cost_volatility.get_json()["forecast"]) == 3
    assert scorecard.status_code == 200
    assert scorecard.get_json()["summary"]["readiness_score"] > 0
    assert scorecard.get_json()["truth_contract"]["business_mutation"] == "none"
    assert training_dataset.status_code == 200
    assert training_dataset.get_json()["dataset_name"] == "shipment_fact_cost_features_v1"
    assert training_dataset.get_json()["returned_rows"] == 3
    assert train_model.status_code == 200
    assert train_model.get_json()["model"]["task"] == "delay"
    assert model_status.status_code == 200
    assert model_status.get_json()["model_count"] >= 1
    assert model_evaluate.status_code == 200
    assert len(model_evaluate.get_json()["evaluation"]["prediction_rows"]) == 2
    assert model_predict.status_code == 200
    assert model_predict.get_json()["prediction"]["mutation"] == "none"
    assert clamped.status_code == 200
    assert clamped.get_json()["runtime_profile"] == "interactive"
    assert clamped.get_json()["runtime_limits"]["limit"] == 5000
