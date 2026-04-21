"""
优化引擎完整测试
================

测试所有求解器和功能

作者: 小彩
日期: 2026-04-19
"""

import sys
import os
import time

sys.path.insert(0, r'D:\物流路径规划系统项目\backend')

from app.services.optimization_engine import (
    SolverFactory,
    CVRPProblem,
    MultiObjectiveVRP,
    VRPData,
    ResultComparator,
    OptimizationVisualizer,
    SolverType
)


def test_all_solvers():
    """测试所有求解器"""
    print("=" * 60)
    print("测试所有求解器")
    print("=" * 60)
    
    # 列出可用求解器
    available = SolverFactory.list_available_solvers()
    print(f"\n可用求解器: {[s.value for s in available]}")
    
    # 创建测试问题
    data = VRPData.generate_random(n_customers=15, seed=42)
    problem = CVRPProblem(data)
    
    results = {}
    
    for solver_type in available:
        print(f"\n测试 {solver_type.value}...")
        
        try:
            start = time.time()
            solver = SolverFactory.create_solver(solver_type)
            result = solver.solve(problem, time_limit=10)
            
            results[solver_type] = result
            
            print(f"  ✅ 成功")
            print(f"     目标值: {result.primary_objective:.2f}")
            print(f"     求解时间: {result.solve_time:.2f}s")
        
        except Exception as e:
            print(f"  ❌ 失败: {e}")
    
    return results


def test_comparison(results):
    """测试对比功能"""
    print("\n" + "=" * 60)
    print("测试结果对比")
    print("=" * 60)
    
    if not results:
        print("没有结果可对比")
        return
    
    comparison = ResultComparator.compare(results)
    
    print(f"\n最佳求解器: {comparison.best_solver.value if comparison.best_solver else 'N/A'}")
    print("\n排名:")
    for rank, (solver, score) in enumerate(comparison.rankings, 1):
        print(f"  {rank}. {solver.value}: {score:.4f}")


def test_multi_objective():
    """测试多目标优化"""
    print("\n" + "=" * 60)
    print("测试多目标优化")
    print("=" * 60)
    
    data = VRPData.generate_random(n_customers=10, seed=42)
    problem = MultiObjectiveVRP(data)
    
    print(f"\n目标数: {problem.n_objectives}")
    
    # 测试 pymoo NSGA-II
    if SolverFactory.is_available(SolverType.PYMOO_NSGA2):
        solver = SolverFactory.create_solver(SolverType.PYMOO_NSGA2)
        result = solver.solve(problem, n_gen=30)
        
        print(f"\nNSGA-II 结果:")
        print(f"  目标值: {result.objective_values}")
        print(f"  Pareto 前沿大小: {result.metadata.get('pareto_front_size', 1)}")


def test_recommendation():
    """测试推荐功能"""
    print("\n" + "=" * 60)
    print("测试求解器推荐")
    print("=" * 60)
    
    test_cases = [
        {'n_orders': 10, 'need_exact': False},
        {'n_orders': 50, 'need_exact': False},
        {'n_orders': 20, 'need_exact': True},
        {'n_orders': 100, 'need_exact': False},
    ]
    
    for case in test_cases:
        from app.services.optimization_engine.solver_factory import SolverFactory
        recommended = SolverFactory.recommend_solvers(
            problem_type=None,  # 简化
            n_customers=case['n_orders']
        )
        
        if recommended:
            print(f"\n{case['n_orders']}订单: 推荐 {[s.value for s in recommended]}")


def main():
    """主测试"""
    print("=" * 60)
    print("优化引擎完整测试")
    print("=" * 60)
    
    # 测试求解器
    results = test_all_solvers()
    
    # 测试对比
    test_comparison(results)
    
    # 测试多目标
    test_multi_objective()
    
    # 测试推荐
    test_recommendation()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
