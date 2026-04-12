#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
物流网络设计模块 - 设施选址与网络优化

功能：
1. P-中位选址问题（P-Median Problem）
2. 覆盖选址问题（Covering Problem）
3. 容量受限设施选址（CFLP）
4. 最小费用流优化
5. 网络场景管理

求解器：PuLP + CPLEX
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import sys
import os
import math
import random
from datetime import datetime
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pulp import *
from app.models import db
from app.models.network import NetworkScenario, NetworkNode, NetworkEdge
from sqlalchemy import text
from flask_jwt_extended import get_jwt_identity

network_bp = Blueprint('network', __name__)


# ============================================================
# 辅助函数
# ============================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    计算两点之间的球面距离（公里）
    使用 Haversine 公式
    """
    R = 6371  # 地球半径（公里）
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def calculate_distance_matrix(locations):
    """
    计算距离矩阵
    
    Args:
        locations: [{'id': int, 'name': str, 'lat': float, 'lon': float}, ...]
    
    Returns:
        distance_matrix: {(i, j): distance}
    """
    distance_matrix = {}
    n = len(locations)
    
    for i in range(n):
        for j in range(n):
            if i == j:
                distance_matrix[(i, j)] = 0
            else:
                dist = haversine_distance(
                    locations[i]['lat'], locations[i]['lon'],
                    locations[j]['lat'], locations[j]['lon']
                )
                distance_matrix[(i, j)] = dist
    
    return distance_matrix


# ============================================================
# P-中位选址问题（P-Median Problem）
# ============================================================

@network_bp.route('/location/p-median', methods=['POST'])
@jwt_required()
def solve_p_median():
    """
    P-中位选址问题求解
    
    问题：选择 p 个设施位置，使所有客户到其最近设施的总加权距离最小
    
    输入格式：
    {
        "customers": [
            {"id": 1, "name": "客户A", "lat": 39.9, "lon": 116.4, "demand": 100},
            ...
        ],
        "candidates": [
            {"id": 1, "name": "候选位置A", "lat": 39.8, "lon": 116.3, "capacity": 500, "fixed_cost": 100000},
            ...
        ],
        "num_facilities": 3,
        "solver": "CBC"  // CBC 或 CPLEX
    }
    
    输出：
    {
        "selected_facilities": [...],
        "assignments": {"客户ID": "设施ID", ...},
        "total_distance": 1234.5,
        "total_cost": 500000,
        "solve_time": 0.5
    }
    """
    import time
    start_time = time.time()
    
    data = request.json
    
    customers = data['customers']
    candidates = data['candidates']
    p = data['num_facilities']
    solver_name = data.get('solver', 'CBC')
    
    # 验证输入
    if p > len(candidates):
        return jsonify({
            'error': f'设施数量 {p} 超过候选位置数量 {len(candidates)}'
        }), 400
    
    # 计算距离矩阵
    all_locations = customers + candidates
    distance_matrix = calculate_distance_matrix(all_locations)
    
    n_customers = len(customers)
    n_candidates = len(candidates)
    
    # 创建索引映射
    customer_indices = list(range(n_customers))
    candidate_indices = list(range(n_customers, n_customers + n_candidates))
    
    # 创建问题
    prob = LpProblem("P_Median_Facility_Location", LpMinimize)
    
    # 决策变量
    # x[j] = 1 如果在候选位置 j 建设施
    x = LpVariable.dicts("x", candidate_indices, cat='Binary')
    
    # y[i,j] = 1 如果客户 i 分配给设施 j
    y = LpVariable.dicts("y", 
        [(i, j) for i in customer_indices for j in candidate_indices],
        cat='Binary')
    
    # 目标函数：最小化总加权距离
    prob += lpSum(
        customers[i]['demand'] * distance_matrix[(i, j)] * y[(i, j)]
        for i in customer_indices
        for j in candidate_indices
    ), "Total_Weighted_Distance"
    
    # 约束1：恰好选择 p 个设施
    prob += lpSum(x[j] for j in candidate_indices) == p, "Select_p_Facilities"
    
    # 约束2：每个客户恰好分配给一个设施
    for i in customer_indices:
        prob += lpSum(y[(i, j)] for j in candidate_indices) == 1, f"Customer_{i}_Assignment"
    
    # 约束3：客户只能分配给已选设施
    for i in customer_indices:
        for j in candidate_indices:
            prob += y[(i, j)] <= x[j], f"Assignment_{i}_{j}"
    
    # 求解
    try:
        if solver_name.upper() == 'CPLEX':
            solver = CPLEX_CMD(msg=0, timeLimit=60)
        else:
            solver = PULP_CBC_CMD(msg=0, timeLimit=60)
        
        prob.solve(solver)
    except Exception as e:
        # CPLEX 不可用时回退到 CBC
        print(f"[警告] {solver_name} 求解器不可用，使用 CBC: {e}")
        solver = PULP_CBC_CMD(msg=0, timeLimit=60)
        prob.solve(solver)
    
    solve_time = time.time() - start_time
    
    # 检查求解状态
    if LpStatus[prob.status] != 'Optimal':
        return jsonify({
            'error': f'求解失败: {LpStatus[prob.status]}',
            'status': LpStatus[prob.status]
        }), 500
    
    # 提取结果
    selected_indices = [j for j in candidate_indices if value(x[j]) == 1]
    selected_facilities = [candidates[j - n_customers] for j in selected_indices]
    
    assignments = {}
    for i in customer_indices:
        for j in candidate_indices:
            if value(y[(i, j)]) == 1:
                assignments[customers[i]['id']] = candidates[j - n_customers]['id']
                break
    
    total_distance = value(prob.objective)
    
    # 计算总成本（固定成本 + 运输成本）
    total_fixed_cost = sum(
        candidates[j - n_customers].get('fixed_cost', 0)
        for j in selected_indices
    )
    transport_cost = total_distance * 2.0  # 假设每公里2元
    total_cost = total_fixed_cost + transport_cost
    
    return jsonify({
        'status': 'success',
        'selected_facilities': selected_facilities,
        'assignments': assignments,
        'total_distance': round(total_distance, 2),
        'total_cost': round(total_cost, 2),
        'total_fixed_cost': total_fixed_cost,
        'transport_cost': round(transport_cost, 2),
        'solve_time': round(solve_time, 3),
        'solver': solver_name
    })


# ============================================================
# 覆盖选址问题（Set Covering Problem）
# ============================================================

@network_bp.route('/location/covering', methods=['POST'])
@jwt_required()
def solve_set_covering():
    """
    集合覆盖问题求解
    
    问题：选择最少的设施位置，使所有客户都在服务范围内
    
    输入格式：
    {
        "customers": [...],
        "candidates": [...],
        "service_radius": 50  // 服务半径（公里）
    }
    
    输出：选择的最少设施数量及位置
    """
    import time
    start_time = time.time()
    
    data = request.json
    
    customers = data['customers']
    candidates = data['candidates']
    service_radius = data['service_radius']
    
    # 计算覆盖关系
    coverage = {}  # {候选j: [可覆盖的客户i列表]}
    
    for j, cand in enumerate(candidates):
        covered_customers = []
        for i, cust in enumerate(customers):
            dist = haversine_distance(cust['lat'], cust['lon'], cand['lat'], cand['lon'])
            if dist <= service_radius:
                covered_customers.append(i)
        coverage[j] = covered_customers
    
    # 创建问题
    prob = LpProblem("Set_Covering", LpMinimize)
    
    # 决策变量
    x = LpVariable.dicts("x", range(len(candidates)), cat='Binary')
    
    # 目标：最小化设施数量
    prob += lpSum(x[j] for j in range(len(candidates))), "Minimize_Facilities"
    
    # 约束：每个客户必须被至少一个设施覆盖
    for i in range(len(customers)):
        covering_facilities = [j for j in range(len(candidates)) if i in coverage[j]]
        if not covering_facilities:
            return jsonify({
                'error': f'客户 {customers[i]["name"]} 无法被任何候选位置覆盖'
            }), 400
        prob += lpSum(x[j] for j in covering_facilities) >= 1, f"Cover_Customer_{i}"
    
    # 求解
    solver = PULP_CBC_CMD(msg=0, timeLimit=60)
    prob.solve(solver)
    
    solve_time = time.time() - start_time
    
    if LpStatus[prob.status] != 'Optimal':
        return jsonify({
            'error': f'求解失败: {LpStatus[prob.status]}'
        }), 500
    
    # 提取结果
    selected_indices = [j for j in range(len(candidates)) if value(x[j]) == 1]
    selected_facilities = [candidates[j] for j in selected_indices]
    
    # 生成覆盖详情
    coverage_details = {}
    for j in selected_indices:
        coverage_details[candidates[j]['id']] = {
            'name': candidates[j]['name'],
            'covered_customers': [customers[i]['name'] for i in coverage[j]]
        }
    
    return jsonify({
        'status': 'success',
        'num_facilities': len(selected_facilities),
        'selected_facilities': selected_facilities,
        'coverage_details': coverage_details,
        'solve_time': round(solve_time, 3)
    })


# ============================================================
# 容量受限设施选址问题（CFLP）
# ============================================================

@network_bp.route('/location/cflp', methods=['POST'])
@jwt_required()
def solve_cflp():
    """
    容量受限设施选址问题（Capacitated Facility Location Problem）
    
    问题：考虑设施容量限制的选址问题
    
    输入格式：
    {
        "customers": [{"id": 1, "name": "客户A", "lat": 39.9, "lon": 116.4, "demand": 100}, ...],
        "candidates": [{"id": 1, "name": "候选A", "lat": 39.8, "lon": 116.3, "capacity": 500, "fixed_cost": 100000}, ...],
        "transport_cost_per_km": 2.0
    }
    """
    import time
    start_time = time.time()
    
    data = request.json
    
    customers = data['customers']
    candidates = data['candidates']
    transport_cost_per_km = data.get('transport_cost_per_km', 2.0)
    
    # 计算距离矩阵
    all_locations = customers + candidates
    distance_matrix = calculate_distance_matrix(all_locations)
    
    n_customers = len(customers)
    n_candidates = len(candidates)
    
    customer_indices = list(range(n_customers))
    candidate_indices = list(range(n_customers, n_customers + n_candidates))
    
    # 创建问题
    prob = LpProblem("CFLP", LpMinimize)
    
    # 决策变量
    x = LpVariable.dicts("x", candidate_indices, cat='Binary')
    y = LpVariable.dicts("y",
        [(i, j) for i in customer_indices for j in candidate_indices],
        lowBound=0, cat='Continuous')  # 分配比例（0-1）
    
    # 目标：最小化总成本（固定成本 + 运输成本）
    prob += lpSum(
        candidates[j - n_customers]['fixed_cost'] * x[j]
        for j in candidate_indices
    ) + lpSum(
        customers[i]['demand'] * distance_matrix[(i, j)] * transport_cost_per_km * y[(i, j)]
        for i in customer_indices
        for j in candidate_indices
    ), "Total_Cost"
    
    # 约束1：每个客户的需求必须完全满足
    for i in customer_indices:
        prob += lpSum(y[(i, j)] for j in candidate_indices) == 1, f"Demand_{i}"
    
    # 约束2：设施容量限制
    for j in candidate_indices:
        prob += lpSum(
            customers[i]['demand'] * y[(i, j)]
            for i in customer_indices
        ) <= candidates[j - n_customers]['capacity'] * x[j], f"Capacity_{j}"
    
    # 求解
    solver = PULP_CBC_CMD(msg=0, timeLimit=120)
    prob.solve(solver)
    
    solve_time = time.time() - start_time
    
    if LpStatus[prob.status] != 'Optimal':
        return jsonify({
            'error': f'求解失败: {LpStatus[prob.status]}'
        }), 500
    
    # 提取结果
    selected_indices = [j for j in candidate_indices if value(x[j]) == 1]
    selected_facilities = []
    
    for j in selected_indices:
        cand = candidates[j - n_customers]
        used_capacity = sum(
            value(y[(i, j)]) * customers[i]['demand']
            for i in customer_indices
        )
        selected_facilities.append({
            **cand,
            'used_capacity': round(used_capacity, 2),
            'utilization': round(used_capacity / cand['capacity'] * 100, 1)
        })
    
    # 分配详情
    assignments = {}
    for i in customer_indices:
        assignments[customers[i]['id']] = {}
        for j in candidate_indices:
            if value(y[(i, j)]) > 0.01:
                assignments[customers[i]['id']][candidates[j - n_customers]['id']] = round(value(y[(i, j)]), 3)
    
    total_cost = value(prob.objective)
    fixed_cost = sum(candidates[j - n_customers]['fixed_cost'] for j in selected_indices)
    transport_cost = total_cost - fixed_cost
    
    return jsonify({
        'status': 'success',
        'selected_facilities': selected_facilities,
        'assignments': assignments,
        'total_cost': round(total_cost, 2),
        'fixed_cost': round(fixed_cost, 2),
        'transport_cost': round(transport_cost, 2),
        'solve_time': round(solve_time, 3)
    })


# ============================================================
# 多目标选址优化
# ============================================================

@network_bp.route('/location/multi-objective', methods=['POST'])
@jwt_required()
def solve_multi_objective():
    """
    多目标设施选址优化
    
    同时优化：
    1. 总成本（固定成本 + 运输成本）
    2. 总距离/服务响应时间
    3. 服务覆盖均衡性
    
    输入格式：
    {
        "customers": [...],
        "candidates": [...],
        "num_facilities": 3,
        "weights": {"cost": 0.4, "distance": 0.4, "balance": 0.2},
        "solver": "CBC"
    }
    """
    import time
    start_time = time.time()
    
    data = request.json
    
    customers = data['customers']
    candidates = data['candidates']
    p = data['num_facilities']
    weights = data.get('weights', {'cost': 0.4, 'distance': 0.4, 'balance': 0.2})
    solver_name = data.get('solver', 'CBC')
    
    # 计算距离矩阵
    all_locations = customers + candidates
    distance_matrix = calculate_distance_matrix(all_locations)
    
    n_customers = len(customers)
    n_candidates = len(candidates)
    
    customer_indices = list(range(n_customers))
    candidate_indices = list(range(n_customers, n_customers + n_candidates))
    
    # 标准化参数
    max_distance = max(distance_matrix.values()) if distance_matrix else 1
    max_cost = max(c.get('fixed_cost', 100000) for c in candidates)
    max_demand = max(c.get('demand', 100) for c in customers)
    
    # 创建问题
    prob = LpProblem("Multi_Objective_Facility_Location", LpMinimize)
    
    # 决策变量
    x = LpVariable.dicts("x", candidate_indices, cat='Binary')
    y = LpVariable.dicts("y",
        [(i, j) for i in customer_indices for j in candidate_indices],
        cat='Binary')
    
    # 辅助变量：最大服务距离（用于均衡性）
    max_service_distance = LpVariable("max_service_distance", lowBound=0)
    
    # 多目标加权
    # 目标1：成本
    cost_obj = lpSum(
        candidates[j - n_customers].get('fixed_cost', 0) * x[j]
        for j in candidate_indices
    ) + lpSum(
        customers[i]['demand'] * distance_matrix[(i, j)] * 2.0 * y[(i, j)]
        for i in customer_indices
        for j in candidate_indices
    )
    
    # 目标2：距离
    distance_obj = lpSum(
        customers[i]['demand'] * distance_matrix[(i, j)] * y[(i, j)]
        for i in customer_indices
        for j in candidate_indices
    )
    
    # 目标3：均衡性（最小化最大服务距离）
    balance_obj = max_service_distance
    
    # 加权目标函数
    prob += (
        weights.get('cost', 0.4) * cost_obj / (max_cost * n_candidates) +
        weights.get('distance', 0.4) * distance_obj / (max_distance * n_customers) +
        weights.get('balance', 0.2) * balance_obj / max_distance
    ), "Weighted_Objective"
    
    # 约束
    prob += lpSum(x[j] for j in candidate_indices) == p, "Select_p_Facilities"
    
    for i in customer_indices:
        prob += lpSum(y[(i, j)] for j in candidate_indices) == 1, f"Customer_{i}_Assignment"
    
    for i in customer_indices:
        for j in candidate_indices:
            prob += y[(i, j)] <= x[j], f"Assignment_{i}_{j}"
    
    # 均衡性约束
    for i in customer_indices:
        for j in candidate_indices:
            prob += distance_matrix[(i, j)] * y[(i, j)] <= max_service_distance, f"Balance_{i}_{j}"
    
    # 求解
    try:
        if solver_name.upper() == 'CPLEX':
            solver = CPLEX_CMD(msg=0, timeLimit=60)
        else:
            solver = PULP_CBC_CMD(msg=0, timeLimit=60)
        prob.solve(solver)
    except Exception as e:
        solver = PULP_CBC_CMD(msg=0, timeLimit=60)
        prob.solve(solver)
    
    solve_time = time.time() - start_time
    
    if LpStatus[prob.status] != 'Optimal':
        return jsonify({
            'error': f'求解失败: {LpStatus[prob.status]}',
            'status': LpStatus[prob.status]
        }), 500
    
    # 提取结果
    selected_indices = [j for j in candidate_indices if value(x[j]) == 1]
    selected_facilities = [candidates[j - n_customers] for j in selected_indices]
    
    assignments = {}
    service_distances = []
    for i in customer_indices:
        for j in candidate_indices:
            if value(y[(i, j)]) == 1:
                assignments[customers[i]['id']] = candidates[j - n_customers]['id']
                service_distances.append(distance_matrix[(i, j)])
                break
    
    # 计算各项指标
    total_fixed_cost = sum(candidates[j - n_customers].get('fixed_cost', 0) for j in selected_indices)
    total_distance = sum(
        customers[i]['demand'] * distance_matrix[(i, j)]
        for i in customer_indices
        for j in candidate_indices if value(y[(i, j)]) == 1
    )
    transport_cost = total_distance * 2.0
    total_cost = total_fixed_cost + transport_cost
    
    avg_service_distance = sum(service_distances) / len(service_distances) if service_distances else 0
    max_service_dist = value(max_service_distance) if value(max_service_distance) else max(service_distances)
    
    # 计算服务水平（50km 内）
    service_level = sum(1 for d in service_distances if d <= 50) / len(service_distances) if service_distances else 0
    
    return jsonify({
        'status': 'success',
        'selected_facilities': selected_facilities,
        'assignments': assignments,
        'objectives': {
            'total_cost': round(total_cost, 2),
            'total_distance': round(total_distance, 2),
            'avg_service_distance': round(avg_service_distance, 2),
            'max_service_distance': round(max_service_dist, 2),
            'service_level': round(service_level, 3)
        },
        'total_fixed_cost': round(total_fixed_cost, 2),
        'transport_cost': round(transport_cost, 2),
        'weights_used': weights,
        'solve_time': round(solve_time, 3),
        'solver': solver_name
    })


# ============================================================
# 动态选址优化（考虑时间维度）
# ============================================================

@network_bp.route('/location/dynamic', methods=['POST'])
@jwt_required()
def solve_dynamic_location():
    """
    动态设施选址优化
    
    考虑需求变化，分阶段优化设施布局
    
    输入格式：
    {
        "periods": [
            {
                "name": "第1年",
                "customers": [...],
                "demand_growth": 1.0
            },
            {
                "name": "第2年",
                "customers": [...],
                "demand_growth": 1.2
            }
        ],
        "candidates": [...],
        "initial_facilities": 2,
        "expansion_allowed": true,
        "relocation_cost": 50000
    }
    """
    import time
    start_time = time.time()
    
    data = request.json
    
    periods = data['periods']
    candidates = data['candidates']
    initial_facilities = data.get('initial_facilities', 2)
    expansion_allowed = data.get('expansion_allowed', True)
    relocation_cost = data.get('relocation_cost', 50000)
    
    n_candidates = len(candidates)
    candidate_indices = list(range(n_candidates))
    n_periods = len(periods)
    period_indices = list(range(n_periods))
    
    # 创建问题
    prob = LpProblem("Dynamic_Facility_Location", LpMinimize)
    
    # 决策变量
    # x[t,j] = 1 如果在时期 t 开设设施 j
    x = LpVariable.dicts("x",
        [(t, j) for t in period_indices for j in candidate_indices],
        cat='Binary')
    
    # y[t,i,j] = 1 如果在时期 t 客户 i 分配给设施 j
    y = LpVariable.dicts("y",
        [(t, i, j) for t in period_indices 
         for i in range(len(periods[0]['customers'])) 
         for j in candidate_indices],
        cat='Binary')
    
    # z[t,j] = 1 如果在时期 t 新开设施 j（用于计算扩张成本）
    z = LpVariable.dicts("z",
        [(t, j) for t in period_indices for j in candidate_indices],
        cat='Binary')
    
    # 目标函数：最小化总成本
    # 包括：固定成本 + 运输成本 + 扩张成本
    
    fixed_cost = lpSum(
        periods[t].get('demand_growth', 1.0) * candidates[j].get('fixed_cost', 0) * x[(t, j)]
        for t in period_indices
        for j in candidate_indices
    )
    
    # 简化：使用第一个时期的客户数据
    base_customers = periods[0]['customers']
    transport_cost = 0
    
    for t in period_indices:
        growth = periods[t].get('demand_growth', 1.0)
        # 使用基础客户计算（简化）
        for i, cust in enumerate(base_customers):
            for j, cand in enumerate(candidates):
                dist = haversine_distance(cust['lat'], cust['lon'], cand['lat'], cand['lon'])
                transport_cost += growth * cust.get('demand', 100) * dist * 2.0 * y[(t, i, j)]
    
    expansion_cost = lpSum(
        relocation_cost * z[(t, j)]
        for t in period_indices[1:]  # 从第二期开始
        for j in candidate_indices
    )
    
    prob += fixed_cost + transport_cost + expansion_cost, "Total_Cost"
    
    # 约束
    # 初始时期设施数量
    prob += lpSum(x[(0, j)] for j in candidate_indices) == initial_facilities, "Initial_Facilities"
    
    # 每个时期每个客户分配给一个设施
    for t in period_indices:
        for i in range(len(base_customers)):
            prob += lpSum(y[(t, i, j)] for j in candidate_indices) == 1, f"Assign_{t}_{i}"
    
    # 只能分配给已建设施
    for t in period_indices:
        for i in range(len(base_customers)):
            for j in candidate_indices:
                prob += y[(t, i, j)] <= x[(t, j)], f"Open_{t}_{i}_{j}"
    
    # 设施只能增加不能减少（扩张约束）
    for t in period_indices[1:]:
        for j in candidate_indices:
            prob += x[(t, j)] >= x[(t-1, j)], f"No_Close_{t}_{j}"
    
    # 追踪新开设施
    for t in period_indices[1:]:
        for j in candidate_indices:
            prob += z[(t, j)] >= x[(t, j)] - x[(t-1, j)], f"New_{t}_{j}"
    
    # 求解
    solver = PULP_CBC_CMD(msg=0, timeLimit=120)
    prob.solve(solver)
    
    solve_time = time.time() - start_time
    
    if LpStatus[prob.status] != 'Optimal':
        return jsonify({
            'error': f'求解失败: {LpStatus[prob.status]}',
            'status': LpStatus[prob.status]
        }), 500
    
    # 提取结果
    results_by_period = []
    
    for t in period_indices:
        selected = [candidates[j] for j in candidate_indices if value(x[(t, j)]) == 1]
        
        assignments = {}
        for i, cust in enumerate(base_customers):
            for j in candidate_indices:
                if value(y[(t, i, j)]) == 1:
                    assignments[cust['id']] = candidates[j]['id']
                    break
        
        results_by_period.append({
            'period': periods[t]['name'],
            'demand_growth': periods[t].get('demand_growth', 1.0),
            'selected_facilities': selected,
            'num_facilities': len(selected),
            'assignments': assignments
        })
    
    total_cost = value(prob.objective)
    
    return jsonify({
        'status': 'success',
        'results_by_period': results_by_period,
        'total_cost': round(total_cost, 2),
        'expansion_periods': n_periods,
        'solve_time': round(solve_time, 3)
    })


# ============================================================
# 测试数据生成
# ============================================================

@network_bp.route('/test-data/generate', methods=['POST'])
@jwt_required()
def generate_test_data():
    """
    生成测试数据
    
    输入格式：
    {
        "num_customers": 20,
        "num_candidates": 8,
        "region": "china"  // china, europe, usa
    }
    """
    data = request.json
    
    num_customers = data.get('num_customers', 20)
    num_candidates = data.get('num_candidates', 8)
    region = data.get('region', 'china')
    
    # 中国主要城市坐标（用于生成随机位置）
    if region == 'china':
        cities = [
            {'name': '北京', 'lat': 39.90, 'lon': 116.41},
            {'name': '上海', 'lat': 31.23, 'lon': 121.47},
            {'name': '广州', 'lat': 23.13, 'lon': 113.26},
            {'name': '深圳', 'lat': 22.53, 'lon': 113.93},
            {'name': '杭州', 'lat': 30.27, 'lon': 120.16},
            {'name': '南京', 'lat': 32.06, 'lon': 118.80},
            {'name': '武汉', 'lat': 30.59, 'lon': 114.31},
            {'name': '成都', 'lat': 30.67, 'lon': 104.07},
            {'name': '重庆', 'lat': 29.56, 'lon': 106.55},
            {'name': '西安', 'lat': 34.34, 'lon': 108.94},
            {'name': '苏州', 'lat': 31.30, 'lon': 120.62},
            {'name': '天津', 'lat': 39.13, 'lon': 117.20},
            {'name': '青岛', 'lat': 36.07, 'lon': 120.38},
            {'name': '郑州', 'lat': 34.75, 'lon': 113.65},
            {'name': '长沙', 'lat': 28.23, 'lon': 112.94},
        ]
        center_lat, center_lon = 35.0, 110.0
        lat_range, lon_range = 15, 20
    else:
        center_lat, center_lon = 40.0, -95.0
        lat_range, lon_range = 10, 15
        cities = []
    
    # 生成客户
    customers = []
    for i in range(num_customers):
        if cities and random.random() > 0.3:
            # 70% 概率使用真实城市附近
            city = random.choice(cities)
            lat = city['lat'] + random.uniform(-0.5, 0.5)
            lon = city['lon'] + random.uniform(-0.5, 0.5)
            name = f"{city['name']}客户{chr(65 + i % 26)}"
        else:
            # 随机位置
            lat = center_lat + random.uniform(-lat_range, lat_range)
            lon = center_lon + random.uniform(-lon_range, lon_range)
            name = f"客户{i+1}"
        
        customers.append({
            'id': i + 1,
            'name': name,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'demand': random.randint(50, 200)
        })
    
    # 生成候选位置
    candidates = []
    for i in range(num_candidates):
        if cities and random.random() > 0.5:
            city = random.choice(cities)
            lat = city['lat'] + random.uniform(-0.3, 0.3)
            lon = city['lon'] + random.uniform(-0.3, 0.3)
            name = f"{city['name']}候选位置"
        else:
            lat = center_lat + random.uniform(-lat_range, lat_range)
            lon = center_lon + random.uniform(-lon_range, lon_range)
            name = f"候选位置{i+1}"
        
        capacity = random.randint(300, 800)
        fixed_cost = capacity * random.randint(200, 500)  # 容量越大，成本越高
        
        candidates.append({
            'id': i + 1,
            'name': name,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'capacity': capacity,
            'fixed_cost': fixed_cost
        })
    
    return jsonify({
        'status': 'success',
        'customers': customers,
        'candidates': candidates,
        'region': region,
        'generated_at': datetime.now().isoformat()
    })


# ============================================================
# 场景管理
# ============================================================

@network_bp.route('/scenarios', methods=['GET'])
@jwt_required()
def list_scenarios():
    """列出所有保存的网络场景"""
    try:
        user_id = get_jwt_identity()
        
        scenarios = NetworkScenario.query.filter_by(created_by=user_id).order_by(NetworkScenario.created_at.desc()).all()
        
        return jsonify({
            'status': 'success',
            'scenarios': [s.to_dict() for s in scenarios],
            'total': len(scenarios)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/scenarios', methods=['POST'])
@jwt_required()
def save_scenario():
    """保存网络场景"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        # 计算服务水平指标
        avg_distance = data.get('avg_distance', 0)
        max_distance = data.get('max_distance', 0)
        service_level = data.get('service_level', 0.95)
        
        # 如果没有提供，从分配结果计算
        if data.get('assignments') and data.get('customers'):
            distances = []
            for cust_id, fac_id in data['assignments'].items():
                cust = next((c for c in data['customers'] if str(c['id']) == str(cust_id)), None)
                fac = next((f for f in data['candidates'] if str(f['id']) == str(fac_id)), None)
                if cust and fac:
                    dist = haversine_distance(cust['lat'], cust['lon'], fac['lat'], fac['lon'])
                    distances.append(dist)
            
            if distances:
                avg_distance = sum(distances) / len(distances)
                max_distance = max(distances)
                # 假设 50km 内为满意服务
                service_level = sum(1 for d in distances if d <= 50) / len(distances)
        
        scenario = NetworkScenario(
            name=data['name'],
            description=data.get('description', ''),
            algorithm=data['algorithm'],
            customers=json.dumps(data.get('customers', [])),
            candidates=json.dumps(data.get('candidates', [])),
            parameters=json.dumps(data.get('parameters', {})),
            selected_facilities=json.dumps(data.get('selected_facilities', [])),
            assignments=json.dumps(data.get('assignments', {})),
            total_cost=data.get('total_cost', 0),
            total_distance=data.get('total_distance', 0),
            total_fixed_cost=data.get('total_fixed_cost', 0),
            transport_cost=data.get('transport_cost', 0),
            solve_time=data.get('solve_time', 0),
            solver=data.get('solver', 'CBC'),
            avg_distance=avg_distance,
            max_distance=max_distance,
            service_level=service_level,
            status=data.get('status', 'draft'),
            created_by=user_id
        )
        
        db.session.add(scenario)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '场景保存成功',
            'scenario_id': scenario.id,
            'scenario': scenario.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/scenarios/<int:scenario_id>', methods=['GET'])
@jwt_required()
def get_scenario(scenario_id):
    """获取场景详情"""
    try:
        scenario = NetworkScenario.query.get(scenario_id)
        
        if not scenario:
            return jsonify({
                'status': 'error',
                'message': '场景不存在'
            }), 404
        
        return jsonify({
            'status': 'success',
            'scenario': scenario.to_dict()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/scenarios/<int:scenario_id>', methods=['PUT'])
@jwt_required()
def update_scenario(scenario_id):
    """更新场景"""
    try:
        user_id = get_jwt_identity()
        scenario = NetworkScenario.query.get(scenario_id)
        
        if not scenario:
            return jsonify({
                'status': 'error',
                'message': '场景不存在'
            }), 404
        
        data = request.json
        
        # 更新字段
        if 'name' in data:
            scenario.name = data['name']
        if 'description' in data:
            scenario.description = data['description']
        if 'status' in data:
            scenario.status = data['status']
        if 'is_favorite' in data:
            scenario.is_favorite = data['is_favorite']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '场景更新成功',
            'scenario': scenario.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/scenarios/<int:scenario_id>', methods=['DELETE'])
@jwt_required()
def delete_scenario(scenario_id):
    """删除场景"""
    try:
        scenario = NetworkScenario.query.get(scenario_id)
        
        if not scenario:
            return jsonify({
                'status': 'error',
                'message': '场景不存在'
            }), 404
        
        db.session.delete(scenario)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '场景已删除'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/scenarios/<int:scenario_id>/compare/<int:other_id>', methods=['GET'])
@jwt_required()
def compare_scenarios(scenario_id, other_id):
    """对比两个场景"""
    try:
        scenario1 = NetworkScenario.query.get(scenario_id)
        scenario2 = NetworkScenario.query.get(other_id)
        
        if not scenario1 or not scenario2:
            return jsonify({
                'status': 'error',
                'message': '场景不存在'
            }), 404
        
        comparison = {
            'scenario1': scenario1.to_dict(),
            'scenario2': scenario2.to_dict(),
            'comparison': {
                'cost_diff': scenario1.total_cost - scenario2.total_cost,
                'distance_diff': scenario1.total_distance - scenario2.total_distance,
                'service_level_diff': (scenario1.service_level or 0) - (scenario2.service_level or 0),
                'facilities_diff': len(json.loads(scenario1.selected_facilities or '[]')) - 
                                   len(json.loads(scenario2.selected_facilities or '[]'))
            }
        }
        
        return jsonify({
            'status': 'success',
            'comparison': comparison
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================
# 网络可视化数据
# ============================================================

@network_bp.route('/visualize', methods=['POST'])
@jwt_required()
def get_visualization_data():
    """
    生成网络可视化数据（用于前端 ECharts）
    
    输入：选址结果
    输出：ECharts 图表配置
    """
    data = request.json
    
    customers = data['customers']
    candidates = data['candidates']
    selected_indices = data.get('selected_indices', [])
    assignments = data.get('assignments', {})
    
    # 构建节点数据
    nodes = []
    links = []
    
    # 添加客户节点
    for i, cust in enumerate(customers):
        nodes.append({
            'name': cust['name'],
            'value': [cust['lon'], cust['lat']],
            'symbolSize': cust['demand'] / 10,
            'itemStyle': {'color': '#91CC75'},
            'category': 0
        })
    
    # 添加设施节点
    for j, cand in enumerate(candidates):
        is_selected = cand['id'] in [candidates[i]['id'] for i in selected_indices] if selected_indices else False
        nodes.append({
            'name': cand['name'],
            'value': [cand['lon'], cand['lat']],
            'symbolSize': 20,
            'itemStyle': {'color': '#EE6666' if is_selected else '#999'},
            'category': 1 if is_selected else 2
        })
    
    # 添加分配连线
    for cust_id, fac_id in assignments.items():
        cust = next((c for c in customers if c['id'] == cust_id), None)
        fac = next((c for c in candidates if c['id'] == fac_id), None)
        if cust and fac:
            links.append({
                'source': cust['name'],
                'target': fac['name'],
                'value': cust['demand']
            })
    
    return jsonify({
        'nodes': nodes,
        'links': links,
        'categories': [
            {'name': '客户'},
            {'name': '已选设施'},
            {'name': '未选设施'}
        ]
    })


# ============================================================
# 真实数据导入
# ============================================================

@network_bp.route('/import/nodes', methods=['POST'])
@jwt_required()
def import_nodes_from_existing():
    """
    从现有 Node 表导入数据到网络节点
    
    输入:
    {
        "customer_types": ["customer"],  // 作为客户的节点类型
        "candidate_types": ["warehouse", "distribution"],  // 作为候选位置的节点类型
        "default_fixed_cost": 100000,  // 默认固定成本
        "default_capacity": 500  // 默认容量
    }
    """
    try:
        from app.models.node import Node
        
        data = request.json
        customer_types = data.get('customer_types', ['customer'])
        candidate_types = data.get('candidate_types', ['warehouse', 'distribution'])
        default_fixed_cost = data.get('default_fixed_cost', 100000)
        default_capacity = data.get('default_capacity', 500)
        
        # 获取所有节点
        all_nodes = Node.query.filter_by(status='active').all()
        
        customers = []
        candidates = []
        
        for i, node in enumerate(all_nodes):
            if node.type in customer_types:
                customers.append({
                    'id': node.id,
                    'name': node.name,
                    'lat': node.latitude,
                    'lon': node.longitude,
                    'demand': node.capacity or random.randint(50, 200),
                    'city': node.city
                })
            elif node.type in candidate_types:
                candidates.append({
                    'id': node.id,
                    'name': node.name,
                    'lat': node.latitude,
                    'lon': node.longitude,
                    'capacity': node.capacity or default_capacity,
                    'fixed_cost': default_fixed_cost,
                    'city': node.city
                })
        
        return jsonify({
            'status': 'success',
            'customers': customers,
            'candidates': candidates,
            'total_customers': len(customers),
            'total_candidates': len(candidates),
            'imported_from': 'existing_nodes'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/import/network-nodes', methods=['POST'])
@jwt_required()
def import_from_network_nodes():
    """
    从网络节点表导入数据
    
    输入:
    {
        "customer_levels": [5],  // 客户层级
        "candidate_levels": [3, 4],  // 候选位置层级（中央仓、区域DC）
        "only_candidates": true  // 是否只使用标记为候选的节点
    }
    """
    try:
        data = request.json
        customer_levels = data.get('customer_levels', [5])
        candidate_levels = data.get('candidate_levels', [3, 4])
        only_candidates = data.get('only_candidates', False)
        
        # 查询客户节点
        customer_query = NetworkNode.query.filter(
            NetworkNode.node_level.in_(customer_levels),
            NetworkNode.status == 'active'
        )
        customers = [{
            'id': n.id,
            'name': n.name,
            'lat': n.latitude,
            'lon': n.longitude,
            'demand': n.demand or random.randint(50, 200),
            'city': n.city
        } for n in customer_query.all()]
        
        # 查询候选位置
        candidate_query = NetworkNode.query.filter(
            NetworkNode.node_level.in_(candidate_levels),
            NetworkNode.status == 'active'
        )
        if only_candidates:
            candidate_query = candidate_query.filter_by(is_candidate=True)
        
        candidates = [{
            'id': n.id,
            'name': n.name,
            'lat': n.latitude,
            'lon': n.longitude,
            'capacity': n.capacity or 500,
            'fixed_cost': n.fixed_cost or 100000,
            'city': n.city
        } for n in candidate_query.all()]
        
        return jsonify({
            'status': 'success',
            'customers': customers,
            'candidates': candidates,
            'total_customers': len(customers),
            'total_candidates': len(candidates)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/network-nodes', methods=['POST'])
@jwt_required()
def create_network_node():
    """创建网络节点"""
    try:
        data = request.json
        
        node = NetworkNode(
            name=data['name'],
            code=data.get('code'),
            node_type=data['node_type'],
            node_level=data.get('node_level', 1),
            province=data.get('province'),
            city=data.get('city'),
            address=data.get('address'),
            longitude=data.get('longitude'),
            latitude=data.get('latitude'),
            capacity=data.get('capacity', 0),
            fixed_cost=data.get('fixed_cost', 0),
            demand=data.get('demand', 0),
            is_candidate=data.get('is_candidate', False),
            contact_name=data.get('contact_name'),
            contact_phone=data.get('contact_phone'),
            notes=data.get('notes')
        )
        
        db.session.add(node)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '节点创建成功',
            'node': node.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@network_bp.route('/network-nodes', methods=['GET'])
@jwt_required()
def list_network_nodes():
    """列出所有网络节点"""
    try:
        node_type = request.args.get('node_type')
        node_level = request.args.get('node_level', type=int)
        is_candidate = request.args.get('is_candidate', type=bool)
        
        query = NetworkNode.query.filter_by(status='active')
        
        if node_type:
            query = query.filter_by(node_type=node_type)
        if node_level:
            query = query.filter_by(node_level=node_level)
        if is_candidate is not None:
            query = query.filter_by(is_candidate=is_candidate)
        
        nodes = query.order_by(NetworkNode.created_at.desc()).all()
        
        return jsonify({
            'status': 'success',
            'nodes': [n.to_dict() for n in nodes],
            'total': len(nodes)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================
# 状态检查
# ============================================================

@network_bp.route('/status', methods=['GET'])
def network_status():
    """网络模块状态"""
    return jsonify({
        'status': 'ok',
        'module': 'network',
        'version': '1.2.0',
        'features': [
            'P-中位选址',
            '集合覆盖选址',
            '容量受限选址(CFLP)',
            '多目标选址优化',
            '动态选址规划',
            '测试数据生成',
            '网络可视化',
            '场景持久化',
            '场景对比',
            '真实数据导入'
        ],
        'solvers': {
            'pulp': 'available',
            'cbc': 'available',
            'cplex': 'available'
        }
    })
