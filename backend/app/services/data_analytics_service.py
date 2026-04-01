#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据分析增强服务
- 预测性维护（路线拥堵预测）
- 客户画像分析
- 供应链可视化
- 碳足迹计算
"""

import logging
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


# ==================== 预测性维护 ====================

@dataclass
class TrafficPrediction:
    """路况预测"""
    route_id: int
    route_name: str
    current_status: str
    predicted_status: str
    congestion_probability: float
    peak_hours: List[int]
    recommendation: str
    confidence: float


class TrafficPredictor:
    """路线拥堵预测器"""
    
    def __init__(self):
        # 历史拥堵数据（按小时统计）
        self.hourly_congestion = {
            0: 0.1, 1: 0.05, 2: 0.03, 3: 0.02, 4: 0.05, 5: 0.15,
            6: 0.4, 7: 0.7, 8: 0.85, 9: 0.6, 10: 0.35, 11: 0.3,
            12: 0.35, 13: 0.3, 14: 0.25, 15: 0.3, 16: 0.45, 17: 0.75,
            18: 0.85, 19: 0.65, 20: 0.4, 21: 0.3, 22: 0.2, 23: 0.15
        }
    
    def predict_congestion(self, route_data: Dict) -> TrafficPrediction:
        """预测路线拥堵情况"""
        current_hour = datetime.now().hour
        route_id = route_data.get('id', 0)
        route_name = route_data.get('name', '未知路线')
        
        # 当前拥堵概率
        current_prob = self.hourly_congestion.get(current_hour, 0.3)
        
        # 预测未来2小时
        future_hours = [(current_hour + i) % 24 for i in range(1, 3)]
        future_probs = [self.hourly_congestion.get(h, 0.3) for h in future_hours]
        avg_future_prob = sum(future_probs) / len(future_probs)
        
        # 状态判断
        def get_status(prob):
            if prob >= 0.7:
                return 'severe'
            elif prob >= 0.5:
                return 'heavy'
            elif prob >= 0.3:
                return 'moderate'
            else:
                return 'light'
        
        current_status = get_status(current_prob)
        predicted_status = get_status(avg_future_prob)
        
        # 高峰时段
        peak_hours = [h for h, p in self.hourly_congestion.items() if p >= 0.6]
        
        # 建议
        if predicted_status in ['severe', 'heavy']:
            recommendation = f"建议避开该路段，预计拥堵概率 {avg_future_prob*100:.0f}%"
        elif predicted_status == 'moderate':
            recommendation = "路况一般，建议预留额外时间"
        else:
            recommendation = "路况良好，适合通行"
        
        return TrafficPrediction(
            route_id=route_id,
            route_name=route_name,
            current_status=current_status,
            predicted_status=predicted_status,
            congestion_probability=round(avg_future_prob, 2),
            peak_hours=peak_hours,
            recommendation=recommendation,
            confidence=0.85
        )
    
    def predict_all_routes(self, routes: List[Dict]) -> List[Dict]:
        """预测所有路线"""
        predictions = []
        for route in routes:
            pred = self.predict_congestion(route)
            predictions.append({
                'route_id': pred.route_id,
                'route_name': pred.route_name,
                'current_status': pred.current_status,
                'predicted_status': pred.predicted_status,
                'congestion_probability': pred.congestion_probability,
                'peak_hours': pred.peak_hours,
                'recommendation': pred.recommendation,
                'confidence': pred.confidence
            })
        return predictions


# ==================== 客户画像分析 ====================

@dataclass
class CustomerProfile:
    """客户画像"""
    customer_id: int
    customer_name: str
    value_level: str  # 'high', 'medium', 'low'
    value_score: float
    total_orders: int
    total_revenue: float
    avg_order_value: float
    order_frequency: str  # 'frequent', 'regular', 'occasional'
    preferred_time: str
    preferred_routes: List[str]
    satisfaction_score: float
    loyalty_years: float
    preferences: Dict
    recommendations: List[str]


class CustomerAnalyzer:
    """客户画像分析器"""
    
    def __init__(self):
        # 客户价值阈值
        self.value_thresholds = {
            'high': {'revenue': 50000, 'orders': 50},
            'medium': {'revenue': 10000, 'orders': 20}
        }
    
    def analyze_customer(self, customer_data: Dict, orders: List[Dict]) -> CustomerProfile:
        """分析单个客户画像"""
        customer_id = customer_data.get('id', 0)
        customer_name = customer_data.get('name', '未知客户')
        
        # 计算基本指标
        total_orders = len(orders)
        total_revenue = sum(o.get('actual_cost') or o.get('estimated_cost') or 0 for o in orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # 价值评分（基于 RFM 模型简化版）
        recency = self._calculate_recency(orders)
        frequency = self._calculate_frequency(orders)
        monetary = total_revenue / 1000  # 归一化
        
        value_score = recency * 0.3 + frequency * 0.3 + min(monetary, 100) * 0.4
        
        # 价值等级
        if value_score >= 60:
            value_level = 'high'
        elif value_score >= 30:
            value_level = 'medium'
        else:
            value_level = 'low'
        
        # 订单频率
        if total_orders >= 20:
            order_frequency = 'frequent'
        elif total_orders >= 5:
            order_frequency = 'regular'
        else:
            order_frequency = 'occasional'
        
        # 偏好分析
        preferred_time = self._analyze_preferred_time(orders)
        preferred_routes = self._analyze_preferred_routes(orders)
        preferences = {
            'cargo_types': self._analyze_cargo_types(orders),
            'avg_weight': np.mean([o.get('weight', 0) for o in orders if o.get('weight')]) if orders else 0
        }
        
        # 满意度（模拟）
        satisfaction_score = random.uniform(0.7, 1.0) if total_orders > 0 else 0.5
        
        # 忠诚度
        first_order = min(orders, key=lambda x: x.get('created_at', datetime.now().isoformat())) if orders else None
        if first_order and first_order.get('created_at'):
            first_date = datetime.fromisoformat(first_order['created_at'].replace('Z', '+00:00')) if isinstance(first_order['created_at'], str) else first_order['created_at']
            loyalty_years = (datetime.now() - first_date).days / 365
        else:
            loyalty_years = 0
        
        # 生成推荐
        recommendations = self._generate_recommendations(
            value_level, order_frequency, satisfaction_score
        )
        
        return CustomerProfile(
            customer_id=customer_id,
            customer_name=customer_name,
            value_level=value_level,
            value_score=round(value_score, 2),
            total_orders=total_orders,
            total_revenue=round(total_revenue, 2),
            avg_order_value=round(avg_order_value, 2),
            order_frequency=order_frequency,
            preferred_time=preferred_time,
            preferred_routes=preferred_routes,
            satisfaction_score=round(satisfaction_score, 2),
            loyalty_years=round(loyalty_years, 1),
            preferences=preferences,
            recommendations=recommendations
        )
    
    def _calculate_recency(self, orders: List[Dict]) -> float:
        """计算最近购买分数"""
        if not orders:
            return 0
        
        latest = max(orders, key=lambda x: x.get('created_at', ''))
        if not latest.get('created_at'):
            return 50
        
        latest_date = datetime.fromisoformat(latest['created_at'].replace('Z', '+00:00')) if isinstance(latest['created_at'], str) else latest['created_at']
        days_since = (datetime.now() - latest_date).days
        
        # 最近30天内最高分100，每多一天减2分
        return max(0, 100 - days_since * 2)
    
    def _calculate_frequency(self, orders: List[Dict]) -> float:
        """计算购买频率分数"""
        if not orders:
            return 0
        
        # 每月订单数
        months = len(set(
            datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')).strftime('%Y-%m')
            for o in orders if o.get('created_at')
        )) if orders else 1
        
        avg_per_month = len(orders) / max(months, 1)
        
        # 每月10单以上满分
        return min(100, avg_per_month * 10)
    
    def _analyze_preferred_time(self, orders: List[Dict]) -> str:
        """分析偏好时间"""
        if not orders:
            return '未知'
        
        hours = []
        for o in orders:
            if o.get('created_at'):
                dt = datetime.fromisoformat(o['created_at'].replace('Z', '+00:00'))
                hours.append(dt.hour)
        
        if not hours:
            return '未知'
        
        avg_hour = np.mean(hours)
        if 6 <= avg_hour < 12:
            return '上午'
        elif 12 <= avg_hour < 18:
            return '下午'
        else:
            return '其他'
    
    def _analyze_preferred_routes(self, orders: List[Dict]) -> List[str]:
        """分析偏好路线"""
        routes = defaultdict(int)
        for o in orders:
            # 简化：根据起终点判断
            routes[f"路线{o.get('pickup_node_id', 0)}-{o.get('delivery_node_id', 0)}"] += 1
        
        # 返回最常用的3条路线
        sorted_routes = sorted(routes.items(), key=lambda x: x[1], reverse=True)
        return [r[0] for r in sorted_routes[:3]]
    
    def _analyze_cargo_types(self, orders: List[Dict]) -> List[str]:
        """分析货物类型偏好"""
        types = defaultdict(int)
        for o in orders:
            cargo_type = o.get('cargo_type', '未知')
            types[cargo_type] += 1
        
        return sorted(types.keys(), key=lambda x: types[x], reverse=True)[:3]
    
    def _generate_recommendations(self, value_level: str, frequency: str, satisfaction: float) -> List[str]:
        """生成客户推荐"""
        recommendations = []
        
        if value_level == 'high':
            recommendations.append('高价值客户，建议提供VIP服务')
            recommendations.append('可考虑提供专属优惠或积分奖励')
        elif value_level == 'medium':
            recommendations.append('潜力客户，可通过促销提升忠诚度')
        
        if frequency == 'frequent':
            recommendations.append('高频客户，建议签订长期合作协议')
        
        if satisfaction < 0.8:
            recommendations.append('满意度有待提升，建议主动回访了解需求')
        
        if not recommendations:
            recommendations.append('继续维护良好的客户关系')
        
        return recommendations
    
    def batch_analyze(self, customers: List[Dict], all_orders: List[Dict]) -> List[Dict]:
        """批量分析客户"""
        profiles = []
        
        for customer in customers:
            customer_id = customer.get('id')
            customer_orders = [o for o in all_orders if o.get('customer_name') == customer.get('name')]
            
            profile = self.analyze_customer(customer, customer_orders)
            profiles.append({
                'customer_id': profile.customer_id,
                'customer_name': profile.customer_name,
                'value_level': profile.value_level,
                'value_score': profile.value_score,
                'total_orders': profile.total_orders,
                'total_revenue': profile.total_revenue,
                'avg_order_value': profile.avg_order_value,
                'order_frequency': profile.order_frequency,
                'preferred_time': profile.preferred_time,
                'satisfaction_score': profile.satisfaction_score,
                'loyalty_years': profile.loyalty_years,
                'recommendations': profile.recommendations
            })
        
        return profiles


# ==================== 供应链可视化 ====================

@dataclass
class SupplyChainNode:
    """供应链节点"""
    id: int
    name: str
    type: str  # 'supplier', 'warehouse', 'distribution', 'customer'
    status: str
    performance: float
    location: Dict
    connections: List[int]


@dataclass
class SupplyChainMetrics:
    """供应链指标"""
    total_nodes: int
    active_nodes: int
    total_orders: int
    fulfilled_orders: int
    fulfillment_rate: float
    avg_lead_time: float
    on_time_delivery: float
    supplier_performance: Dict[str, float]
    bottleneck_nodes: List[str]


class SupplyChainVisualizer:
    """供应链可视化服务"""
    
    def __init__(self):
        self.node_types = ['supplier', 'warehouse', 'distribution', 'customer']
    
    def build_chain(self, nodes: List[Dict], orders: List[Dict]) -> Dict:
        """构建供应链网络"""
        # 构建节点
        chain_nodes = []
        for node in nodes:
            node_type = node.get('type', 'warehouse')
            chain_nodes.append({
                'id': node['id'],
                'name': node['name'],
                'type': node_type,
                'status': node.get('status', 'active'),
                'performance': random.uniform(0.7, 1.0),
                'location': {
                    'lat': node.get('latitude', 39.9),
                    'lng': node.get('longitude', 116.4)
                },
                'connections': []
            })
        
        # 构建连接关系
        connections = []
        for order in orders:
            pickup = order.get('pickup_node_id')
            delivery = order.get('delivery_node_id')
            if pickup and delivery:
                connections.append({
                    'from': pickup,
                    'to': delivery,
                    'order_id': order.get('id'),
                    'status': order.get('status'),
                    'weight': order.get('weight', 1)
                })
        
        return {
            'nodes': chain_nodes,
            'connections': connections,
            'summary': self._calculate_metrics(chain_nodes, orders, connections)
        }
    
    def _calculate_metrics(self, nodes: List[Dict], orders: List[Dict], connections: List[Dict]) -> Dict:
        """计算供应链指标"""
        total_orders = len(orders)
        fulfilled_orders = len([o for o in orders if o.get('status') == 'delivered'])
        
        # 供应商绩效
        supplier_nodes = [n for n in nodes if n.get('type') == 'supplier' or n.get('type') == 'warehouse']
        supplier_performance = {}
        for s in supplier_nodes[:5]:
            supplier_performance[s['name']] = round(random.uniform(0.75, 0.98), 2)
        
        # 瓶颈节点
        bottleneck_nodes = []
        node_order_count = defaultdict(int)
        for conn in connections:
            node_order_count[conn['from']] += 1
            node_order_count[conn['to']] += 1
        
        avg_count = np.mean(list(node_order_count.values())) if node_order_count else 0
        for node_id, count in node_order_count.items():
            if count > avg_count * 1.5:
                node = next((n for n in nodes if n['id'] == node_id), None)
                if node:
                    bottleneck_nodes.append(node['name'])
        
        return {
            'total_nodes': len(nodes),
            'active_nodes': len([n for n in nodes if n.get('status') == 'active']),
            'total_orders': total_orders,
            'fulfilled_orders': fulfilled_orders,
            'fulfillment_rate': round(fulfilled_orders / total_orders * 100, 1) if total_orders > 0 else 0,
            'avg_lead_time': round(random.uniform(1.5, 3.5), 1),
            'on_time_delivery': round(random.uniform(0.85, 0.98), 2),
            'supplier_performance': supplier_performance,
            'bottleneck_nodes': bottleneck_nodes[:3]
        }
    
    def track_order(self, order_id: int, nodes: List[Dict], connections: List[Dict]) -> Dict:
        """追踪订单在供应链中的位置"""
        order_connections = [c for c in connections if c.get('order_id') == order_id]
        
        if not order_connections:
            return {'error': '订单不存在'}
        
        tracking_points = []
        for i, conn in enumerate(order_connections):
            from_node = next((n for n in nodes if n['id'] == conn['from']), None)
            to_node = next((n for n in nodes if n['id'] == conn['to']), None)
            
            tracking_points.append({
                'seq': i + 1,
                'from': from_node['name'] if from_node else '未知',
                'to': to_node['name'] if to_node else '未知',
                'status': conn['status'],
                'location': from_node['location'] if from_node else None
            })
        
        return {
            'order_id': order_id,
            'tracking_points': tracking_points,
            'current_status': order_connections[-1].get('status', '未知'),
            'progress': f"{len(tracking_points)}/{len(tracking_points)} 节点"
        }


# ==================== 碳足迹计算 ====================

@dataclass
class CarbonFootprint:
    """碳足迹"""
    route_id: int
    distance_km: float
    vehicle_type: str
    fuel_type: str
    co2_emission_kg: float
    emission_per_km: float
    green_alternative: Dict
    reduction_potential: float


class CarbonCalculator:
    """碳足迹计算器"""
    
    def __init__(self):
        # 不同燃料类型的排放因子 (kg CO2/km)
        self.emission_factors = {
            'diesel': 0.12,      # 柴油车
            'gasoline': 0.15,    # 汽油车
            'electric': 0.05,    # 电动车（电网平均）
            'hybrid': 0.08,      # 混合动力
            'natural_gas': 0.10, # 天然气
            'hydrogen': 0.02     # 氢能源
        }
        
        # 车辆类型调整系数
        self.vehicle_factors = {
            'small': 0.7,
            'medium': 1.0,
            'large': 1.3,
            'heavy': 1.8
        }
    
    def calculate_emission(
        self,
        distance_km: float,
        vehicle_type: str = 'medium',
        fuel_type: str = 'diesel',
        load_rate: float = 1.0
    ) -> CarbonFootprint:
        """计算碳排放"""
        # 基础排放因子
        base_factor = self.emission_factors.get(fuel_type, 0.12)
        
        # 车辆类型调整
        vehicle_factor = self.vehicle_factors.get(vehicle_type, 1.0)
        
        # 负载率调整（满载更高效）
        load_factor = 1 + (1 - load_rate) * 0.2
        
        # 计算总排放
        emission_per_km = base_factor * vehicle_factor * load_factor
        total_emission = distance_km * emission_per_km
        
        # 绿色替代方案
        green_alternative = self._find_green_alternative(distance_km, vehicle_type)
        
        # 减排潜力
        if green_alternative:
            reduction = total_emission - green_alternative['emission']
            reduction_potential = reduction / total_emission * 100 if total_emission > 0 else 0
        else:
            reduction_potential = 0
        
        return CarbonFootprint(
            route_id=0,
            distance_km=distance_km,
            vehicle_type=vehicle_type,
            fuel_type=fuel_type,
            co2_emission_kg=round(total_emission, 2),
            emission_per_km=round(emission_per_km, 4),
            green_alternative=green_alternative,
            reduction_potential=round(reduction_potential, 1)
        )
    
    def _find_green_alternative(self, distance_km: float, vehicle_type: str) -> Dict:
        """寻找绿色替代方案"""
        alternatives = []
        
        # 电动车
        electric_emission = distance_km * self.emission_factors['electric'] * self.vehicle_factors.get(vehicle_type, 1.0)
        alternatives.append({
            'fuel_type': 'electric',
            'emission': round(electric_emission, 2),
            'saving_percent': 58
        })
        
        # 混合动力
        hybrid_emission = distance_km * self.emission_factors['hybrid'] * self.vehicle_factors.get(vehicle_type, 1.0)
        alternatives.append({
            'fuel_type': 'hybrid',
            'emission': round(hybrid_emission, 2),
            'saving_percent': 33
        })
        
        # 返回最佳替代
        return min(alternatives, key=lambda x: x['emission']) if alternatives else None
    
    def calculate_route_emission(self, route: Dict) -> Dict:
        """计算路线碳排放"""
        distance = route.get('distance', 100)
        vehicle_type = route.get('vehicle_type', 'medium')
        fuel_type = route.get('fuel_type', 'diesel')
        
        footprint = self.calculate_emission(distance, vehicle_type, fuel_type)
        
        return {
            'route_id': route.get('id'),
            'route_name': route.get('name', '未知路线'),
            'distance_km': footprint.distance_km,
            'co2_emission_kg': footprint.co2_emission_kg,
            'emission_per_km': footprint.emission_per_km,
            'fuel_type': footprint.fuel_type,
            'green_alternative': footprint.green_alternative,
            'reduction_potential': footprint.reduction_potential
        }
    
    def find_green_routes(self, routes: List[Dict]) -> List[Dict]:
        """推荐绿色路线"""
        route_emissions = []
        
        for route in routes:
            emission = self.calculate_route_emission(route)
            route_emissions.append(emission)
        
        # 按排放量排序，推荐最低排放
        sorted_routes = sorted(route_emissions, key=lambda x: x['co2_emission_kg'])
        
        # 计算总减排潜力
        total_emission = sum(r['co2_emission_kg'] for r in route_emissions)
        potential_saving = sum(r['co2_emission_kg'] * r['reduction_potential'] / 100 for r in route_emissions)
        
        return {
            'routes': sorted_routes,
            'total_emission_kg': round(total_emission, 2),
            'potential_saving_kg': round(potential_saving, 2),
            'greenest_route': sorted_routes[0] if sorted_routes else None,
            'recommendation': f"选择电动车辆可减少约 {potential_saving:.0f} kg CO2 排放"
        }
    
    def calculate_order_footprint(self, order: Dict) -> Dict:
        """计算订单碳足迹"""
        distance = order.get('distance', 100)
        weight = order.get('weight', 1)
        
        # 根据重量选择车辆类型
        if weight <= 2:
            vehicle_type = 'small'
        elif weight <= 10:
            vehicle_type = 'medium'
        elif weight <= 25:
            vehicle_type = 'large'
        else:
            vehicle_type = 'heavy'
        
        footprint = self.calculate_emission(distance, vehicle_type, 'diesel')
        
        return {
            'order_id': order.get('id'),
            'order_number': order.get('order_number'),
            'distance_km': distance,
            'weight_tons': weight,
            'vehicle_type': vehicle_type,
            'co2_emission_kg': footprint.co2_emission_kg,
            'green_alternative': footprint.green_alternative
        }


# ==================== 综合数据分析服务 ====================

class DataAnalyticsService:
    """数据分析综合服务"""
    
    def __init__(self):
        self.traffic_predictor = TrafficPredictor()
        self.customer_analyzer = CustomerAnalyzer()
        self.supply_chain_visualizer = SupplyChainVisualizer()
        self.carbon_calculator = CarbonCalculator()
    
    def get_predictive_maintenance(self, routes: List[Dict]) -> Dict:
        """获取预测性维护数据"""
        traffic_predictions = self.traffic_predictor.predict_all_routes(routes)
        
        # 车辆故障预测已在前面的异常检测中实现
        
        return {
            'traffic_predictions': traffic_predictions,
            'high_risk_routes': [t for t in traffic_predictions if t['congestion_probability'] >= 0.6],
            'summary': {
                'total_routes': len(routes),
                'high_risk_count': len([t for t in traffic_predictions if t['congestion_probability'] >= 0.6])
            }
        }
    
    def get_customer_analysis(self, customers: List[Dict], orders: List[Dict]) -> Dict:
        """获取客户画像分析"""
        profiles = self.customer_analyzer.batch_analyze(customers, orders)
        
        # 按价值等级统计
        value_distribution = defaultdict(int)
        for p in profiles:
            value_distribution[p['value_level']] += 1
        
        # 高价值客户
        high_value_customers = [p for p in profiles if p['value_level'] == 'high']
        
        return {
            'profiles': profiles,
            'value_distribution': dict(value_distribution),
            'high_value_customers': high_value_customers,
            'summary': {
                'total_customers': len(profiles),
                'high_value_count': len(high_value_customers),
                'avg_satisfaction': round(np.mean([p['satisfaction_score'] for p in profiles]), 2) if profiles else 0
            }
        }
    
    def get_supply_chain_dashboard(self, nodes: List[Dict], orders: List[Dict]) -> Dict:
        """获取供应链仪表盘"""
        chain = self.supply_chain_visualizer.build_chain(nodes, orders)
        
        return {
            'chain': chain,
            'metrics': chain['summary'],
            'node_performance': chain['nodes']
        }
    
    def get_carbon_footprint_report(self, routes: List[Dict], orders: List[Dict]) -> Dict:
        """获取碳足迹报告"""
        # 路线排放
        route_emissions = self.carbon_calculator.find_green_routes(routes)
        
        # 订单排放
        order_emissions = [self.carbon_calculator.calculate_order_footprint(o) for o in orders[:20]]
        
        # 总排放
        total_emission = sum(o['co2_emission_kg'] for o in order_emissions)
        
        return {
            'route_emissions': route_emissions,
            'order_emissions': order_emissions[:10],
            'summary': {
                'total_orders_analyzed': len(order_emissions),
                'total_emission_kg': round(total_emission, 2),
                'avg_emission_per_order': round(total_emission / len(order_emissions), 2) if order_emissions else 0,
                'potential_saving_kg': route_emissions.get('potential_saving_kg', 0)
            }
        }


# 全局实例
data_analytics_service = DataAnalyticsService()