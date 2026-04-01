#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多目标路径优化服务

支持的优化目标：
- distance: 距离最短
- time: 时间最短
- cost: 成本最低
- traffic: 路况最优
- weather_risk: 天气风险最小

算法：
- 加权求和法 (Weighted Sum)
- Pareto 最优解集
- NSGA-II 遗传算法（可选）
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from flask import current_app


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    path: List = field(default_factory=list)
    objectives: Dict = field(default_factory=dict)
    weighted_score: float = 0.0
    algorithm: str = ''
    dominated: bool = False  # 是否被支配（用于 Pareto 筛选）
    rank: int = 0  # Pareto 排名
    crowding_distance: float = 0.0  # 拥挤度距离


@dataclass
class ObjectiveConfig:
    """优化目标配置"""
    name: str
    display_name: str
    unit: str
    minimize: bool = True  # True: 最小化, False: 最大化
    default_weight: float = 1.0
    min_value: float = 0.0
    max_value: float = float('inf')


class MultiObjectiveOptimizer:
    """多目标路径优化器"""
    
    # 预定义的优化目标
    OBJECTIVES = {
        'distance': ObjectiveConfig(
            name='distance',
            display_name='距离',
            unit='km',
            minimize=True,
            default_weight=0.25,
            min_value=0,
            max_value=10000
        ),
        'time': ObjectiveConfig(
            name='time',
            display_name='时间',
            unit='min',
            minimize=True,
            default_weight=0.30,
            min_value=0,
            max_value=1440  # 24小时
        ),
        'cost': ObjectiveConfig(
            name='cost',
            display_name='成本',
            unit='元',
            minimize=True,
            default_weight=0.20,
            min_value=0,
            max_value=100000
        ),
        'traffic': ObjectiveConfig(
            name='traffic',
            display_name='路况评分',
            unit='分',
            minimize=False,  # 路况评分越高越好
            default_weight=0.15,
            min_value=0,
            max_value=100
        ),
        'weather_risk': ObjectiveConfig(
            name='weather_risk',
            display_name='天气风险',
            unit='%',
            minimize=True,
            default_weight=0.10,
            min_value=0,
            max_value=100
        )
    }
    
    def __init__(self):
        self.results = []
    
    def optimize_weighted_sum(
        self,
        routes: List[Dict],
        weights: Dict[str, float] = None
    ) -> OptimizationResult:
        """
        加权求和法
        
        将多个目标加权求和为一个综合得分，适合用户明确偏好时使用
        
        Args:
            routes: 候选路线列表，每个路线包含各目标值
            weights: 各目标的权重，归一化后使用
        
        Returns:
            最优路线结果
        """
        if not routes:
            return OptimizationResult(success=False, algorithm='weighted_sum')
        
        # 默认权重
        if weights is None:
            weights = {k: v.default_weight for k, v in self.OBJECTIVES.items()}
        
        # 归一化权重
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # 归一化各目标值
        normalized_routes = self._normalize_objectives(routes)
        
        # 计算加权得分
        best_route = None
        best_score = float('inf')
        
        for i, route in enumerate(normalized_routes):
            score = 0.0
            
            for obj_name, obj_config in self.OBJECTIVES.items():
                if obj_name in route['objectives']:
                    value = route['objectives'][obj_name]
                    weight = weights.get(obj_name, 0)
                    
                    # 如果是最小化目标，归一化后的值直接使用
                    # 如果是最大化目标，取反或用 1 - 归一化值
                    if obj_config.minimize:
                        score += weight * value
                    else:
                        score += weight * (1 - value)
            
            if score < best_score:
                best_score = score
                best_route = route
        
        if best_route:
            return OptimizationResult(
                success=True,
                path=best_route.get('path', []),
                objectives=best_route.get('original_objectives', {}),
                weighted_score=best_score,
                algorithm='weighted_sum'
            )
        
        return OptimizationResult(success=False, algorithm='weighted_sum')
    
    def find_pareto_front(
        self,
        routes: List[Dict]
    ) -> List[OptimizationResult]:
        """
        寻找 Pareto 最优解集
        
        Pareto 最优解：不存在另一个解在所有目标上都不比它差，且至少有一个目标更好
        
        Args:
            routes: 候选路线列表
        
        Returns:
            Pareto 最优解列表
        """
        if not routes:
            return []
        
        # 转换为结果对象
        results = []
        for route in routes:
            results.append(OptimizationResult(
                success=True,
                path=route.get('path', []),
                objectives=route.get('objectives', {}),
                algorithm='pareto'
            ))
        
        # Pareto 排序
        pareto_fronts = self._fast_non_dominated_sort(results)
        
        # 计算拥挤度距离
        for front in pareto_fronts:
            self._calculate_crowding_distance(front)
        
        # 设置排名
        for rank, front in enumerate(pareto_fronts):
            for result in front:
                result.rank = rank
        
        # 返回第一层（Pareto 前沿）
        return pareto_fronts[0] if pareto_fronts else []
    
    def _normalize_objectives(self, routes: List[Dict]) -> List[Dict]:
        """归一化目标值到 [0, 1]"""
        if not routes:
            return []
        
        # 找出每个目标的最小最大值
        min_max = {}
        for obj_name in self.OBJECTIVES.keys():
            values = []
            for route in routes:
                if 'objectives' in route and obj_name in route['objectives']:
                    values.append(route['objectives'][obj_name])
                elif obj_name in route:
                    values.append(route[obj_name])
            
            if values:
                min_max[obj_name] = {
                    'min': min(values),
                    'max': max(values)
                }
        
        # 归一化
        normalized = []
        for route in routes:
            normalized_route = route.copy()
            normalized_route['objectives'] = {}
            normalized_route['original_objectives'] = {}
            
            for obj_name, config in self.OBJECTIVES.items():
                # 获取原始值
                if 'objectives' in route and obj_name in route['objectives']:
                    value = route['objectives'][obj_name]
                elif obj_name in route:
                    value = route[obj_name]
                else:
                    continue
                
                normalized_route['original_objectives'][obj_name] = value
                
                # 归一化到 [0, 1]
                if obj_name in min_max:
                    range_val = min_max[obj_name]['max'] - min_max[obj_name]['min']
                    if range_val > 0:
                        normalized_val = (value - min_max[obj_name]['min']) / range_val
                    else:
                        normalized_val = 0
                else:
                    normalized_val = 0
                
                normalized_route['objectives'][obj_name] = normalized_val
            
            normalized.append(normalized_route)
        
        return normalized
    
    def _fast_non_dominated_sort(
        self,
        results: List[OptimizationResult]
    ) -> List[List[OptimizationResult]]:
        """快速非支配排序"""
        fronts = [[]]
        
        for p in results:
            p.domination_count = 0
            p.dominated_solutions = []
            
            for q in results:
                if self._dominates(p, q):
                    p.dominated_solutions.append(q)
                elif self._dominates(q, p):
                    p.domination_count += 1
            
            if p.domination_count == 0:
                p.rank = 0
                fronts[0].append(p)
        
        i = 0
        while fronts[i]:
            next_front = []
            for p in fronts[i]:
                for q in p.dominated_solutions:
                    q.domination_count -= 1
                    if q.domination_count == 0:
                        q.rank = i + 1
                        next_front.append(q)
            i += 1
            fronts.append(next_front)
        
        return fronts
    
    def _dominates(
        self,
        p: OptimizationResult,
        q: OptimizationResult
    ) -> bool:
        """
        判断 p 是否支配 q
        
        p 支配 q 当且仅当：
        - p 在所有目标上都不比 q 差
        - p 至少有一个目标比 q 好
        """
        at_least_one_better = False
        
        for obj_name, config in self.OBJECTIVES.items():
            p_val = p.objectives.get(obj_name, 0)
            q_val = q.objectives.get(obj_name, 0)
            
            if config.minimize:
                if p_val > q_val:
                    return False
                if p_val < q_val:
                    at_least_one_better = True
            else:
                if p_val < q_val:
                    return False
                if p_val > q_val:
                    at_least_one_better = True
        
        return at_least_one_better
    
    def _calculate_crowding_distance(
        self,
        front: List[OptimizationResult]
    ) -> None:
        """计算拥挤度距离"""
        if not front:
            return
        
        n = len(front)
        
        # 初始化拥挤度距离
        for solution in front:
            solution.crowding_distance = 0
        
        # 对每个目标计算拥挤度
        for obj_name in self.OBJECTIVES.keys():
            # 按该目标排序
            sorted_front = sorted(
                front,
                key=lambda x: x.objectives.get(obj_name, 0)
            )
            
            # 边界点设为无穷大
            sorted_front[0].crowding_distance = float('inf')
            sorted_front[-1].crowding_distance = float('inf')
            
            # 计算中间点的拥挤度
            for i in range(1, n - 1):
                range_val = (
                    sorted_front[-1].objectives.get(obj_name, 0) -
                    sorted_front[0].objectives.get(obj_name, 0)
                )
                if range_val > 0:
                    sorted_front[i].crowding_distance += (
                        (sorted_front[i + 1].objectives.get(obj_name, 0) -
                         sorted_front[i - 1].objectives.get(obj_name, 0)) /
                        range_val
                    )
    
    def generate_recommendations(
        self,
        routes: List[Dict],
        weights: Dict[str, float] = None
    ) -> Dict:
        """
        生成推荐结果
        
        同时返回加权求和的最优解和 Pareto 最优解集
        """
        # 归一化处理
        normalized = self._normalize_objectives(routes)
        
        # 加权求和最优解
        weighted_best = self.optimize_weighted_sum(routes, weights)
        
        # Pareto 最优解集
        pareto_front = self.find_pareto_front(routes)
        
        # 生成推荐报告
        recommendations = []
        
        # 1. 加权最优解
        if weighted_best.success:
            recommendations.append({
                'type': 'weighted_best',
                'title': '综合最优方案',
                'description': self._generate_description(weighted_best),
                'path': weighted_best.path,
                'objectives': weighted_best.objectives,
                'score': weighted_best.weighted_score
            })
        
        # 2. Pareto 最优解（按拥挤度排序，推荐最具代表性的）
        if pareto_front:
            # 按拥挤度排序
            pareto_sorted = sorted(
                pareto_front,
                key=lambda x: x.crowding_distance,
                reverse=True
            )
            
            for i, solution in enumerate(pareto_sorted[:5]):  # 最多5个
                # Infinity 无法被 JSON 序列化，转为很大的数字
                cd = solution.crowding_distance
                cd_value = 9999 if cd == float('inf') or cd == float('-inf') else cd
                
                recommendations.append({
                    'type': 'pareto',
                    'title': f'均衡方案 {i + 1}',
                    'description': self._generate_description(solution),
                    'path': solution.path,
                    'objectives': solution.objectives,
                    'rank': solution.rank,
                    'crowding_distance': cd_value
                })
        
        # 3. 单目标最优解（每个目标的最优）
        for obj_name, config in self.OBJECTIVES.items():
            if routes:
                sorted_routes = sorted(
                    routes,
                    key=lambda x: x.get('objectives', {}).get(obj_name, x.get(obj_name, float('inf')))
                )
                if config.minimize:
                    best = sorted_routes[0]
                else:
                    best = sorted_routes[-1]
                
                recommendations.append({
                    'type': 'single_objective',
                    'title': f'{config.display_name}最优',
                    'objective': obj_name,
                    'description': f'{config.display_name}最小' if config.minimize else f'{config.display_name}最大',
                    'path': best.get('path', []),
                    'objectives': best.get('objectives', {}),
                    'best_value': best.get('objectives', {}).get(obj_name, best.get(obj_name))
                })
        
        return {
            'success': True,
            'recommendations': recommendations,
            'pareto_count': len(pareto_front),
            'total_routes': len(routes),
            'weights_used': weights or {k: v.default_weight for k, v in self.OBJECTIVES.items()}
        }
    
    def _generate_description(self, result: OptimizationResult) -> str:
        """生成方案描述"""
        objectives = result.objectives
        
        parts = []
        for obj_name, config in self.OBJECTIVES.items():
            if obj_name in objectives:
                value = objectives[obj_name]
                if config.minimize:
                    parts.append(f"{config.display_name}{value:.1f}{config.unit}")
                else:
                    parts.append(f"{config.display_name}{value:.1f}{config.unit}")
        
        return '，'.join(parts)


# 单例
_optimizer = None


def get_multi_objective_optimizer():
    """获取多目标优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = MultiObjectiveOptimizer()
    return _optimizer
