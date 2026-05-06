"""
VRP Problem Builder
===================

将业务输入统一构建为优化问题对象，作为 B3 编排层的第一块基础设施。

职责：
- 解析 payload
- 调用 PreciseDistanceProvider 构建距离矩阵
- 构建 VRPData
- 自动识别问题类型
- 返回 problem / vrp_data / build_metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

from app.services.precise_distance_provider import get_precise_distance_provider
from app.services.optimization_engine.problems import (
    VRPData,
    CVRPProblem,
    MultiObjectiveVRP,
)
from app.services.optimization_engine.base import ProblemType


@dataclass
class ProblemBuildResult:
    """统一问题构建结果"""
    problem: Any
    vrp_data: VRPData
    problem_type: ProblemType
    build_metadata: Dict[str, Any] = field(default_factory=dict)


class VRPProblemBuilder:
    """统一构建 VRP / CVRP / Multi-objective 问题。"""

    def __init__(self):
        self.distance_provider = get_precise_distance_provider()

    def detect_problem_type(self, payload: Dict[str, Any]) -> ProblemType:
        """
        第一版问题识别规则：
        - 显式 problem_type=multi_objective / objective_mode=multi_objective -> MULTI_OBJECTIVE
        - 其他默认 CVRP
        """
        explicit = str(payload.get("problem_type", "")).strip().lower()
        objective_mode = str(payload.get("objective_mode", "")).strip().lower()

        if explicit in {"multi_objective", "multi-objective", "pareto"}:
            return ProblemType.MULTI_OBJECTIVE
        if objective_mode in {"multi_objective", "multi-objective", "pareto"}:
            return ProblemType.MULTI_OBJECTIVE
        return ProblemType.CVRP

    def build_from_payload(self, payload: Dict[str, Any]) -> ProblemBuildResult:
        """从 API payload 构建统一优化问题。"""
        if not payload:
            raise ValueError("payload 不能为空")

        customers = np.array(payload.get("customers", []), dtype=float)
        demands = np.array(payload.get("demands", []))
        depot = np.array(payload.get("depot", [50, 50]), dtype=float)
        capacity = float(payload.get("capacity", 50))
        use_precise_distance = bool(payload.get("use_precise_distance", True))
        strategy = int(payload.get("strategy", 0))
        service_times = np.array(payload.get("service_times", []), dtype=float)

        if len(customers) == 0:
            raise ValueError("customers 不能为空")
        if len(demands) != len(customers):
            raise ValueError("demands 长度必须与 customers 一致")
        if capacity <= 0:
            raise ValueError("capacity 必须大于 0")

        n_customers = len(customers)
        n_vehicles = max(1, int(np.ceil(demands.sum() / capacity * 1.5)))

        matrix_result = self.distance_provider.build_from_depot_and_customers(
            depot=(float(depot[0]), float(depot[1])),
            customers=[(float(row[0]), float(row[1])) for row in customers],
            strategy=strategy,
            use_amap=use_precise_distance,
        )

        vrp_data = VRPData(
            n_customers=n_customers,
            n_vehicles=n_vehicles,
            vehicle_capacity=capacity,
            depot=depot,
            customers=customers,
            demands=demands,
            distance_matrix=np.array(matrix_result.distance_matrix_km, dtype=float),
            duration_matrix=np.array(matrix_result.duration_matrix_min, dtype=float),
            distance_precision=matrix_result.precision,
            source_summary=matrix_result.source_summary,
            metadata={
                "distance_source": "precise_distance_provider",
                "distance_provider": matrix_result.metadata.get("provider", "PreciseDistanceProvider"),
                "strategy": strategy,
                "use_precise_distance": use_precise_distance,
                "cache_stats": matrix_result.cache_stats,
            },
        )

        problem_type = self.detect_problem_type(payload)

        if problem_type == ProblemType.MULTI_OBJECTIVE:
            if len(service_times) == 0:
                service_times = np.zeros(n_customers, dtype=float)
            elif len(service_times) != n_customers:
                raise ValueError("service_times 长度必须与 customers 一致")
            problem = MultiObjectiveVRP(vrp_data, service_times=service_times)
        else:
            problem = CVRPProblem(vrp_data)
            problem_type = ProblemType.CVRP

        build_metadata = {
            "problem_type": problem_type.value,
            "n_customers": n_customers,
            "n_vehicles": n_vehicles,
            "vehicle_capacity": capacity,
            "distance_precision": matrix_result.precision,
            "source_summary": matrix_result.source_summary,
            "distance_metadata": vrp_data.metadata,
            "use_precise_distance": use_precise_distance,
            "strategy": strategy,
            "has_service_times": len(service_times) == n_customers and n_customers > 0,
        }

        return ProblemBuildResult(
            problem=problem,
            vrp_data=vrp_data,
            problem_type=problem_type,
            build_metadata=build_metadata,
        )
