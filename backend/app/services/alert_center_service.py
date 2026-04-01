#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能预警中心服务
支持：订单预警、车辆预警、路线预警、供应链预警
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from app.models import db
from app.models import Order, Vehicle, Route, Node

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

@dataclass
class Alert:
    """预警信息"""
    id: str
    type: str  # 'order', 'vehicle', 'route', 'supply_chain'
    level: str  # 'critical', 'high', 'medium', 'low'
    title: str
    message: str
    source: str
    source_id: int
    created_at: datetime
    is_read: bool = False
    is_resolved: bool = False
    actions: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AlertStatistics:
    """预警统计"""
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unread: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)


# ==================== 预警规则 ====================

class AlertRules:
    """预警规则配置"""
    
    # 订单预警规则
    ORDER_RULES = {
        'overdue': {
            'name': '订单超时',
            'condition': 'estimated_delivery < now AND status NOT IN (delivered, cancelled)',
            'level': 'high',
            'message': '订单 {order_number} 已超时，预计送达时间已过',
            'actions': ['联系客户', '加急处理', '重新调度']
        },
        'cost_overrun': {
            'name': '成本超预算',
            'condition': 'actual_cost > estimated_cost * 1.2',
            'level': 'medium',
            'message': '订单 {order_number} 成本超出预算20%',
            'actions': ['审核成本', '优化路线', '联系客户']
        },
        'high_priority_pending': {
            'name': '高优先级待处理',
            'condition': 'priority = "urgent" AND status = "pending"',
            'level': 'critical',
            'message': '紧急订单 {order_number} 尚未分配车辆',
            'actions': ['立即分配', '联系司机', '启动应急预案']
        },
        'unassigned_long_time': {
            'name': '长期未分配',
            'condition': 'status = "pending" AND created_at < now - 24h',
            'level': 'medium',
            'message': '订单 {order_number} 已超过24小时未分配',
            'actions': ['查看原因', '重新分配', '联系客户']
        }
    }
    
    # 车辆预警规则
    VEHICLE_RULES = {
        'maintenance_due': {
            'name': '维保到期',
            'condition': 'next_maintenance < now + 7d',
            'level': 'medium',
            'message': '车辆 {plate_number} 即将到期维保',
            'actions': ['预约维保', '调整调度', '通知司机']
        },
        'location_anomaly': {
            'name': '位置异常',
            'condition': 'last_location_update < now - 2h AND status = "in_use"',
            'level': 'high',
            'message': '车辆 {plate_number} 位置信息超过2小时未更新',
            'actions': ['联系司机', '检查设备', '启动追踪']
        },
        'idle_long_time': {
            'name': '长时间闲置',
            'condition': 'status = "available" AND last_used < now - 72h',
            'level': 'low',
            'message': '车辆 {plate_number} 已闲置超过3天',
            'actions': ['检查状态', '安排任务', '维护保养']
        }
    }
    
    # 路线预警规则
    ROUTE_RULES = {
        'weather_warning': {
            'name': '天气预警',
            'condition': 'weather_condition IN (rain, storm, snow)',
            'level': 'high',
            'message': '路线 {name} 受恶劣天气影响',
            'actions': ['绕行建议', '延迟发货', '通知司机']
        },
        'traffic_congestion': {
            'name': '交通拥堵',
            'condition': 'traffic_level = "severe"',
            'level': 'medium',
            'message': '路线 {name} 存在严重拥堵',
            'actions': ['绕行建议', '调整时间', '通知客户']
        },
        'distance_anomaly': {
            'name': '距离异常',
            'condition': 'actual_distance > planned_distance * 1.3',
            'level': 'medium',
            'message': '路线 {name} 实际距离超出计划30%',
            'actions': ['检查原因', '重新规划', '更新计划']
        }
    }
    
    # 供应链预警规则
    SUPPLY_CHAIN_RULES = {
        'supplier_risk': {
            'name': '供应商风险',
            'condition': 'supplier_risk_level = "high"',
            'level': 'high',
            'message': '供应商 {supplier_name} 风险等级升高',
            'actions': ['寻找替代', '增加库存', '重新评估']
        },
        'material_shortage': {
            'name': '物料短缺',
            'condition': 'inventory_level < safety_stock',
            'level': 'critical',
            'message': '物料 {material_name} 库存低于安全库存',
            'actions': ['紧急采购', '调整计划', '通知生产']
        },
        'price_volatility': {
            'name': '价格波动',
            'condition': 'price_change > 15%',
            'level': 'medium',
            'message': '物料 {material_name} 价格波动超过15%',
            'actions': ['评估影响', '锁定价格', '调整报价']
        }
    }


# ==================== 智能预警服务 ====================

class AlertCenterService:
    """智能预警中心服务"""
    
    def __init__(self):
        self.rules = AlertRules()
        self._alert_id_counter = 0
    
    def _generate_alert_id(self) -> str:
        """生成预警ID"""
        self._alert_id_counter += 1
        return f"ALT{datetime.now().strftime('%Y%m%d')}{self._alert_id_counter:04d}"
    
    def check_all_alerts(self) -> List[Alert]:
        """检查所有预警"""
        alerts = []
        
        # 检查订单预警
        alerts.extend(self._check_order_alerts())
        
        # 检查车辆预警
        alerts.extend(self._check_vehicle_alerts())
        
        # 检查路线预警
        alerts.extend(self._check_route_alerts())
        
        # 检查供应链预警
        alerts.extend(self._check_supply_chain_alerts())
        
        # 按严重程度排序
        level_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: level_order.get(x.level, 4))
        
        return alerts
    
    def _check_order_alerts(self) -> List[Alert]:
        """检查订单预警"""
        alerts = []
        now = datetime.now()
        
        try:
            # 1. 检查超时订单
            overdue_orders = Order.query.filter(
                Order.status.in_(['pending', 'assigned', 'in_transit']),
                Order.created_at < now - timedelta(hours=24)
            ).all()
            
            for order in overdue_orders:
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='order',
                    level='high',
                    title='订单超时预警',
                    message=f'订单 {order.order_number} 已超过24小时未完成',
                    source='order',
                    source_id=order.id,
                    created_at=now,
                    actions=['查看详情', '联系司机', '重新调度'],
                    metadata={'order_number': order.order_number, 'status': order.status}
                ))
            
            # 2. 检查紧急订单
            urgent_orders = Order.query.filter(
                Order.priority == 'urgent',
                Order.status == 'pending'
            ).all()
            
            for order in urgent_orders:
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='order',
                    level='critical',
                    title='紧急订单待处理',
                    message=f'紧急订单 {order.order_number} 尚未分配车辆',
                    source='order',
                    source_id=order.id,
                    created_at=now,
                    actions=['立即分配', '启动应急预案'],
                    metadata={'order_number': order.order_number, 'customer': order.customer_name}
                ))
            
            # 3. 检查成本异常
            cost_anomaly_orders = Order.query.filter(
                Order.actual_cost.isnot(None),
                Order.estimated_cost.isnot(None),
                Order.actual_cost > Order.estimated_cost * 1.2
            ).limit(10).all()
            
            for order in cost_anomaly_orders:
                overrun_percent = round((order.actual_cost / order.estimated_cost - 1) * 100, 1)
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='order',
                    level='medium',
                    title='成本超预算',
                    message=f'订单 {order.order_number} 成本超出预算 {overrun_percent}%',
                    source='order',
                    source_id=order.id,
                    created_at=now,
                    actions=['审核成本', '分析原因'],
                    metadata={'order_number': order.order_number, 'overrun_percent': overrun_percent}
                ))
        
        except Exception as e:
            logger.error(f"检查订单预警失败: {e}")
        
        return alerts
    
    def _check_vehicle_alerts(self) -> List[Alert]:
        """检查车辆预警"""
        alerts = []
        now = datetime.now()
        
        try:
            # 1. 检查车辆状态
            in_use_vehicles = Vehicle.query.filter(Vehicle.status == 'in_use').all()
            
            for vehicle in in_use_vehicles:
                # 模拟检查位置更新（实际应从GPS数据获取）
                # 如果超过2小时未更新位置
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='vehicle',
                    level='low',
                    title='车辆运行监控',
                    message=f'车辆 {vehicle.plate_number} 正在执行任务',
                    source='vehicle',
                    source_id=vehicle.id,
                    created_at=now,
                    actions=['查看轨迹', '联系司机'],
                    metadata={'plate_number': vehicle.plate_number, 'driver': vehicle.driver_name}
                ))
            
            # 2. 检查闲置车辆
            idle_vehicles = Vehicle.query.filter(
                Vehicle.status == 'available'
            ).limit(5).all()
            
            if len(idle_vehicles) > 3:
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='vehicle',
                    level='low',
                    title='车辆利用率提醒',
                    message=f'当前有 {len(idle_vehicles)} 辆车辆处于空闲状态',
                    source='vehicle',
                    source_id=0,
                    created_at=now,
                    actions=['查看调度', '安排任务'],
                    metadata={'idle_count': len(idle_vehicles)}
                ))
        
        except Exception as e:
            logger.error(f"检查车辆预警失败: {e}")
        
        return alerts
    
    def _check_route_alerts(self) -> List[Alert]:
        """检查路线预警"""
        alerts = []
        now = datetime.now()
        
        try:
            routes = Route.query.limit(10).all()
            
            for route in routes:
                # 检查距离异常
                if route.distance and route.distance > 1000:
                    alerts.append(Alert(
                        id=self._generate_alert_id(),
                        type='route',
                        level='low',
                        title='长距离路线提醒',
                        message=f'路线 {route.name} 距离较长 ({route.distance}km)，建议检查优化',
                        source='route',
                        source_id=route.id,
                        created_at=now,
                        actions=['优化路线', '检查成本'],
                        metadata={'route_name': route.name, 'distance': route.distance}
                    ))
        
        except Exception as e:
            logger.error(f"检查路线预警失败: {e}")
        
        return alerts
    
    def _check_supply_chain_alerts(self) -> List[Alert]:
        """检查供应链预警"""
        alerts = []
        now = datetime.now()
        
        try:
            # 检查节点状态
            nodes = Node.query.filter(Node.status != 'active').limit(5).all()
            
            for node in nodes:
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='supply_chain',
                    level='medium',
                    title='节点状态异常',
                    message=f'节点 {node.name} 状态异常',
                    source='node',
                    source_id=node.id,
                    created_at=now,
                    actions=['检查状态', '联系负责人'],
                    metadata={'node_name': node.name, 'status': node.status}
                ))
            
            # 添加示例供应链预警
            if not nodes:
                alerts.append(Alert(
                    id=self._generate_alert_id(),
                    type='supply_chain',
                    level='low',
                    title='供应链状态',
                    message='供应链运行正常，无异常预警',
                    source='system',
                    source_id=0,
                    created_at=now,
                    actions=['查看详情'],
                    metadata={'status': 'normal'}
                ))
        
        except Exception as e:
            logger.error(f"检查供应链预警失败: {e}")
        
        return alerts
    
    def get_alert_statistics(self, alerts: List[Alert] = None) -> AlertStatistics:
        """获取预警统计"""
        if alerts is None:
            alerts = self.check_all_alerts()
        
        stats = AlertStatistics()
        stats.total = len(alerts)
        
        for alert in alerts:
            # 按级别统计
            if alert.level == 'critical':
                stats.critical += 1
            elif alert.level == 'high':
                stats.high += 1
            elif alert.level == 'medium':
                stats.medium += 1
            else:
                stats.low += 1
            
            # 未读统计
            if not alert.is_read:
                stats.unread += 1
            
            # 按类型统计
            if alert.type not in stats.by_type:
                stats.by_type[alert.type] = 0
            stats.by_type[alert.type] += 1
        
        return stats
    
    def get_alerts_by_type(self, alert_type: str) -> List[Alert]:
        """按类型获取预警"""
        all_alerts = self.check_all_alerts()
        return [a for a in all_alerts if a.type == alert_type]
    
    def get_alerts_by_level(self, level: str) -> List[Alert]:
        """按级别获取预警"""
        all_alerts = self.check_all_alerts()
        return [a for a in all_alerts if a.level == level]
    
    def mark_as_read(self, alert_id: str) -> bool:
        """标记为已读"""
        # 实际实现应更新数据库
        return True
    
    def mark_as_resolved(self, alert_id: str) -> bool:
        """标记为已解决"""
        # 实际实现应更新数据库
        return True
    
    def get_dashboard_data(self) -> Dict:
        """获取仪表盘数据"""
        alerts = self.check_all_alerts()
        stats = self.get_alert_statistics(alerts)
        
        return {
            'alerts': [
                {
                    'id': a.id,
                    'type': a.type,
                    'level': a.level,
                    'title': a.title,
                    'message': a.message,
                    'source': a.source,
                    'source_id': a.source_id,
                    'created_at': a.created_at.isoformat(),
                    'is_read': a.is_read,
                    'actions': a.actions,
                    'metadata': a.metadata
                }
                for a in alerts[:20]  # 只返回最近20条
            ],
            'statistics': {
                'total': stats.total,
                'critical': stats.critical,
                'high': stats.high,
                'medium': stats.medium,
                'low': stats.low,
                'unread': stats.unread,
                'by_type': stats.by_type
            },
            'summary': {
                'health_score': max(0, 100 - stats.critical * 20 - stats.high * 10 - stats.medium * 5),
                'status': 'danger' if stats.critical > 0 else 'warning' if stats.high > 0 else 'normal',
                'recommendation': self._generate_recommendation(stats)
            }
        }
    
    def _generate_recommendation(self, stats: AlertStatistics) -> str:
        """生成系统建议"""
        if stats.critical > 0:
            return f'系统检测到 {stats.critical} 个严重预警，请立即处理！'
        elif stats.high > 0:
            return f'有 {stats.high} 个高级预警待处理，建议尽快关注。'
        elif stats.medium > 0:
            return f'有 {stats.medium} 个中级预警，建议适当关注。'
        else:
            return '系统运行正常，暂无需要紧急处理的事项。'


# 单例实例
_alert_center_service = None


def get_alert_center_service() -> AlertCenterService:
    """获取预警中心服务实例"""
    global _alert_center_service
    if _alert_center_service is None:
        _alert_center_service = AlertCenterService()
    return _alert_center_service