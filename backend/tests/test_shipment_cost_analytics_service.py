import importlib
import os
import sys
from datetime import datetime, timedelta


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


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


def _build_app(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")
    _clear_logistics_prometheus_collectors()

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    importlib.import_module("app")
    from app import create_app
    from app.models import DataImportBatch, ShipmentFact, User, db

    app = create_app("testing")

    with app.app_context():
        db.create_all()
        user = User(
            username="admin",
            email="admin-cost@example.com",
            real_name="Admin",
            role="admin",
            status="active",
        )
        user.password = "admin123"
        db.session.add(user)

        batch = DataImportBatch(
            dataset_source="unit-test",
            source_filename="cost.csv",
            quality_status="ready",
            raw_record_count=12,
            fact_record_count=12,
        )
        db.session.add(batch)
        db.session.flush()

        base = datetime(2026, 5, 1, 8, 0, 0)
        facts = []
        for idx in range(12):
            shipped_at = base + timedelta(days=idx)
            eta_at = shipped_at + timedelta(hours=24)
            actual_hours = 20 if idx % 4 else 30
            freight = 100 + idx * 10
            origin = "广州" if idx < 8 else "深圳"
            destination = "上海" if idx % 3 else "杭州"
            facts.append(
                ShipmentFact(
                    batch_id=batch.id,
                    external_shipment_id=f"SHP-COST-{idx:03d}",
                    external_order_id=f"ORD-COST-{idx:03d}",
                    origin_city_std=origin,
                    destination_city_std=destination,
                    origin_lng=113.2644,
                    origin_lat=23.1291,
                    destination_lng=121.4737 if destination == "上海" else 120.1551,
                    destination_lat=31.2304 if destination == "上海" else 30.2741,
                    geo_status="resolved",
                    cargo_type="普货",
                    logistics_company="测试物流",
                    transport_mode="truck",
                    freight=freight,
                    insurance_amount=freight * 2,
                    standard_status="delivered",
                    shipped_at=shipped_at,
                    eta_at=eta_at,
                    delivered_at=shipped_at + timedelta(hours=actual_hours),
                    signed_at=shipped_at + timedelta(hours=actual_hours + 1),
                    exception_reason="晚到" if idx == 0 else None,
                    weight_kg=500 + idx * 20,
                    volume_m3=1.5 + idx * 0.1,
                )
            )
        db.session.add_all(facts)
        db.session.commit()

    return app


def test_shipment_cost_analytics_uses_real_freight_and_service_kpis(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_cost_analytics_service import ShipmentCostAnalyticsService

        result = ShipmentCostAnalyticsService().operations_summary(
            {"limit": 100, "trend_days": 7, "lane_limit": 5}
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["provider_status"] == "ok"
    assert result["fallback_reason"] is None
    assert result["kpis"]["total_shipments"] == 12
    assert result["kpis"]["freight_records"] == 12
    assert result["kpis"]["total_freight"] == 1860
    assert result["kpis"]["freight_coverage"] == 1
    assert result["kpis"]["on_time_rate"] == 0.75
    assert result["kpis"]["exception_shipments"] == 1
    assert len(result["trend"]) == 7
    assert result["top_lanes"]
    assert result["city_breakdown"]
    assert result["cost_components"][0]["source"] == "freight_amount_allocation_heuristic"
    assert result["truth_contract"]["business_mutation"] == "none"


def test_operations_scorecard_aggregates_cost_and_service_readiness(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_cost_analytics_service import ShipmentCostAnalyticsService

        result = ShipmentCostAnalyticsService().operations_scorecard(
            {"limit": 100, "trend_days": 7, "lane_limit": 5}
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "shipment_fact_operations_scorecard"
    assert result["scorecard_version"] == "shipment_operations_scorecard_v1"
    assert result["summary"]["readiness_score"] > 0
    assert result["summary"]["total_freight"] == 1860
    assert {component["id"] for component in result["components"]} >= {
        "data_coverage",
        "service_quality",
        "cost_efficiency",
        "exception_pressure",
        "lane_concentration",
    }
    assert {gate["id"] for gate in result["gates"]} >= {
        "real_freight_available",
        "service_kpis_available",
        "unit_cost_available",
        "shadow_boundary_preserved",
    }
    assert result["truth_contract"]["business_mutation"] == "none"


def test_operations_summary_route_requires_auth_and_returns_truth_contract(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    unauthorized = client.get("/api/analytics/operations-summary")
    unauthorized_scorecard = client.get("/api/analytics/operations-scorecard")
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.get_json()["access_token"]
    response = client.post(
        "/api/analytics/operations-summary",
        json={"limit": 100, "trend_days": 7, "lane_limit": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    scorecard = client.post(
        "/api/analytics/operations-scorecard",
        json={"limit": 100, "trend_days": 7, "lane_limit": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    payload = response.get_json()
    scorecard_payload = scorecard.get_json()

    assert unauthorized.status_code == 401
    assert unauthorized_scorecard.status_code == 401
    assert response.status_code == 200
    assert payload["summary"]["records_scanned"] == 12
    assert payload["kpis"]["avg_freight_per_paid_shipment"] == 155
    assert payload["truth_contract"]["revenue_cost_source"] == "shipment_facts.freight"
    assert payload["authenticity_level"] == "B"
    assert scorecard.status_code == 200
    assert scorecard_payload["summary"]["readiness_score"] > 0
    assert scorecard_payload["truth_contract"]["business_mutation"] == "none"
