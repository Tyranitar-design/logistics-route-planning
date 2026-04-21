"""
遗传算法求解器
==============

使用遗传算法求解 VRP 问题

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Optional, Dict, Any
import random
from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    SolverRegistry,
    timeit
)


@SolverRegistry.register(SolverType.GENETIC)
class GeneticSolver(OptimizationSolver):
    """
    遗传算法求解器
    """
    
    def __init__(self,
                 pop_size: int = 100,
                 crossover_prob: float = 0.9,
                 mutation_prob: float = 0.2,
                 elite_size: int = 10,
                 **kwargs):
        """
        初始化
        
        Args:
            pop_size: 种群大小
            crossover_prob: 交叉概率
            mutation_prob: 变异概率
            elite_size: 精英数量
            **kwargs: 其他参数
        """
        super().__init__("Genetic Algorithm", SolverType.GENETIC)
        self.pop_size = pop_size
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.elite_size = elite_size
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        """遗传算法总是可用"""
        return True
    
    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              n_gen: int = 100,
              **kwargs) -> OptimizationResult:
        """
        求解 VRP 问题
        
        Args:
            problem: VRP 问题
            time_limit: 时间限制（秒）
            n_gen: 迭代次数
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        import time
        start_time = time.time()
        
        data = problem.data
        n = data.n_customers
        
        # 初始化种群
        population = [self._random_chromosome(n) for _ in range(self.pop_size)]
        
        best_solution = None
        best_fitness = float('inf')
        
        for gen in range(n_gen):
            # 检查时间限制
            if time.time() - start_time > time_limit:
                break
            
            # 评估适应度
            fitness = []
            for chrom in population:
                routes = self._decode_routes(chrom, data)
                obj = problem.evaluate(routes)
                fitness.append(obj[0])
            
            # 更新最优
            min_idx = np.argmin(fitness)
            if fitness[min_idx] < best_fitness:
                best_fitness = fitness[min_idx]
                best_solution = population[min_idx].copy()
            
            # 选择
            selected = self._selection(population, fitness)
            
            # 交叉
            offspring = []
            while len(offspring) < self.pop_size - self.elite_size:
                p1, p2 = random.sample(selected, 2)
                if random.random() < self.crossover_prob:
                    child = self._crossover(p1, p2)
                else:
                    child = p1.copy()
                offspring.append(child)
            
            # 变异
            for i in range(len(offspring)):
                if random.random() < self.mutation_prob:
                    offspring[i] = self._mutate(offspring[i])
            
            # 精英保留
            elite_indices = np.argsort(fitness)[:self.elite_size]
            elite = [population[i].copy() for i in elite_indices]
            
            # 新一代
            population = elite + offspring[:self.pop_size - self.elite_size]
        
        # 最终解
        best_routes = self._decode_routes(best_solution, data)
        
        result = OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=best_routes,
            objective_values=np.array([best_fitness]),
            solve_time=0.0,
            iterations=n_gen,
            routes=best_routes
        )
        
        return result
    
    def _random_chromosome(self, n: int) -> np.ndarray:
        """生成随机染色体"""
        return np.random.permutation(n)
    
    def _decode_routes(self, chrom: np.ndarray, data) -> List[List[int]]:
        """解码染色体为路线"""
        routes = []
        route = []
        load = 0
        
        # 需求转为列表避免索引问题
        demands_list = list(data.demands)
        
        for idx in chrom:
            customer = int(idx) + 1
            demand = demands_list[customer - 1]
            if load + demand <= data.vehicle_capacity:
                route.append(customer)
                load += demand
            else:
                if route:
                    routes.append(route)
                route = [customer]
                load = demand
        
        if route:
            routes.append(route)
        
        return routes
    
    def _selection(self, population: List, fitness: List) -> List:
        """锦标赛选择"""
        selected = []
        for _ in range(self.pop_size):
            i, j = random.sample(range(len(population)), 2)
            if fitness[i] < fitness[j]:
                selected.append(population[i])
            else:
                selected.append(population[j])
        return selected
    
    def _crossover(self, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        """顺序交叉"""
        n = len(p1)
        a, b = sorted(random.sample(range(n), 2))
        
        child = np.full(n, -1)
        child[a:b+1] = p1[a:b+1]
        
        pos = (b + 1) % n
        for i in range(n):
            idx = (b + 1 + i) % n
            if p2[idx] not in child:
                child[pos] = p2[idx]
                pos = (pos + 1) % n
        
        return child
    
    def _mutate(self, chrom: np.ndarray) -> np.ndarray:
        """交换变异"""
        child = chrom.copy()
        a, b = random.sample(range(len(child)), 2)
        child[a], child[b] = child[b], child[a]
        return child
