import sys
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.precise_distance_provider import PreciseDistanceProvider
from app.services.distance_cache_service import DistanceCacheService


def test_precise_distance_provider_fallback_matrix_shape_and_diagonal():
    provider = PreciseDistanceProvider(use_cache=False)

    result = provider.build_distance_matrix([
        (116.397, 39.908),
        (121.473, 31.230),
        (113.2644, 23.1291),
    ])

    assert result.node_count == 3
    assert len(result.distance_matrix_km) == 3
    assert len(result.duration_matrix_min) == 3

    dist = np.asarray(result.distance_matrix_km, dtype=float)
    dur = np.asarray(result.duration_matrix_min, dtype=float)

    assert dist.shape == (3, 3)
    assert dur.shape == (3, 3)
    assert np.allclose(np.diag(dist), 0.0)
    assert np.allclose(np.diag(dur), 0.0)

    # fallback 模式下应全部为近似距离（除对角线）
    assert result.precision["exact_count"] == 0
    assert result.precision["approx_count"] == 6
    assert result.precision["total_count"] == 9
    assert result.source_summary["haversine_corrected"] == 6
    assert result.source_summary["diagonal"] == 3


def test_precise_distance_provider_from_depot_and_customers_returns_consistent_ids():
    provider = PreciseDistanceProvider(use_cache=False)

    result = provider.build_from_depot_and_customers(
        depot=(116.397, 39.908),
        customers=[(121.473, 31.230), (113.2644, 23.1291)],
        customer_ids=[101, 102],
        depot_id="depot-A",
    )

    assert result.node_ids == ["depot-A", 101, 102]
    assert result.node_count == 3
    assert result.metadata["provider"] == "PreciseDistanceProvider"


def test_precise_distance_provider_upgrades_approx_cache_to_amap_exact(monkeypatch, tmp_path):
    cache = DistanceCacheService(db_path=str(tmp_path / "distance_cache.db"))
    origin = (116.4074, 39.9042)
    destination = (113.5439, 22.1987)
    cache.put_cached(
        origin,
        destination,
        distance_m=2586640,
        duration_s=155198,
        source="haversine_corrected",
        strategy=0,
        correction_factor=1.3,
    )

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy):
            results = []
            for origin_idx, origin_coord in enumerate(origins, start=1):
                for dest_idx, dest_coord in enumerate(destinations, start=1):
                    if origin_coord == dest_coord:
                        distance = 0
                        duration = 0
                    elif origin_coord == origin and dest_coord == destination:
                        distance = 2234000
                        duration = 112200
                    else:
                        distance = 2299000
                        duration = 118800
                    results.append(
                        {
                            "origin_id": str(origin_idx),
                            "dest_id": str(dest_idx),
                            "distance": distance,
                            "duration": duration,
                        }
                    )
            return {
                "success": True,
                "results": results,
            }

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    provider = PreciseDistanceProvider()
    provider._distance_cache = cache

    result = provider.build_distance_matrix(
        [origin, destination],
        node_ids=["beijing", "macau"],
        use_amap=True,
    )

    assert result.distance_matrix_km[0][1] == 2234.0
    assert result.precision["exact_count"] >= 1
    assert result.precision["fresh_amap_count"] >= 1
    assert result.source_summary["amap"] >= 1
    assert result.metadata["fallback_reason"] is None


def test_precise_distance_provider_reports_amap_failure_when_approx_cache_cannot_upgrade(
    monkeypatch,
    tmp_path,
):
    cache = DistanceCacheService(db_path=str(tmp_path / "distance_cache.db"))
    origin = (116.4074, 39.9042)
    destination = (113.5439, 22.1987)
    cache.put_cached(
        origin,
        destination,
        distance_m=2586640,
        duration_s=155198,
        source="haversine_corrected",
        strategy=0,
        correction_factor=1.3,
    )

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy):
            return {
                "success": False,
                "provider": "amap",
                "provider_status": "unavailable",
                "fallback_reason": "AMAP_KEY_MISSING",
                "error": "AMAP_KEY_MISSING",
            }

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    provider = PreciseDistanceProvider()
    provider._distance_cache = cache

    result = provider.build_distance_matrix(
        [origin, destination],
        node_ids=["beijing", "macau"],
        use_amap=True,
    )

    assert result.distance_matrix_km[0][1] == 2586.64
    assert result.precision["exact_count"] == 0
    assert result.precision["approx_count"] > 0
    assert result.metadata["fallback_reason"] == "AMAP_KEY_MISSING"
    assert result.metadata["provider_status"] == "unavailable"


def test_precise_distance_provider_uses_driving_route_when_distance_matrix_fails(
    monkeypatch,
    tmp_path,
):
    cache = DistanceCacheService(db_path=str(tmp_path / "distance_cache.db"))
    origin = (116.4074, 39.9042)
    destination = (113.5439, 22.1987)

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy):
            return {
                "success": False,
                "provider": "amap",
                "provider_status": "degraded",
                "fallback_reason": "AMAP_DISTANCE_MATRIX_NO_ROUTE",
                "error": "AMAP_DISTANCE_MATRIX_NO_ROUTE",
            }

        def driving_route(self, origin_coord, destination_coord, strategy=0, show_traffic=True):
            from app.services.amap_service import AmapRouteResult

            if origin_coord == destination_coord:
                return AmapRouteResult(success=False, fallback_reason="SAME_POINT")

            return AmapRouteResult(
                success=True,
                distance=2234000,
                duration=112200,
                provider="amap",
                provider_status="ok",
                degraded=False,
                fallback_reason=None,
            )

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    provider = PreciseDistanceProvider()
    provider._distance_cache = cache

    result = provider.build_distance_matrix(
        [origin, destination],
        node_ids=["beijing", "macau"],
        use_amap=True,
    )

    assert result.distance_matrix_km[0][1] == 2234.0
    assert result.duration_matrix_min[0][1] == 1870.0
    assert result.precision["exact_count"] >= 1
    assert result.source_summary["amap_route"] >= 1
    assert result.cache_stats["amap_route_successes"] >= 1
    assert result.metadata["fallback_reason"] is None
    assert result.metadata["distance_matrix_fallback_reason"] == "AMAP_DISTANCE_MATRIX_NO_ROUTE"


def test_precise_distance_provider_rejects_implausibly_tiny_amap_matrix_distance(
    monkeypatch,
    tmp_path,
):
    cache = DistanceCacheService(db_path=str(tmp_path / "distance_cache.db"))
    origin = (116.4074, 39.9042)
    destination = (113.5439, 22.1987)

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy):
            results = []
            for origin_idx, origin_coord in enumerate(origins, start=1):
                for dest_idx, dest_coord in enumerate(destinations, start=1):
                    if origin_coord == dest_coord:
                        distance = 0
                        duration = 0
                    else:
                        distance = 20
                        duration = 60
                    results.append(
                        {
                            "origin_id": str(origin_idx),
                            "dest_id": str(dest_idx),
                            "distance": distance,
                            "duration": duration,
                        }
                    )
            return {"success": True, "results": results}

        def driving_route(self, origin_coord, destination_coord, strategy=0, show_traffic=True):
            from app.services.amap_service import AmapRouteResult

            if origin_coord == destination_coord:
                return AmapRouteResult(success=False, fallback_reason="SAME_POINT")

            return AmapRouteResult(
                success=True,
                distance=2234000,
                duration=112200,
                provider="amap",
                provider_status="ok",
                degraded=False,
                fallback_reason=None,
            )

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    provider = PreciseDistanceProvider()
    provider._distance_cache = cache

    result = provider.build_distance_matrix(
        [origin, destination],
        node_ids=["beijing", "macau"],
        use_amap=True,
    )

    assert result.distance_matrix_km[0][1] == 2234.0
    assert result.precision["exact_count"] >= 1
    assert result.source_summary["amap_route"] >= 1
    assert result.cache_stats["amap_rejected_pairs"] >= 1
    assert result.metadata["fallback_reason"] is None
    assert result.metadata["amap_rejected_pairs"] >= 1


def test_precise_distance_provider_revalidates_implausibly_tiny_exact_cache(
    monkeypatch,
    tmp_path,
):
    cache = DistanceCacheService(db_path=str(tmp_path / "distance_cache.db"))
    origin = (116.4074, 39.9042)
    destination = (113.5439, 22.1987)
    cache.put_cached(
        origin,
        destination,
        distance_m=20,
        duration_s=60,
        source="amap",
        strategy=0,
        correction_factor=0.0,
    )

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy):
            return {
                "success": False,
                "provider": "amap",
                "provider_status": "degraded",
                "fallback_reason": "AMAP_DISTANCE_MATRIX_NO_ROUTE",
            }

        def driving_route(self, origin_coord, destination_coord, strategy=0, show_traffic=True):
            from app.services.amap_service import AmapRouteResult

            if origin_coord == destination_coord:
                return AmapRouteResult(success=False, fallback_reason="SAME_POINT")

            return AmapRouteResult(
                success=True,
                distance=2234000,
                duration=112200,
                provider="amap",
                provider_status="ok",
                degraded=False,
                fallback_reason=None,
            )

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    provider = PreciseDistanceProvider()
    provider._distance_cache = cache

    result = provider.build_distance_matrix(
        [origin, destination],
        node_ids=["beijing", "macau"],
        use_amap=True,
    )

    assert result.distance_matrix_km[0][1] == 2234.0
    assert result.source_summary["amap_route"] >= 1
    assert result.cache_stats["cache_rejected_pairs"] >= 1
    assert result.cache_stats["amap_route_successes"] >= 1
