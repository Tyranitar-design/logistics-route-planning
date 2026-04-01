"""
动态定价引擎服务
- 基于供需关系的动态定价
- 时间因素定价（高峰/低谷）
- 距离因素定价
- 竞争因素定价
- 实时调价建议
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd


class SupplyDemandAnalyzer:
    """供需分析器"""
    
    def __init__(self):
        self.demand_history = []
        self.supply_history = []
        self.elasticity = 1.5  # 需求价格弹性
    
    def analyze(self, region: str = None) -> Dict[str, Any]:
        """分析供需状况"""
        # 模拟供需数据
        base_demand = random.uniform(0.5, 1.5)  # 0.5-1.5 倍基准需求
        base_supply = random.uniform(0.6, 1.4)  # 0.6-1.4 倍基准供给
        
        # 区域差异
        region_factors = {
            '北京': (1.3, 1.1), '上海': (1.4, 1.2), '广州': (1.1, 1.0),
            '深圳': (1.2, 1.1), '杭州': (0.9, 1.0), '成都': (0.8, 0.9)
        }
        
        if region in region_factors:
            demand_factor, supply_factor = region_factors[region]
            base_demand *= demand_factor
            base_supply *= supply_factor
        
        # 供需比
        supply_demand_ratio = base_supply / base_demand if base_demand > 0 else 1
        
        return {
            'demand_level': base_demand,
            'supply_level': base_supply,
            'ratio': supply_demand_ratio,
            'status': self._get_status(supply_demand_ratio)
        }
    
    def _get_status(self, ratio: float) -> str:
        """获取供需状态"""
        if ratio < 0.7:
            return 'supply_shortage'  # 供给不足
        elif ratio > 1.3:
            return 'demand_shortage'  # 需求不足
        else:
            return 'balanced'  # 平衡
    
    def calculate_price_adjustment(self, ratio: float) -> float:
        """计算价格调整系数"""
        if ratio < 0.7:
            # 供给不足，价格上涨
            return 1 + (0.7 - ratio) * 0.5
        elif ratio > 1.3:
            # 需求不足，价格下降
            return 1 - (ratio - 1.3) * 0.3
        else:
            return 1.0


class TimeFactorPricing:
    """时间因素定价"""
    
    def __init__(self):
        # 时段定价系数
        self.hour_factors = {
            # 凌晨 0-6 点：低谷
            **{h: 0.8 for h in range(0, 6)},
            # 早晨 6-9 点：早高峰
            **{h: 1.3 for h in range(6, 9)},
            # 上午 9-12 点：正常
            **{h: 1.0 for h in range(9, 12)},
            # 中午 12-14 点：午间
            **{h: 1.1 for h in range(12, 14)},
            # 下午 14-18 点：正常
            **{h: 1.0 for h in range(14, 18)},
            # 傍晚 18-21 点：晚高峰
            **{h: 1.4 for h in range(18, 21)},
            # 夜间 21-24 点：略高
            **{h: 1.2 for h in range(21, 24)}
        }
        
        # 星期定价系数
        self.weekday_factors = {
            0: 1.0,  # 周一
            1: 1.0,  # 周二
            2: 1.0,  # 周三
            3: 1.0,  # 周四
            4: 1.2,  # 周五
            5: 1.3,  # 周六
            6: 1.3   # 周日
        }
        
        # 节假日系数
        self.holiday_factor = 1.5
    
    def get_time_factor(self, dt: datetime = None) -> Dict[str, Any]:
        """获取时间定价系数"""
        if dt is None:
            dt = datetime.now()
        
        hour = dt.hour
        weekday = dt.weekday()
        
        hour_factor = self.hour_factors.get(hour, 1.0)
        weekday_factor = self.weekday_factors.get(weekday, 1.0)
        
        # 判断是否高峰时段
        is_peak = hour_factor > 1.2
        
        return {
            'hour_factor': hour_factor,
            'weekday_factor': weekday_factor,
            'total_factor': hour_factor * weekday_factor,
            'is_peak_hour': is_peak,
            'time_slot': self._get_time_slot(hour)
        }
    
    def _get_time_slot(self, hour: int) -> str:
        """获取时段名称"""
        if 0 <= hour < 6:
            return '凌晨低谷'
        elif 6 <= hour < 9:
            return '早高峰'
        elif 9 <= hour < 12:
            return '上午正常'
        elif 12 <= hour < 14:
            return '午间时段'
        elif 14 <= hour < 18:
            return '下午正常'
        elif 18 <= hour < 21:
            return '晚高峰'
        else:
            return '夜间时段'


class DistancePricing:
    """距离因素定价"""
    
    def __init__(self):
        # 基础价格配置
        self.base_price = 15.0  # 起步价
        self.base_distance = 3.0  # 起步距离（公里）
        self.price_per_km = 2.5  # 每公里价格
        
        # 远距离折扣
        self.long_distance_threshold = 50  # 长距离阈值（公里）
        self.long_distance_discount = 0.8  # 长距离折扣系数
    
    def calculate_distance_price(self, distance: float) -> Dict[str, Any]:
        """计算距离价格"""
        if distance <= self.base_distance:
            # 起步价内
            return {
                'base_price': self.base_price,
                'distance_charge': 0,
                'total_price': self.base_price,
                'is_long_distance': False
            }
        
        # 超出起步距离
        extra_distance = distance - self.base_distance
        distance_charge = extra_distance * self.price_per_km
        
        # 长距离折扣
        is_long_distance = distance > self.long_distance_threshold
        if is_long_distance:
            distance_charge *= self.long_distance_discount
        
        total = self.base_price + distance_charge
        
        return {
            'base_price': self.base_price,
            'distance_charge': round(distance_charge, 2),
            'total_price': round(total, 2),
            'distance': distance,
            'is_long_distance': is_long_distance,
            'discount_applied': self.long_distance_discount if is_long_distance else 1.0
        }


class DynamicPricingEngine:
    """动态定价引擎"""
    
    def __init__(self):
        self.supply_demand = SupplyDemandAnalyzer()
        self.time_pricing = TimeFactorPricing()
        self.distance_pricing = DistancePricing()
        
        # 定价历史
        self.pricing_history = []
        
        # 价格上下限
        self.max_price_multiplier = 2.5  # 最高2.5倍
        self.min_price_multiplier = 0.5  # 最低0.5倍
    
    def calculate_price(
        self,
        distance: float,
        weight: float = 1.0,
        region: str = None,
        urgency: str = 'normal',
        custom_time: datetime = None
    ) -> Dict[str, Any]:
        """
        计算动态价格
        
        Args:
            distance: 距离（公里）
            weight: 货物重量（吨）
            region: 区域
            urgency: 紧急程度 (normal, urgent, scheduled)
            custom_time: 指定时间
        """
        # 1. 基础距离价格
        distance_result = self.distance_pricing.calculate_distance_price(distance)
        base_price = distance_result['total_price']
        
        # 2. 时间因素
        time_result = self.time_pricing.get_time_factor(custom_time)
        time_multiplier = time_result['total_factor']
        
        # 3. 供需因素
        supply_demand_result = self.supply_demand.analyze(region)
        supply_demand_multiplier = self.supply_demand.calculate_price_adjustment(
            supply_demand_result['ratio']
        )
        
        # 4. 紧急程度
        urgency_multiplier = {
            'normal': 1.0,
            'urgent': 1.5,
            'scheduled': 0.9
        }.get(urgency, 1.0)
        
        # 5. 重量因素（大货量优惠）
        weight_multiplier = 1.0
        if weight > 5:
            weight_multiplier = 0.9
        elif weight > 10:
            weight_multiplier = 0.85
        
        # 综合定价系数
        total_multiplier = (
            time_multiplier * 
            supply_demand_multiplier * 
            urgency_multiplier * 
            weight_multiplier
        )
        
        # 限制价格范围
        total_multiplier = max(
            self.min_price_multiplier,
            min(self.max_price_multiplier, total_multiplier)
        )
        
        # 最终价格
        final_price = base_price * total_multiplier
        final_price = round(final_price, 2)
        
        # 构建结果
        result = {
            'base_price': base_price,
            'final_price': final_price,
            'multiplier': round(total_multiplier, 3),
            'breakdown': {
                'distance': distance_result,
                'time': time_result,
                'supply_demand': supply_demand_result,
                'urgency': urgency_multiplier,
                'weight': weight_multiplier
            },
            'price_components': {
                'time_adjustment': round((time_multiplier - 1) * base_price, 2),
                'supply_demand_adjustment': round((supply_demand_multiplier - 1) * base_price, 2),
                'urgency_adjustment': round((urgency_multiplier - 1) * base_price, 2),
                'weight_discount': round((1 - weight_multiplier) * base_price, 2)
            },
            'suggestions': self._generate_suggestions(
                time_result, supply_demand_result, urgency
            )
        }
        
        # 记录历史
        self.pricing_history.append({
            'timestamp': datetime.now().isoformat(),
            'distance': distance,
            'region': region,
            'final_price': final_price,
            'multiplier': total_multiplier
        })
        
        # 保留最近100条记录
        if len(self.pricing_history) > 100:
            self.pricing_history = self.pricing_history[-100:]
        
        return result
    
    def _generate_suggestions(
        self,
        time_result: Dict,
        supply_demand_result: Dict,
        urgency: str
    ) -> List[str]:
        """生成定价建议"""
        suggestions = []
        
        # 时间建议
        if time_result['is_peak_hour']:
            suggestions.append("当前为高峰时段，价格上浮。建议选择非高峰时段可节省运费。")
        
        # 供需建议
        status = supply_demand_result['status']
        if status == 'supply_shortage':
            suggestions.append("当前区域车辆紧张，价格上浮。建议提前预约可获得更优价格。")
        elif status == 'demand_shortage':
            suggestions.append("当前区域运力充足，价格优惠。是下单的好时机！")
        
        # 紧急程度建议
        if urgency == 'urgent':
            suggestions.append("紧急订单已加价50%。如非紧急，建议选择普通配送。")
        
        if not suggestions:
            suggestions.append("当前定价合理，建议下单。")
        
        return suggestions
    
    def get_price_forecast(
        self,
        distance: float,
        region: str = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取价格预测（未来N小时）
        
        帮助用户选择最佳下单时间
        """
        forecasts = []
        base_time = datetime.now()
        
        for h in range(hours):
            forecast_time = base_time + timedelta(hours=h)
            
            # 计算该时段价格
            price_result = self.calculate_price(
                distance=distance,
                region=region,
                custom_time=forecast_time
            )
            
            forecasts.append({
                'hour': h,
                'time': forecast_time.strftime('%Y-%m-%d %H:00'),
                'price': price_result['final_price'],
                'multiplier': price_result['multiplier'],
                'is_peak': price_result['breakdown']['time']['is_peak_hour']
            })
        
        # 找出最佳下单时间
        best_time = min(forecasts, key=lambda x: x['price'])
        worst_time = max(forecasts, key=lambda x: x['price'])
        
        # 计算潜在节省
        potential_savings = worst_time['price'] - best_time['price']
        
        return {
            'forecasts': forecasts,
            'best_time': best_time,
            'worst_time': worst_time,
            'potential_savings': round(potential_savings, 2),
            'recommendation': f"建议在 {best_time['time']} 下单，可节省 ¥{potential_savings:.2f}"
        }
    
    def batch_pricing(
        self,
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量定价
        
        用于订单列表的价格计算和优化建议
        """
        results = []
        total_original = 0
        total_optimized = 0
        
        for order in orders:
            price = self.calculate_price(
                distance=order.get('distance', 10),
                weight=order.get('weight', 1),
                region=order.get('region'),
                urgency=order.get('urgency', 'normal')
            )
            
            results.append({
                'order_id': order.get('id'),
                'original_price': price['base_price'],
                'final_price': price['final_price'],
                'savings': round(price['base_price'] - price['final_price'], 2),
                'suggestions': price['suggestions']
            })
            
            total_original += price['base_price']
            total_optimized += price['final_price']
        
        return {
            'orders': results,
            'summary': {
                'total_orders': len(orders),
                'total_original': round(total_original, 2),
                'total_optimized': round(total_optimized, 2),
                'total_savings': round(total_original - total_optimized, 2)
            }
        }
    
    def get_pricing_statistics(self) -> Dict[str, Any]:
        """获取定价统计"""
        if not self.pricing_history:
            return {
                'total_orders': 0,
                'message': '暂无定价历史'
            }
        
        df = pd.DataFrame(self.pricing_history)
        
        return {
            'total_orders': len(df),
            'avg_price': round(df['final_price'].mean(), 2),
            'max_price': round(df['final_price'].max(), 2),
            'min_price': round(df['final_price'].min(), 2),
            'avg_multiplier': round(df['multiplier'].mean(), 3),
            'avg_distance': round(df['distance'].mean(), 2),
            'price_distribution': {
                'low': len(df[df['multiplier'] < 0.9]),
                'normal': len(df[(df['multiplier'] >= 0.9) & (df['multiplier'] <= 1.1)]),
                'high': len(df[df['multiplier'] > 1.1])
            }
        }


# 全局实例
dynamic_pricing_engine = DynamicPricingEngine()