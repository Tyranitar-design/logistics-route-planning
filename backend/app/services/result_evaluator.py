"""
Result Evaluator
================

统一评估单目标/多目标求解结果。

B3 第一版目标：
- 可行性校验
- 统一结果摘要
- gap / 距离精度 / Pareto 摘要
- 输出结构稳定，便于 API 与前端消费
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.optimization_engine.base import ProblemType, OptimizationResult
from app.services.optimization_engine.metrics import compute_pareto_metrics


@dataclass
class QualityReport:
    feasible: bool
    violations: List[str] = field(default_factory=list)
    objective_summary: Dict[str, Any] = field(default_factory=dict)
    solver_summary: Dict[str, Any] = field(default_factory=dict)
    distance_precision_summary: Dict[str, Any] = field(default_factory=dict)
    pareto_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feasible": self.feasible,
            "violations": self.violations,
            "objective_summary": self.objective_summary,
            "solver_summary": self.solver_summary,
            "distance_precision_summary": self.distance_precision_summary,
            "pareto_summary": self.pareto_summary,
        }


class ResultEvaluator:
    """统一结果评估器。"""

    def evaluate(self, problem: Any, result: OptimizationResult) -> QualityReport:
        violations = self._check_violations(problem, result)
        feasible = len(violations) == 0

        objective_summary = self._build_objective_summary(result)
        solver_summary = self._build_solver_summary(result)
        distance_precision_summary = self._build_distance_precision_summary(result)
        pareto_summary = self._build_pareto_summary(problem, result)

        return QualityReport(
            feasible=feasible,
            violations=violations,
            objective_summary=objective_summary,
            solver_summary=solver_summary,
            distance_precision_summary=distance_precision_summary,
            pareto_summary=pareto_summary,
        )

    def _check_violations(self, problem: Any, result: OptimizationResult) -> List[str]:
        violations: List[str] = []
        routes = result.routes or result.solution or []
        data = problem.data

        visited: List[int] = []
        for route in routes:
            for customer in route:
                if customer == 0:
                    continue
                visited.append(int(customer))

        expected = set(range(1, data.n_customers + 1))
        actual = set(visited)

        duplicates = [c for c in actual if visited.count(c) > 1]
        if duplicates:
            violations.append(f"存在重复客户: {sorted(duplicates)}")

        missing = sorted(expected - actual)
        if missing:
            violations.append(f"存在遗漏客户: {missing}")

        extra = sorted(actual - expected)
        if extra:
            violations.append(f"存在非法客户编号: {extra}")

        # 容量约束检查
        if hasattr(data, "vehicle_capacity") and hasattr(data, "demands"):
            demands = list(data.demands)
            for idx, route in enumerate(routes, start=1):
                pure_route = [c for c in route if c != 0]
                load = sum(float(demands[c - 1]) for c in pure_route if 1 <= c <= len(demands))
                if load > float(data.vehicle_capacity):
                    violations.append(
                        f"路线 {idx} 超载: load={load}, capacity={data.vehicle_capacity}"
                    )

        return violations

    def _build_objective_summary(self, result: OptimizationResult) -> Dict[str, Any]:
        objectives = [float(x) for x in np.asarray(result.objective_values).tolist()]
        return {
            "primary_objective": float(result.primary_objective),
            "objective_values": objectives,
            "n_objectives": len(objectives),
            "gap": float(result.gap) if result.gap is not None else None,
        }

    def _build_solver_summary(self, result: OptimizationResult) -> Dict[str, Any]:
        return {
            "solver_name": result.solver_name,
            "problem_type": result.problem_type.value if isinstance(result.problem_type, ProblemType) else str(result.problem_type),
            "solve_time": float(result.solve_time),
            "iterations": int(result.iterations),
            "is_optimal": bool(result.is_optimal),
            "metadata": result.metadata,
        }

    def _build_distance_precision_summary(self, result: OptimizationResult) -> Dict[str, Any]:
        precision = result.metadata.get("distance_precision", {}) if result.metadata else {}
        source_summary = result.metadata.get("source_summary", {}) if result.metadata else {}

        exact = int(precision.get("exact_count", 0))
        approx = int(precision.get("approx_count", 0))
        total = int(precision.get("total_count", 0))

        exact_ratio = round(exact / total, 4) if total else 0.0
        approx_ratio = round(approx / total, 4) if total else 0.0

        return {
            "distance_source": result.metadata.get("distance_source", "unknown") if result.metadata else "unknown",
            "exact_count": exact,
            "approx_count": approx,
            "total_count": total,
            "exact_ratio": exact_ratio,
            "approx_ratio": approx_ratio,
            "source_summary": source_summary,
        }

    def _build_pareto_summary(self, problem: Any, result: OptimizationResult) -> Dict[str, Any]:
        objective_values = np.asarray(result.objective_values)

        if getattr(problem, "problem_type", None) != ProblemType.MULTI_OBJECTIVE:
            return {
                "enabled": False,
                "reason": "not_multi_objective",
            }

        if objective_values.ndim == 1:
            metrics = compute_pareto_metrics([objective_values.tolist()])
        else:
            metrics = compute_pareto_metrics(objective_values.tolist())

        return {
            "enabled": True,
            "pareto_front_size": result.metadata.get("pareto_front_size") if result.metadata else None,
            "metrics": metrics,
        }
