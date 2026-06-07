#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一精确距离提供层
====================

作为优化引擎的统一距离数据入口：
1. 优先复用 distance_cache_service 的缓存 / 高德 / Haversine 兜底策略
2. 输出统一的距离矩阵与时间矩阵结构
3. 输出精度统计与来源摘要，供求解器与 API 复用

作者: 小彩
日期: 2026-05-05
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


Coordinate = Tuple[float, float]  # (lng, lat)


@dataclass
class DistanceMatrixResult:
    """统一距离矩阵结果"""
    node_ids: List[Any]
    coordinates: List[Coordinate]
    distance_matrix_km: List[List[float]]
    duration_matrix_min: List[List[float]]
    precision: Dict[str, int] = field(default_factory=dict)
    cache_stats: Dict[str, int] = field(default_factory=dict)
    source_summary: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.coordinates)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_ids": self.node_ids,
            "coordinates": self.coordinates,
            "distance_matrix_km": self.distance_matrix_km,
            "duration_matrix_min": self.duration_matrix_min,
            "precision": self.precision,
            "cache_stats": self.cache_stats,
            "source_summary": self.source_summary,
            "metadata": self.metadata,
            "node_count": self.node_count,
        }


class PreciseDistanceProvider:
    """优化引擎统一距离提供层"""

    DEFAULT_AVG_SPEED_KMH = 60.0
    DEFAULT_CORRECTION_FACTOR = 1.3

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self._distance_cache = None

    @property
    def distance_cache(self):
        if self._distance_cache is None and self.use_cache:
            try:
                from app.services.distance_cache_service import get_distance_cache
                self._distance_cache = get_distance_cache()
            except Exception:
                self._distance_cache = None
        return self._distance_cache

    def build_distance_matrix(
        self,
        coordinates: Sequence[Coordinate],
        node_ids: Optional[Sequence[Any]] = None,
        strategy: int = 0,
        use_amap: bool = True,
    ) -> DistanceMatrixResult:
        """
        根据坐标列表构建统一距离矩阵。

        Args:
            coordinates: [(lng, lat), ...]
            node_ids: 可选节点 ID 列表；为空时使用顺序索引
            strategy: 高德路线策略
            use_amap: 是否允许调用高德 API
        """
        coords = [self._normalize_coordinate(c) for c in coordinates]
        n = len(coords)

        if node_ids is None:
            normalized_ids = list(range(n))
        else:
            normalized_ids = list(node_ids)
            if len(normalized_ids) != n:
                raise ValueError("node_ids 长度必须与 coordinates 一致")

        if n == 0:
            return DistanceMatrixResult(
                node_ids=[],
                coordinates=[],
                distance_matrix_km=[],
                duration_matrix_min=[],
                precision={"exact_count": 0, "approx_count": 0, "total_count": 0},
                cache_stats={"cache_hits": 0, "amap_calls": 0, "haversine_fallbacks": 0},
                source_summary={},
                metadata={"strategy": strategy, "provider": "PreciseDistanceProvider", "used_cache_service": False},
            )

        if self.distance_cache:
            try:
                raw = self.distance_cache.get_distance_matrix(
                    coords,
                    coords,
                    strategy=strategy,
                    use_amap=use_amap,
                )
                return self._from_cache_matrix_result(
                    normalized_ids,
                    coords,
                    raw,
                    strategy=strategy,
                    use_amap=use_amap,
                )
            except Exception as exc:
                return self._build_fallback_matrix(
                    normalized_ids,
                    coords,
                    strategy=strategy,
                    use_amap=use_amap,
                    reason=f"distance_cache_error:{exc}",
                )

        return self._build_fallback_matrix(
            normalized_ids,
            coords,
            strategy=strategy,
            use_amap=use_amap,
            reason="distance_cache_unavailable",
        )

    def build_from_depot_and_customers(
        self,
        depot: Coordinate,
        customers: Sequence[Coordinate],
        customer_ids: Optional[Sequence[Any]] = None,
        depot_id: Any = 0,
        strategy: int = 0,
        use_amap: bool = True,
    ) -> DistanceMatrixResult:
        """从仓库 + 客户列表构建矩阵，默认 depot 位于第一个位置。"""
        coords = [depot] + list(customers)
        ids = [depot_id] + (list(customer_ids) if customer_ids is not None else list(range(1, len(customers) + 1)))
        return self.build_distance_matrix(coords, ids, strategy=strategy, use_amap=use_amap)

    def _from_cache_matrix_result(
        self,
        node_ids: List[Any],
        coords: List[Coordinate],
        raw: Dict[str, Any],
        strategy: int,
        use_amap: bool,
    ) -> DistanceMatrixResult:
        matrix = raw.get("matrix", []) or []
        n = len(coords)

        distance_matrix_km: List[List[float]] = []
        duration_matrix_min: List[List[float]] = []
        source_summary: Dict[str, int] = {}
        exact_count = 0
        approx_count = 0
        exact_cache_count = 0
        approx_cache_count = 0
        fresh_amap_count = 0
        fallback_count = 0

        for i in range(n):
            dist_row: List[float] = []
            dur_row: List[float] = []
            for j in range(n):
                cell = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else None

                if cell:
                    distance_km = round(float(cell.get("distance_km", 0.0)), 2)
                    duration_min = round(float(cell.get("duration_minutes", 0.0)), 1)
                    raw_source = str(cell.get("source", "unknown"))
                    is_exact = bool(cell.get("is_exact", False))

                    if raw_source == "cache":
                        source = "cache_exact" if is_exact else "cache_approx"
                    elif raw_source == "amap":
                        source = "amap"
                    elif raw_source == "amap_route":
                        source = "amap_route"
                    elif raw_source == "haversine_corrected":
                        source = "haversine_corrected"
                    else:
                        source = raw_source
                else:
                    distance_km = 0.0 if i == j else round(self._corrected_distance_km(coords[i], coords[j]), 2)
                    duration_min = 0.0 if i == j else round(self._estimate_duration_minutes(distance_km), 1)
                    source = "diagonal" if i == j else "haversine_corrected"
                    is_exact = False

                dist_row.append(distance_km)
                dur_row.append(duration_min)

                source_summary[source] = source_summary.get(source, 0) + 1
                if i != j:
                    if is_exact:
                        exact_count += 1
                    else:
                        approx_count += 1

                    if source == "cache_exact":
                        exact_cache_count += 1
                    elif source == "cache_approx":
                        approx_cache_count += 1
                    elif source == "amap":
                        fresh_amap_count += 1
                    elif source == "amap_route":
                        fresh_amap_count += 1
                    elif source == "haversine_corrected":
                        fallback_count += 1

            distance_matrix_km.append(dist_row)
            duration_matrix_min.append(dur_row)

        total_count = n * n
        precision = {
            "exact_count": exact_count,
            "approx_count": approx_count,
            "total_count": total_count,
            "exact_cache_count": exact_cache_count,
            "approx_cache_count": approx_cache_count,
            "fresh_amap_count": fresh_amap_count,
            "fallback_count": fallback_count,
        }

        cache_stats = {
            "cache_hits": int(raw.get("cache_hits", 0)),
            "amap_calls": int(raw.get("amap_calls", 0)),
            "haversine_fallbacks": int(raw.get("haversine_fallbacks", 0)),
            "total_pairs": int(raw.get("total_pairs", total_count)),
            "amap_attempted_pairs": int(raw.get("amap_attempted_pairs", 0)),
            "amap_successes": int(raw.get("amap_successes", 0)),
            "amap_route_attempted_pairs": int(raw.get("amap_route_attempted_pairs", 0)),
            "amap_route_successes": int(raw.get("amap_route_successes", 0)),
            "amap_rejected_pairs": int(raw.get("amap_rejected_pairs", 0)),
            "cache_rejected_pairs": int(raw.get("cache_rejected_pairs", 0)),
        }

        return DistanceMatrixResult(
            node_ids=node_ids,
            coordinates=coords,
            distance_matrix_km=distance_matrix_km,
            duration_matrix_min=duration_matrix_min,
            precision=precision,
            cache_stats=cache_stats,
            source_summary=source_summary,
            metadata={
                "strategy": strategy,
                "provider": "PreciseDistanceProvider",
                "used_cache_service": True,
                "use_amap": use_amap,
                "provider_status": raw.get("provider_status") or "ok",
                "fallback_reason": raw.get("fallback_reason"),
                "distance_matrix_fallback_reason": raw.get("distance_matrix_fallback_reason"),
                "amap_attempted_pairs": int(raw.get("amap_attempted_pairs", 0)),
                "amap_successes": int(raw.get("amap_successes", 0)),
                "amap_route_attempted_pairs": int(raw.get("amap_route_attempted_pairs", 0)),
                "amap_route_successes": int(raw.get("amap_route_successes", 0)),
                "amap_rejected_pairs": int(raw.get("amap_rejected_pairs", 0)),
                "cache_rejected_pairs": int(raw.get("cache_rejected_pairs", 0)),
            },
        )

    def _build_fallback_matrix(
        self,
        node_ids: List[Any],
        coords: List[Coordinate],
        strategy: int,
        use_amap: bool,
        reason: str,
    ) -> DistanceMatrixResult:
        n = len(coords)
        distance_matrix_km: List[List[float]] = []
        duration_matrix_min: List[List[float]] = []

        for i in range(n):
            dist_row: List[float] = []
            dur_row: List[float] = []
            for j in range(n):
                if i == j:
                    dist_row.append(0.0)
                    dur_row.append(0.0)
                else:
                    d = round(self._corrected_distance_km(coords[i], coords[j]), 2)
                    dist_row.append(d)
                    dur_row.append(round(self._estimate_duration_minutes(d), 1))
            distance_matrix_km.append(dist_row)
            duration_matrix_min.append(dur_row)

        total_count = n * n
        approx_count = n * n - n

        return DistanceMatrixResult(
            node_ids=node_ids,
            coordinates=coords,
            distance_matrix_km=distance_matrix_km,
            duration_matrix_min=duration_matrix_min,
            precision={
                "exact_count": 0,
                "approx_count": approx_count,
                "total_count": total_count,
            },
            cache_stats={
                "cache_hits": 0,
                "amap_calls": 0,
                "haversine_fallbacks": approx_count,
                "total_pairs": total_count,
            },
            source_summary={
                "diagonal": n,
                "haversine_corrected": approx_count,
            },
            metadata={
                "strategy": strategy,
                "provider": "PreciseDistanceProvider",
                "used_cache_service": False,
                "use_amap": use_amap,
                "fallback_reason": reason,
            },
        )

    @staticmethod
    def _normalize_coordinate(coord: Coordinate) -> Coordinate:
        if coord is None or len(coord) != 2:
            raise ValueError("坐标必须是 (lng, lat) 二元组")
        lng, lat = float(coord[0]), float(coord[1])
        return (lng, lat)

    @classmethod
    def _corrected_distance_km(cls, origin: Coordinate, destination: Coordinate) -> float:
        lng1, lat1 = origin
        lng2, lat2 = destination
        radius = 6371.0

        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return radius * c * cls.DEFAULT_CORRECTION_FACTOR

    @classmethod
    def _estimate_duration_minutes(cls, distance_km: float) -> float:
        return (distance_km / cls.DEFAULT_AVG_SPEED_KMH) * 60.0


_precise_distance_provider = None


def get_precise_distance_provider() -> PreciseDistanceProvider:
    global _precise_distance_provider
    if _precise_distance_provider is None:
        _precise_distance_provider = PreciseDistanceProvider()
    return _precise_distance_provider
