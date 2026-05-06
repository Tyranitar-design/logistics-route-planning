"""
Solver Recommendation Engine
============================

基于问题类型、规模、实时性与精确性需求，输出可解释的求解器推荐。

B3 第一版目标：
- 规则可解释
- 输出推荐 + 备选项 + 原因
- 不引入黑盒模型
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.optimization_engine.base import ProblemType, SolverType


@dataclass
class SolverRecommendation:
    recommended_solver: SolverType
    alternatives: List[SolverType] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)
    problem_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_solver": self.recommended_solver.value,
            "alternatives": [s.value for s in self.alternatives],
            "reasoning": self.reasoning,
            "problem_summary": self.problem_summary,
        }


class SolverRecommendationEngine:
    """解释型求解器推荐引擎。"""

    SMALL_SCALE_THRESHOLD = 20
    MEDIUM_SCALE_THRESHOLD = 80

    def recommend(
        self,
        problem_type: ProblemType,
        n_customers: int,
        require_high_accuracy: bool = False,
        prefer_fast_response: bool = False,
        realtime: bool = False,
        available_solvers: Optional[List[SolverType]] = None,
    ) -> SolverRecommendation:
        available = set(available_solvers) if available_solvers else set(SolverType)
        reasoning: List[str] = []

        scale = self._classify_scale(n_customers)
        problem_summary = {
            "problem_type": problem_type.value,
            "n_customers": n_customers,
            "scale": scale,
            "require_high_accuracy": require_high_accuracy,
            "prefer_fast_response": prefer_fast_response,
            "realtime": realtime,
        }

        candidates: List[SolverType] = []

        if problem_type == ProblemType.MULTI_OBJECTIVE:
            reasoning.append("问题类型为多目标优化，优先推荐支持 Pareto 前沿求解的 pymoo 系列。")
            candidates = [SolverType.PYMOO_NSGA2, SolverType.PYMOO_NSGA3, SolverType.ORTOOLS]
            if n_customers >= self.MEDIUM_SCALE_THRESHOLD:
                reasoning.append("客户规模偏大，保留 OR-Tools 作为更稳的快速备选。")

        elif require_high_accuracy and scale == "small":
            reasoning.append("问题规模较小且要求高精度，优先推荐精确求解器 Gurobi。")
            candidates = [SolverType.GUROBI, SolverType.ORTOOLS, SolverType.ALNS]

        elif realtime or prefer_fast_response:
            reasoning.append("场景偏实时或强调快速响应，优先推荐 OR-Tools。")
            candidates = [SolverType.ORTOOLS, SolverType.ALNS, SolverType.GENETIC]

        elif scale == "large":
            reasoning.append("客户规模较大，优先推荐启发式/元启发式求解器。")
            candidates = [SolverType.ALNS, SolverType.ORTOOLS, SolverType.GENETIC]

        elif scale == "medium":
            reasoning.append("中等规模问题，推荐兼顾稳定性与速度的 OR-Tools。")
            candidates = [SolverType.ORTOOLS, SolverType.ALNS, SolverType.GUROBI]

        else:
            reasoning.append("默认推荐稳定通用的 OR-Tools 作为主解器。")
            candidates = [SolverType.ORTOOLS, SolverType.GUROBI, SolverType.ALNS]

        filtered = [solver for solver in candidates if solver in available]
        if not filtered:
            fallback = [solver for solver in [SolverType.ORTOOLS, SolverType.GENETIC, SolverType.ALNS] if solver in available]
            if fallback:
                filtered = fallback
                reasoning.append("首选候选不可用，已回退到当前可用求解器。")
            else:
                raise ValueError("没有可用的候选求解器")

        recommended = filtered[0]
        alternatives = filtered[1:]
        reasoning.append(f"最终推荐：{recommended.value}")

        return SolverRecommendation(
            recommended_solver=recommended,
            alternatives=alternatives,
            reasoning=reasoning,
            problem_summary=problem_summary,
        )

    def _classify_scale(self, n_customers: int) -> str:
        if n_customers < self.SMALL_SCALE_THRESHOLD:
            return "small"
        if n_customers < self.MEDIUM_SCALE_THRESHOLD:
            return "medium"
        return "large"
