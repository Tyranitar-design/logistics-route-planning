import importlib
import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _build_app(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")
    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app
    from app.models import db

    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


def _case_graphml_path(name: str) -> Path:
    path = Path(__file__).resolve().parents[1] / "var" / "test_food_supply_osm" / name
    if path.exists():
        path.unlink()
    return path


def test_food_supply_adapter_reads_real_case_workbook():
    from app.services.food_supply_case_service import FoodSupplyCaseService

    service = FoodSupplyCaseService()
    dataset = service.load_dataset()

    assert dataset["case_id"] == "peach-supply-chain-2023"
    assert len(dataset["nodes"]["orchards"]) == 5
    assert len(dataset["nodes"]["facilities"]) == 3
    assert len(dataset["nodes"]["b_stores"]) >= 40
    assert dataset["demands"]["b2b"]["row_count"] >= 600
    assert dataset["demands"]["c2c"]["row_count"] >= 20000
    assert dataset["resources"]["vehicles"]
    assert dataset["resources"]["drones"][0]["payload_kg"] == 10
    assert dataset["diagnostics"]["coordinate_system"] == "WGS84/EPSG:4326"


def test_food_supply_import_apply_persists_case_tables(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    validate_response = client.post("/api/cases/food-supply/import/validate", json={})
    validate_payload = validate_response.get_json()
    assert validate_response.status_code == 200
    assert validate_payload["success"] is True
    assert validate_payload["summary"]["orchard_count"] == 5

    apply_response = client.post("/api/cases/food-supply/import/apply", json={"persist": True})
    apply_payload = apply_response.get_json()
    assert apply_response.status_code == 200
    assert apply_payload["success"] is True
    assert apply_payload["persisted"] is True
    assert apply_payload["summary"]["node_count"] >= 50
    assert apply_payload["postgis_geometry"]["provider_status"] in {"ok", "skipped", "degraded"}
    assert apply_payload["postgis_geometry"]["fallback_reason"] in {None, "POSTGIS_REQUIRES_POSTGRESQL_RUNTIME"} or apply_payload["postgis_geometry"]["fallback_reason"].startswith("POSTGIS_GEOMETRY_MATERIALIZATION_FAILED")

    summary_response = client.get("/api/cases/food-supply/summary")
    summary_payload = summary_response.get_json()
    assert summary_response.status_code == 200
    assert summary_payload["success"] is True
    assert summary_payload["summary"]["node_count"] >= 50
    assert summary_payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_network_dispatch_and_scenario_are_safe(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    client.post("/api/cases/food-supply/import/apply", json={"persist": True})

    network_response = client.get("/api/cases/food-supply/network")
    network_payload = network_response.get_json()
    assert network_response.status_code == 200
    assert network_payload["success"] is True
    assert network_payload["distance_source"] in {
        "case_postgis_coordinates",
        "case_database_coordinates",
        "case_excel_coordinates",
    }
    assert network_payload["authenticity_level"] in {"B", "C"}

    dispatch_response = client.post(
        "/api/cases/food-supply/optimize/dispatch",
        json={"wave_date": "06-01", "store_limit": 8, "persist": False},
    )
    dispatch_payload = dispatch_response.get_json()
    assert dispatch_response.status_code == 200
    assert dispatch_payload["success"] is True
    assert dispatch_payload["summary"]["assigned_orders"] > 0
    assert dispatch_payload["constraint_validation"]["capacity_violations"] == 0
    assert dispatch_payload["truth_contract"]["business_mutation"] == "none"

    scenario_response = client.post(
        "/api/cases/food-supply/scenarios",
        json={"name": "食品案例 dry run", "persist": False, "summary": {"orders": 8}},
    )
    scenario_payload = scenario_response.get_json()
    assert scenario_response.status_code == 200
    assert scenario_payload["success"] is True
    assert scenario_payload["persisted"] is False
    assert scenario_payload["business_mutation"] == "none"


def test_food_supply_solver_compare_reports_capabilities_and_metrics(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/solver-compare",
        json={"wave_date": "06-01", "store_limit": 8, "max_facilities": 2},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver"] == "case_solver_comparison"
    assert payload["summary"]["compared_solvers"] >= 4
    assert payload["summary"]["recommended_solver"]
    assert payload["constraint_validation"]["invalid_recommendations"] == 0
    assert payload["truth_contract"]["rl_policy_mode"] == "shadow_rerank_only"

    solver_ids = {row["solver_id"] for row in payload["solver_results"]}
    assert {"greedy_capacity_dispatch", "greedy_network_design", "deterministic_pareto"}.issubset(solver_ids)
    assert any(row["solver_id"] in {"gurobi", "cplex_docplex", "ortools", "pymoo"} for row in payload["solver_results"])
    for row in payload["solver_results"]:
        assert "provider_status" in row
        assert "metrics" in row
        assert row["hard_constraints_owner"] == "solver_layer"


def test_food_supply_distance_matrix_reports_provider_modes(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/distance-matrix/build",
        json={"limit": 8, "matrix_mode": "osm", "persist": False},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["matrix_mode"] == "osm"
    assert payload["summary"]["pair_count"] > 0
    assert payload["provider_status"] in {"ok", "degraded"}
    for row in payload["pairs"][:5]:
        assert row["distance_source"] in {"osm_network", "haversine_fallback"}
        assert row["path_source"] in {"osm_graph", "local_case_baseline"}
        assert row["authenticity_level"] in {"B", "C"}
        assert "fallback_reason" in row


def test_food_supply_amap_matrix_uses_provider_success(monkeypatch):
    app = _build_app(monkeypatch)

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy=0):
            results = []
            for origin_idx, _origin in enumerate(origins, start=1):
                for dest_idx, _dest in enumerate(destinations, start=1):
                    results.append(
                        {
                            "origin_id": str(origin_idx),
                            "dest_id": str(dest_idx),
                            "distance": 1200 + origin_idx * 100 + dest_idx,
                            "duration": 300 + origin_idx * 10 + dest_idx,
                        }
                    )
            return {
                "success": True,
                "provider": "amap",
                "provider_status": "ok",
                "degraded": False,
                "fallback_reason": None,
                "results": results,
            }

    from app.services import food_supply_case_service as module
    from app.services.food_supply_case_service import FoodSupplyCaseService

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)

    with app.app_context():
        payload = FoodSupplyCaseService().build_distance_matrix(limit=4, matrix_mode="amap", persist=False)

    assert payload["success"] is True
    assert payload["provider_status"] == "ok"
    assert payload["distance_source"] == "amap_driving"
    assert payload["path_source"] == "amap_distance_matrix"
    assert payload["authenticity_level"] == "A"
    assert payload["diagnostics"]["source_summary"]["amap_driving"] == payload["summary"]["pair_count"]
    for row in payload["pairs"][:3]:
        assert row["distance_source"] == "amap_driving"
        assert row["path_source"] == "amap_distance_matrix"
        assert row["fallback_reason"] is None


def test_food_supply_provider_failure_falls_back_per_pair(monkeypatch):
    app = _build_app(monkeypatch)

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy=0):
            return {
                "success": True,
                "provider": "amap",
                "provider_status": "degraded",
                "degraded": True,
                "fallback_reason": "AMAP_DNS_TIMEOUT",
                "results": [
                    {
                        "origin_id": str(origin_idx),
                        "dest_id": str(dest_idx),
                        "distance": -1,
                        "duration": -1,
                        "degraded": True,
                    }
                    for origin_idx, _origin in enumerate(origins, start=1)
                    for dest_idx, _dest in enumerate(destinations, start=1)
                ],
            }

    from app.services import food_supply_case_service as module
    from app.services.food_supply_case_service import FoodSupplyCaseService

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)

    with app.app_context():
        payload = FoodSupplyCaseService().build_distance_matrix(limit=4, matrix_mode="amap", persist=False)

    assert payload["provider_status"] == "degraded"
    assert payload["fallback_reason"] == "AMAP_DNS_TIMEOUT"
    assert payload["distance_source"] == "haversine_fallback"
    assert payload["diagnostics"]["source_summary"]["haversine_fallback"] == payload["summary"]["pair_count"]
    for row in payload["pairs"][:3]:
        assert row["distance_source"] == "haversine_fallback"
        assert row["path_source"] == "local_case_baseline"
        assert row["fallback_reason"] == "AMAP_DNS_TIMEOUT"


def test_food_supply_tianditu_matrix_uses_provider_success(monkeypatch):
    app = _build_app(monkeypatch)

    class FakeTiandituService:
        def distance_matrix(self, origins, destinations, strategy="0"):
            return {
                "success": True,
                "provider": "tianditu",
                "provider_status": "ok",
                "degraded": False,
                "fallback_reason": None,
                "results": [
                    {
                        "origin_id": origin_idx,
                        "dest_id": dest_idx,
                        "distance": 2400 + origin_idx * 100 + dest_idx,
                        "duration": 600 + origin_idx * 10 + dest_idx,
                        "success": True,
                    }
                    for origin_idx, _origin in enumerate(origins)
                    for dest_idx, _dest in enumerate(destinations)
                ],
            }

    from app.services import food_supply_case_service as module
    from app.services.food_supply_case_service import FoodSupplyCaseService

    monkeypatch.setattr(module, "get_tianditu_service", lambda: FakeTiandituService(), raising=False)

    with app.app_context():
        payload = FoodSupplyCaseService().build_distance_matrix(limit=4, matrix_mode="tianditu", persist=False)

    assert payload["provider_status"] == "ok"
    assert payload["distance_source"] == "tianditu_driving"
    assert payload["path_source"] == "tianditu_route_matrix"
    assert payload["authenticity_level"] == "A"
    assert payload["diagnostics"]["source_summary"]["tianditu_driving"] == payload["summary"]["pair_count"]


def test_food_supply_osm_matrix_uses_graph_provenance(monkeypatch):
    pytest.importorskip("osmnx")
    app = _build_app(monkeypatch)

    import networkx as nx

    from app.services.food_supply_case_service import FoodSupplyCaseService

    fake_nodes = [
        {"node_code": "A", "name": "A", "node_type": "facility", "lon": 113.0, "lat": 23.0},
        {"node_code": "B", "name": "B", "node_type": "b_store", "lon": 113.01, "lat": 23.0},
        {"node_code": "C", "name": "C", "node_type": "b_store", "lon": 113.02, "lat": 23.0},
    ]
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"
    graph.add_node(1, x=113.0, y=23.0)
    graph.add_node(2, x=113.01, y=23.0)
    graph.add_node(3, x=113.02, y=23.0)
    for u, v, length in [(1, 2, 1000), (2, 1, 1000), (2, 3, 1100), (3, 2, 1100), (1, 3, 2300), (3, 1, 2300)]:
        graph.add_edge(u, v, length=length)

    service = FoodSupplyCaseService()
    monkeypatch.setattr(service, "_nodes_from_db", lambda: fake_nodes)
    monkeypatch.setattr(service, "_load_osm_graph", lambda nodes: graph, raising=False)

    with app.app_context():
        payload = service.build_distance_matrix(limit=3, matrix_mode="osm", persist=False)

    assert payload["provider_status"] == "ok"
    assert payload["distance_source"] == "osm_network"
    assert payload["path_source"] == "osm_graph"
    assert payload["authenticity_level"] == "B"
    assert payload["diagnostics"]["source_summary"]["osm_network"] == payload["summary"]["pair_count"]
    assert payload["pairs"][0]["distance_source"] == "osm_network"
    assert payload["pairs"][0]["fallback_reason"] is None


def test_food_supply_osm_cache_status_and_baseline_build(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    cache_path = _case_graphml_path("food-case-baseline.graphml")
    monkeypatch.setenv("FOOD_SUPPLY_OSM_GRAPHML", str(cache_path))

    status_response = client.get("/api/cases/food-supply/osm-cache/status")
    status_payload = status_response.get_json()
    assert status_response.status_code == 200
    assert status_payload["success"] is True
    assert status_payload["exists"] is False
    assert status_payload["provider_status"] == "degraded"
    assert status_payload["fallback_reason"] == "OSM_GRAPHML_CACHE_MISSING"
    assert status_payload["cache_path"] == str(cache_path)

    build_response = client.post(
        "/api/cases/food-supply/osm-cache/build",
        json={"mode": "case-baseline", "limit": 8, "overwrite": True},
    )
    build_payload = build_response.get_json()
    assert build_response.status_code == 200
    assert build_payload["success"] is True
    if build_payload["provider_status"] != "ok" and "Permission" in str(build_payload.get("fallback_reason")):
        pytest.skip(f"GraphML cache path is not writable in this sandbox: {build_payload.get('fallback_reason')}")
    assert build_payload["provider_status"] == "ok"
    assert build_payload["cache_kind"] == "case_baseline_graphml"
    assert build_payload["authenticity_level"] == "C"
    assert Path(build_payload["cache_path"]).exists()
    assert build_payload["summary"]["node_count"] >= 2
    assert build_payload["summary"]["edge_count"] >= 2

    status_after = client.get("/api/cases/food-supply/osm-cache/status").get_json()
    assert status_after["exists"] is True
    assert status_after["cache_kind"] == "case_baseline_graphml"


def test_food_supply_route_preview_uses_osm_graphml_cache(monkeypatch):
    pytest.importorskip("osmnx")
    app = _build_app(monkeypatch)
    client = app.test_client()

    cache_path = _case_graphml_path("food-case-preview.graphml")
    monkeypatch.setenv("FOOD_SUPPLY_OSM_GRAPHML", str(cache_path))
    build_payload = client.post("/api/cases/food-supply/osm-cache/build", json={"mode": "case-baseline", "limit": 8, "overwrite": True}).get_json()
    if build_payload.get("provider_status") != "ok" and "Permission" in str(build_payload.get("fallback_reason")):
        pytest.skip(f"GraphML cache path is not writable in this sandbox: {build_payload.get('fallback_reason')}")

    response = client.post(
        "/api/cases/food-supply/routes/preview",
        json={"source_code": "FAC-1", "target_code": "BSTORE-001", "provider": "osm"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["route"]["provider"] == "osm"
    assert payload["route"]["path_source"] in {"case_graphml_baseline", "osm_graphml_cache"}
    assert payload["route"]["distance_source"] in {"haversine_fallback", "osm_network"}
    assert payload["route"]["authenticity_level"] in {"B", "C"}
    assert len(payload["route"]["polyline"]) >= 2
    assert {"lon", "lat"}.issubset(payload["route"]["polyline"][0])
    assert payload["route"]["fallback_reason"] in {None, "CASE_BASELINE_GRAPHML_NOT_REAL_OSM"}


def test_food_supply_route_preview_provider_success(monkeypatch):
    app = _build_app(monkeypatch)

    class FakeAmapRoute:
        success = True
        distance = 1800
        duration = 420
        polyline = [[113.0, 23.0], [113.006, 23.002], [113.012, 23.004]]
        provider_status = "ok"
        degraded = False
        fallback_reason = None

    class FakeAmapService:
        def driving_route(self, origin, destination, waypoints=None, strategy=0, show_traffic=True):
            return FakeAmapRoute()

    from app.services import food_supply_case_service as module

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/routes/preview",
        json={"source_code": "FAC-1", "target_code": "BSTORE-001", "provider": "amap"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["provider_status"] == "ok"
    assert payload["route"]["provider"] == "amap"
    assert payload["route"]["distance_source"] == "amap_driving"
    assert payload["route"]["path_source"] == "amap_route_polyline"
    assert payload["route"]["authenticity_level"] == "A"
    assert payload["route"]["fallback_reason"] is None
    assert len(payload["route"]["polyline"]) == 3


def test_food_supply_route_compare_returns_provider_rows(monkeypatch):
    app = _build_app(monkeypatch)
    cache_path = _case_graphml_path("food-case-compare.graphml")
    monkeypatch.setenv("FOOD_SUPPLY_OSM_GRAPHML", str(cache_path))

    class FakeAmapRoute:
        success = True
        distance = 1800
        duration = 420
        polyline = [[113.0, 23.0], [113.006, 23.002], [113.012, 23.004]]
        provider_status = "ok"
        degraded = False
        fallback_reason = None

    class FakeAmapService:
        def driving_route(self, origin, destination, waypoints=None, strategy=0, show_traffic=True):
            return FakeAmapRoute()

    from app.services import food_supply_case_service as module

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)
    client = app.test_client()
    client.post("/api/cases/food-supply/osm-cache/build", json={"mode": "case-baseline", "limit": 8, "overwrite": True})

    response = client.post(
        "/api/cases/food-supply/routes/compare",
        json={
            "source_code": "FAC-1",
            "target_code": "BSTORE-001",
            "providers": ["amap", "osm", "haversine"],
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["summary"]["provider_count"] == 3
    assert payload["summary"]["ok_count"] >= 1
    assert payload["summary"]["geometry_count"] >= 1
    assert payload["summary"]["best_distance_km"] > 0
    assert payload["summary"]["best_quality_score"] >= payload["summary"]["recommended_score"] > 0
    assert payload["summary"]["average_quality_score"] > 0
    assert payload["summary"]["recommendation_reason"] == "PREFERRED_NON_DEGRADED_AB_PROVIDER_GEOMETRY"
    providers = {row["provider"] for row in payload["routes"]}
    assert providers == {"amap", "osm", "haversine"}
    amap_row = next(row for row in payload["routes"] if row["provider"] == "amap")
    assert amap_row["distance_source"] == "amap_driving"
    assert amap_row["path_source"] == "amap_route_polyline"
    assert amap_row["authenticity_level"] == "A"
    assert amap_row["quality_score"] >= 90
    assert amap_row["quality_band"] == "high"
    assert {"authenticity", "provider_status", "geometry", "fallback", "relative_distance"}.issubset(amap_row["score_breakdown"])
    assert len(amap_row["polyline"]) == 3
    assert payload["recommended_route"]["provider"] == "amap"
    assert payload["recommended_route"]["quality_score"] == payload["summary"]["recommended_score"]
    for row in payload["routes"]:
        assert {"distance_source", "path_source", "authenticity_level", "fallback_reason", "quality_score", "score_breakdown"}.issubset(row)


def test_food_supply_route_compare_cache_and_history(monkeypatch):
    app = _build_app(monkeypatch)
    cache_path = _case_graphml_path("food-case-cache-history.graphml")
    monkeypatch.setenv("FOOD_SUPPLY_OSM_GRAPHML", str(cache_path))

    class FakeAmapRoute:
        success = True
        distance = 2000
        duration = 480
        polyline = [[113.0, 23.0], [113.01, 23.01]]
        provider_status = "ok"
        degraded = False
        fallback_reason = None

    class FakeAmapService:
        calls = 0

        def driving_route(self, origin, destination, waypoints=None, strategy=0, show_traffic=True):
            FakeAmapService.calls += 1
            return FakeAmapRoute()

    from app.services import food_supply_case_service as module

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)
    client = app.test_client()
    client.post("/api/cases/food-supply/osm-cache/build", json={"mode": "case-baseline", "limit": 8, "overwrite": True})
    payload = {
        "source_code": "FAC-1",
        "target_code": "BSTORE-001",
        "providers": ["amap", "haversine"],
        "use_cache": True,
        "persist": True,
    }

    first = client.post("/api/cases/food-supply/routes/compare", json=payload)
    first_payload = first.get_json()
    second = client.post("/api/cases/food-supply/routes/compare", json=payload)
    second_payload = second.get_json()
    history = client.get("/api/cases/food-supply/routes/compare/history?limit=5")
    history_payload = history.get_json()

    assert first.status_code == 200
    assert first_payload["cache_status"] == "stored"
    assert first_payload["cache_entry_id"] > 0
    assert first_payload["summary"]["recommended_score"] > 0
    assert second.status_code == 200
    assert second_payload["cache_status"] == "hit"
    assert second_payload["cache_entry_id"] == first_payload["cache_entry_id"]
    assert FakeAmapService.calls == 1
    assert history.status_code == 200
    assert history_payload["success"] is True
    assert history_payload["summary"]["history_count"] >= 1
    latest = history_payload["history"][0]
    assert latest["source_code"] == "FAC-1"
    assert latest["target_code"] == "BSTORE-001"
    assert latest["recommended_provider"] == first_payload["summary"]["recommended_provider"]
    assert latest["recommended_score"] == first_payload["summary"]["recommended_score"]
    assert latest["summary"]["cache_entry_id"] == first_payload["cache_entry_id"]
    assert history_payload["cache_contract"]["table"] == "case_food_route_comparisons"
    assert history_payload["cache_contract"]["raw_fact_mutation"] is False


def test_food_supply_milp_network_design_contract(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/network-design",
        json={"solver_mode": "milp", "max_facilities": 2, "store_limit": 8, "persist": False},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver_family"] in {"gurobi_milp", "cplex_docplex_milp", "greedy_cflp"}
    assert payload["execution_mode"] in {"exact_milp", "greedy_fallback"}
    assert payload["constraint_validation"]["throughput_violations"] == 0
    assert payload["constraint_validation"]["unassigned_customers"] == 0
    if payload["execution_mode"] == "exact_milp":
        assert payload["provider_status"] == "ok"
        assert payload["solver_plan"]["exact_solver"]["status"] in {"OPTIMAL", "FEASIBLE"}
    else:
        assert payload["fallback_reason"]


def test_food_supply_ortools_dispatch_contract(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/dispatch",
        json={"solver_mode": "ortools", "wave_date": "06-01", "store_limit": 8, "persist": False},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver_family"] in {"ortools_cvrp", "greedy_capacity_dispatch"}
    assert payload["execution_mode"] in {"vrp_solver", "greedy_fallback"}
    assert payload["constraint_validation"]["capacity_violations"] == 0
    assert payload["constraint_validation"]["duplicate_assignment_violations"] == 0
    assert "metaheuristics" in payload
    assert any(row["solver_family"] in {"particle_swarm", "pyvrp"} for row in payload["metaheuristics"])


def test_food_supply_pyvrp_dispatch_contract(monkeypatch):
    pytest.importorskip("pyvrp")
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/dispatch",
        json={"solver_mode": "pyvrp", "wave_date": "06-01", "store_limit": 8, "persist": False},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver_family"] == "pyvrp_cvrp"
    assert payload["execution_mode"] == "hybrid_genetic_vrp"
    assert payload["constraint_validation"]["capacity_violations"] == 0
    assert payload["constraint_validation"]["duplicate_assignment_violations"] == 0
    assert payload["summary"]["assigned_orders"] > 0
    assert payload["summary"]["pyvrp_iterations"] >= 0


def test_food_supply_pymoo_nsga_pareto_contract(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/pareto",
        json={"algorithm_family": "nsga", "store_limit": 8, "max_facilities": 2},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver_family"] in {"pymoo_nsga", "deterministic_pareto"}
    assert payload["execution_mode"] in {"multi_objective_search", "deterministic_fallback"}
    assert len(payload["pareto_front"]) >= 4
    for point in payload["pareto_front"][:4]:
        assert {"cost", "carbon_kg", "freshness_risk", "service_level"}.issubset(point)


def test_food_supply_advanced_solver_compare_executes_when_requested(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/solver-compare",
        json={"advanced_mode": True, "wave_date": "06-01", "store_limit": 8, "max_facilities": 2},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["summary"]["advanced_mode"] is True
    executed_families = {row.get("solver_family") for row in payload["solver_results"] if row.get("execution_mode") not in {None, "readiness_only"}}
    assert executed_families & {"gurobi_milp", "cplex_docplex_milp", "greedy_cflp"}
    assert executed_families & {"ortools_cvrp", "greedy_capacity_dispatch"}
    assert executed_families & {"pyvrp_cvrp"}
    assert executed_families & {"pymoo_nsga", "deterministic_pareto"}
    for row in payload["solver_results"]:
        assert "solver_family" in row
        assert "execution_mode" in row


# ---------------------------------------------------------------------------
# C 端地理编码 + 区域聚类 + 无人机最后一公里（enhance-food-supply-c2c-geocoding-drone-lastmile）
# ---------------------------------------------------------------------------


class _FakeAmapGeocode:
    """模拟高德 geocode 成功结果，字段对齐 AmapGeocodeResult。"""

    def __init__(self, lon=117.27, lat=31.86, success=True, fallback_reason=None):
        self.success = success
        self.longitude = lon
        self.latitude = lat
        self.formatted_address = "安徽省合肥市包河区"
        self.province = "安徽省"
        self.city = "合肥市"
        self.district = "包河区"
        self.provider = "amap"
        self.provider_status = "ok" if success else "degraded"
        self.degraded = not success
        self.fallback_reason = fallback_reason
        self.authenticity = "高德地理编码"
        self.error = fallback_reason


class _FakeAmapGeocodeService:
    """按地址前缀返回成功/失败，用于验证 provider 降级与缓存。"""

    def __init__(self, fail_all=False, fail_keywords=("未知",)):
        self.fail_all = fail_all
        self.fail_keywords = fail_keywords
        self.calls = 0

    def geocode(self, address, city=None):
        self.calls += 1
        if self.fail_all or any(kw in str(address) for kw in self.fail_keywords):
            return _FakeAmapGeocode(success=False, fallback_reason="AMAP_GEOCODE_EMPTY")
        return _FakeAmapGeocode()


def test_food_supply_c2c_clusters_returns_bounded_centroids(monkeypatch):
    """C 端 22259 行必须聚合成有界区域中心，并保留地址维度与真实性契约。"""
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.get("/api/cases/food-supply/c2c/clusters")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    clusters = payload["clusters"]
    assert len(clusters) >= 5  # 至少 5 个区域中心
    assert len(clusters) <= 80  # 有界上限
    for cluster in clusters:
        assert {"region", "orders", "weight_kg", "boxes", "date_labels"}.issubset(cluster)
        assert "cluster_authenticity_level" in cluster
        assert cluster["cluster_authenticity_level"] in {"A", "B", "C"}
    assert payload["data_source"] == "case_excel_workbooks"
    assert payload["authenticity_level"] in {"A", "B", "C"}
    assert payload["truth_contract"]["raw_fact_mutation"] is False
    # 摘要必须报告聚合前后规模，证明 22k 行被降维
    assert payload["summary"]["raw_row_count"] >= 20000
    assert payload["summary"]["cluster_count"] == len(clusters)


def test_food_supply_c2c_geocode_provider_success_and_cache(monkeypatch):
    """高德成功返回 A 级坐标，第二次走缓存且不再调用 provider。"""
    app = _build_app(monkeypatch)
    from app.services import food_supply_case_service as module

    fake = _FakeAmapGeocodeService()
    monkeypatch.setattr(module, "get_amap_service", lambda: fake, raising=False)

    client = app.test_client()
    first = client.post(
        "/api/cases/food-supply/c2c/geocode",
        json={"geocode_limit": 5, "persist": True, "provider": "amap"},
    )
    first_payload = first.get_json()
    assert first.status_code == 200
    assert first_payload["success"] is True
    assert first_payload["summary"]["resolved"] >= 1
    assert first_payload["summary"]["requested"] >= 1
    for row in first_payload["rows"][:3]:
        if row.get("needs_geocoding"):
            continue
        assert row["distance_source"] == "amap_geocode"
        assert row["path_source"] == "amap_geocode"
        assert row["authenticity_level"] == "A"
        assert row["longitude"] is not None and row["latitude"] is not None

    first_calls = fake.calls
    second = client.post(
        "/api/cases/food-supply/c2c/geocode",
        json={"geocode_limit": 5, "persist": False, "provider": "amap", "use_cache": True},
    )
    second_payload = second.get_json()
    assert second.status_code == 200
    assert second_payload["cache_status"] == "hit"
    # 缓存命中后不应再调用 provider
    assert fake.calls == first_calls
    assert second_payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_c2c_geocode_provider_failure_uses_local_fallback(monkeypatch):
    """provider 失败时使用本地区域中心兜底，标 C 级，绝不造假坐标。"""
    app = _build_app(monkeypatch)
    from app.services import food_supply_case_service as module

    fake = _FakeAmapGeocodeService(fail_all=True)
    monkeypatch.setattr(module, "get_amap_service", lambda: fake, raising=False)

    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/c2c/geocode",
        json={"geocode_limit": 8, "persist": False, "provider": "amap"},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    # 失败行必须显式标记 needs_geocoding 或使用本地兜底，且 authenticity 不得为 A
    assert payload["summary"]["resolved"] + payload["summary"]["needs_geocoding"] == payload["summary"]["requested"]
    for row in payload["rows"]:
        if row.get("needs_geocoding"):
            assert row["authenticity_level"] == "C"
            assert row["fallback_reason"]
        else:
            assert row["authenticity_level"] in {"B", "C"}
            assert row["distance_source"] != "amap_geocode"


def test_food_supply_c2c_geocode_bounded_limit_enforced(monkeypatch):
    """geocode_limit 必须被硬上限裁剪，避免打爆 provider 配额。"""
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/c2c/geocode",
        json={"geocode_limit": 99999, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["diagnostics"]["effective_geocode_limit"] <= 200
    assert payload["diagnostics"]["requested_geocode_limit"] == 99999


def test_food_supply_c2c_geocode_status_reports_cache(monkeypatch):
    """geocode/status 必须返回缓存规模、provider 就绪态与真实性契约。"""
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.get("/api/cases/food-supply/c2c/geocode/status")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert {"cache_count", "provider_status", "distance_source"}.issubset(payload)
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_last_mile_drone_feasibility_and_mode_comparison(monkeypatch):
    """无人机最后一公里必须按载重+续航筛选可行簇，并输出三模式对比。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    client.post("/api/cases/food-supply/import/apply", json={"persist": True})

    response = client.post(
        "/api/cases/food-supply/optimize/last-mile",
        json={"cluster_limit": 12, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver"] == "case_last_mile_comparison"
    assert "clusters" in payload
    assert len(payload["clusters"]) >= 1
    for cluster in payload["clusters"]:
        assert {"cluster", "modes"}.issubset(cluster)
        modes = {m["mode"] for m in cluster["modes"]}
        assert {"drone", "vehicle", "hybrid"}.issubset(modes)
        for mode in cluster["modes"]:
            assert {"cost", "duration_min", "carbon_kg", "freshness_risk", "service_level", "feasible", "fallback_reason"}.issubset(mode)
    assert payload["constraint_validation"]["payload_violations"] is not None
    assert payload["constraint_validation"]["range_violations"] is not None
    assert payload["truth_contract"]["business_mutation"] == "none"


def test_food_supply_last_mile_recommendation_feasible_only(monkeypatch):
    """推荐模式必须可行；无人机不可行的簇不得被推荐为 drone。"""
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/last-mile",
        json={"cluster_limit": 10, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    for cluster in payload["clusters"]:
        recommended = cluster.get("recommended_mode")
        if recommended is None:
            continue
        recommended_row = next(m for m in cluster["modes"] if m["mode"] == recommended)
        assert recommended_row["feasible"] is True
        assert recommended_row["fallback_reason"] is None
    assert payload["summary"]["recommendation_reason"]


def test_food_supply_last_mile_truth_contract_isolated(monkeypatch):
    """最后一公里持久化只写案例表，不污染生产事实。"""
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/api/cases/food-supply/optimize/last-mile",
        json={"cluster_limit": 8, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    contract = payload["truth_contract"]
    assert contract["raw_fact_mutation"] is False
    assert contract["shipment_facts_mutated"] is False
    assert contract["orders_or_vehicles_mutated"] is False
    assert contract["rl_policy_mode"] == "shadow_rerank_only"


def test_food_supply_dataset_cache_memoizes_excel_parse(monkeypatch):
    """进程级缓存必须避免每次请求重读 22k 行 Excel。"""
    from app.services.food_supply_case_service import FoodSupplyCaseService

    service = FoodSupplyCaseService()
    calls = {"count": 0}
    original_rows = service._rows

    def counting_rows(path, min_row=1):
        calls["count"] += 1
        return original_rows(path, min_row=min_row)

    monkeypatch.setattr(service, "_rows", counting_rows)

    app = _build_app(monkeypatch)
    with app.app_context():
        first = service.load_dataset()
        calls_after_first = calls["count"]
        second = service.load_dataset()
        calls_after_second = calls["count"]
    assert first is not None and second is not None
    # 第二次应命中进程级缓存，不再重新解析所有工作簿
    assert calls_after_second == calls_after_first


# ---------------------------------------------------------------------------
# Phase 1: 果园 92 天时序 + 需求预测 + 采摘波次（orchard-forecast-multimodal-freshness）
# ---------------------------------------------------------------------------


def test_food_supply_orchard_timeseries_reads_92_days(monkeypatch):
    """果园 92 天逐日箱数必须完整读取，并保留日期/星期用于季节性分析。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.get("/api/cases/food-supply/orchards/timeseries")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    series = payload["series"]
    assert len(series) == 5
    for orchard in series:
        assert {"orchard_code", "name", "daily", "total_boxes", "peak_day_boxes"}.issubset(orchard)
        assert len(orchard["daily"]) == 92
        assert orchard["daily"][0]["date"] == "06-01"
        assert orchard["daily"][-1]["date"] == "08-31"
        assert "weekday" in orchard["daily"][0]
    assert payload["summary"]["day_count"] == 92
    assert payload["summary"]["orchard_count"] == 5
    assert payload["summary"]["season_total_boxes"] > 0
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_orchard_forecast_reports_waves_and_model_stage(monkeypatch):
    """预测必须输出 model_stage、逐日预测与保鲜感知的采摘波次。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.get("/api/cases/food-supply/orchards/forecast?horizon=14&freshness_days=4")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["model_stage"]
    assert len(payload["forecast"]) == 5
    for orchard in payload["forecast"]:
        assert {"orchard_code", "forecast_daily", "trend", "harvest_waves"}.issubset(orchard)
        assert len(orchard["forecast_daily"]) == 14
        for wave in orchard["harvest_waves"]:
            assert wave["days"] <= 4  # 采摘波次必须尊重保鲜窗口
            assert wave["boxes"] >= 0
    assert payload["summary"]["horizon"] == 14
    assert payload["summary"]["freshness_days"] == 4
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_orchard_forecast_optuna_mode(monkeypatch):
    """use_optuna=true 时优先 optuna 调参 lightgbm；失败逐级降级。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.get("/api/cases/food-supply/orchards/forecast?horizon=7&freshness_days=4&use_optuna=1")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["model_stage"] in {"lightgbm_optuna_tuned", "lightgbm_trained", "deterministic_baseline"}
    for orchard in payload["forecast"]:
        assert len(orchard["forecast_daily"]) == 7
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_orchard_forecast_ml_mode_transparent(monkeypatch):
    """use_ml=true 时优先用 lightgbm 训练；库缺失/数据不足则透明降级 deterministic。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.get("/api/cases/food-supply/orchards/forecast?horizon=10&freshness_days=4&use_ml=1")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    # lightgbm 可用则 lightgbm_trained，否则降级 deterministic_baseline（都合法）
    assert payload["model_stage"] in {"lightgbm_trained", "deterministic_baseline"}
    for orchard in payload["forecast"]:
        assert {"orchard_code", "forecast_daily", "harvest_waves"}.issubset(orchard)
        assert len(orchard["forecast_daily"]) == 10
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_geocode_case_regions_upgrades_clusters(monkeypatch):
    """批量 geocoding region 名缓存后，c2c_clusters 读缓存升级 authenticity C→A。"""
    app = _build_app(monkeypatch)
    from app.services import food_supply_case_service as module

    fake = _FakeAmapGeocodeService()
    monkeypatch.setattr(module, "get_amap_service", lambda: fake, raising=False)
    client = app.test_client()

    resp = client.post("/api/cases/food-supply/c2c/geocode-regions", json={"persist": True, "provider": "amap"})
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["success"] is True
    assert payload["summary"]["resolved"] >= 1

    clusters_resp = client.get("/api/cases/food-supply/c2c/clusters")
    clusters_payload = clusters_resp.get_json()
    assert clusters_resp.status_code == 200
    a_count = sum(1 for c in clusters_payload["clusters"] if c.get("cluster_authenticity_level") == "A")
    assert a_count >= 1  # 缓存命中后 C→A 升级
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_geocode_poi_fallback(monkeypatch):
    """geocode 失败时 POI 搜索救回，缓存写入 + cluster 升级。"""
    app = _build_app(monkeypatch)
    from app.services import food_supply_case_service as module

    class _FakeAmapPoiService:
        def geocode(self, address, city=None):
            return _FakeAmapGeocode(success=False, fallback_reason="AMAP_GEOCODE_EMPTY")

        def place_text_search(self, keywords, city=None, types=None):
            return _FakeAmapGeocode(lon=117.31, lat=31.79)

    monkeypatch.setattr(module, "get_amap_service", lambda: _FakeAmapPoiService(), raising=False)
    client = app.test_client()
    resp = client.post("/api/cases/food-supply/c2c/geocode-regions", json={"persist": True, "provider": "amap"})
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["success"] is True
    assert payload["summary"]["resolved"] >= 1  # POI 救回
    # 验证有 amap_poi 来源
    poi_rows = [r for r in payload["rows"] if r.get("distance_source") == "amap_poi_search"]
    assert len(poi_rows) >= 1
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_business_kpi_reports_core_metrics(monkeypatch):
    """业务核心 KPI：SLA/覆盖率/产能/履约率必须可计算且合规。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.get("/api/cases/food-supply/business-kpi")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    kpi = payload["kpi"]
    assert {"sla", "coverage", "capacity_boxes", "fulfillment"}.issubset(kpi)
    assert 0 <= kpi["sla"] <= 1
    assert 0 <= kpi["coverage"] <= 1
    assert 0 <= kpi["fulfillment"] <= 1
    assert kpi["capacity_boxes"] > 0
    assert payload["truth_contract"]["raw_fact_mutation"] is False
    """use_ml=true 时优先用 lightgbm 训练；库缺失/数据不足则透明降级 deterministic。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.get("/api/cases/food-supply/orchards/forecast?horizon=10&freshness_days=4&use_ml=1")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    # lightgbm 可用则 lightgbm_trained，否则降级 deterministic_baseline（都合法）
    assert payload["model_stage"] in {"lightgbm_trained", "deterministic_baseline"}
    for orchard in payload["forecast"]:
        assert {"orchard_code", "forecast_daily", "harvest_waves"}.issubset(orchard)
        assert len(orchard["forecast_daily"]) == 10
    assert payload["truth_contract"]["raw_fact_mutation"] is False


# ---------------------------------------------------------------------------
# Phase 2: 货运机场 geocoding + 空运多式联运（orchard-forecast-multimodal-freshness）
# ---------------------------------------------------------------------------


def test_food_supply_freight_airports_have_local_centroid(monkeypatch):
    """货运机场必须用城市名匹配本地坐标库，未命中如实标 needs_geocoding，绝不造假。"""
    from app.services.food_supply_case_service import FoodSupplyCaseService

    service = FoodSupplyCaseService()
    dataset = service.load_dataset()
    freight = dataset["nodes"]["freight_airports"]
    assert len(freight) >= 20
    resolved = [a for a in freight if a.get("lon") is not None]
    needs = [a for a in freight if a.get("lon") is None]
    assert len(resolved) >= 10  # 大部分货运机场能匹配城市坐标
    for a in resolved:
        assert a["data_quality"] == "region_centroid_fallback"
        assert a["fallback_reason"] == "FREIGHT_AIRPORT_REGION_CENTROID_FALLBACK"
    for a in needs:
        assert a["data_quality"] == "needs_geocoding"


def test_food_supply_multimodal_compares_three_modes(monkeypatch):
    """多式联运必须输出 pure_road / air_plus_road / air_plus_drone 三模式对比。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    client.post("/api/cases/food-supply/import/apply", json={"persist": True})

    response = client.post("/api/cases/food-supply/optimize/multimodal", json={"cluster_limit": 6, "persist": False})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver"] == "case_multimodal_comparison"
    assert len(payload["clusters"]) >= 1
    for cluster in payload["clusters"]:
        modes = {m["mode"] for m in cluster["modes"]}
        assert {"pure_road", "air_plus_road", "air_plus_drone"}.issubset(modes)
        for m in cluster["modes"]:
            assert {"cost", "duration_min", "carbon_kg", "freshness_risk", "feasible", "fallback_reason"}.issubset(m)
    assert payload["constraint_validation"]["airport_handling_violations"] is not None
    assert payload["constraint_validation"]["freight_airports_geocoded"] >= 10
    assert payload["truth_contract"]["raw_fact_mutation"] is False


# ---------------------------------------------------------------------------
# Phase 5: 真实路网距离接入 last-mile（orchard-forecast-multimodal-freshness）
# ---------------------------------------------------------------------------


def test_food_supply_last_mile_accepts_amap_distance_mode(monkeypatch):
    """last-mile 支持 distance_mode=amap，provider 成功返回 A 级真实路网距离。"""
    app = _build_app(monkeypatch)
    from app.services import food_supply_case_service as module

    class FakeAmapDistanceService:
        def distance_matrix(self, origins, destinations, strategy=0):
            results = []
            for oi, _ in enumerate(origins, start=1):
                for di, _ in enumerate(destinations, start=1):
                    results.append({"origin_id": str(oi), "dest_id": str(di), "distance": 50000 + di * 1000, "duration": 3600 + di * 60})
            return {"success": True, "provider": "amap", "provider_status": "ok", "degraded": False, "fallback_reason": None, "results": results}

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapDistanceService(), raising=False)
    client = app.test_client()
    response = client.post("/api/cases/food-supply/optimize/last-mile", json={"cluster_limit": 4, "distance_mode": "amap", "persist": False})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["distance_mode"] == "amap"
    amap_used = any(c.get("distance_source") == "amap_driving" for c in payload["clusters"])
    assert amap_used
    assert payload["authenticity_level"] in {"A", "B"}
    assert payload["truth_contract"]["raw_fact_mutation"] is False


# ---------------------------------------------------------------------------
# Phase 3: 鲜度衰减模型 + VRPTW 时间窗（orchard-forecast-multimodal-freshness）
# ---------------------------------------------------------------------------


def test_food_supply_freshness_model_respects_temp_and_time(monkeypatch):
    """鲜度模型：冷链比常温鲜度高，30℃ 4 天衰减完。"""
    from app.services.food_supply_case_service import FoodSupplyCaseService

    svc = FoodSupplyCaseService()
    cold = svc._freshness_score(hours=10, temp_c=4, transfers=1)
    hot = svc._freshness_score(hours=10, temp_c=30, transfers=1)
    assert cold["freshness_score"] > hot["freshness_score"]
    long_hot = svc._freshness_score(hours=96, temp_c=30, transfers=0)
    assert long_hot["freshness_score"] <= 0.01  # 30℃ 4 天衰减完


def test_food_supply_dispatch_fresh_enforces_time_window(monkeypatch):
    """VRPTW：超 48h 时间窗的订单必须进 unassigned，绝不静默丢弃。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={"wave_date": "06-01", "store_limit": 8, "time_window_hours": 48, "freshness_window_days": 4, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["solver_family"] == "greedy_vrptw_fresh"
    for plan in payload["plans"]:
        assert "freshness_score" in plan
        assert 0 <= plan["freshness_score"] <= 1
        assert plan["within_time_window"] is True
    assert payload["constraint_validation"]["time_window_violations"] is not None
    assert payload["constraint_validation"]["unassigned_orders"] == len(payload["unassigned_orders"])
    assert payload["freshness_model"]["stage"]
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_dispatch_fresh_ortools_solver(monkeypatch):
    """solver_mode=ortools 时优先 OR-Tools VRPTW；库缺失/失败则降级 greedy。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={"wave_date": "06-01", "store_limit": 8, "solver_mode": "ortools", "time_window_hours": 48, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    # ortools 可用则 ortools_cvrptw，否则降级 greedy_vrptw_fresh
    assert payload["solver_family"] in {"ortools_cvrptw", "greedy_vrptw_fresh"}
    if payload["solver_family"] == "ortools_cvrptw":
        assert payload["execution_mode"] == "vrptw_solver"
        assert payload["solver"] == "case_vrptw_fresh_ortools"
        assert any(m["solver_family"] == "ortools" for m in payload["metaheuristics"])
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_dispatch_fresh_returns_replay_contract(monkeypatch):
    """调度响应必须包含前端可播放的轨迹帧与鲜度曲线，并标明估算路径真实性。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={"wave_date": "06-01", "store_limit": 6, "solver_mode": "greedy", "time_window_hours": 48, "persist": False},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["path_source"] == "case_vrptw_estimated_replay"
    assert payload["authenticity_level"] == "C"
    assert payload["animation"]["stage"] == "dispatch_solver_replay_v1"
    assert payload["animation"]["route_count"] == len(payload["plans"])
    assert payload["animation"]["frame_count"] >= payload["animation"]["route_count"] * 5
    assert payload["animation"]["fallback_reason"] == "VRPTW_USES_HAVERSINE_DISTANCE_NOT_REAL_ROAD"

    first_route = payload["animation"]["routes"][0]
    assert first_route["route_geometry"]["polyline_points"] == 2
    assert {"lon", "lat"}.issubset(first_route["frames"][0])
    assert first_route["frames"][0]["progress"] == 0
    assert first_route["frames"][-1]["progress"] == 1
    timeline = first_route["freshness_timeline"]
    assert timeline[0]["freshness_score"] >= timeline[-1]["freshness_score"]
    assert payload["plans"][0]["animation_frame_count"] == len(first_route["frames"])
    assert payload["plans"][0]["route_geometry"]["path_source"] == "case_vrptw_estimated_replay"
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_dispatch_fresh_returns_mathematical_model_contract(monkeypatch):
    """调度响应必须返回可审计的多目标 VRPTW 数学模型画像。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={
            "wave_date": "06-01",
            "store_limit": 6,
            "solver_mode": "greedy",
            "time_window_hours": 48,
            "persist": False,
            "objective_weights": {
                "cost": 0.4,
                "freshness": 0.3,
                "sla": 0.2,
                "balance": 0.1,
            },
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    model = payload["mathematical_model"]
    assert model["model_id"] == "food_fresh_vrptw_mo_v2"
    assert model["solver_family"] == payload["solver_family"]
    assert model["score_direction"] == "lower_is_better"
    assert abs(sum(model["weights"].values()) - 1.0) < 0.001
    assert {term["key"] for term in model["objective_terms"]} == {
        "transport_cost",
        "carbon",
        "freshness_risk",
        "sla_penalty",
        "load_balance",
    }
    assert model["current_solution"]["assigned_orders"] == payload["summary"]["assigned_orders"]
    assert model["current_solution"]["hard_constraint_ok"] is True
    assert [control["key"] for control in model["weight_controls"]] == [
        "transport_cost",
        "freshness_risk",
        "sla_penalty",
        "carbon",
        "load_balance",
    ]
    assert model["weight_sensitivity"]["stage"] == "same_solution_rescore"
    assert model["weight_sensitivity"]["front_quality"] == "scorecard_projection_not_solver_pareto"
    assert len(model["weight_sensitivity"]["score_points"]) >= 5
    assert any(point["scenario_id"] == "current_custom" for point in model["weight_sensitivity"]["score_points"])
    assert any(block["id"] == "capacity" and block["hard"] for block in model["constraint_blocks"])
    assert "x_{ijk}" in model["objective_latex"]
    assert any("不伪装" in note or "不宣称" in note for note in model["truth_notes"])
    assert any("重新求解" in note for note in model["truth_notes"])


def test_food_supply_dispatch_fresh_objective_weights_rescore_solution(monkeypatch):
    """成本/鲜度等权重变化必须影响 scorecard，同时不改变 truth contract 边界。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    base_payload = {
        "wave_date": "06-01",
        "store_limit": 6,
        "solver_mode": "greedy",
        "time_window_hours": 48,
        "persist": False,
    }

    cost_response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={
            **base_payload,
            "objective_weights": {
                "transport_cost": 1,
                "carbon": 0,
                "freshness_risk": 0,
                "sla_penalty": 0,
                "load_balance": 0,
            },
        },
    )
    freshness_response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={
            **base_payload,
            "objective_weights": {
                "transport_cost": 0,
                "carbon": 0,
                "freshness_risk": 1,
                "sla_penalty": 0,
                "load_balance": 0,
            },
        },
    )

    assert cost_response.status_code == 200
    assert freshness_response.status_code == 200
    cost_model = cost_response.get_json()["mathematical_model"]
    freshness_model = freshness_response.get_json()["mathematical_model"]

    assert cost_model["weights"]["transport_cost"] == 1
    assert freshness_model["weights"]["freshness_risk"] == 1
    assert cost_model["objective_score"] != freshness_model["objective_score"]
    assert cost_model["truth_notes"] == freshness_model["truth_notes"]
    assert cost_response.get_json()["truth_contract"]["rl_policy_mode"] == "shadow_rerank_only"


def test_food_supply_dispatch_fresh_can_upgrade_replay_to_amap_polyline(monkeypatch):
    """route_provider=amap 时，高德成功应升级为 A 级真实路网 polyline 回放。"""
    app = _build_app(monkeypatch)

    class FakeAmapRoute:
        success = True
        distance = 18800
        duration = 2040
        polyline = [[113.0, 23.0], [113.006, 23.002], [113.012, 23.006], [113.02, 23.01]]
        provider_status = "ok"
        degraded = False
        fallback_reason = None

    class FakeAmapService:
        calls = 0

        def driving_route(self, origin, destination, waypoints=None, strategy=0, show_traffic=True):
            FakeAmapService.calls += 1
            return FakeAmapRoute()

    from app.services import food_supply_case_service as module

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={
            "wave_date": "06-01",
            "store_limit": 4,
            "solver_mode": "greedy",
            "route_provider": "amap",
            "time_window_hours": 48,
            "persist": False,
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert FakeAmapService.calls == len(payload["plans"])
    assert payload["provider_status"] == "ok"
    assert payload["distance_source"] == "amap_driving"
    assert payload["path_source"] == "amap_route_polyline"
    assert payload["authenticity_level"] == "A"
    assert payload["fallback_reason"] is None
    assert payload["animation"]["path_source"] == "amap_route_polyline"
    assert payload["animation"]["authenticity_level"] == "A"
    assert payload["animation"]["provider_route_summary"]["exact_route_count"] == len(payload["plans"])

    first_plan = payload["plans"][0]
    assert first_plan["distance_source"] == "amap_driving"
    assert first_plan["path_source"] == "amap_route_polyline"
    assert first_plan["authenticity_level"] == "A"
    assert first_plan["distance_km"] == 18.8
    assert first_plan["duration_min"] == 34.0
    assert first_plan["route_geometry"]["polyline_points"] == 4
    assert first_plan["route_geometry"]["fallback_reason"] is None
    assert payload["animation"]["routes"][0]["frames"][-1]["distance_km"] == 18.8
    assert payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_dispatch_fresh_uses_amap_distance_matrix_when_polyline_unavailable(monkeypatch):
    """路线 polyline 不可用但距离矩阵成功时，调度回放应升级为 B 级真实距离 + 估算几何。"""
    app = _build_app(monkeypatch)

    class FakeAmapRouteFailure:
        success = False
        distance = 0
        duration = 0
        polyline = []
        provider_status = "degraded"
        degraded = True
        fallback_reason = "AMAP_ROUTE_TIMEOUT"

    class FakeAmapService:
        route_calls = 0
        matrix_calls = 0

        def driving_route(self, origin, destination, waypoints=None, strategy=0, show_traffic=True):
            FakeAmapService.route_calls += 1
            return FakeAmapRouteFailure()

        def distance_matrix(self, origins, destinations, strategy=0):
            FakeAmapService.matrix_calls += 1
            return {
                "success": True,
                "provider": "amap",
                "provider_status": "ok",
                "degraded": False,
                "fallback_reason": None,
                "results": [
                    {
                        "origin_id": "1",
                        "dest_id": str(dest_idx),
                        "distance": 16000 + dest_idx * 1000,
                        "duration": 1800 + dest_idx * 120,
                    }
                    for dest_idx, _dest in enumerate(destinations, start=1)
                ],
            }

    from app.services import food_supply_case_service as module

    monkeypatch.setattr(module, "get_amap_service", lambda: FakeAmapService(), raising=False)
    client = app.test_client()
    response = client.post(
        "/api/cases/food-supply/optimize/dispatch-fresh",
        json={
            "wave_date": "06-01",
            "store_limit": 4,
            "solver_mode": "greedy",
            "route_provider": "amap",
            "time_window_hours": 48,
            "persist": False,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert FakeAmapService.matrix_calls == 1
    assert FakeAmapService.route_calls == len(payload["plans"])
    assert payload["provider_status"] == "degraded"
    assert payload["distance_source"] == "amap_distance_matrix"
    assert payload["path_source"] == "estimated_polyline_with_amap_distance_matrix"
    assert payload["authenticity_level"] == "B"
    assert payload["fallback_reason"] == "DISPATCH_ROUTE_POLYLINE_UNAVAILABLE_DISTANCE_MATRIX_USED"
    assert payload["animation"]["provider_route_summary"]["upgrade_status"] == "matrix_distance"
    assert payload["animation"]["provider_route_summary"]["exact_route_count"] == 0
    assert payload["animation"]["provider_route_summary"]["matrix_distance_count"] == len(payload["plans"])
    assert payload["animation"]["provider_route_summary"]["fallback_route_count"] == 0

    first_plan = payload["plans"][0]
    assert first_plan["distance_source"] == "amap_distance_matrix"
    assert first_plan["path_source"] == "estimated_polyline_with_amap_distance_matrix"
    assert first_plan["authenticity_level"] == "B"
    assert first_plan["distance_km"] == 17.0
    assert first_plan["duration_min"] == 32.0
    assert first_plan["route_geometry"]["polyline_points"] == 2
    assert first_plan["route_geometry"]["provider_status"] == "degraded"
    assert first_plan["route_geometry"]["fallback_reason"] == "AMAP_ROUTE_TIMEOUT"
    assert payload["truth_contract"]["raw_fact_mutation"] is False


# ---------------------------------------------------------------------------
# Phase 6: 可追溯链路 + Phase 7: 场景持久化对比（orchard-forecast-multimodal-freshness）
# ---------------------------------------------------------------------------


def test_food_supply_trace_issue_and_lookup_round_trip(monkeypatch):
    """追溯码签发与 lookup 必须确定性还原采摘→包装→运输→签收链路。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    issue = client.post(
        "/api/cases/food-supply/trace/issue",
        json={"orchard_code": "ORCHARD-A", "wave_date": "09-01", "cluster_code": "CC-HEFEI"},
    )
    issue_payload = issue.get_json()
    assert issue.status_code == 200
    assert issue_payload["success"] is True
    trace_code = issue_payload["trace_code"]
    assert trace_code.startswith("FSC-TRACE-A-0901-HEFEI-")
    stages = issue_payload["stages"]
    assert [s["stage"] for s in stages] == ["harvest", "pack", "transport", "sign"]

    lookup = client.get(f"/api/cases/food-supply/trace/{trace_code}")
    lookup_payload = lookup.get_json()
    assert lookup.status_code == 200
    assert lookup_payload["success"] is True
    assert lookup_payload["found"] is True
    assert lookup_payload["orchard_code"] == "ORCHARD-A"
    assert len(lookup_payload["stages"]) == 4
    assert lookup_payload["truth_contract"]["raw_fact_mutation"] is False


def test_food_supply_scenario_list_and_compare_recommends_feasible(monkeypatch):
    """场景对比必须只在 feasible 场景中推荐，并给出原因。"""
    app = _build_app(monkeypatch)
    client = app.test_client()
    fixture = [
        {"cost": 100, "carbon_kg": 10, "feasible": True, "freshness_score": 0.9, "service_level": 0.95, "duration_min": 600},
        {"cost": 80, "carbon_kg": 8, "feasible": True, "freshness_score": 0.85, "service_level": 0.92, "duration_min": 550},
        {"cost": 50, "carbon_kg": 5, "feasible": False, "freshness_score": 0.5, "service_level": 0.6, "duration_min": 400},
    ]
    for i, summary in enumerate(fixture):
        resp = client.post("/api/cases/food-supply/scenarios", json={"name": f"方案{i+1}", "persist": True, "summary": summary})
        assert resp.status_code == 200

    lst = client.get("/api/cases/food-supply/scenarios")
    lst_payload = lst.get_json()
    assert lst.status_code == 200
    assert lst_payload["success"] is True
    assert lst_payload["summary"]["count"] >= 3

    cmp = client.post("/api/cases/food-supply/scenarios/compare", json={})
    cmp_payload = cmp.get_json()
    assert cmp.status_code == 200
    assert cmp_payload["success"] is True
    assert len(cmp_payload["comparison"]) >= 3
    if cmp_payload["recommended_scenario"]:
        rec = next(c for c in cmp_payload["comparison"] if c["scenario_code"] == cmp_payload["recommended_scenario"])
        assert rec["feasible"] is True
    assert cmp_payload["truth_contract"]["raw_fact_mutation"] is False
