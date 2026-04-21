"""
优化引擎模块
===========

统一的优化算法接口，支持多种求解器：
- Gurobi（精确求解）
- pymoo（多目标优化）
- OR-Tools（启发式求解）
- 自定义算法（ALNS、遗传算法等）

作者: 小彩
日期: 2026-04-19
"""

from .base import (
    OptimizationProblem,
    OptimizationSolver,
    OptimizationResult,
    SolverType,
    ProblemType
)

from .problems import (
    VRPData,
    VRPProblem,
    CVRPProblem,
    VRPTWProblem,
    FacilityLocationProblem,
    MultiObjectiveVRP
)

from .solver_factory import SolverFactory
from .comparison import ResultComparator
from .visualization import OptimizationVisualizer

# 导入所有求解器以触发注册
from .solvers import (
    ORToolsSolver,
    PymooNSGA2Solver,
    PymooNSGA3Solver,
    GeneticSolver,
    GurobiSolver,
    GurobiVRPTWSolver,
    ALNSSolver,
    ColumnGenerationSolver
)

__all__ = [
    # 基础类
    'OptimizationProblem',
    'OptimizationSolver', 
    'OptimizationResult',
    'SolverType',
    'ProblemType',
    
    # 数据类
    'VRPData',
    
    # 问题定义
    'VRPProblem',
    'CVRPProblem',
    'VRPTWProblem',
    'FacilityLocationProblem',
    'MultiObjectiveVRP',
    
    # 工厂类
    'SolverFactory',
    
    # 对比工具
    'ResultComparator',
    
    # 可视化
    'OptimizationVisualizer',
]

__version__ = '1.0.0'
