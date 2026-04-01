"""
库存优化服务
- EOQ 经济订货量模型
- 安全库存计算
- VMI 供应商管理库存
- 再订货点计算
- 库存周转分析
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd


class EOQModel:
    """
    EOQ 经济订货量模型
    
    用于计算最优订货数量，使总库存成本最低
    """
    
    def __init__(self):
        self.annual_demand = 0
        self.ordering_cost = 0  # 每次订货成本
        self.holding_cost = 0   # 单位持有成本
        self.unit_price = 0     # 单价
    
    def calculate_eoq(
        self,
        annual_demand: float,
        ordering_cost: float,
        holding_cost_per_unit: float,
        unit_price: float = 1.0
    ) -> Dict[str, Any]:
        """
        计算经济订货量
        
        EOQ = sqrt(2 * D * S / H)
        
        Args:
            annual_demand: 年需求量
            ordering_cost: 每次订货成本
            holding_cost_per_unit: 单位年持有成本
            unit_price: 单价
        
        Returns:
            EOQ 计算结果
        """
        # EOQ 公式
        eoq = np.sqrt(2 * annual_demand * ordering_cost / holding_cost_per_unit)
        
        # 订货次数
        orders_per_year = annual_demand / eoq
        
        # 订货周期（天）
        order_cycle = 365 / orders_per_year
        
        # 总成本
        total_ordering_cost = orders_per_year * ordering_cost
        total_holding_cost = (eoq / 2) * holding_cost_per_unit
        total_inventory_cost = total_ordering_cost + total_holding_cost
        
        # 年采购成本
        purchase_cost = annual_demand * unit_price
        total_cost = purchase_cost + total_inventory_cost
        
        return {
            'eoq': round(eoq, 2),
            'orders_per_year': round(orders_per_year, 2),
            'order_cycle_days': round(order_cycle, 1),
            'costs': {
                'total_ordering_cost': round(total_ordering_cost, 2),
                'total_holding_cost': round(total_holding_cost, 2),
                'total_inventory_cost': round(total_inventory_cost, 2),
                'purchase_cost': round(purchase_cost, 2),
                'total_cost': round(total_cost, 2)
            },
            'parameters': {
                'annual_demand': annual_demand,
                'ordering_cost': ordering_cost,
                'holding_cost_per_unit': holding_cost_per_unit,
                'unit_price': unit_price
            }
        }
    
    def calculate_with_discount(
        self,
        annual_demand: float,
        ordering_cost: float,
        holding_cost_rate: float,
        unit_price: float,
        discount_thresholds: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        考虑数量折扣的 EOQ 计算
        
        Args:
            discount_thresholds: 折扣阈值列表
                [{'min_qty': 0, 'discount': 0}, {'min_qty': 100, 'discount': 0.05}]
        """
        results = []
        
        for discount_tier in discount_thresholds:
            min_qty = discount_tier.get('min_qty', 0)
            discount = discount_tier.get('discount', 0)
            
            adjusted_price = unit_price * (1 - discount)
            holding_cost = adjusted_price * holding_cost_rate
            
            # 计算 EOQ
            eoq = np.sqrt(2 * annual_demand * ordering_cost / holding_cost)
            
            # 检查是否在折扣范围内
            if eoq < min_qty:
                # 需要增加订货量才能获得折扣
                actual_qty = min_qty
            else:
                actual_qty = eoq
            
            # 计算总成本
            orders_per_year = annual_demand / actual_qty
            total_ordering_cost = orders_per_year * ordering_cost
            total_holding_cost = (actual_qty / 2) * holding_cost
            purchase_cost = annual_demand * adjusted_price
            total_cost = purchase_cost + total_ordering_cost + total_holding_cost
            
            results.append({
                'discount_tier': discount_tier,
                'adjusted_price': round(adjusted_price, 2),
                'suggested_qty': round(actual_qty, 2),
                'total_cost': round(total_cost, 2),
                'savings': round(annual_demand * unit_price - purchase_cost, 2)
            })
        
        # 找出最优方案
        optimal = min(results, key=lambda x: x['total_cost'])
        
        return {
            'all_options': results,
            'optimal': optimal,
            'recommendation': f"建议订货量 {optimal['suggested_qty']:.0f} 件，享受 {optimal['discount_tier']['discount']*100:.0f}% 折扣"
        }


class SafetyStockCalculator:
    """
    安全库存计算器
    
    用于应对需求和供应的不确定性
    """
    
    def __init__(self):
        self.service_level_factors = {
            0.90: 1.28,  # 90% 服务水平
            0.95: 1.65,  # 95% 服务水平
            0.97: 1.88,  # 97% 服务水平
            0.99: 2.33,  # 99% 服务水平
        }
    
    def calculate_safety_stock(
        self,
        avg_demand: float,
        demand_std: float,
        lead_time: float,
        lead_time_std: float = 0,
        service_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        计算安全库存
        
        SS = Z * sqrt(LT * σd² + d² * σLT²)
        
        Args:
            avg_demand: 平均日需求量
            demand_std: 需求标准差
            lead_time: 平均提前期（天）
            lead_time_std: 提前期标准差
            service_level: 服务水平（0.9-0.99）
        """
        # 获取 Z 值
        z = self.service_level_factors.get(service_level, 1.65)
        
        # 安全库存计算
        if lead_time_std > 0:
            # 考虑提前期变动
            safety_stock = z * np.sqrt(
                lead_time * demand_std**2 + 
                avg_demand**2 * lead_time_std**2
            )
        else:
            # 仅考虑需求变动
            safety_stock = z * demand_std * np.sqrt(lead_time)
        
        # 再订货点
        reorder_point = avg_demand * lead_time + safety_stock
        
        return {
            'safety_stock': round(safety_stock, 2),
            'reorder_point': round(reorder_point, 2),
            'avg_demand': avg_demand,
            'demand_std': demand_std,
            'lead_time': lead_time,
            'service_level': service_level,
            'z_factor': z,
            'explanation': f"在{service_level*100:.0f}%服务水平下，需保持{round(safety_stock, 0):.0f}单位安全库存"
        }
    
    def calculate_for_seasonal(
        self,
        historical_demand: List[float],
        lead_time: float,
        service_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        考虑季节性的安全库存计算
        """
        demand = np.array(historical_demand)
        
        # 计算移动平均
        window = min(7, len(demand) // 2)
        moving_avg = np.convolve(demand, np.ones(window)/window, mode='valid')
        
        # 计算季节性因子
        seasonal_factors = []
        for i, d in enumerate(demand[window-1:]):
            if moving_avg[i - window + 1] > 0:
                seasonal_factors.append(d / moving_avg[i - window + 1])
        
        avg_seasonal = np.mean(seasonal_factors) if seasonal_factors else 1.0
        
        # 计算需求标准差（去季节化）
        deseasonalized = demand / avg_seasonal
        demand_std = np.std(deseasonalized)
        
        # 计算安全库存
        result = self.calculate_safety_stock(
            avg_demand=np.mean(demand),
            demand_std=demand_std,
            lead_time=lead_time,
            service_level=service_level
        )
        
        result['seasonal_factor'] = round(avg_seasonal, 3)
        result['demand_trend'] = 'increasing' if moving_avg[-1] > moving_avg[0] else 'decreasing'
        
        return result


class VMIModel:
    """
    VMI 供应商管理库存模型
    
    用于优化供应商与买方的库存协作
    """
    
    def __init__(self):
        self.vmi_params = {}
    
    def setup_vmi(
        self,
        supplier_id: str,
        min_inventory: float,
        max_inventory: float,
        replenishment_frequency: int,
        lead_time: float
    ) -> Dict[str, Any]:
        """
        设置 VMI 参数
        
        Args:
            supplier_id: 供应商ID
            min_inventory: 最小库存水平
            max_inventory: 最大库存水平
            replenishment_frequency: 补货频率（天）
            lead_time: 提前期
        """
        self.vmi_params[supplier_id] = {
            'min_inventory': min_inventory,
            'max_inventory': max_inventory,
            'replenishment_frequency': replenishment_frequency,
            'lead_time': lead_time,
            'target_inventory': (min_inventory + max_inventory) / 2
        }
        
        return {
            'supplier_id': supplier_id,
            'config': self.vmi_params[supplier_id],
            'status': 'VMI 参数已配置'
        }
    
    def calculate_replenishment(
        self,
        supplier_id: str,
        current_inventory: float,
        avg_daily_demand: float
    ) -> Dict[str, Any]:
        """
        计算补货量
        
        VMI 补货量 = 目标库存 - 当前库存
        """
        if supplier_id not in self.vmi_params:
            return {'error': '供应商 VMI 参数未配置'}
        
        params = self.vmi_params[supplier_id]
        target = params['target_inventory']
        
        # 计算补货量
        replenishment_qty = target - current_inventory
        
        # 检查是否需要补货
        if current_inventory < params['min_inventory']:
            need_replenish = True
            urgency = 'urgent'
        elif current_inventory < target:
            need_replenish = True
            urgency = 'normal'
        else:
            need_replenish = False
            urgency = 'none'
        
        # 预计到达时间
        eta_days = params['lead_time']
        
        # 预计消耗
        expected_consumption = avg_daily_demand * eta_days
        
        # 预计库存
        projected_inventory = current_inventory - expected_consumption + (replenishment_qty if need_replenish else 0)
        
        return {
            'supplier_id': supplier_id,
            'current_inventory': current_inventory,
            'target_inventory': target,
            'replenishment_qty': max(0, round(replenishment_qty, 2)),
            'need_replenish': need_replenish,
            'urgency': urgency,
            'eta_days': eta_days,
            'projected_inventory': round(projected_inventory, 2),
            'days_of_stock': round(current_inventory / avg_daily_demand, 1) if avg_daily_demand > 0 else 0,
            'recommendation': self._get_recommendation(need_replenish, replenishment_qty, urgency)
        }
    
    def _get_recommendation(self, need: bool, qty: float, urgency: str) -> str:
        """获取补货建议"""
        if not need:
            return "库存充足，暂无需补货"
        elif urgency == 'urgent':
            return f"⚠️ 库存低于安全水平，需立即补货 {qty:.0f} 单位"
        else:
            return f"建议补货 {qty:.0f} 单位，维持目标库存水平"
    
    def get_vmi_performance(
        self,
        supplier_id: str,
        stockouts: int,
        total_periods: int,
        avg_inventory: float,
        target_inventory: float
    ) -> Dict[str, Any]:
        """
        评估 VMI 绩效
        """
        service_level = 1 - (stockouts / total_periods)
        inventory_efficiency = avg_inventory / target_inventory if target_inventory > 0 else 0
        
        # 计算 VMI 得分
        score = service_level * 60 + (1 - abs(inventory_efficiency - 1)) * 40
        
        return {
            'supplier_id': supplier_id,
            'service_level': round(service_level * 100, 1),
            'stockouts': stockouts,
            'inventory_efficiency': round(inventory_efficiency * 100, 1),
            'vmi_score': round(score, 1),
            'rating': '优秀' if score >= 85 else '良好' if score >= 70 else '需改进'
        }


class InventoryOptimizationService:
    """
    库存优化综合服务
    """
    
    def __init__(self):
        self.eoq = EOQModel()
        self.safety_stock = SafetyStockCalculator()
        self.vmi = VMIModel()
        
        # 库存数据
        self.inventory_data = {}
    
    def optimize_inventory(
        self,
        item_id: str,
        annual_demand: float,
        ordering_cost: float,
        holding_cost_rate: float,
        unit_price: float,
        lead_time: float,
        demand_std: float,
        service_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        综合库存优化
        
        返回完整的库存策略建议
        """
        # 计算 EOQ
        holding_cost_per_unit = unit_price * holding_cost_rate
        eoq_result = self.eoq.calculate_eoq(
            annual_demand, ordering_cost, holding_cost_per_unit, unit_price
        )
        
        # 计算安全库存
        avg_daily_demand = annual_demand / 365
        safety_result = self.safety_stock.calculate_safety_stock(
            avg_daily_demand, demand_std, lead_time, 0, service_level
        )
        
        # 综合建议
        return {
            'item_id': item_id,
            'economic_order_quantity': eoq_result['eoq'],
            'order_cycle_days': eoq_result['order_cycle_days'],
            'safety_stock': safety_result['safety_stock'],
            'reorder_point': safety_result['reorder_point'],
            'max_inventory': eoq_result['eoq'] + safety_result['safety_stock'],
            'costs': eoq_result['costs'],
            'policy': {
                'order_when': f"库存降至 {safety_result['reorder_point']:.0f} 单位时订货",
                'order_qty': f"每次订货 {eoq_result['eoq']:.0f} 单位",
                'order_frequency': f"每 {eoq_result['order_cycle_days']:.0f} 天订货一次"
            },
            'service_level': service_level
        }
    
    def analyze_inventory_turnover(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        库存周转分析
        """
        results = []
        
        for item in items:
            avg_inventory = item.get('avg_inventory', 0)
            annual_usage = item.get('annual_usage', 0)
            
            turnover_rate = annual_usage / avg_inventory if avg_inventory > 0 else 0
            days_of_stock = 365 / turnover_rate if turnover_rate > 0 else 0
            
            # 评估周转效率
            if turnover_rate >= 6:
                efficiency = '优秀'
            elif turnover_rate >= 4:
                efficiency = '良好'
            elif turnover_rate >= 2:
                efficiency = '一般'
            else:
                efficiency = '需改进'
            
            results.append({
                'item_id': item.get('id'),
                'item_name': item.get('name', ''),
                'avg_inventory': avg_inventory,
                'annual_usage': annual_usage,
                'turnover_rate': round(turnover_rate, 2),
                'days_of_stock': round(days_of_stock, 1),
                'efficiency': efficiency
            })
        
        # 汇总统计
        total_inventory = sum(r['avg_inventory'] for r in results)
        total_usage = sum(r['annual_usage'] for r in results)
        avg_turnover = total_usage / total_inventory if total_inventory > 0 else 0
        
        # ABC 分类
        sorted_items = sorted(results, key=lambda x: x['annual_usage'], reverse=True)
        total_usage_sum = sum(r['annual_usage'] for r in sorted_items)
        cumulative = 0
        
        for r in sorted_items:
            cumulative += r['annual_usage']
            ratio = cumulative / total_usage_sum if total_usage_sum > 0 else 0
            
            if ratio <= 0.8:
                r['abc_class'] = 'A'
            elif ratio <= 0.95:
                r['abc_class'] = 'B'
            else:
                r['abc_class'] = 'C'
        
        return {
            'items': results,
            'summary': {
                'total_items': len(items),
                'total_inventory': round(total_inventory, 2),
                'total_usage': round(total_usage, 2),
                'avg_turnover_rate': round(avg_turnover, 2),
                'class_a_count': len([r for r in results if r.get('abc_class') == 'A']),
                'class_b_count': len([r for r in results if r.get('abc_class') == 'B']),
                'class_c_count': len([r for r in results if r.get('abc_class') == 'C'])
            }
        }
    
    def get_inventory_alerts(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        库存预警
        """
        alerts = []
        
        for item in items:
            current = item.get('current_inventory', 0)
            reorder_point = item.get('reorder_point', 0)
            safety_stock = item.get('safety_stock', 0)
            
            if current <= safety_stock * 0.5:
                alerts.append({
                    'item_id': item.get('id'),
                    'item_name': item.get('name', ''),
                    'level': 'critical',
                    'message': f"库存严重不足！当前 {current}，安全库存 {safety_stock}",
                    'current_inventory': current,
                    'safety_stock': safety_stock
                })
            elif current <= safety_stock:
                alerts.append({
                    'item_id': item.get('id'),
                    'item_name': item.get('name', ''),
                    'level': 'warning',
                    'message': f"库存低于安全水平，当前 {current}，安全库存 {safety_stock}",
                    'current_inventory': current,
                    'safety_stock': safety_stock
                })
            elif current <= reorder_point:
                alerts.append({
                    'item_id': item.get('id'),
                    'item_name': item.get('name', ''),
                    'level': 'info',
                    'message': f"接近再订货点，当前 {current}，再订货点 {reorder_point}",
                    'current_inventory': current,
                    'reorder_point': reorder_point
                })
        
        # 按严重程度排序
        level_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: level_order.get(x['level'], 3))
        
        return {
            'alerts': alerts,
            'total_alerts': len(alerts),
            'critical_count': len([a for a in alerts if a['level'] == 'critical']),
            'warning_count': len([a for a in alerts if a['level'] == 'warning']),
            'info_count': len([a for a in alerts if a['level'] == 'info'])
        }
    
    def simulate_inventory_policy(
        self,
        initial_inventory: float,
        daily_demand_func,
        lead_time: float,
        eoq: float,
        reorder_point: float,
        days: int = 365
    ) -> Dict[str, Any]:
        """
        库存策略模拟
        
        模拟给定策略下的库存变化
        """
        inventory = initial_inventory
        pending_orders = []  # 待到货订单
        daily_inventory = []
        stockouts = 0
        orders_placed = 0
        
        for day in range(days):
            # 处理到货
            arrived = [o for o in pending_orders if o['arrival_day'] == day]
            for order in arrived:
                inventory += order['qty']
            pending_orders = [o for o in pending_orders if o['arrival_day'] > day]
            
            # 检查是否需要订货
            if inventory <= reorder_point:
                pending_orders.append({
                    'qty': eoq,
                    'arrival_day': day + lead_time
                })
                orders_placed += 1
            
            # 满足需求
            demand = daily_demand_func(day)
            if inventory >= demand:
                inventory -= demand
            else:
                stockouts += 1
                inventory = 0
            
            daily_inventory.append(inventory)
        
        return {
            'initial_inventory': initial_inventory,
            'final_inventory': inventory,
            'avg_inventory': np.mean(daily_inventory),
            'min_inventory': np.min(daily_inventory),
            'max_inventory': np.max(daily_inventory),
            'stockouts': stockouts,
            'service_level': 1 - stockouts / days,
            'orders_placed': orders_placed,
            'daily_inventory': daily_inventory
        }


# 全局实例
inventory_service = InventoryOptimizationService()