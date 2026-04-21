"""
优化引擎基础类
=============

定义统一的问题接口、求解器接口和结果类

作者: 小彩
日期: 2026-04-19
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import time


class SolverType(Enum):
    """求解器类型"""
    GUROBI = "gurobi"           # Gurobi 精确求解
    GUROBI_VRPTW = "gurobi_vrptw"  # Gurobi VRPTW
    ORTOOLS = "ortools"         # OR-Tools 启发式
    PYMOO_NSGA2 = "pymoo_nsga2" # pymoo NSGA-II
    PYMOO_NSGA3 = "pymoo_nsga3" # pymoo NSGA-III
    GENETIC = "genetic"         # 遗传算法
    ALNS = "alns"               # 自适应大邻域搜索
    COLUMN_GENERATION = "column_generation"  # 列生成
    LAGRANGIAN = "lagrangian"   # 拉格朗日松弛


class ProblemType(Enum):
    """问题类型"""
    VRP = "vrp"                 # 车辆路径问题
    CVRP = "cvrp"               # 容量约束VRP
    VRPTW = "vrptw"             # 带时间窗VRP
    TSP = "tsp"                 # 旅行商问题
    FACILITY_LOCATION = "facility_location"  # 设施选址
    KNAPSACK = "knapsack"       # 背包问题
    SCHEDULING = "scheduling"   # 调度问题
    COLD_CHAIN = "cold_chain"   # 冷链配送
    MULTI_OBJECTIVE = "multi_objective"  # 多目标优化


@dataclass
class OptimizationResult:
    """优化结果"""
    # 基本信息
    solver_name: str                    # 求解器名称
    problem_type: ProblemType           # 问题类型
    
    # 解
    solution: Any                       # 解（问题相关）
    objective_values: np.ndarray        # 目标值
    
    # 性能指标
    solve_time: float                   # 求解时间（秒）
    gap: Optional[float] = None         # 最优间隙
    iterations: int = 0                 # 迭代次数
    
    # 额外信息
    routes: Optional[List[List[int]]] = None  # 路线（VRP问题）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据
    
    @property
    def is_optimal(self) -> bool:
        """是否最优"""
        return self.gap is not None and self.gap < 1e-6
    
    @property
    def primary_objective(self) -> float:
        """主目标值"""
        return self.objective_values[0]
    
    def __str__(self) -> str:
        s = f"求解器: {self.solver_name}\n"
        s += f"问题类型: {self.problem_type.value}\n"
        s += f"目标值: {self.objective_values}\n"
        s += f"求解时间: {self.solve_time:.2f}s\n"
        if self.gap is not None:
            s += f"最优间隙: {self.gap:.2%}\n"
        return s


class OptimizationProblem(ABC):
    """
    优化问题基类
    
    所有具体问题需要继承此类并实现相关方法
    """
    
    def __init__(self, name: str = "OptimizationProblem"):
        self.name = name
        self.problem_type: ProblemType = ProblemType.VRP
        self.n_objectives: int = 1
        self.n_variables: int = 0
        self.n_constraints: int = 0
    
    @abstractmethod
    def evaluate(self, solution: Any) -> np.ndarray:
        """
        评估解的目标值
        
        Args:
            solution: 解（问题相关）
        
        Returns:
            目标值数组
        """
        pass
    
    @abstractmethod
    def is_feasible(self, solution: Any) -> bool:
        """
        检查解是否可行
        
        Args:
            solution: 解
        
        Returns:
            是否可行
        """
        pass
    
    def get_initial_solution(self) -> Any:
        """
        获取初始解（可选）
        
        Returns:
            初始解
        """
        return None
    
    def get_problem_size(self) -> Tuple[int, int, int]:
        """
        获取问题规模
        
        Returns:
            (变量数, 约束数, 目标数)
        """
        return (self.n_variables, self.n_constraints, self.n_objectives)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', type={self.problem_type.value})"


class OptimizationSolver(ABC):
    """
    优化求解器基类
    
    所有具体求解器需要继承此类并实现 solve 方法
    """
    
    def __init__(self, name: str, solver_type: SolverType):
        self.name = name
        self.solver_type = solver_type
        self.parameters: Dict[str, Any] = {}
    
    @abstractmethod
    def solve(self, problem: OptimizationProblem, 
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """
        求解优化问题
        
        Args:
            problem: 优化问题
            time_limit: 时间限制（秒）
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        pass
    
    def set_parameter(self, key: str, value: Any):
        """设置参数"""
        self.parameters[key] = value
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取参数"""
        return self.parameters.get(key, default)
    
    def is_available(self) -> bool:
        """
        检查求解器是否可用
        
        Returns:
            是否可用
        """
        return True
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', type={self.solver_type.value})"


class SolverRegistry:
    """
    求解器注册表
    
    管理所有可用的求解器
    """
    
    _solvers: Dict[SolverType, type] = {}
    
    @classmethod
    def register(cls, solver_type: SolverType):
        """
        注册求解器装饰器
        
        用法:
            @SolverRegistry.register(SolverType.GUROBI)
            class GurobiSolver(OptimizationSolver):
                pass
        """
        def decorator(solver_class: type):
            cls._solvers[solver_type] = solver_class
            return solver_class
        return decorator
    
    @classmethod
    def get_solver(cls, solver_type: SolverType, **kwargs) -> OptimizationSolver:
        """
        获取求解器实例
        
        Args:
            solver_type: 求解器类型
            **kwargs: 求解器参数
        
        Returns:
            求解器实例
        """
        if solver_type not in cls._solvers:
            raise ValueError(f"未注册的求解器类型: {solver_type}")
        
        solver_class = cls._solvers[solver_type]
        return solver_class(**kwargs)
    
    @classmethod
    def list_solvers(cls) -> List[SolverType]:
        """列出所有已注册的求解器"""
        return list(cls._solvers.keys())
    
    @classmethod
    def is_available(cls, solver_type: SolverType) -> bool:
        """检查求解器是否可用"""
        if solver_type not in cls._solvers:
            return False
        
        try:
            solver = cls.get_solver(solver_type)
            return solver.is_available()
        except:
            return False


def timeit(func):
    """计时装饰器"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        if isinstance(result, OptimizationResult):
            result.solve_time = elapsed
        
        return result
    return wrapper
