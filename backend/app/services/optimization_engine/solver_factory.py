"""
求解器工厂
==========

根据问题类型和用户选择创建合适的求解器

作者: 小彩
日期: 2026-04-19
"""

from typing import Dict, List, Optional, Type
from .base import (
    OptimizationSolver, 
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    ProblemType,
    SolverRegistry
)

# 导入求解器以触发注册（必须在 SolverFactory 类定义之前）
from .solvers import (
    ORToolsSolver,
    PymooNSGA2Solver,
    PymooNSGA3Solver,
    GeneticSolver,
    GurobiSolver,
    GurobiVRPTWSolver,
    ALNSSolver,
    ColumnGenerationSolver,
    LagrangianSolver
)


class SolverFactory:
    """
    求解器工厂类
    
    根据问题类型和用户偏好创建合适的求解器
    """
    
    # 求解器推荐映射
    RECOMMENDATIONS: Dict[ProblemType, List[SolverType]] = {
        ProblemType.VRP: [
            SolverType.ORTOOLS,      # 首选：快速
            SolverType.GUROBI,       # 精确求解
            SolverType.GENETIC,      # 启发式
        ],
        ProblemType.CVRP: [
            SolverType.ORTOOLS,
            SolverType.GUROBI,
            SolverType.COLUMN_GENERATION,  # 大规模
            SolverType.ALNS,
        ],
        ProblemType.VRPTW: [
            SolverType.ORTOOLS,
            SolverType.GUROBI,
        ],
        ProblemType.FACILITY_LOCATION: [
            SolverType.GUROBI,
            SolverType.LAGRANGIAN,
        ],
        ProblemType.MULTI_OBJECTIVE: [
            SolverType.PYMOO_NSGA2,  # 2-3目标
            SolverType.PYMOO_NSGA3,  # 4+目标
        ],
        ProblemType.COLD_CHAIN: [
            SolverType.PYMOO_NSGA2,
            SolverType.ALNS,
        ],
    }
    
    @classmethod
    def create_solver(cls, 
                      solver_type: SolverType,
                      **kwargs) -> OptimizationSolver:
        """
        创建求解器
        
        Args:
            solver_type: 求解器类型
            **kwargs: 求解器参数
        
        Returns:
            求解器实例
        """
        return SolverRegistry.get_solver(solver_type, **kwargs)
    
    @classmethod
    def recommend_solvers(cls, 
                          problem_type: ProblemType,
                          available_only: bool = True) -> List[SolverType]:
        """
        推荐求解器
        
        Args:
            problem_type: 问题类型
            available_only: 是否只返回可用的求解器
        
        Returns:
            推荐的求解器列表
        """
        recommended = cls.RECOMMENDATIONS.get(problem_type, [])
        
        if available_only:
            recommended = [s for s in recommended if cls.is_available(s)]
        
        return recommended
    
    @classmethod
    def get_best_solver(cls, 
                        problem_type: ProblemType) -> Optional[SolverType]:
        """
        获取最佳求解器
        
        Args:
            problem_type: 问题类型
        
        Returns:
            最佳求解器类型（第一个可用的推荐求解器）
        """
        available = cls.recommend_solvers(problem_type, available_only=True)
        return available[0] if available else None
    
    @classmethod
    def is_available(cls, solver_type: SolverType) -> bool:
        """检查求解器是否可用"""
        return SolverRegistry.is_available(solver_type)
    
    @classmethod
    def list_all_solvers(cls) -> List[SolverType]:
        """列出所有求解器"""
        return list(SolverType)
    
    @classmethod
    def list_available_solvers(cls) -> List[SolverType]:
        """列出所有可用的求解器"""
        return [s for s in SolverType if cls.is_available(s)]
    
    @classmethod
    def solve_with_best(cls,
                        problem: OptimizationProblem,
                        time_limit: float = 60.0,
                        **kwargs) -> OptimizationResult:
        """
        使用最佳求解器求解
        
        Args:
            problem: 优化问题
            time_limit: 时间限制
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        best_type = cls.get_best_solver(problem.problem_type)
        
        if best_type is None:
            raise RuntimeError(f"没有可用的求解器处理问题类型: {problem.problem_type}")
        
        solver = cls.create_solver(best_type)
        return solver.solve(problem, time_limit=time_limit, **kwargs)
    
    @classmethod
    def solve_with_all(cls,
                       problem: OptimizationProblem,
                       solver_types: Optional[List[SolverType]] = None,
                       time_limit: float = 60.0,
                       **kwargs) -> Dict[SolverType, OptimizationResult]:
        """
        使用多个求解器求解并对比
        
        Args:
            problem: 优化问题
            solver_types: 求解器列表（None 则使用推荐）
            time_limit: 时间限制
            **kwargs: 其他参数
        
        Returns:
            {求解器类型: 结果} 字典
        """
        if solver_types is None:
            solver_types = cls.recommend_solvers(problem.problem_type, available_only=True)
        
        results = {}
        
        for solver_type in solver_types:
            try:
                solver = cls.create_solver(solver_type)
                result = solver.solve(problem, time_limit=time_limit, **kwargs)
                results[solver_type] = result
            except Exception as e:
                print(f"求解器 {solver_type.value} 失败: {e}")
        
        return results
    
    @classmethod
    def get_solver_info(cls, solver_type: SolverType) -> Dict[str, str]:
        """
        获取求解器信息
        
        Args:
            solver_type: 求解器类型
        
        Returns:
            求解器信息字典
        """
        info = {
            SolverType.GUROBI: {
                "name": "Gurobi",
                "description": "商业级数学优化求解器，支持精确求解",
                "pros": "求解质量高，支持大规模问题",
                "cons": "需要许可证",
                "best_for": "精确求解、大规模MIP"
            },
            SolverType.GUROBI_VRPTW: {
                "name": "Gurobi-VRPTW",
                "description": "Gurobi 带时间窗求解器",
                "pros": "支持时间窗约束",
                "cons": "需要许可证",
                "best_for": "VRPTW问题"
            },
            SolverType.ORTOOLS: {
                "name": "OR-Tools",
                "description": "Google开源优化工具，支持多种启发式算法",
                "pros": "免费开源，求解速度快",
                "cons": "启发式方法可能不是最优",
                "best_for": "快速求解、原型开发"
            },
            SolverType.PYMOO_NSGA2: {
                "name": "NSGA-II (pymoo)",
                "description": "经典多目标优化算法",
                "pros": "多目标效果好，Pareto前沿质量高",
                "cons": "仅限2-3目标效果最好",
                "best_for": "多目标优化（2-3目标）"
            },
            SolverType.PYMOO_NSGA3: {
                "name": "NSGA-III (pymoo)",
                "description": "高维多目标优化算法",
                "pros": "支持4+目标",
                "cons": "需要设置参考点",
                "best_for": "高维多目标优化"
            },
            SolverType.ALNS: {
                "name": "ALNS",
                "description": "自适应大邻域搜索",
                "pros": "求解速度快，适合大规模问题",
                "cons": "参数需要调整",
                "best_for": "大规模VRP"
            },
            SolverType.COLUMN_GENERATION: {
                "name": "Column Generation",
                "description": "列生成算法",
                "pros": "大规模问题有效",
                "cons": "实现复杂",
                "best_for": "大规模线性规划"
            },
            SolverType.GENETIC: {
                "name": "Genetic Algorithm",
                "description": "遗传算法",
                "pros": "通用性强，易实现",
                "cons": "收敛速度可能较慢",
                "best_for": "一般组合优化"
            },
            SolverType.LAGRANGIAN: {
                "name": "Lagrangian Relaxation",
                "description": "拉格朗日松弛",
                "pros": "提供下界，适合约束复杂的问题",
                "cons": "需要问题结构适合松弛",
                "best_for": "约束复杂的问题"
            }
        }
        
        return info.get(solver_type, {
            "name": solver_type.value,
            "description": "未知求解器"
        })
