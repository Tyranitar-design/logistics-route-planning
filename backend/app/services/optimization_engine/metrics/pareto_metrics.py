"""
Pareto 前沿基础质量指标
======================

B2 第一阶段正式实现：
- pareto_count
- objective_ranges
- spread
- extreme_point_coverage
"""

from __future__ import annotations

from typing import Sequence, Dict, Any
import numpy as np


class ParetoMetricsError(ValueError):
    """Pareto 指标输入非法时抛出"""


def validate_objectives(objectives: Sequence[Sequence[float]]) -> np.ndarray:
    arr = np.asarray(objectives, dtype=float)
    if arr.ndim != 2:
        raise ParetoMetricsError("objectives 必须是二维数组")
    if arr.shape[0] == 0:
        raise ParetoMetricsError("objectives 不能为空")
    return arr


def _compute_objective_ranges(arr: np.ndarray) -> Dict[str, Dict[str, float]]:
    ranges: Dict[str, Dict[str, float]] = {}
    for j in range(arr.shape[1]):
        col = arr[:, j]
        min_v = float(np.min(col))
        max_v = float(np.max(col))
        ranges[f"objective_{j}"] = {
            "min": min_v,
            "max": max_v,
            "span": float(max_v - min_v),
        }
    return ranges


def _compute_spread(arr: np.ndarray) -> float:
    """
    轻量 spread 指标：
    - 先按各目标归一化到 [0,1]
    - 计算每个解到前一个解的欧氏距离（按第一目标排序）
    - 返回距离的变异系数友好版本：1 / (1 + cv)
    - 越接近 1 表示分布越均匀
    """
    n_points, n_obj = arr.shape
    if n_points <= 1:
        return 0.0

    mins = np.min(arr, axis=0)
    maxs = np.max(arr, axis=0)
    spans = np.where((maxs - mins) == 0, 1.0, (maxs - mins))
    normalized = (arr - mins) / spans

    order = np.argsort(normalized[:, 0])
    sorted_points = normalized[order]

    distances = []
    for i in range(1, len(sorted_points)):
        distances.append(float(np.linalg.norm(sorted_points[i] - sorted_points[i - 1])))

    if not distances:
        return 0.0

    mean_d = float(np.mean(distances))
    if mean_d == 0:
        return 0.0
    std_d = float(np.std(distances))
    cv = std_d / mean_d
    return float(round(1.0 / (1.0 + cv), 6))


def _compute_extreme_point_coverage(arr: np.ndarray) -> Dict[str, Any]:
    """
    统计每个目标的极值点是否被不同解覆盖。
    """
    n_points, n_obj = arr.shape
    if n_points == 0:
        return {
            "unique_extreme_solutions": 0,
            "coverage_ratio": 0.0,
            "extreme_indices": {}
        }

    extreme_indices = {}
    unique_indices = set()

    for j in range(n_obj):
        col = arr[:, j]
        min_idx = int(np.argmin(col))
        max_idx = int(np.argmax(col))
        extreme_indices[f"objective_{j}"] = {
            "min_index": min_idx,
            "max_index": max_idx,
        }
        unique_indices.add(min_idx)
        unique_indices.add(max_idx)

    coverage_ratio = len(unique_indices) / max(1, 2 * n_obj)
    return {
        "unique_extreme_solutions": len(unique_indices),
        "coverage_ratio": float(round(coverage_ratio, 6)),
        "extreme_indices": extreme_indices,
    }


def compute_pareto_metrics(objectives: Sequence[Sequence[float]]) -> Dict[str, Any]:
    """
    计算 Pareto 前沿基础质量指标。
    """
    arr = validate_objectives(objectives)

    return {
        "pareto_count": int(arr.shape[0]),
        "n_objectives": int(arr.shape[1]),
        "objective_ranges": _compute_objective_ranges(arr),
        "spread": _compute_spread(arr),
        "extreme_point_coverage": _compute_extreme_point_coverage(arr),
        "status": "ok",
    }
