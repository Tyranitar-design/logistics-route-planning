#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
供应链风险管理服务
基于卡拉杰克矩阵、风险评估矩阵、CBA决策模型、AWRP成本估算
"""

import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from app.models import db
from app.models import Order, Vehicle, Route, Node

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

@dataclass
class RiskAssessment:
    """风险评估结果"""
    risk_level: str  # 'critical', 'high', 'medium', 'low'
    probability: float  # 0-1
    impact: float  # 0-1
    score: float  # 概率 × 影响
    recommendation: str
    mitigation_strategies: List[str] = field(default_factory=list)


@dataclass
class KraljicItem:
    """卡拉杰克矩阵物资分类"""
    item_id: int
    item_name: str
    profit_impact: float  # 0-100 利润影响度
    supply_risk: float  # 0-100 供应风险度
    category: str  # 'strategic', 'leverage', 'bottleneck', 'routine'
    strategy: str
    color: str


@dataclass
class CBADecision:
    """成本效益分析决策结果"""
    scenario: str  # 'wait' or 'transfer'
    wait_cost: float
    transfer_cost: float
    critical_days: float
    recommendation: str
    cost_breakdown: Dict


@dataclass
class AWRPCostEstimate:
    """AWRP战争附加费成本估算"""
    cargo_value: float  # 货物价值
    route_type: str  # 'normal', 'high_risk', 'critical'
    base_awrp_rate: float  # 基础费率
    current_awrp_rate: float  # 当前费率
    insurance_cost_before: float  # 危机前保险成本
    insurance_cost_after: float  # 危机后保险成本
    cost_increase_ratio: float  # 成本增长倍数


# ==================== 卡拉杰克矩阵服务 ====================

class KraljicMatrixService:
    """
    卡拉杰克矩阵服务
    根据利润影响和供应风险对采购物资/订单进行分类
    """
    
    # 象限阈值
    PROFIT_IMPACT_THRESHOLD = 50  # 利润影响阈值
    SUPPLY_RISK_THRESHOLD = 50    # 供应风险阈值
    
    # 分类策略
    CATEGORY_STRATEGIES = {
        'strategic': {
            'name': '战略项目',
            'strategy': '建立战略伙伴关系，协同创新，深度穿透审核，签订长期协议',
            'color': '#FF6B6B',
            'risk_level': 'high'
        },
        'leverage': {
            'name': '杠杆项目',
            'strategy': '充分利用市场竞争，招标采购，最大化议价能力，优化总拥有成本',
            'color': '#4ECDC4',
            'risk_level': 'low'
        },
        'bottleneck': {
            'name': '瓶颈项目',
            'strategy': '保障供应为首要目标，寻找替代品，建立安全库存，与供应商保持良好沟通',
            'color': '#FFE66D',
            'risk_level': 'high'
        },
        'routine': {
            'name': '常规项目',
            'strategy': '简化采购流程，推行电子化、自动化采购，追求运营效率',
            'color': '#95E1D3',
            'risk_level': 'low'
        }
    }
    
    def classify_item(
        self,
        item_id: int,
        item_name: str,
        profit_impact: float,
        supply_risk: float
    ) -> KraljicItem:
        """
        对物资/订单进行分类
        
        Args:
            item_id: 物资ID
            item_name: 物资名称
            profit_impact: 利润影响度 (0-100)
            supply_risk: 供应风险度 (0-100)
        
        Returns:
            分类结果
        """
        # 确定象限
        if profit_impact >= self.PROFIT_IMPACT_THRESHOLD:
            if supply_risk >= self.SUPPLY_RISK_THRESHOLD:
                category = 'strategic'  # 战略项目：高利润影响 + 高供应风险
            else:
                category = 'leverage'   # 杠杆项目：高利润影响 + 低供应风险
        else:
            if supply_risk >= self.SUPPLY_RISK_THRESHOLD:
                category = 'bottleneck'  # 瓶颈项目：低利润影响 + 高供应风险
            else:
                category = 'routine'     # 常规项目：低利润影响 + 低供应风险
        
        strategy_info = self.CATEGORY_STRATEGIES[category]
        
        return KraljicItem(
            item_id=item_id,
            item_name=item_name,
            profit_impact=profit_impact,
            supply_risk=supply_risk,
            category=category,
            strategy=strategy_info['strategy'],
            color=strategy_info['color']
        )
    
    def classify_orders(self, orders: List[Order]) -> List[KraljicItem]:
        """批量分类订单"""
        results = []
        for order in orders:
            # 基于订单特征计算利润影响和供应风险
            profit_impact = self._calculate_profit_impact(order)
            supply_risk = self._calculate_supply_risk(order)
            
            item = self.classify_item(
                item_id=order.id,
                item_name=order.order_number,
                profit_impact=profit_impact,
                supply_risk=supply_risk
            )
            results.append(item)
        
        return results
    
    def _calculate_profit_impact(self, order: Order) -> float:
        """计算订单的利润影响度"""
        # 基于订单价值、客户重要性、时效要求等
        score = 50  # 基础分
        
        # 订单价值影响
        if order.estimated_cost and order.estimated_cost > 10000:
            score += min(20, order.estimated_cost / 5000)
        
        # 优先级影响
        if order.priority == 'urgent':
            score += 20
        elif order.priority == 'high':
            score += 10
        
        # 客户影响（简化）
        if order.customer_name and len(order.customer_name) > 0:
            score += 5
        
        return min(100, max(0, score))
    
    def _calculate_supply_risk(self, order: Order) -> float:
        """计算订单的供应风险度"""
        score = 30  # 基础风险
        
        # 距离风险
        if order.distance and order.distance > 500:
            score += min(20, order.distance / 100)
        
        # 节点可用性风险
        if order.pickup_node and order.delivery_node:
            # 如果两个节点都在高风险区域
            score += 15
        
        # 时效压力风险
        if order.priority == 'urgent':
            score += 15
        
        return min(100, max(0, score))
    
    def get_matrix_statistics(self, items: List[KraljicItem]) -> Dict:
        """获取矩阵统计信息"""
        stats = {
            'strategic': 0,
            'leverage': 0,
            'bottleneck': 0,
            'routine': 0,
            'total': len(items),
            'high_risk_count': 0,
            'avg_profit_impact': 0,
            'avg_supply_risk': 0
        }
        
        total_profit = 0
        total_risk = 0
        
        for item in items:
            stats[item.category] += 1
            total_profit += item.profit_impact
            total_risk += item.supply_risk
            
            if item.category in ['strategic', 'bottleneck']:
                stats['high_risk_count'] += 1
        
        if items:
            stats['avg_profit_impact'] = round(total_profit / len(items), 1)
            stats['avg_supply_risk'] = round(total_risk / len(items), 1)
        
        return stats


# ==================== 风险评估矩阵服务 ====================

class RiskAssessmentService:
    """
    风险评估矩阵服务
    基于概率×影响程度进行风险量化评估
    """
    
    # 风险等级阈值
    RISK_LEVELS = {
        'critical': {'min': 0.64, 'color': '#FF0000', 'name': '关键风险'},
        'high': {'min': 0.36, 'color': '#FF6B6B', 'name': '重大风险'},
        'medium': {'min': 0.16, 'color': '#FFE66D', 'name': '一般风险'},
        'low': {'min': 0, 'color': '#95E1D3', 'name': '可接受风险'}
    }
    
    # 风险应对策略库
    MITIGATION_STRATEGIES = {
        'critical': [
            '立即启动应急预案',
            '高层管理层介入',
            '调动所有可用资源',
            '考虑业务连续性计划'
        ],
        'high': [
            '制定详细的应对计划',
            '建立战略储备',
            '寻找替代方案',
            '购买保险或签订保障协议'
        ],
        'medium': [
            '纳入常规监控',
            '制定预案但不立即执行',
            '定期评估风险变化'
        ],
        'low': [
            '常规监控即可',
            '无需额外投入资源'
        ]
    }
    
    def assess_route_risk(
        self,
        route: Route,
        weather_factor: float = 1.0,
        traffic_factor: float = 1.0,
        geopolitical_factor: float = 1.0
    ) -> RiskAssessment:
        """
        评估路线风险
        
        Args:
            route: 路线对象
            weather_factor: 天气风险因子 (0-1)
            traffic_factor: 交通风险因子 (0-1)
            geopolitical_factor: 地缘政治风险因子 (0-1)
        
        Returns:
            风险评估结果
        """
        # 计算概率（基于多种因素）
        probability = self._calculate_probability(
            route, weather_factor, traffic_factor, geopolitical_factor
        )
        
        # 计算影响程度
        impact = self._calculate_impact(route)
        
        # 计算风险得分
        score = probability * impact
        
        # 确定风险等级
        risk_level = self._get_risk_level(score)
        
        # 生成建议
        level_info = self.RISK_LEVELS[risk_level]
        strategies = self.MITIGATION_STRATEGIES[risk_level]
        
        recommendation = self._generate_recommendation(risk_level, probability, impact)
        
        return RiskAssessment(
            risk_level=risk_level,
            probability=round(probability, 3),
            impact=round(impact, 3),
            score=round(score, 3),
            recommendation=recommendation,
            mitigation_strategies=strategies
        )
    
    def _calculate_probability(
        self,
        route: Route,
        weather_factor: float,
        traffic_factor: float,
        geopolitical_factor: float
    ) -> float:
        """计算风险发生概率"""
        base_probability = 0.1  # 基础概率
        
        # 距离因素
        if route.distance:
            base_probability += min(0.3, route.distance / 3000)
        
        # 天气因素
        base_probability *= weather_factor
        
        # 交通因素
        base_probability *= traffic_factor
        
        # 地缘政治因素
        base_probability *= geopolitical_factor
        
        return min(1.0, base_probability)
    
    def _calculate_impact(self, route: Route) -> float:
        """计算风险影响程度"""
        impact = 0.3  # 基础影响
        
        # 成本影响 - 使用 toll_cost 和 fuel_cost 或 distance 计算
        try:
            total_cost = 0
            if hasattr(route, 'toll_cost') and route.toll_cost:
                total_cost += route.toll_cost
            if hasattr(route, 'fuel_cost') and route.fuel_cost:
                total_cost += route.fuel_cost
            if total_cost > 0:
                impact += min(0.3, total_cost / 50000)
            elif route.distance:
                # 用距离估算成本
                estimated_cost = route.distance * 5  # 约5元/公里
                impact += min(0.3, estimated_cost / 50000)
        except:
            pass
        
        # 时间影响
        try:
            if hasattr(route, 'duration') and route.duration:
                impact += min(0.2, route.duration / 600)
            elif hasattr(route, 'estimated_time') and route.estimated_time:
                impact += min(0.2, route.estimated_time / 600)
            elif route.distance:
                # 用距离估算时间
                estimated_duration = route.distance / 60 * 60  # 假设60km/h
                impact += min(0.2, estimated_duration / 600)
        except:
            pass
        
        return min(1.0, impact)
    
    def _get_risk_level(self, score: float) -> str:
        """根据得分确定风险等级"""
        for level, info in self.RISK_LEVELS.items():
            if score >= info['min']:
                return level
        return 'low'
    
    def _generate_recommendation(
        self,
        risk_level: str,
        probability: float,
        impact: float
    ) -> str:
        """生成风险应对建议"""
        if risk_level == 'critical':
            return f'风险极高！发生概率{probability*100:.1f}%，影响程度{impact*100:.1f}%，必须立即采取行动'
        elif risk_level == 'high':
            return f'风险较高，需制定详细应对计划，定期监控风险变化'
        elif risk_level == 'medium':
            return f'风险中等，纳入常规监控，制定预案但不立即执行'
        else:
            return f'风险较低，可接受，进行常规监控即可'
    
    def get_matrix_data(
        self,
        routes: List[Route] = None,
        orders: List[Order] = None
    ) -> Dict:
        """生成风险矩阵可视化数据"""
        matrix = [[0 for _ in range(5)] for _ in range(5)]
        
        items = []
        
        if routes:
            for route in routes:
                assessment = self.assess_route_risk(route)
                prob_idx = min(4, int(assessment.probability * 5))
                impact_idx = min(4, int(assessment.impact * 5))
                matrix[impact_idx][prob_idx] += 1
                items.append({
                    'id': route.id,
                    'name': route.name,
                    'probability': assessment.probability,
                    'impact': assessment.impact,
                    'score': assessment.score,
                    'level': assessment.risk_level
                })
        
        if orders:
            for order in orders:
                # 简化订单风险评估
                prob = min(1.0, (order.distance or 100) / 1000)
                impact = min(1.0, (order.estimated_cost or 1000) / 10000)
                prob_idx = min(4, int(prob * 5))
                impact_idx = min(4, int(impact * 5))
                matrix[impact_idx][prob_idx] += 1
        
        return {
            'matrix': matrix,
            'items': items,
            'level_colors': {k: v['color'] for k, v in self.RISK_LEVELS.items()},
            'level_names': {k: v['name'] for k, v in self.RISK_LEVELS.items()}
        }


# ==================== CBA决策模型服务 ====================

class CBADecisionService:
    """
    成本效益分析决策服务
    用于物流中断时的应急决策
    """
    
    def calculate_decision(
        self,
        cargo_value: float,
        fixed_loss: float,
        daily_loss: float,
        transfer_cost: float,
        waiting_days: float = 0
    ) -> CBADecision:
        """
        计算等待vs转运决策
        
        Args:
            cargo_value: 货物价值
            fixed_loss: 固定损失（仓储、管理等）
            daily_loss: 每日损失（停工、违约金等）
            transfer_cost: 紧急转运成本（如空运费）
            waiting_days: 已等待天数（可选）
        
        Returns:
            决策结果
        """
        # 计算临界点
        # 等待总成本 = 固定损失 + 每日损失 × 天数
        # 转运总成本 = 转运费用
        # 临界点：等待成本 = 转运成本
        # 固定损失 + 每日损失 × X = 转运成本
        # X = (转运成本 - 固定损失) / 每日损失
        
        if daily_loss > 0:
            critical_days = (transfer_cost - fixed_loss) / daily_loss
        else:
            critical_days = float('inf')
        
        # 计算当前两种方案的成本
        current_wait_cost = fixed_loss + daily_loss * waiting_days
        current_transfer_cost = transfer_cost
        
        # 决策建议
        if critical_days <= 0:
            # 转运成本低于固定损失，立即转运
            scenario = 'transfer'
            recommendation = '转运成本低于等待固定损失，建议立即转运'
        elif waiting_days >= critical_days:
            scenario = 'transfer'
            recommendation = f'已等待{waiting_days}天，超过临界点{critical_days:.1f}天，建议立即转运'
        else:
            remaining_days = critical_days - waiting_days
            if remaining_days <= 3:
                scenario = 'transfer'
                recommendation = f'距离临界点仅剩{remaining_days:.1f}天，建议准备转运'
            else:
                scenario = 'wait'
                recommendation = f'还可等待{remaining_days:.1f}天，暂不急于转运'
        
        return CBADecision(
            scenario=scenario,
            wait_cost=round(current_wait_cost, 2),
            transfer_cost=round(current_transfer_cost, 2),
            critical_days=round(critical_days, 2),
            recommendation=recommendation,
            cost_breakdown={
                'fixed_loss': fixed_loss,
                'daily_loss': daily_loss,
                'transfer_cost': transfer_cost,
                'waiting_days': waiting_days,
                'remaining_days': round(max(0, critical_days - waiting_days), 2)
            }
        )
    
    def batch_analyze(self, scenarios: List[Dict]) -> List[Dict]:
        """批量分析多个场景"""
        results = []
        for scenario in scenarios:
            decision = self.calculate_decision(
                cargo_value=scenario.get('cargo_value', 0),
                fixed_loss=scenario.get('fixed_loss', 0),
                daily_loss=scenario.get('daily_loss', 0),
                transfer_cost=scenario.get('transfer_cost', 0),
                waiting_days=scenario.get('waiting_days', 0)
            )
            results.append({
                'name': scenario.get('name', '未命名场景'),
                'decision': decision.__dict__
            })
        return results


# ==================== AWRP成本估算服务 ====================

class AWRPCostService:
    """
    AWRP（战争风险附加费）成本估算服务
    用于高风险区域运输成本估算
    """
    
    # 风险等级对应的AWRP费率
    RISK_RATES = {
        'normal': {'base': 0.001, 'crisis': 0.001},      # 正常：0.1%
        'high_risk': {'base': 0.0025, 'crisis': 0.005},  # 高风险：0.25% → 0.5%
        'critical': {'base': 0.0025, 'crisis': 0.01}     # 危机：0.25% → 1.0%
    }
    
    # 典型危机区域
    CRISIS_ZONES = {
        'hormuz': {'name': '霍尔木兹海峡', 'risk_level': 'critical'},
        'suez': {'name': '苏伊士运河', 'risk_level': 'high_risk'},
        'malacca': {'name': '马六甲海峡', 'risk_level': 'high_risk'},
        'taiwan': {'name': '台湾海峡', 'risk_level': 'high_risk'},
        'normal': {'name': '正常航线', 'risk_level': 'normal'}
    }
    
    def estimate_cost(
        self,
        cargo_value: float,
        zone: str = 'normal',
        is_crisis: bool = False
    ) -> AWRPCostEstimate:
        """
        估算AWRP成本
        
        Args:
            cargo_value: 货物价值（美元）
            zone: 危机区域代码
            is_crisis: 是否处于危机状态
        
        Returns:
            成本估算结果
        """
        # 获取区域信息
        zone_info = self.CRISIS_ZONES.get(zone, self.CRISIS_ZONES['normal'])
        risk_level = zone_info['risk_level']
        rates = self.RISK_RATES[risk_level]
        
        base_rate = rates['base']
        current_rate = rates['crisis'] if is_crisis else rates['base']
        
        # 计算保险成本
        insurance_before = cargo_value * base_rate
        insurance_after = cargo_value * current_rate
        
        # 成本增长倍数
        if base_rate > 0:
            increase_ratio = current_rate / base_rate
        else:
            increase_ratio = 1.0
        
        return AWRPCostEstimate(
            cargo_value=cargo_value,
            route_type=risk_level,
            base_awrp_rate=base_rate,
            current_awrp_rate=current_rate,
            insurance_cost_before=round(insurance_before, 2),
            insurance_cost_after=round(insurance_after, 2),
            cost_increase_ratio=round(increase_ratio, 2)
        )
    
    def compare_routes(
        self,
        cargo_value: float,
        route_a: Dict,  # 穿越风险区域
        route_b: Dict   # 绕行方案
    ) -> Dict:
        """
        对比两条路线的总成本
        
        Args:
            cargo_value: 货物价值
            route_a: 路线A参数 {base_cost, zone, extra_days, daily_time_cost}
            route_b: 路线B参数 {base_cost, extra_fuel, extra_days, daily_time_cost}
        
        Returns:
            对比结果
        """
        # 路线A：穿越风险区域
        zone = route_a.get('zone', 'normal')
        is_crisis = route_a.get('is_crisis', False)
        awrp_estimate = self.estimate_cost(cargo_value, zone, is_crisis)
        
        cost_a = (
            route_a.get('base_cost', 0) +
            awrp_estimate.insurance_cost_after +
            route_a.get('extra_days', 0) * route_a.get('daily_time_cost', 0)
        )
        
        # 路线B：绕行方案
        cost_b = (
            route_b.get('base_cost', 0) +
            route_b.get('extra_fuel', 0) +
            route_b.get('extra_days', 0) * route_b.get('daily_time_cost', 0)
        )
        
        # 决策建议
        if cost_a < cost_b:
            recommendation = '建议穿越风险区域，总成本更低'
            saving = cost_b - cost_a
        else:
            recommendation = '建议绕行，规避风险更经济'
            saving = cost_a - cost_b
        
        return {
            'route_a': {
                'name': '穿越风险区域',
                'base_cost': route_a.get('base_cost', 0),
                'awrp_cost': awrp_estimate.insurance_cost_after,
                'time_cost': route_a.get('extra_days', 0) * route_a.get('daily_time_cost', 0),
                'total_cost': round(cost_a, 2)
            },
            'route_b': {
                'name': '绕行方案',
                'base_cost': route_b.get('base_cost', 0),
                'extra_fuel': route_b.get('extra_fuel', 0),
                'time_cost': route_b.get('extra_days', 0) * route_b.get('daily_time_cost', 0),
                'total_cost': round(cost_b, 2)
            },
            'recommendation': recommendation,
            'saving': round(saving, 2),
            'awrp_details': {
                'base_rate': awrp_estimate.base_awrp_rate,
                'current_rate': awrp_estimate.current_awrp_rate,
                'increase_ratio': awrp_estimate.cost_increase_ratio
            }
        }
    
    def get_zone_list(self) -> List[Dict]:
        """获取所有危机区域列表"""
        return [
            {'code': code, 'name': info['name'], 'risk_level': info['risk_level']}
            for code, info in self.CRISIS_ZONES.items()
        ]


# ==================== 综合服务 ====================

class SupplyChainRiskService:
    """供应链风险管理综合服务"""
    
    def __init__(self):
        self.kraljic = KraljicMatrixService()
        self.risk_assessment = RiskAssessmentService()
        self.cba = CBADecisionService()
        self.awrp = AWRPCostService()
    
    def get_dashboard_data(self) -> Dict:
        """获取风险管理仪表盘数据"""
        # 查询数据
        orders = Order.query.filter(Order.status.in_(['pending', 'assigned'])).limit(50).all()
        routes = Route.query.limit(20).all()
        
        # 卡拉杰克矩阵
        kraljic_items = self.kraljic.classify_orders(orders)
        kraljic_stats = self.kraljic.get_matrix_statistics(kraljic_items)
        
        # 风险矩阵
        risk_matrix = self.risk_assessment.get_matrix_data(routes, orders)
        
        return {
            'kraljic_matrix': {
                'items': [
                    {
                        'id': item.item_id,
                        'name': item.item_name,
                        'profit_impact': item.profit_impact,
                        'supply_risk': item.supply_risk,
                        'category': item.category,
                        'strategy': item.strategy,
                        'color': item.color
                    }
                    for item in kraljic_items
                ],
                'statistics': kraljic_stats
            },
            'risk_matrix': risk_matrix,
            'crisis_zones': self.awrp.get_zone_list()
        }


# 单例实例
_supply_chain_risk_service = None


def get_supply_chain_risk_service() -> SupplyChainRiskService:
    """获取供应链风险管理服务实例"""
    global _supply_chain_risk_service
    if _supply_chain_risk_service is None:
        _supply_chain_risk_service = SupplyChainRiskService()
    return _supply_chain_risk_service