import sys
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.precise_distance_provider import PreciseDistanceProvider


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
