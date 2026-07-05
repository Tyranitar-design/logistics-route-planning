import importlib
import os
import sys
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
    from app.models import DataImportBatch, ShipmentFact, db

    app = create_app("testing")

    with app.app_context():
        db.create_all()
        batch = DataImportBatch(
            dataset_source="unit-test",
            source_filename="anomaly.csv",
            quality_status="ready",
            raw_record_count=18,
            fact_record_count=18,
        )
        db.session.add(batch)
        db.session.flush()

        base = datetime(2026, 5, 1, 8, 0, 0)
        facts = []
        for idx in range(12):
            shipped_at = base + timedelta(hours=idx)
            facts.append(
                _fact(
                    ShipmentFact,
                    batch.id,
                    idx,
                    shipped_at,
                    freight=100 + idx,
                    weight_kg=1000,
                    delivered_at=shipped_at + timedelta(hours=24 + (idx % 3)),
                    eta_at=shipped_at + timedelta(hours=25),
                )
            )

        facts.extend(
            [
                _fact(
                    ShipmentFact,
                    batch.id,
                    12,
                    base + timedelta(days=2),
                    freight=5000,
                    weight_kg=1000,
                    delivered_at=base + timedelta(days=3),
                    eta_at=base + timedelta(days=3),
                    external_order_id="ORD-ANOM-COST",
                ),
                _fact(
                    ShipmentFact,
                    batch.id,
                    13,
                    base + timedelta(days=3),
                    freight=130,
                    weight_kg=1000,
                    delivered_at=base + timedelta(days=3, hours=220),
                    eta_at=base + timedelta(days=4),
                    external_order_id="ORD-ANOM-ETA",
                ),
                _fact(
                    ShipmentFact,
                    batch.id,
                    14,
                    base + timedelta(days=4),
                    freight=140,
                    weight_kg=1000,
                    delivered_at=base + timedelta(days=4, hours=40),
                    eta_at=base + timedelta(days=4, hours=25),
                    external_order_id="ORD-ANOM-DELAY",
                ),
                _fact(
                    ShipmentFact,
                    batch.id,
                    15,
                    base + timedelta(days=5),
                    freight=150,
                    weight_kg=1000,
                    delivered_at=base + timedelta(days=5, hours=20),
                    eta_at=base + timedelta(days=5, hours=22),
                    destination_lng=None,
                    destination_lat=None,
                    geo_status="unresolved",
                    external_order_id="ORD-ANOM-GEO",
                ),
                _fact(
                    ShipmentFact,
                    batch.id,
                    16,
                    base + timedelta(days=6),
                    freight=160,
                    weight_kg=1000,
                    delivered_at=base + timedelta(days=6, hours=20),
                    eta_at=base + timedelta(days=6, hours=22),
                    standard_status="exception",
                    exception_reason="地址无法联系",
                    external_order_id="ORD-ANOM-STATUS",
                ),
                _fact(
                    ShipmentFact,
                    batch.id,
                    17,
                    base + timedelta(days=7),
                    freight=170,
                    weight_kg=1000,
                    delivered_at=base + timedelta(days=7, hours=-1),
                    eta_at=base + timedelta(days=7, hours=22),
                    external_order_id="ORD-ANOM-TIME",
                ),
            ]
        )

        db.session.add_all(facts)
        db.session.commit()

    return app


def _fact(
    ShipmentFact,
    batch_id,
    idx,
    shipped_at,
    freight,
    weight_kg,
    delivered_at,
    eta_at,
    destination_lng=121.4737,
    destination_lat=31.2304,
    geo_status="resolved",
    standard_status="delivered",
    exception_reason=None,
    external_order_id=None,
):
    return ShipmentFact(
        batch_id=batch_id,
        external_shipment_id=f"SHP-ANOM-{idx:03d}",
        external_order_id=external_order_id or f"ORD-ANOM-{idx:03d}",
        origin_city_std="广州",
        destination_city_std="上海",
        origin_lng=113.2644,
        origin_lat=23.1291,
        destination_lng=destination_lng,
        destination_lat=destination_lat,
        geo_status=geo_status,
        cargo_type="普货",
        logistics_company="测试物流",
        transport_mode="truck",
        freight=freight,
        standard_status=standard_status,
        exception_reason=exception_reason,
        shipped_at=shipped_at,
        eta_at=eta_at,
        delivered_at=delivered_at,
        signed_at=delivered_at + timedelta(minutes=30) if delivered_at else None,
        weight_kg=weight_kg,
        volume_m3=2.0,
    )


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


def test_shipment_anomaly_health_uses_real_facts(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_anomaly_service import ShipmentAnomalyService

        result = ShipmentAnomalyService().health()

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["provider_status"] == "ok"
    assert result["summary"]["total_records"] == 18
    assert result["readiness"]["rules"]["ready"] is True
    assert result["truth_contract"]["path_source"] == "not_route_geometry_anomaly_features"


def test_shipment_anomaly_detection_explains_real_fact_outliers(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_anomaly_service import ShipmentAnomalyService

        result = ShipmentAnomalyService().detect(
            {
                "tasks": ["status", "geo", "cost", "eta", "delay"],
                "limit": 100,
                "anomaly_limit": 50,
                "use_ml": False,
                "z_threshold": 3.0,
            }
        )

    anomaly_types = {item["anomaly_type"] for item in result["anomalies"]}

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["distance_source"] == "shipment_fact_coordinates_haversine_when_needed"
    assert result["path_source"] == "not_route_geometry_anomaly_features"
    assert result["summary"]["records_scanned"] == 18
    assert result["summary"]["anomaly_count"] >= 5
    assert result["diagnostics"]["ml_detector"]["fallback_reason"] == "DISABLED_BY_REQUEST"
    assert "status_exception" in anomaly_types
    assert "coordinate_missing" in anomaly_types
    assert "cost_outlier" in anomaly_types
    assert "eta_transit_outlier" in anomaly_types
    assert "delay_threshold_breach" in anomaly_types
    assert all(item["explanation"] for item in result["anomalies"])
    assert all(item["actions"] for item in result["anomalies"])


def test_shipment_anomaly_detection_streams_column_projections(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from sqlalchemy.orm import Query

        from app.services.shipment_anomaly_service import ShipmentAnomalyService

        def fail_all(self):
            raise AssertionError("anomaly detection must not load full ORM result sets with Query.all()")

        monkeypatch.setattr(Query, "all", fail_all)

        result = ShipmentAnomalyService().detect(
            {
                "tasks": ["status", "geo", "cost", "eta", "delay"],
                "limit": 100,
                "anomaly_limit": 20,
                "use_ml": False,
                "z_threshold": 3.0,
            }
        )

    assert result["success"] is True
    assert result["summary"]["records_scanned"] == 18
    assert result["summary"]["anomaly_count"] >= 5


def test_shipment_anomaly_scorecard_aggregates_readiness(monkeypatch):
    app = _build_app(monkeypatch)

    with app.app_context():
        from app.services.shipment_anomaly_service import ShipmentAnomalyService

        result = ShipmentAnomalyService().scorecard(
            {
                "tasks": ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion"],
                "limit": 100,
                "anomaly_limit": 50,
                "use_ml": False,
                "z_threshold": 3.0,
            }
        )

    assert result["success"] is True
    assert result["data_source"] == "shipment_fact"
    assert result["model_family"] == "anomaly_readiness_scorecard"
    assert result["scorecard_version"] == "shipment_anomaly_scorecard_v1"
    assert result["summary"]["readiness_score"] > 0
    assert result["summary"]["records_scanned"] == 18
    assert result["summary"]["high_risk_count"] >= 1
    assert {component["id"] for component in result["components"]} >= {
        "data_readiness",
        "signal_coverage",
        "risk_pressure",
        "explainability",
        "ml_shadow_readiness",
    }
    assert {gate["id"] for gate in result["gates"]} >= {
        "real_data_available",
        "rule_and_statistics_ready",
        "explainability_contract",
        "shadow_boundary_preserved",
    }
    assert result["truth_contract"]["business_mutation"] == "none"


def test_ai_anomaly_routes_and_explain_are_available(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    route_rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/ai-anomaly/health" in route_rules
    assert "/api/ai-anomaly/detect" in route_rules
    assert "/api/ai-anomaly/scorecard" in route_rules
    assert "/api/ai-anomaly/explain" in route_rules

    health = client.get("/api/ai-anomaly/health")
    detect = client.post(
        "/api/ai-anomaly/detect",
        json={
            "tasks": ["status", "geo", "cost", "eta", "delay"],
            "limit": 100,
            "anomaly_limit": 20,
            "use_ml": False,
            "z_threshold": 3.0,
        },
    )
    scorecard = client.post(
        "/api/ai-anomaly/scorecard",
        json={
            "tasks": ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion"],
            "limit": 100,
            "anomaly_limit": 20,
            "use_ml": False,
            "z_threshold": 3.0,
        },
    )
    clamped = client.post(
        "/api/ai-anomaly/detect",
        json={
            "runtime_profile": "interactive",
            "tasks": ["status", "ml"],
            "limit": 50000,
            "anomaly_limit": 500,
            "use_ml": True,
        },
    )
    explain = client.get("/api/ai-anomaly/explain?order_id=ORD-ANOM-COST")
    missing = client.get("/api/ai-anomaly/explain?order_id=NO-SUCH-ORDER")

    assert health.status_code == 200
    assert health.get_json()["summary"]["total_records"] == 18
    assert detect.status_code == 200
    assert detect.get_json()["summary"]["anomaly_count"] >= 5
    assert scorecard.status_code == 200
    assert scorecard.get_json()["summary"]["readiness_score"] > 0
    assert scorecard.get_json()["truth_contract"]["business_mutation"] == "none"
    assert clamped.status_code == 200
    assert clamped.get_json()["runtime_profile"] == "interactive"
    assert clamped.get_json()["runtime_limits"]["limit"] == 5000
    assert clamped.get_json()["runtime_limits"]["anomaly_limit"] == 80
    assert clamped.get_json()["runtime_limits"]["use_ml"] is False
    assert explain.status_code == 200
    assert explain.get_json()["query"] == "ORD-ANOM-COST"
    assert explain.get_json()["anomaly_count"] >= 1
    assert missing.status_code == 200
    assert missing.get_json()["fallback_reason"] == "SHIPMENT_FACT_NOT_FOUND"
