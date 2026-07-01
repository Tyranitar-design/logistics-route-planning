import importlib
import json
import os
import sys

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
    from app.models import Node, Route, db

    app = create_app("testing")
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                Node(
                    id=1,
                    name="北京仓库",
                    type="warehouse",
                    city="北京",
                    longitude=116.4074,
                    latitude=39.9042,
                    status="active",
                ),
                Node(
                    id=2,
                    name="上海配送站",
                    type="station",
                    city="上海",
                    longitude=121.4737,
                    latitude=31.2304,
                    status="active",
                ),
            ]
        )
        db.session.add(
            Route(
                id=1,
                name="北京-上海",
                start_node_id=1,
                end_node_id=2,
                distance=None,
                duration=0.92,
                status="active",
                route_data='{"legacy": true}',
            )
        )
        db.session.commit()

    return app


def test_route_distance_backfill_dry_run_does_not_mutate(monkeypatch):
    app = _build_app(monkeypatch)

    from app.models import Route
    from app.services.route_distance_backfill_service import backfill_route_distances

    with app.app_context():
        result = backfill_route_distances(apply=False, provider="haversine")
        route = Route.query.get(1)

    assert result["summary"]["candidate_routes"] == 1
    assert result["summary"]["updated"] == 1
    assert result["summary"]["dry_run"] is True
    assert route.distance is None
    assert route.route_data == '{"legacy": true}'


def test_route_distance_backfill_apply_marks_source(monkeypatch):
    app = _build_app(monkeypatch)

    from app.models import Route
    from app.services.route_distance_backfill_service import backfill_route_distances

    with app.app_context():
        result = backfill_route_distances(apply=True, provider="haversine")
        route = Route.query.get(1)
        route_data = json.loads(route.route_data)

    assert result["summary"]["candidate_routes"] == 1
    assert result["summary"]["updated"] == 1
    assert route.distance > 0
    assert route.duration > 0
    assert route_data["legacy"] is True
    assert route_data["distance_source"] == "haversine_corrected"
    assert route_data["duration_source"] == "estimated_speed"
    assert route_data["provider_status"] == "degraded"
    assert route_data["distance_backfill"]["fallback_reason"] == "ROUTE_DISTANCE_BACKFILL_HAVERSINE"
