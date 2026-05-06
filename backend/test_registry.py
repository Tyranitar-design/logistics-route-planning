"""测试求解器注册"""
import sys
sys.path.insert(0, r'D:\物流路径规划系统项目\backend')

from app.services.optimization_engine.base import SolverRegistry, SolverType
from app.services.optimization_engine.solvers import GurobiSolver, GurobiVRPTWSolver

print("注册的求解器:")
for st in SolverRegistry.list_solvers():
    solver_class = SolverRegistry._solvers.get(st)
    if solver_class:
        print(f"  {st.value}: {solver_class.__name__}")

print("\n检查 Gurobi 类型:")
print(f"  GUROBI: {SolverType.GUROBI}")
print(f"  GUROBI_VRPTW: {SolverType.GUROBI_VRPTW}")
