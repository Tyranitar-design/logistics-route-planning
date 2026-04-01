#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时异常检测系统
支持：订单超时、成本飙升、路线偏离、天气影响、车辆故障预测
使用统计方法 + 机器学习进行实时监控
"""

import logging
import random
import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class AlertType(Enum):
    """预警类型"""
    ORDER_TIMEOUT = 'order_timeout'           # 订单超时
    COST_SPIKE = 'cost_spike'                 # 成本飙升
    ROUTE_DEVIATION = 'route_deviation'       # 路线偏离
    WEATHER_IMPACT = 'weather_impact'         # 天气影响
    VEHICLE_FAULT_PREDICTION = 'vehicle_fault' # 车辆故障预测


class AlertLevel(Enum):
    """预警级别"""
    CRITICAL = 'critical'   # 严重
    HIGH = 'high'          # 高
    MEDIUM = 'medium'      # 中
    LOW = 'low'            # 低
    INFO = 'info'          # 信息


# ==================== 数据模型 ====================

@dataclass
class AnomalyEvent:
    """异常事件"""
    id: str
    type: AlertType
    level: AlertLevel
    title: str
    message: str
    source: str
    source_id: int
    detected_at: datetime
    value: float
    threshold: float
    deviation: float  # 偏差百分比
    trend: str  # 'rising', 'falling', 'stable'
    is_confirmed: bool = False
    actions: List[str] = field(default_factory=list)
    related_events: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class DetectionResult:
    """检测结果"""
    is_anomaly: bool
    value: float
    threshold: float
    deviation: float
    confidence: float
    trend: str
    explanation: str


# ==================== 检测器基类 ====================

class BaseDetector:
    """检测器基类"""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.history = []
        self.threshold = 0
        self.is_trained = False
    
    def update_history(self, value: float):
        """更新历史数据"""
        self.history.append({
            'value': value,
            'timestamp': datetime.now()
        })
        # 保持窗口大小
        if len(self.history) > self.window_size:
            self.history = self.history[-self.window_size:]
    
    def calculate_stats(self) -> Dict:
        """计算统计量"""
        if not self.history:
            return {'mean': 0, 'std': 0, 'min': 0, 'max': 0}
        
        values = [h['value'] for h in self.history]
        return {
            'mean': np.mean(values),
            'std': np.std(values) if len(values) > 1 else 0,
            'min': np.min(values),
            'max': np.max(values)
        }
    
    def detect(self, value: float) -> DetectionResult:
        """检测异常（子类实现）"""
        raise NotImplementedError


# ==================== 订单超时检测器 ====================

class OrderTimeoutDetector(BaseDetector):
    """订单超时异常检测器"""
    
    def __init__(self):
        super().__init__(window_size=100)
        self.timeout_thresholds = {
            'normal': 48,      # 普通订单：48小时
            'urgent': 12,      # 紧急订单：12小时
            'scheduled': 72    # 预约订单：72小时
        }
    
    def detect_order(self, order: Dict) -> DetectionResult:
        """检测单个订单是否超时"""
        # 获取订单优先级
        priority = order.get('priority', 'normal')
        threshold_hours = self.timeout_thresholds.get(priority, 48)
        
        # 计算已用时间
        created_at = order.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        if not created_at:
            return DetectionResult(
                is_anomaly=False, value=0, threshold=threshold_hours,
                deviation=0, confidence=1.0, trend='stable',
                explanation='无法计算时间'
            )
        
        elapsed_hours = (datetime.now() - created_at).total_seconds() / 3600
        
        # 计算偏差
        deviation = (elapsed_hours - threshold_hours) / threshold_hours * 100 if threshold_hours > 0 else 0
        
        # 判断是否超时
        is_timeout = elapsed_hours > threshold_hours
        status = order.get('status') or 'pending'  # 默认 pending
        
        # 只有待处理或运输中的订单才算超时
        is_anomaly = is_timeout and status in ['pending', 'assigned', 'in_transit']
        
        # 趋势判断
        if elapsed_hours > threshold_hours * 1.5:
            trend = 'critical'
        elif elapsed_hours > threshold_hours:
            trend = 'warning'
        else:
            trend = 'normal'
        
        return DetectionResult(
            is_anomaly=is_anomaly,
            value=elapsed_hours,
            threshold=threshold_hours,
            deviation=deviation,
            confidence=0.95,
            trend=trend,
            explanation=f"订单已耗时 {elapsed_hours:.1f} 小时，阈值 {threshold_hours} 小时"
        )
    
    def batch_detect(self, orders: List[Dict]) -> List[AnomalyEvent]:
        """批量检测订单"""
        anomalies = []
        
        for order in orders:
            result = self.detect_order(order)
            
            if result.is_anomaly:
                level = AlertLevel.CRITICAL if result.trend == 'critical' else AlertLevel.HIGH
                
                event = AnomalyEvent(
                    id=f"order_timeout_{order.get('id', random.randint(1000, 9999))}",
                    type=AlertType.ORDER_TIMEOUT,
                    level=level,
                    title=f"订单超时预警",
                    message=f"订单 {order.get('order_number', 'N/A')} 已超时 {result.value:.1f} 小时",
                    source='order',
                    source_id=order.get('id', 0),
                    detected_at=datetime.now(),
                    value=result.value,
                    threshold=result.threshold,
                    deviation=result.deviation,
                    trend=result.trend,
                    actions=['立即处理', '联系客户', '加急配送', '重新调度']
                )
                anomalies.append(event)
        
        return anomalies


# ==================== 成本异常检测器 ====================

class CostAnomalyDetector(BaseDetector):
    """成本异常飙升检测器"""
    
    def __init__(self, z_threshold: float = 2.5):
        super().__init__(window_size=50)
        self.z_threshold = z_threshold
        self.cost_history = defaultdict(list)  # 按路线存储
    
    def detect(self, current_cost: float, route_id: int = None) -> DetectionResult:
        """检测成本异常"""
        # 更新历史
        history_key = route_id or 'global'
        self.cost_history[history_key].append(current_cost)
        
        # 保持窗口大小
        if len(self.cost_history[history_key]) > self.window_size:
            self.cost_history[history_key] = self.cost_history[history_key][-self.window_size:]
        
        values = self.cost_history[history_key]
        
        if len(values) < 5:
            return DetectionResult(
                is_anomaly=False, value=current_cost, threshold=0,
                deviation=0, confidence=0.5, trend='stable',
                explanation='数据不足，无法判断'
            )
        
        # 计算统计量
        mean = np.mean(values[:-1])  # 排除当前值
        std = np.std(values[:-1])
        
        if std == 0:
            std = mean * 0.1  # 避免除零
        
        # Z-score 检测
        z_score = (current_cost - mean) / std
        is_anomaly = abs(z_score) > self.z_threshold
        
        # 计算偏差
        deviation = (current_cost - mean) / mean * 100 if mean > 0 else 0
        
        # 趋势分析
        recent = values[-5:]
        if len(recent) >= 3:
            trend_values = np.gradient(recent)
            avg_trend = np.mean(trend_values)
            if avg_trend > mean * 0.05:
                trend = 'rising'
            elif avg_trend < -mean * 0.05:
                trend = 'falling'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return DetectionResult(
            is_anomaly=is_anomaly,
            value=current_cost,
            threshold=mean * (1 + self.z_threshold * std / mean),
            deviation=deviation,
            confidence=min(0.99, 0.7 + len(values) * 0.01),
            trend=trend,
            explanation=f"当前成本 ¥{current_cost:.2f}，均值 ¥{mean:.2f}，Z-score={z_score:.2f}"
        )
    
    def detect_batch(self, orders: List[Dict]) -> List[AnomalyEvent]:
        """批量检测成本异常"""
        anomalies = []
        
        for order in orders:
            cost = order.get('actual_cost') or order.get('estimated_cost') or 0
            route_id = order.get('vehicle_id')  # 使用 vehicle_id 替代
            
            if not cost or cost <= 0:
                continue
            
            result = self.detect(cost, route_id)
            
            if result.is_anomaly:
                level = AlertLevel.HIGH if result.deviation > 50 else AlertLevel.MEDIUM
                
                event = AnomalyEvent(
                    id=f"cost_spike_{order.get('id', random.randint(1000, 9999))}",
                    type=AlertType.COST_SPIKE,
                    level=level,
                    title=f"成本异常飙升",
                    message=f"订单 {order.get('order_number', 'N/A')} 成本 ¥{cost:.0f}，超出均值 {result.deviation:.0f}%",
                    source='order',
                    source_id=order.get('id', 0),
                    detected_at=datetime.now(),
                    value=cost,
                    threshold=result.threshold,
                    deviation=result.deviation,
                    trend=result.trend,
                    actions=['审核成本', '检查路线', '优化配送', '联系客户']
                )
                anomalies.append(event)
        
        return anomalies


# ==================== 路线偏离检测器 ====================

class RouteDeviationDetector(BaseDetector):
    """路线偏离预警检测器"""
    
    def __init__(self, deviation_threshold: float = 0.3):
        super().__init__(window_size=20)
        self.deviation_threshold = deviation_threshold  # 30% 偏离阈值
        self.planned_routes = {}  # 计划路线存储
    
    def set_planned_route(self, vehicle_id: int, route: List[Dict]):
        """设置计划路线"""
        self.planned_routes[vehicle_id] = {
            'waypoints': route,
            'total_distance': sum(wp.get('distance', 0) for wp in route),
            'created_at': datetime.now()
        }
    
    def detect(self, vehicle_id: int, current_position: Dict, 
               actual_distance: float) -> DetectionResult:
        """检测路线偏离"""
        planned = self.planned_routes.get(vehicle_id)
        
        if not planned:
            return DetectionResult(
                is_anomaly=False, value=actual_distance, threshold=0,
                deviation=0, confidence=0.5, trend='stable',
                explanation='无计划路线数据'
            )
        
        planned_distance = planned['total_distance']
        
        # 计算偏离程度
        if planned_distance > 0:
            deviation_ratio = (actual_distance - planned_distance) / planned_distance
        else:
            deviation_ratio = 0
        
        # 判断是否偏离
        is_anomaly = deviation_ratio > self.deviation_threshold
        
        # 趋势分析
        if deviation_ratio > 0.5:
            trend = 'severe_deviation'
        elif deviation_ratio > 0.3:
            trend = 'moderate_deviation'
        elif deviation_ratio > 0.1:
            trend = 'minor_deviation'
        else:
            trend = 'on_track'
        
        return DetectionResult(
            is_anomaly=is_anomaly,
            value=actual_distance,
            threshold=planned_distance,
            deviation=deviation_ratio * 100,
            confidence=0.9,
            trend=trend,
            explanation=f"实际行驶 {actual_distance:.1f}km，计划 {planned_distance:.1f}km，偏离 {deviation_ratio*100:.0f}%"
        )
    
    def check_realtime(self, vehicle_positions: List[Dict]) -> List[AnomalyEvent]:
        """实时检查车辆位置"""
        anomalies = []
        
        for pos in vehicle_positions:
            vehicle_id = pos.get('vehicle_id')
            actual_distance = pos.get('total_distance', 0)
            
            result = self.detect(vehicle_id, pos, actual_distance)
            
            if result.is_anomaly:
                level = AlertLevel.HIGH if result.trend == 'severe_deviation' else AlertLevel.MEDIUM
                
                event = AnomalyEvent(
                    id=f"route_deviation_{vehicle_id}_{datetime.now().strftime('%Y%m%d%H%M')}",
                    type=AlertType.ROUTE_DEVIATION,
                    level=level,
                    title=f"路线偏离预警",
                    message=f"车辆 {pos.get('plate_number', 'N/A')} 偏离计划路线 {result.deviation:.0f}%",
                    source='vehicle',
                    source_id=vehicle_id,
                    detected_at=datetime.now(),
                    value=actual_distance,
                    threshold=result.threshold,
                    deviation=result.deviation,
                    trend=result.trend,
                    actions=['联系司机', '重新规划', '检查路况', '更新路线'],
                    metadata={'current_position': pos}
                )
                anomalies.append(event)
        
        return anomalies


# ==================== 天气影响检测器 ====================

class WeatherImpactDetector(BaseDetector):
    """天气影响预警检测器"""
    
    def __init__(self):
        super().__init__(window_size=10)
        # 天气影响系数
        self.weather_impact = {
            'sunny': {'delay_factor': 1.0, 'risk_level': 0, 'speed_factor': 1.0},
            'cloudy': {'delay_factor': 1.05, 'risk_level': 0, 'speed_factor': 0.95},
            'rain': {'delay_factor': 1.3, 'risk_level': 1, 'speed_factor': 0.7},
            'heavy_rain': {'delay_factor': 1.8, 'risk_level': 2, 'speed_factor': 0.5},
            'storm': {'delay_factor': 2.5, 'risk_level': 3, 'speed_factor': 0.3},
            'snow': {'delay_factor': 2.0, 'risk_level': 2, 'speed_factor': 0.4},
            'fog': {'delay_factor': 1.5, 'risk_level': 1, 'speed_factor': 0.6},
            'haze': {'delay_factor': 1.2, 'risk_level': 1, 'speed_factor': 0.8}
        }
    
    def detect(self, weather_data: Dict) -> DetectionResult:
        """检测天气影响"""
        weather = weather_data.get('weather', 'sunny')
        impact = self.weather_impact.get(weather, self.weather_impact['sunny'])
        
        # 判断是否需要预警
        risk_level = impact['risk_level']
        is_anomaly = risk_level >= 2  # 风险等级 >= 2 需要预警
        
        # 计算影响程度
        delay_percent = (impact['delay_factor'] - 1) * 100
        
        if risk_level >= 3:
            trend = 'severe'
        elif risk_level >= 2:
            trend = 'moderate'
        elif risk_level >= 1:
            trend = 'minor'
        else:
            trend = 'normal'
        
        return DetectionResult(
            is_anomaly=is_anomaly,
            value=impact['delay_factor'],
            threshold=1.5,  # 延迟超过 50% 为异常
            deviation=delay_percent,
            confidence=0.85,
            trend=trend,
            explanation=f"天气 {weather}，预计延迟 {delay_percent:.0f}%，风险等级 {risk_level}"
        )
    
    def check_regions(self, weather_by_region: Dict[str, Dict]) -> List[AnomalyEvent]:
        """检查各区域天气"""
        anomalies = []
        
        for region, weather_data in weather_by_region.items():
            result = self.detect(weather_data)
            
            if result.is_anomaly:
                weather = weather_data.get('weather', 'unknown')
                level = AlertLevel.CRITICAL if result.trend == 'severe' else AlertLevel.HIGH
                
                event = AnomalyEvent(
                    id=f"weather_{region}_{datetime.now().strftime('%Y%m%d%H')}",
                    type=AlertType.WEATHER_IMPACT,
                    level=level,
                    title=f"天气影响预警 - {region}",
                    message=f"{region} 地区天气 {weather}，预计延迟 {result.deviation:.0f}%",
                    source='weather',
                    source_id=0,
                    detected_at=datetime.now(),
                    value=result.value,
                    threshold=result.threshold,
                    deviation=result.deviation,
                    trend=result.trend,
                    actions=['暂停配送', '调整路线', '通知客户', '安全检查'],
                    metadata={'region': region, 'weather': weather_data}
                )
                anomalies.append(event)
        
        return anomalies


# ==================== 车辆故障预测检测器 ====================

class VehicleFaultPredictor(BaseDetector):
    """车辆故障预测检测器"""
    
    def __init__(self):
        super().__init__(window_size=100)
        # 故障风险因子
        self.risk_factors = {
            'mileage': {'high': 100000, 'critical': 200000},  # 里程
            'age_years': {'high': 5, 'critical': 10},         # 车龄
            'last_maintenance_days': {'high': 90, 'critical': 180},  # 维保间隔
            'fuel_consumption_anomaly': {'high': 1.2, 'critical': 1.5},  # 油耗异常
            'temperature_anomaly': {'high': 5, 'critical': 10},  # 温度异常
        }
    
    def calculate_risk_score(self, vehicle: Dict) -> Tuple[float, List[str]]:
        """计算故障风险分数"""
        score = 0
        risk_items = []
        
        # 里程风险
        mileage = vehicle.get('total_mileage', 0)
        if mileage > self.risk_factors['mileage']['critical']:
            score += 30
            risk_items.append(f"高里程 ({mileage/10000:.0f}万公里)")
        elif mileage > self.risk_factors['mileage']['high']:
            score += 15
            risk_items.append(f"里程较高 ({mileage/10000:.0f}万公里)")
        
        # 车龄风险
        purchase_date = vehicle.get('purchase_date')
        if purchase_date:
            try:
                if isinstance(purchase_date, str):
                    purchase_date = datetime.fromisoformat(purchase_date.replace('Z', '+00:00'))
                age_years = (datetime.now() - purchase_date).days / 365
                
                if age_years > self.risk_factors['age_years']['critical']:
                    score += 25
                    risk_items.append(f"车龄过长 ({age_years:.1f}年)")
                elif age_years > self.risk_factors['age_years']['high']:
                    score += 12
                    risk_items.append(f"车龄较长 ({age_years:.1f}年)")
            except Exception:
                pass  # 忽略日期解析错误
        
        # 维保间隔风险
        last_maintenance = vehicle.get('last_maintenance')
        if last_maintenance:
            try:
                if isinstance(last_maintenance, str):
                    last_maintenance = datetime.fromisoformat(last_maintenance.replace('Z', '+00:00'))
                maintenance_days = (datetime.now() - last_maintenance).days
                
                if maintenance_days > self.risk_factors['last_maintenance_days']['critical']:
                    score += 35
                    risk_items.append(f"维保逾期 ({maintenance_days}天)")
                elif maintenance_days > self.risk_factors['last_maintenance_days']['high']:
                    score += 20
                    risk_items.append(f"维保即将到期 ({maintenance_days}天)")
            except Exception:
                pass  # 忽略日期解析错误
        
        # 状态异常
        status = vehicle.get('status', 'available')
        if status == 'maintenance':
            score += 10
            risk_items.append("车辆在修")
        
        # 随机故障因子（模拟传感器数据）
        if random.random() < 0.1:  # 10% 概率出现异常
            anomaly_type = random.choice(['油耗异常', '温度异常', '胎压异常'])
            score += 15
            risk_items.append(anomaly_type)
        
        return min(score, 100), risk_items
    
    def predict(self, vehicle: Dict) -> DetectionResult:
        """预测车辆故障风险"""
        score, risk_items = self.calculate_risk_score(vehicle)
        
        # 判断是否需要预警
        is_anomaly = score >= 40
        threshold = 40
        
        # 趋势判断
        if score >= 70:
            trend = 'critical'
        elif score >= 50:
            trend = 'high'
        elif score >= 40:
            trend = 'medium'
        else:
            trend = 'low'
        
        explanation = f"故障风险评分: {score}/100"
        if risk_items:
            explanation += f"，风险项: {', '.join(risk_items)}"
        
        return DetectionResult(
            is_anomaly=is_anomaly,
            value=score,
            threshold=threshold,
            deviation=(score - threshold) / threshold * 100 if threshold > 0 else 0,
            confidence=0.8,
            trend=trend,
            explanation=explanation
        )
    
    def batch_predict(self, vehicles: List[Dict]) -> List[AnomalyEvent]:
        """批量预测车辆故障"""
        anomalies = []
        
        for vehicle in vehicles:
            result = self.predict(vehicle)
            
            if result.is_anomaly:
                if result.trend == 'critical':
                    level = AlertLevel.CRITICAL
                elif result.trend == 'high':
                    level = AlertLevel.HIGH
                else:
                    level = AlertLevel.MEDIUM
                
                event = AnomalyEvent(
                    id=f"vehicle_fault_{vehicle.get('id', random.randint(1000, 9999))}",
                    type=AlertType.VEHICLE_FAULT_PREDICTION,
                    level=level,
                    title=f"车辆故障预测预警",
                    message=f"车辆 {vehicle.get('plate_number', 'N/A')} 故障风险评分 {result.value}/100",
                    source='vehicle',
                    source_id=vehicle.get('id', 0),
                    detected_at=datetime.now(),
                    value=result.value,
                    threshold=result.threshold,
                    deviation=result.deviation,
                    trend=result.trend,
                    actions=['安排检修', '更换车辆', '调整任务', '备件准备'],
                    metadata={'risk_score': result.value, 'vehicle': vehicle}
                )
                anomalies.append(event)
        
        return anomalies


# ==================== 综合异常检测服务 ====================

class RealtimeAnomalyDetectionService:
    """实时异常检测综合服务"""
    
    def __init__(self):
        self.order_timeout_detector = OrderTimeoutDetector()
        self.cost_anomaly_detector = CostAnomalyDetector()
        self.route_deviation_detector = RouteDeviationDetector()
        self.weather_impact_detector = WeatherImpactDetector()
        self.vehicle_fault_predictor = VehicleFaultPredictor()
        
        # 检测历史
        self.detection_history = []
        self.max_history = 1000
    
    def run_full_detection(
        self,
        orders: List[Dict] = None,
        vehicles: List[Dict] = None,
        vehicle_positions: List[Dict] = None,
        weather_data: Dict[str, Dict] = None
    ) -> Dict[str, Any]:
        """
        运行全量异常检测
        
        Returns:
            检测结果汇总
        """
        all_anomalies = []
        detection_time = datetime.now()
        
        # 1. 订单超时检测
        if orders:
            order_anomalies = self.order_timeout_detector.batch_detect(orders)
            all_anomalies.extend(order_anomalies)
        
        # 2. 成本异常检测
        if orders:
            cost_anomalies = self.cost_anomaly_detector.detect_batch(orders)
            all_anomalies.extend(cost_anomalies)
        
        # 3. 路线偏离检测
        if vehicle_positions:
            route_anomalies = self.route_deviation_detector.check_realtime(vehicle_positions)
            all_anomalies.extend(route_anomalies)
        
        # 4. 天气影响检测
        if weather_data:
            weather_anomalies = self.weather_impact_detector.check_regions(weather_data)
            all_anomalies.extend(weather_anomalies)
        
        # 5. 车辆故障预测
        if vehicles:
            vehicle_anomalies = self.vehicle_fault_predictor.batch_predict(vehicles)
            all_anomalies.extend(vehicle_anomalies)
        
        # 按严重程度排序
        level_order = {
            AlertLevel.CRITICAL: 0,
            AlertLevel.HIGH: 1,
            AlertLevel.MEDIUM: 2,
            AlertLevel.LOW: 3,
            AlertLevel.INFO: 4
        }
        all_anomalies.sort(key=lambda x: level_order.get(x.level, 5))
        
        # 统计
        summary = {
            'total_anomalies': len(all_anomalies),
            'by_type': {},
            'by_level': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
        
        for anomaly in all_anomalies:
            # 按类型统计
            type_name = anomaly.type.value
            if type_name not in summary['by_type']:
                summary['by_type'][type_name] = 0
            summary['by_type'][type_name] += 1
            
            # 按级别统计
            level_name = anomaly.level.value
            if level_name in summary['by_level']:
                summary['by_level'][level_name] += 1
        
        # 记录历史
        self.detection_history.append({
            'timestamp': detection_time,
            'summary': summary,
            'anomalies': [
                {
                    'id': a.id,
                    'type': a.type.value,
                    'level': a.level.value,
                    'message': a.message
                }
                for a in all_anomalies[:50]  # 只保留前50条
            ]
        })
        
        # 保持历史大小
        if len(self.detection_history) > self.max_history:
            self.detection_history = self.detection_history[-self.max_history:]
        
        return {
            'success': True,
            'detection_time': detection_time.isoformat(),
            'summary': summary,
            'anomalies': [
                {
                    'id': a.id,
                    'type': a.type.value,
                    'level': a.level.value,
                    'title': a.title,
                    'message': a.message,
                    'source': a.source,
                    'source_id': a.source_id,
                    'value': a.value,
                    'threshold': a.threshold,
                    'deviation': round(a.deviation, 2),
                    'trend': a.trend,
                    'actions': a.actions,
                    'detected_at': a.detected_at.isoformat()
                }
                for a in all_anomalies
            ]
        }
    
    def get_detection_history(self, limit: int = 10) -> List[Dict]:
        """获取检测历史"""
        return self.detection_history[-limit:]
    
    def get_anomaly_trends(self, hours: int = 24) -> Dict:
        """获取异常趋势"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        trend_data = []
        for record in self.detection_history:
            record_time = record['timestamp']
            if record_time > cutoff:
                trend_data.append({
                    'time': record_time.isoformat(),
                    'total': record['summary']['total_anomalies'],
                    'by_type': record['summary']['by_type']
                })
        
        return {
            'period_hours': hours,
            'data_points': len(trend_data),
            'trends': trend_data
        }


# 全局实例
realtime_anomaly_service = RealtimeAnomalyDetectionService()