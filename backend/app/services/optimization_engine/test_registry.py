"""
测试求解器注册
"""

import sys
sys.path.insert(0, r'D:\物流路径规划系统项目\backend')

# 先导入基础类
from app.services.optimization_engine.base import SolverRegistry, SolverType

print("=" * 50)
print("测试求解器注册")
print("=" * 50)

# 检查注册表
print(f"\n已注册的求解器: {SolverRegistry.list_solvers()}")

# 导入求解器（触发注册）
print("\n导入求解器...")
from app.services.optimization_engine.solvers import (
    ORToolsSolver,
    GeneticSolver,
    PymooNSGA2Solver,
    GurobiSolver,
    ALNSSolver
)

print(f"\n导入后已注册的求解器: {SolverRegistry.list_solvers()}")

# 检查可用性
print("\n检查求解器可用性:")
for solver_type in SolverType:
    try:
        available = SolverRegistry.is_available(solver_type)
        print(f"  {solver_type.value}: {'✅ 可用' if available else '❌ 不可用'}")
    except Exception as e:
        print(f"  {solver_type.value}: ❌ 错误 - {e}")

# 尝试创建求解器
print("\n尝试创建求解器:")
for solver_type in [SolverType.GENETIC, SolverType.ORTOOLS]:
    try:
        solver = SolverRegistry.get_solver(solver_type)
        print(f"  {solver_type.value}: ✅ 创建成功 - {solver.name}")
    except Exception as e:
        print(f"  {solver_type.value}: ❌ 创建失败 - {e}")
