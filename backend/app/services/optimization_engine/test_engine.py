"""
优化引擎测试
============

测试基础架构和求解器

作者: 小彩
日期: 2026-04-19
"""

import sys
import os

# 添加路径
sys.path.insert(0, r'D:\物流路径规划系统项目\backend')

from app.services.optimization_engine import (
    SolverFactory,
    VRPProblem,
    CVRPProblem,
    MultiObjectiveVRP,
    VRPData,
    ResultComparator,
    SolverType
)


def test_basic_structure():
    """测试基础结构"""
    print("=" * 60)
    print("测试1: 基础结构")
    print("=" * 60)
    
    # 测试数据生成
    data = VRPData.generate_random(n_customers=10, seed=42)
    print(f"\n✅ 数据生成成功")
    print(f"   客户数: {data.n_customers}")
    print(f"   车辆数: {data.n_vehicles}")
    print(f"   总需求: {data.demands.sum()}")
    
    # 测试问题创建
    problem = VRPProblem(data)
    print(f"\n✅ 问题创建成功")
    print(f"   问题类型: {problem.problem_type.value}")
    print(f"   目标数: {problem.n_objectives}")
    
    # 测试初始解
    initial = problem.get_initial_solution()
    print(f"\n✅ 初始解生成成功")
    print(f"   路线数: {len(initial)}")
    
    # 测试评估
    obj = problem.evaluate(initial)
    print(f"\n✅ 评估成功")
    print(f"   目标值: {obj}")
    
    return True


def test_solver_factory():
    """测试求解器工厂"""
    print("\n" + "=" * 60)
    print("测试2: 求解器工厂")
    print("=" * 60)
    
    # 列出所有求解器
    all_solvers = SolverFactory.list_all_solvers()
    print(f"\n所有求解器: {[s.value for s in all_solvers]}")
    
    # 列出可用求解器
    available = SolverFactory.list_available_solvers()
    print(f"可用求解器: {[s.value for s in available]}")
    
    # 推荐
    from app.services.optimization_engine.base import ProblemType
    recommended = SolverFactory.recommend_solvers(ProblemType.VRP)
    print(f"VRP推荐: {[s.value for s in recommended]}")
    
    return True


def test_genetic_solver():
    """测试遗传算法求解器"""
    print("\n" + "=" * 60)
    print("测试3: 遗传算法求解器")
    print("=" * 60)
    
    # 创建问题
    data = VRPData.generate_random(n_customers=10, seed=42)
    problem = CVRPProblem(data)
    
    # 创建求解器
    solver = SolverFactory.create_solver(SolverType.GENETIC, pop_size=50)
    
    print(f"\n求解器: {solver.name}")
    print(f"可用: {solver.is_available()}")
    
    # 求解
    result = solver.solve(problem, time_limit=10, n_gen=50)
    
    print(f"\n✅ 求解成功")
    print(f"   目标值: {result.objective_values}")
    print(f"   求解时间: {result.solve_time:.2f}s")
    print(f"   路线数: {len(result.routes)}")
    
    return True


def test_multi_objective():
    """测试多目标优化"""
    print("\n" + "=" * 60)
    print("测试4: 多目标优化")
    print("=" * 60)
    
    # 创建多目标问题
    data = VRPData.generate_random(n_customers=10, seed=42)
    problem = MultiObjectiveVRP(data)
    
    print(f"\n问题类型: {problem.problem_type.value}")
    print(f"目标数: {problem.n_objectives}")
    
    # 获取初始解
    initial = problem.get_initial_solution()
    obj = problem.evaluate(initial)
    
    print(f"\n✅ 初始解评估成功")
    print(f"   总距离: {obj[0]:.2f}")
    print(f"   总时间: {obj[1]:.2f}")
    print(f"   车辆数: {int(obj[2])}")
    
    return True


def test_comparison():
    """测试结果对比"""
    print("\n" + "=" * 60)
    print("测试5: 结果对比")
    print("=" * 60)
    
    # 创建问题
    data = VRPData.generate_random(n_customers=10, seed=42)
    problem = CVRPProblem(data)
    
    # 用多个求解器求解
    results = SolverFactory.solve_with_all(
        problem,
        solver_types=[SolverType.GENETIC],  # 只测试遗传算法
        time_limit=10
    )
    
    print(f"\n求解器结果:")
    for solver_type, result in results.items():
        print(f"  {solver_type.value}: {result.primary_objective:.2f}")
    
    # 对比
    if results:
        comparison = ResultComparator.compare(results)
        report = ResultComparator.generate_report(comparison)
        print(report)
    
    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("优化引擎基础架构测试")
    print("=" * 60)
    
    tests = [
        ("基础结构", test_basic_structure),
        ("求解器工厂", test_solver_factory),
        ("遗传算法求解器", test_genetic_solver),
        ("多目标优化", test_multi_objective),
        ("结果对比", test_comparison),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {name} 测试通过")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
