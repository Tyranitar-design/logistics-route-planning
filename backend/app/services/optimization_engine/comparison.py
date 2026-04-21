"""
结果对比工具
============

对比不同求解器的结果

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .base import OptimizationResult, SolverType


@dataclass
class ComparisonResult:
    """对比结果"""
    solver_results: Dict[SolverType, OptimizationResult]
    best_solver: Optional[SolverType]
    rankings: List[Tuple[SolverType, float]]  # (求解器, 得分)
    metrics: Dict[str, Dict[SolverType, float]]


class ResultComparator:
    """
    结果对比器
    
    对比不同求解器的结果，给出排名和建议
    """
    
    @classmethod
    def compare(cls,
                results: Dict[SolverType, OptimizationResult],
                weights: Optional[np.ndarray] = None) -> ComparisonResult:
        """
        对比结果
        
        Args:
            results: {求解器类型: 结果} 字典
            weights: 目标权重（多目标时使用）
        
        Returns:
            对比结果
        """
        if not results:
            raise ValueError("结果字典为空")
        
        # 计算综合得分
        scores = {}
        for solver_type, result in results.items():
            score = cls._calculate_score(result, weights)
            scores[solver_type] = score
        
        # 排名
        rankings = sorted(scores.items(), key=lambda x: x[1])
        
        # 最佳求解器
        best_solver = rankings[0][0] if rankings else None
        
        # 计算指标
        metrics = cls._calculate_metrics(results)
        
        return ComparisonResult(
            solver_results=results,
            best_solver=best_solver,
            rankings=rankings,
            metrics=metrics
        )
    
    @classmethod
    def _calculate_score(cls,
                         result: OptimizationResult,
                         weights: Optional[np.ndarray] = None) -> float:
        """
        计算综合得分
        
        Args:
            result: 优化结果
            weights: 目标权重
        
        Returns:
            得分（越小越好）
        """
        obj_values = result.objective_values
        
        if weights is None:
            # 默认权重：所有目标等权
            weights = np.ones(len(obj_values))
        
        # 加权求和
        score = np.sum(weights * obj_values)
        
        # 加上惩罚项（时间、间隙）
        score += result.solve_time * 0.01  # 时间惩罚
        
        if result.gap is not None:
            score += result.gap * 100  # 间隙惩罚
        
        return score
    
    @classmethod
    def _calculate_metrics(cls,
                          results: Dict[SolverType, OptimizationResult]) -> Dict[str, Dict[SolverType, float]]:
        """
        计算各种指标
        
        Args:
            results: 结果字典
        
        Returns:
            {指标名: {求解器: 值}}
        """
        metrics = {
            'objective': {},
            'time': {},
            'gap': {},
            'iterations': {}
        }
        
        for solver_type, result in results.items():
            metrics['objective'][solver_type] = result.primary_objective
            metrics['time'][solver_type] = result.solve_time
            metrics['gap'][solver_type] = result.gap if result.gap is not None else float('nan')
            metrics['iterations'][solver_type] = result.iterations
        
        return metrics
    
    @classmethod
    def generate_report(cls,
                        comparison: ComparisonResult) -> str:
        """
        生成对比报告
        
        Args:
            comparison: 对比结果
        
        Returns:
            报告字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append("求解器对比报告")
        lines.append("=" * 60)
        
        # 排名表
        lines.append("\n## 排名")
        lines.append("-" * 60)
        lines.append(f"{'排名':<6} {'求解器':<20} {'得分':<12} {'目标值':<12} {'时间(s)':<10}")
        lines.append("-" * 60)
        
        for rank, (solver_type, score) in enumerate(comparison.rankings, 1):
            result = comparison.solver_results[solver_type]
            lines.append(
                f"{rank:<6} {solver_type.value:<20} {score:<12.2f} "
                f"{result.primary_objective:<12.2f} {result.solve_time:<10.2f}"
            )
        
        # 最佳求解器
        lines.append("\n## 最佳求解器")
        lines.append("-" * 60)
        if comparison.best_solver:
            best_result = comparison.solver_results[comparison.best_solver]
            lines.append(f"推荐: {comparison.best_solver.value}")
            lines.append(f"目标值: {best_result.objective_values}")
            lines.append(f"求解时间: {best_result.solve_time:.2f}s")
            if best_result.gap is not None:
                lines.append(f"最优间隙: {best_result.gap:.2%}")
        
        # 详细对比
        lines.append("\n## 详细对比")
        lines.append("-" * 60)
        
        for metric_name, values in comparison.metrics.items():
            lines.append(f"\n### {metric_name}")
            for solver_type, value in values.items():
                if metric_name == 'gap' and np.isnan(value):
                    lines.append(f"  {solver_type.value}: N/A")
                else:
                    lines.append(f"  {solver_type.value}: {value:.4f}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    @classmethod
    def find_pareto_front(cls,
                          results: Dict[SolverType, OptimizationResult]) -> List[SolverType]:
        """
        找出 Pareto 前沿的求解器（多目标）
        
        Args:
            results: 结果字典
        
        Returns:
            Pareto 前沿的求解器列表
        """
        solver_types = list(results.keys())
        pareto_front = []
        
        for i, solver_i in enumerate(solver_types):
            result_i = results[solver_i]
            dominated = False
            
            for j, solver_j in enumerate(solver_types):
                if i == j:
                    continue
                
                result_j = results[solver_j]
                
                # 检查是否被支配
                if cls._dominates(result_j.objective_values, result_i.objective_values):
                    dominated = True
                    break
            
            if not dominated:
                pareto_front.append(solver_i)
        
        return pareto_front
    
    @classmethod
    def _dominates(cls, a: np.ndarray, b: np.ndarray) -> bool:
        """
        检查 a 是否支配 b（最小化问题）
        
        Args:
            a: 目标值 a
            b: 目标值 b
        
        Returns:
            a 是否支配 b
        """
        return np.all(a <= b) and np.any(a < b)
    
    @classmethod
    def calculate_hypervolume(cls,
                              results: Dict[SolverType, OptimizationResult],
                              reference_point: np.ndarray) -> float:
        """
        计算超体积指标（多目标）
        
        Args:
            results: 结果字典
            reference_point: 参考点
        
        Returns:
            超体积值
        """
        # 收集所有目标值
        points = np.array([r.objective_values for r in results.values()])
        
        # 简化的超体积计算（2目标）
        if points.shape[1] == 2:
            # 排序
            sorted_idx = np.argsort(points[:, 0])
            points = points[sorted_idx]
            
            hv = 0.0
            prev_x = reference_point[0]
            
            for point in points:
                if point[0] < reference_point[0] and point[1] < reference_point[1]:
                    width = prev_x - point[0]
                    height = reference_point[1] - point[1]
                    hv += width * height
                    prev_x = point[0]
            
            return hv
        
        return 0.0
