"""
Gurobi 求解器
=============

使用 Gurobi 进行精确求解

支持：
- VRP/CVRP/VRPTW
- MTZ 消子回路约束
- 多目标优化

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Optional, Dict, Any
from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    SolverRegistry,
    timeit
)


@SolverRegistry.register(SolverType.GUROBI)
class GurobiSolver(OptimizationSolver):
    """
    Gurobi 精确求解器
    
    使用 MTZ 公式消子回路
    """
    
    def __init__(self,
                 mip_focus: int = 1,  # 1=可行解, 2=最优解, 3=边界
                 heuristics: float = 0.5,
                 **kwargs):
        """
        初始化
        
        Args:
            mip_focus: MIP 求解重点
            heuristics: 启发式参数
            **kwargs: 其他参数
        """
        super().__init__("Gurobi", SolverType.GUROBI)
        self.mip_focus = mip_focus
        self.heuristics = heuristics
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        """检查 Gurobi 是否可用"""
        try:
            import gurobipy as gp
            return True
        except ImportError:
            return False
    
    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              mip_gap: float = 0.01,
              **kwargs) -> OptimizationResult:
        """
        求解 VRP 问题
        
        Args:
            problem: VRP 问题
            time_limit: 时间限制（秒）
            mip_gap: MIP 间隙容忍度
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        import gurobipy as gp
        from gurobipy import GRB
        
        data = problem.data
        
        # 创建模型
        model = gp.Model("VRP_Gurobi")
        model.setParam('OutputFlag', 0)
        model.setParam('TimeLimit', time_limit)
        model.setParam('MIPGap', mip_gap)
        model.setParam('MIPFocus', self.mip_focus)
        model.setParam('Heuristics', self.heuristics)
        
        # 节点数和车辆数
        n = data.n_customers  # 客户数
        V = n + 1  # 总节点数（含仓库）
        K = data.n_vehicles
        Q = data.vehicle_capacity
        c = data.distance_matrix
        # 需求转换为列表确保索引正确
        demands_list = [0] + [int(d) for d in data.demands]
        d = np.array(demands_list)  # 仓库需求为0
        
        # ========================
        # 决策变量
        # ========================
        
        # x[i,j,k] = 1 如果车辆 k 从 i 到 j
        x = model.addVars(V, V, K, vtype=GRB.BINARY, name="x")
        
        # u[i,k] = 车辆 k 在节点 i 的累计负载（MTZ）
        u = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, ub=Q, name="u")
        
        # ========================
        # 目标函数
        # ========================
        
        model.setObjective(
            gp.quicksum(c[i][j] * x[i, j, k] 
                       for i in range(V) for j in range(V) for k in range(K)),
            GRB.MINIMIZE
        )
        
        # ========================
        # 约束条件
        # ========================
        
        # C1: 每个客户被访问一次
        for j in range(1, V):
            model.addConstr(
                gp.quicksum(x[i, j, k] for i in range(V) for k in range(K)) == 1,
                name=f"visit_{j}"
            )
        
        # C2: 流平衡
        for k in range(K):
            for j in range(V):
                model.addConstr(
                    gp.quicksum(x[i, j, k] for i in range(V)) ==
                    gp.quicksum(x[j, i, k] for i in range(V)),
                    name=f"flow_{j}_{k}"
                )
        
        # C3: 车辆从仓库出发
        for k in range(K):
            model.addConstr(
                gp.quicksum(x[0, j, k] for j in range(1, V)) == 1,
                name=f"depart_{k}"
            )
        
        # C4: 车辆返回仓库
        for k in range(K):
            model.addConstr(
                gp.quicksum(x[i, 0, k] for i in range(1, V)) == 1,
                name=f"return_{k}"
            )
        
        # C5: MTZ 消子回路 + 容量约束
        for k in range(K):
            for i in range(1, V):
                for j in range(1, V):
                    if i != j:
                        model.addConstr(
                            u[i, k] + d[j] - u[j, k] <= Q * (1 - x[i, j, k]),
                            name=f"mtz_{i}_{j}_{k}"
                        )
        
        # C6: 负载下界
        for k in range(K):
            for i in range(1, V):
                model.addConstr(
                    d[i] <= u[i, k],
                    name=f"lb_u_{i}_{k}"
                )
        
        # ========================
        # 求解
        # ========================
        
        model.optimize()
        
        if model.status not in [GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SOLUTION_LIMIT]:
            raise RuntimeError(f"Gurobi 求解失败，状态码: {model.status}")
        
        # ========================
        # 提取解
        # ========================
        
        routes = []
        for k in range(K):
            route = [0]
            current = 0
            
            while True:
                next_node = None
                for j in range(V):
                    if j != current and x[current, j, k].X > 0.5:
                        next_node = j
                        break
                
                if next_node is None or next_node == 0:
                    break
                
                route.append(next_node)
                current = next_node
            
            if len(route) > 1:
                route.append(0)
                routes.append(route)
        
        # 计算间隙
        gap = model.MIPGap if model.status == GRB.TIME_LIMIT else 0.0
        
        # 创建结果
        result = OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=routes,
            objective_values=np.array([model.ObjVal]),
            solve_time=0.0,  # 由装饰器填充
            gap=gap,
            routes=routes,
            metadata={
                'model_status': model.status,
                'node_count': model.NodeCount,
                'iteration_count': model.IterCount
            }
        )
        
        return result


@SolverRegistry.register(SolverType.GUROBI_VRPTW)
class GurobiVRPTWSolver(OptimizationSolver):
    """
    Gurobi VRPTW 求解器
    
    带时间窗约束的 VRP
    """
    
    def __init__(self, **kwargs):
        super().__init__("Gurobi-VRPTW", SolverType.GUROBI)
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        try:
            import gurobipy as gp
            return True
        except ImportError:
            return False
    
    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """求解 VRPTW"""
        import gurobipy as gp
        from gurobipy import GRB
        
        data = problem.data
        tw = problem.time_windows
        st = problem.service_times
        
        model = gp.Model("VRPTW_Gurobi")
        model.setParam('OutputFlag', 0)
        model.setParam('TimeLimit', time_limit)
        
        n = data.n_customers
        V = n + 1
        K = min(data.n_vehicles, 10)  # 限制车辆数避免模型过大
        Q = data.vehicle_capacity
        c = data.distance_matrix
        d = np.concatenate([[0], data.demands])
        
        # 变量
        x = model.addVars(V, V, K, vtype=GRB.BINARY, name="x")
        u = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, name="u")  # 负载
        t = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, name="t")  # 到达时间
        
        # 大M
        M = 1000
        
        # 目标：最小化总距离
        model.setObjective(
            gp.quicksum(c[i][j] * x[i, j, k] 
                       for i in range(V) for j in range(V) for k in range(K)),
            GRB.MINIMIZE
        )
        
        # 访问约束
        for j in range(1, V):
            model.addConstr(
                gp.quicksum(x[i, j, k] for i in range(V) for k in range(K)) == 1
            )
        
        # 流平衡
        for k in range(K):
            for j in range(V):
                model.addConstr(
                    gp.quicksum(x[i, j, k] for i in range(V)) ==
                    gp.quicksum(x[j, i, k] for i in range(V))
                )
        
        # 从仓库出发
        for k in range(K):
            model.addConstr(gp.quicksum(x[0, j, k] for j in range(1, V)) == 1)
            model.addConstr(gp.quicksum(x[i, 0, k] for i in range(1, V)) == 1)
        
        # MTZ
        for k in range(K):
            for i in range(1, V):
                for j in range(1, V):
                    if i != j:
                        model.addConstr(
                            u[i, k] + d[j] - u[j, k] <= Q * (1 - x[i, j, k])
                        )
        
        # 时间窗约束
        for k in range(K):
            # 仓库时间窗
            model.addConstr(t[0, k] >= tw[0, 0])
            model.addConstr(t[0, k] <= tw[0, 1])
            
            for i in range(1, V):
                # 到达时间约束
                model.addConstr(t[i, k] >= tw[i, 0])
                model.addConstr(t[i, k] <= tw[i, 1] + M * (1 - 
                    gp.quicksum(x[j, i, k] for j in range(V))))
        
        # 时间连续性
        for k in range(K):
            for i in range(V):
                for j in range(1, V):
                    if i != j:
                        model.addConstr(
                            t[i, k] + st[i] + c[i][j] - t[j, k] <= 
                            M * (1 - x[i, j, k])
                        )
        
        model.optimize()
        
        if model.status not in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            raise RuntimeError("求解失败")
        
        # 提取路线
        routes = []
        for k in range(K):
            route = [0]
            current = 0
            while True:
                next_node = None
                for j in range(V):
                    if j != current and x[current, j, k].X > 0.5:
                        next_node = j
                        break
                if next_node is None or next_node == 0:
                    break
                route.append(next_node)
                current = next_node
            if len(route) > 1:
                route.append(0)
                routes.append(route)
        
        gap = model.MIPGap if model.status == GRB.TIME_LIMIT else 0.0
        
        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=routes,
            objective_values=np.array([model.ObjVal]),
            solve_time=0.0,
            gap=gap,
            routes=routes
        )
