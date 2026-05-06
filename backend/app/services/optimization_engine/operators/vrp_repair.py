"""
VRP 可行性修复器
================

B2 第一阶段正式实现：
- 容量约束修复接口
- 客户完整性校验接口
"""

from __future__ import annotations

from typing import Sequence, List


class VRPRepairError(ValueError):
    """修复器输入非法时抛出"""


def validate_customer_sequence(customers: Sequence[int]) -> List[int]:
    values = list(int(x) for x in customers)
    if len(values) != len(set(values)):
        raise VRPRepairError("客户序列中存在重复客户")
    return values


def repair_capacity_feasibility(
    customer_sequence: Sequence[int],
    demands: Sequence[float],
    vehicle_capacity: float,
) -> List[List[int]]:
    """
    将客户序列修复为满足容量约束的路线集合。

    规则：
    - 按输入顺序遍历客户
    - 若加入当前路线会超载，则切分为新路线
    - 保证所有客户恰好出现一次
    - 不自动插入 depot，返回纯客户路线，供上层自行决定是否补 0
    """
    customers = validate_customer_sequence(customer_sequence)
    if vehicle_capacity <= 0:
        raise VRPRepairError("vehicle_capacity 必须大于 0")

    demand_list = list(float(x) for x in demands)
    if not demand_list:
        raise VRPRepairError("demands 不能为空")

    routes: List[List[int]] = []
    current_route: List[int] = []
    current_load = 0.0

    for customer in customers:
        demand_idx = customer - 1
        if demand_idx < 0 or demand_idx >= len(demand_list):
            raise VRPRepairError(f"客户 {customer} 超出 demands 范围")

        demand = float(demand_list[demand_idx])
        if demand < 0:
            raise VRPRepairError(f"客户 {customer} 的需求不能为负数")
        if demand > vehicle_capacity:
            raise VRPRepairError(
                f"客户 {customer} 单点需求 {demand} 超过车辆容量 {vehicle_capacity}"
            )

        if current_route and current_load + demand > vehicle_capacity:
            routes.append(current_route)
            current_route = [customer]
            current_load = demand
        else:
            current_route.append(customer)
            current_load += demand

    if current_route:
        routes.append(current_route)

    # 完整性二次校验
    flattened = [c for route in routes for c in route]
    if flattened != customers:
        raise VRPRepairError("repair 后客户顺序或完整性异常")
    if len(flattened) != len(set(flattened)):
        raise VRPRepairError("repair 后仍存在重复客户")

    for route in routes:
        route_load = sum(demand_list[c - 1] for c in route)
        if route_load > vehicle_capacity:
            raise VRPRepairError("repair 后仍存在超载路线")

    return routes
