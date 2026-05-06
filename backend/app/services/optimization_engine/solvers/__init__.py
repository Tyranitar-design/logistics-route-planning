"""
求解器模块
=========

包含各种优化求解器的实现

作者: 小彩
日期: 2026-04-19
更新: 2026-04-25 添加 PyVRP、DRL-VRP
"""

from .ortools_solver import ORToolsSolver
from .pymoo_solver import PymooNSGA2Solver, PymooNSGA3Solver
from .genetic_solver import GeneticSolver
from .gurobi_solver import GurobiSolver, GurobiVRPTWSolver
from .alns_solver import ALNSSolver
from .column_generation_solver import ColumnGenerationSolver
from .lagrangian_solver import LagrangianSolver

# 新增求解器 (2026-04-25)
try:
    from .pyvrp_solver import PyVRPSolver
except ImportError:
    PyVRPSolver = None

try:
    from .drl_vrp_solver import DRLVRPSolver
except ImportError:
    DRLVRPSolver = None

__all__ = [
    'ORToolsSolver',
    'PymooNSGA2Solver',
    'PymooNSGA3Solver',
    'GeneticSolver',
    'GurobiSolver',
    'GurobiVRPTWSolver',
    'ALNSSolver',
    'ColumnGenerationSolver',
    'LagrangianSolver',
    'PyVRPSolver',
    'DRLVRPSolver',
]
