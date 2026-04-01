#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级路径优化算法服务
包含：蚁群算法(ACO)、粒子群优化(PSO)、深度强化学习(DRL)
"""

import logging
import random
import math
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, field
from copy import deepcopy
from collections import defaultdict
from app.models import db
from app.models import Order, Vehicle, Node

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    best_route: List[int]  # 最优路径节点序列
    best_cost: float
    best_distance: float
    algorithm: str
    iterations: int
    convergence_history: List[float]
    execution_time: float
    metadata: Dict = field(default_factory=dict)
    error: str = None


@dataclass
class ACOParameters:
    """蚁群算法参数"""
    ant_count: int = 30          # 蚂蚁数量
    max_iterations: int = 100    # 最大迭代次数
    alpha: float = 1.0           # 信息素重要程度
    beta: float = 2.0            # 启发函数重要程度
    rho: float = 0.5             # 信息素挥发系数
    q: float = 100.0             # 信息素增强系数
    initial_pheromone: float = 1.0  # 初始信息素浓度


@dataclass
class PSOParameters:
    """粒子群优化参数"""
    particle_count: int = 30     # 粒子数量
    max_iterations: int = 100    # 最大迭代次数
    w: float = 0.729             # 惯性权重
    c1: float = 1.494            # 个体学习因子
    c2: float = 1.494            # 社会学习因子
    v_max: float = 4.0           # 最大速度


# ==================== 蚁群算法 (ACO) ====================

class AntColonyOptimizer:
    """
    蚁群算法优化器
    模拟蚂蚁觅食行为，通过信息素更新寻找最优路径
    适用于TSP、VRP等组合优化问题
    """
    
    def __init__(self, params: ACOParameters = None):
        self.params = params or ACOParameters()
        self.pheromone_matrix = None
        self.distance_matrix = None
        self.heuristic_matrix = None
    
    def optimize(
        self,
        nodes: List[Node],
        distance_matrix: Dict[Tuple[int, int], float],
        start_node_id: int = None,
        end_node_id: int = None
    ) -> OptimizationResult:
        """
        使用蚁群算法优化路径
        
        Args:
            nodes: 节点列表
            distance_matrix: 距离矩阵 {(from_id, to_id): distance}
            start_node_id: 起点节点ID
            end_node_id: 终点节点ID
        
        Returns:
            优化结果
        """
        start_time = datetime.now()
        
        if not nodes or len(nodes) < 2:
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='ACO',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error='节点数量不足'
            )
        
        try:
            # 初始化
            node_ids = [n.id for n in nodes]
            node_count = len(node_ids)
            id_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}
            idx_to_id = {idx: nid for idx, nid in enumerate(node_ids)}
            
            # 构建距离矩阵
            dist_matrix = self._build_distance_matrix(node_ids, distance_matrix)
            
            # 构建启发式矩阵 (启发式信息 = 1/距离)
            heuristic_matrix = np.zeros((node_count, node_count))
            for i in range(node_count):
                for j in range(node_count):
                    if i != j and dist_matrix[i][j] > 0:
                        heuristic_matrix[i][j] = 1.0 / dist_matrix[i][j]
            
            # 初始化信息素矩阵
            pheromone_matrix = np.full((node_count, node_count), self.params.initial_pheromone)
            
            # 最优解记录
            best_route = []
            best_cost = float('inf')
            best_distance = 0
            convergence_history = []
            
            # 迭代优化
            for iteration in range(self.params.max_iterations):
                all_route_ids = []
                all_route_indices = []
                all_costs = []
                
                # 每只蚂蚁构建路径
                for ant in range(self.params.ant_count):
                    route_ids, cost, route_indices = self._construct_route(
                        node_count, dist_matrix, pheromone_matrix, 
                        heuristic_matrix, start_node_id, end_node_id,
                        id_to_idx, idx_to_id
                    )
                    all_route_ids.append(route_ids)
                    all_route_indices.append(route_indices)
                    all_costs.append(cost)
                    
                    # 更新最优解
                    if cost < best_cost:
                        best_cost = cost
                        best_route = route_ids
                        best_distance = self._calculate_route_distance(route_indices, dist_matrix)
                
                # 更新信息素
                pheromone_matrix = self._update_pheromone(
                    pheromone_matrix, all_route_indices, all_costs
                )
                
                convergence_history.append(best_cost)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return OptimizationResult(
                success=True,
                best_route=best_route,
                best_cost=round(best_cost, 2),
                best_distance=round(best_distance, 2),
                algorithm='ACO',
                iterations=self.params.max_iterations,
                convergence_history=[round(c, 2) for c in convergence_history],
                execution_time=round(execution_time, 3),
                metadata={
                    'ant_count': self.params.ant_count,
                    'alpha': self.params.alpha,
                    'beta': self.params.beta,
                    'rho': self.params.rho
                }
            )
        
        except Exception as e:
            logger.error(f"蚁群算法优化失败: {e}")
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='ACO',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error=str(e)
            )
    
    def _construct_route(
        self,
        node_count: int,
        dist_matrix: np.ndarray,
        pheromone_matrix: np.ndarray,
        heuristic_matrix: np.ndarray,
        start_node_id: int,
        end_node_id: int,
        id_to_idx: Dict,
        idx_to_id: Dict
    ) -> Tuple[List[int], float, List[int]]:
        """构建单条路径
        
        Returns:
            (route_ids, total_cost, route_indices) - 节点ID列表、总成本、节点索引列表
        """
        route_ids = []
        route_indices = []
        visited = set()
        total_cost = 0
        
        # 选择起点
        if start_node_id and start_node_id in id_to_idx:
            current = id_to_idx[start_node_id]
        else:
            current = random.randint(0, node_count - 1)
        
        route_ids.append(idx_to_id[current])
        route_indices.append(current)
        visited.add(current)
        
        # 构建路径
        while len(visited) < node_count:
            # 计算转移概率
            probabilities = []
            candidates = []
            
            for j in range(node_count):
                if j not in visited and dist_matrix[current][j] > 0:
                    # 信息素 × 启发式信息
                    tau = pheromone_matrix[current][j] ** self.params.alpha
                    eta = heuristic_matrix[current][j] ** self.params.beta
                    prob = tau * eta
                    probabilities.append(prob)
                    candidates.append(j)
            
            if not candidates:
                break
            
            # 轮盘赌选择
            total_prob = sum(probabilities)
            if total_prob > 0:
                probabilities = [p / total_prob for p in probabilities]
                next_node = random.choices(candidates, weights=probabilities)[0]
            else:
                next_node = random.choice(candidates)
            
            route_ids.append(idx_to_id[next_node])
            route_indices.append(next_node)
            total_cost += dist_matrix[current][next_node]
            visited.add(next_node)
            current = next_node
            
            # 如果指定了终点且到达终点，结束
            if end_node_id and idx_to_id[current] == end_node_id:
                break
        
        return route_ids, total_cost, route_indices
    
    def _update_pheromone(
        self,
        pheromone_matrix: np.ndarray,
        routes: List[List[int]],
        costs: List[float]
    ) -> np.ndarray:
        """更新信息素"""
        # 信息素挥发
        pheromone_matrix *= (1 - self.params.rho)
        
        # 信息素增强
        for route, cost in zip(routes, costs):
            if cost > 0:
                delta = self.params.q / cost
                for i in range(len(route) - 1):
                    pheromone_matrix[route[i]][route[i+1]] += delta
                    pheromone_matrix[route[i+1]][route[i]] += delta
        
        return pheromone_matrix
    
    def _build_distance_matrix(
        self,
        node_ids: List[int],
        distance_matrix: Dict
    ) -> np.ndarray:
        """构建numpy距离矩阵"""
        n = len(node_ids)
        matrix = np.full((n, n), 1000.0)  # 默认大距离
        
        for i, id1 in enumerate(node_ids):
            for j, id2 in enumerate(node_ids):
                if i == j:
                    matrix[i][j] = 0
                else:
                    key = (min(id1, id2), max(id1, id2))
                    if key in distance_matrix:
                        matrix[i][j] = distance_matrix[key]
                    elif (id1, id2) in distance_matrix:
                        matrix[i][j] = distance_matrix[(id1, id2)]
        
        return matrix
    
    def _calculate_route_distance(
        self,
        route_indices: List[int],
        dist_matrix: np.ndarray
    ) -> float:
        """计算路径总距离（使用索引）"""
        total = 0
        for i in range(len(route_indices) - 1):
            total += dist_matrix[route_indices[i]][route_indices[i+1]]
        return total


# ==================== 粒子群优化 (PSO) ====================

class ParticleSwarmOptimizer:
    """
    粒子群优化器
    模拟鸟群觅食行为，通过群体协作寻找最优解
    适用于连续优化和部分离散优化问题
    """
    
    def __init__(self, params: PSOParameters = None):
        self.params = params or PSOParameters()
    
    def optimize_route(
        self,
        nodes: List[Node],
        distance_matrix: Dict[Tuple[int, int], float],
        start_node_id: int = None,
        end_node_id: int = None
    ) -> OptimizationResult:
        """
        使用PSO优化路径（离散版本）
        
        Args:
            nodes: 节点列表
            distance_matrix: 距离矩阵
            start_node_id: 起点
            end_node_id: 终点
        
        Returns:
            优化结果
        """
        start_time = datetime.now()
        
        if not nodes or len(nodes) < 2:
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='PSO',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error='节点数量不足'
            )
        
        try:
            node_ids = [n.id for n in nodes]
            node_count = len(node_ids)
            
            # 初始化粒子群
            particles = []
            velocities = []
            personal_best = []
            personal_best_cost = []
            
            for _ in range(self.params.particle_count):
                # 随机初始化粒子位置（排列）
                particle = list(range(node_count))
                random.shuffle(particle)
                particles.append(particle)
                
                # 初始化速度（交换操作序列）
                velocity = []
                velocities.append(velocity)
                
                # 计算初始适应度
                cost = self._calculate_cost(particle, node_ids, distance_matrix)
                personal_best.append(particle.copy())
                personal_best_cost.append(cost)
            
            # 全局最优
            global_best_idx = np.argmin(personal_best_cost)
            global_best = personal_best[global_best_idx].copy()
            global_best_cost = personal_best_cost[global_best_idx]
            
            convergence_history = []
            
            # 迭代优化
            for iteration in range(self.params.max_iterations):
                for i in range(self.params.particle_count):
                    # 更新速度和位置（离散版本使用交换操作）
                    new_particle = self._update_particle_position(
                        particles[i], personal_best[i], global_best
                    )
                    
                    # 计算新位置的成本
                    new_cost = self._calculate_cost(new_particle, node_ids, distance_matrix)
                    
                    # 更新个体最优
                    if new_cost < personal_best_cost[i]:
                        personal_best[i] = new_particle.copy()
                        personal_best_cost[i] = new_cost
                        
                        # 更新全局最优
                        if new_cost < global_best_cost:
                            global_best = new_particle.copy()
                            global_best_cost = new_cost
                    
                    particles[i] = new_particle
                
                convergence_history.append(global_best_cost)
            
            # 转换最优解
            best_route = [node_ids[idx] for idx in global_best]
            best_distance = self._calculate_total_distance(best_route, distance_matrix)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return OptimizationResult(
                success=True,
                best_route=best_route,
                best_cost=round(global_best_cost, 2),
                best_distance=round(best_distance, 2),
                algorithm='PSO',
                iterations=self.params.max_iterations,
                convergence_history=[round(c, 2) for c in convergence_history],
                execution_time=round(execution_time, 3),
                metadata={
                    'particle_count': self.params.particle_count,
                    'w': self.params.w,
                    'c1': self.params.c1,
                    'c2': self.params.c2
                }
            )
        
        except Exception as e:
            logger.error(f"粒子群优化失败: {e}")
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='PSO',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error=str(e)
            )
    
    def _update_particle_position(
        self,
        current: List[int],
        personal_best: List[int],
        global_best: List[int]
    ) -> List[int]:
        """更新粒子位置（离散版本）"""
        new_position = current.copy()
        n = len(current)
        
        # 基于个体最优的交换（认知部分）
        if random.random() < self.params.c1 / 2:
            i, j = random.sample(range(n), 2)
            if personal_best[i] != new_position[i] or personal_best[j] != new_position[j]:
                new_position[i], new_position[j] = new_position[j], new_position[i]
        
        # 基于全局最优的交换（社会部分）
        if random.random() < self.params.c2 / 2:
            i, j = random.sample(range(n), 2)
            if global_best[i] != new_position[i] or global_best[j] != new_position[j]:
                new_position[i], new_position[j] = new_position[j], new_position[i]
        
        # 随机扰动（惯性）
        if random.random() < self.params.w:
            i, j = random.sample(range(n), 2)
            new_position[i], new_position[j] = new_position[j], new_position[i]
        
        return new_position
    
    def _calculate_cost(
        self,
        permutation: List[int],
        node_ids: List[int],
        distance_matrix: Dict
    ) -> float:
        """计算路径成本"""
        total = 0
        for i in range(len(permutation) - 1):
            id1 = node_ids[permutation[i]]
            id2 = node_ids[permutation[i + 1]]
            
            key = (min(id1, id2), max(id1, id2))
            if key in distance_matrix:
                total += distance_matrix[key]
            elif (id1, id2) in distance_matrix:
                total += distance_matrix[(id1, id2)]
            else:
                total += 100  # 默认成本
        
        return total
    
    def _calculate_total_distance(
        self,
        route: List[int],
        distance_matrix: Dict
    ) -> float:
        """计算总距离"""
        total = 0
        for i in range(len(route) - 1):
            key = (min(route[i], route[i+1]), max(route[i], route[i+1]))
            if key in distance_matrix:
                total += distance_matrix[key]
        return total


# ==================== 深度强化学习 (DRL) ====================

class DRLRouteOptimizer:
    """
    深度强化学习路径优化器
    使用简化的Q-Learning算法（无需TensorFlow依赖）
    适用于动态环境下的路径优化
    """
    
    def __init__(self, learning_rate: float = 0.1, discount_factor: float = 0.95,
                 epsilon: float = 0.3, episodes: int = 500):
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.episodes = episodes
        self.q_table = {}
    
    def optimize_route(
        self,
        nodes: List[Node],
        distance_matrix: Dict[Tuple[int, int], float],
        start_node_id: int = None
    ) -> OptimizationResult:
        """
        使用Q-Learning优化路径
        
        Args:
            nodes: 节点列表
            distance_matrix: 距离矩阵
            start_node_id: 起点节点ID
        
        Returns:
            优化结果
        """
        start_time = datetime.now()
        
        if not nodes or len(nodes) < 2:
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='DRL-Q-Learning',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error='节点数量不足'
            )
        
        try:
            node_ids = [n.id for n in nodes]
            node_count = len(node_ids)
            
            # 初始化Q表
            self.q_table = defaultdict(lambda: defaultdict(float))
            
            # 训练
            best_route = []
            best_cost = float('inf')
            convergence_history = []
            
            for episode in range(self.episodes):
                # 选择起点
                if start_node_id and start_node_id in node_ids:
                    current = start_node_id
                else:
                    current = random.choice(node_ids)
                
                route = [current]
                visited = {current}
                total_cost = 0
                
                # 构建路径
                while len(visited) < node_count:
                    # ε-greedy策略选择动作
                    next_node = self._select_action(current, node_ids, visited, distance_matrix)
                    
                    if next_node is None:
                        break
                    
                    # 计算奖励
                    key = (min(current, next_node), max(current, next_node))
                    distance = distance_matrix.get(key, distance_matrix.get((current, next_node), 100))
                    reward = -distance  # 负奖励，距离越短奖励越高
                    
                    # 更新Q值
                    self._update_q_value(current, next_node, reward, visited)
                    
                    route.append(next_node)
                    visited.add(next_node)
                    total_cost += distance
                    current = next_node
                
                # 更新最优解
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_route = route
                
                convergence_history.append(best_cost)
                
                # 衰减探索率
                self.epsilon = max(0.01, self.epsilon * 0.995)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return OptimizationResult(
                success=True,
                best_route=best_route,
                best_cost=round(best_cost, 2),
                best_distance=round(best_cost, 2),
                algorithm='DRL-Q-Learning',
                iterations=self.episodes,
                convergence_history=[round(c, 2) for c in convergence_history[::10]],  # 每10次记录一次
                execution_time=round(execution_time, 3),
                metadata={
                    'learning_rate': self.learning_rate,
                    'discount_factor': self.discount_factor,
                    'final_epsilon': round(self.epsilon, 4),
                    'q_table_size': len(self.q_table)
                }
            )
        
        except Exception as e:
            logger.error(f"深度强化学习优化失败: {e}")
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='DRL-Q-Learning',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error=str(e)
            )
    
    def _select_action(
        self,
        current: int,
        node_ids: List[int],
        visited: set,
        distance_matrix: Dict
    ) -> Optional[int]:
        """选择下一个节点（ε-greedy策略）"""
        candidates = [n for n in node_ids if n not in visited]
        
        if not candidates:
            return None
        
        # 探索：随机选择
        if random.random() < self.epsilon:
            return random.choice(candidates)
        
        # 利用：选择Q值最大的动作
        state = (current, tuple(sorted(visited)))
        q_values = {node: self.q_table[state][node] for node in candidates}
        
        if all(v == 0 for v in q_values.values()):
            return random.choice(candidates)
        
        return max(q_values.items(), key=lambda x: x[1])[0]
    
    def _update_q_value(
        self,
        current: int,
        next_node: int,
        reward: float,
        visited: set
    ):
        """更新Q值"""
        state = (current, tuple(sorted(visited)))
        new_visited = visited | {next_node}
        next_state = (next_node, tuple(sorted(new_visited)))
        
        # Q-Learning更新公式
        current_q = self.q_table[state][next_node]
        max_next_q = max(self.q_table[next_state].values(), default=0)
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state][next_node] = new_q


# ==================== 混合优化器 ====================

class HybridOptimizer:
    """
    混合优化器
    结合多种算法的优点，分阶段优化
    """
    
    def __init__(self):
        self.aco = AntColonyOptimizer()
        self.pso = ParticleSwarmOptimizer()
        self.drl = DRLRouteOptimizer()
    
    def optimize(
        self,
        nodes: List[Node],
        distance_matrix: Dict[Tuple[int, int], float],
        algorithm: str = 'hybrid'
    ) -> OptimizationResult:
        """
        混合优化
        
        Args:
            nodes: 节点列表
            distance_matrix: 距离矩阵
            algorithm: 算法选择 ('aco', 'pso', 'drl', 'hybrid')
        
        Returns:
            优化结果
        """
        start_time = datetime.now()
        results = []
        
        if algorithm in ['aco', 'hybrid']:
            aco_result = self.aco.optimize(nodes, distance_matrix)
            if aco_result.success:
                results.append(aco_result)
        
        if algorithm in ['pso', 'hybrid']:
            pso_result = self.pso.optimize_route(nodes, distance_matrix)
            if pso_result.success:
                results.append(pso_result)
        
        if algorithm in ['drl', 'hybrid']:
            drl_result = self.drl.optimize_route(nodes, distance_matrix)
            if drl_result.success:
                results.append(drl_result)
        
        if not results:
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm='hybrid',
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error='所有算法都失败了'
            )
        
        # 选择最优结果
        best = min(results, key=lambda x: x.best_cost)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return OptimizationResult(
            success=True,
            best_route=best.best_route,
            best_cost=best.best_cost,
            best_distance=best.best_distance,
            algorithm=f'hybrid[{best.algorithm}]',
            iterations=sum(r.iterations for r in results),
            convergence_history=best.convergence_history,
            execution_time=round(execution_time, 3),
            metadata={
                'algorithms_used': [r.algorithm for r in results],
                'best_algorithm': best.algorithm,
                'all_results': [
                    {'algorithm': r.algorithm, 'cost': r.best_cost}
                    for r in results
                ]
            }
        )


# ==================== 主服务类 ====================

class AdvancedRouteOptimizationService:
    """高级路径优化服务"""
    
    def __init__(self):
        self.aco = AntColonyOptimizer()
        self.pso = ParticleSwarmOptimizer()
        self.drl = DRLRouteOptimizer()
        self.hybrid = HybridOptimizer()
    
    def optimize(
        self,
        node_ids: List[int] = None,
        algorithm: str = 'hybrid',
        params: Dict = None
    ) -> OptimizationResult:
        """
        路径优化入口
        
        Args:
            node_ids: 节点ID列表
            algorithm: 算法选择 ('aco', 'pso', 'drl', 'hybrid')
            params: 算法参数
        
        Returns:
            优化结果
        """
        try:
            # 查询节点
            if node_ids:
                nodes = Node.query.filter(Node.id.in_(node_ids)).all()
            else:
                nodes = Node.query.limit(20).all()
            
            if len(nodes) < 2:
                return OptimizationResult(
                    success=False,
                    best_route=[],
                    best_cost=0,
                    best_distance=0,
                    algorithm=algorithm,
                    iterations=0,
                    convergence_history=[],
                    execution_time=0,
                    error='节点数量不足'
                )
            
            # 构建距离矩阵
            distance_matrix = self._build_distance_matrix(nodes)
            
            # 选择算法优化
            if algorithm == 'aco':
                return self.aco.optimize(nodes, distance_matrix)
            elif algorithm == 'pso':
                return self.pso.optimize_route(nodes, distance_matrix)
            elif algorithm == 'drl':
                return self.drl.optimize_route(nodes, distance_matrix)
            else:
                return self.hybrid.optimize(nodes, distance_matrix)
        
        except Exception as e:
            logger.error(f"高级路径优化失败: {e}")
            return OptimizationResult(
                success=False,
                best_route=[],
                best_cost=0,
                best_distance=0,
                algorithm=algorithm,
                iterations=0,
                convergence_history=[],
                execution_time=0,
                error=str(e)
            )
    
    def _build_distance_matrix(self, nodes: List[Node]) -> Dict[Tuple[int, int], float]:
        """构建距离矩阵"""
        matrix = {}
        
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes):
                if i < j:
                    dist = self._calculate_distance(node1, node2)
                    matrix[(node1.id, node2.id)] = dist
        
        return matrix
    
    def _calculate_distance(self, node1: Node, node2: Node) -> float:
        """计算两点距离"""
        if not node1 or not node2:
            return 100
        
        lat1, lng1 = node1.latitude or 0, node1.longitude or 0
        lat2, lng2 = node2.latitude or 0, node2.longitude or 0
        
        if not (lat1 and lng1 and lat2 and lng2):
            return 50
        
        # Haversine公式
        R = 6371
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    
    def compare_algorithms(
        self,
        node_ids: List[int] = None
    ) -> Dict:
        """对比不同算法效果"""
        results = {}
        
        for algo in ['aco', 'pso', 'drl', 'hybrid']:
            result = self.optimize(node_ids, algo)
            results[algo] = {
                'success': result.success,
                'best_cost': result.best_cost,
                'best_distance': result.best_distance,
                'execution_time': result.execution_time,
                'iterations': result.iterations
            }
        
        return results


# 单例实例
_advanced_route_optimization_service = None


def get_advanced_route_optimization_service() -> AdvancedRouteOptimizationService:
    """获取高级路径优化服务实例"""
    global _advanced_route_optimization_service
    if _advanced_route_optimization_service is None:
        _advanced_route_optimization_service = AdvancedRouteOptimizationService()
    return _advanced_route_optimization_service