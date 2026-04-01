#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据分析服务
提供运营报表、成本分析、KPI 监控、预测分析
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import math

from app.models import db
from app.models import Order, Vehicle, Node, Route

logger = logging.getLogger(__name__)


@dataclass
class KPIMetrics:
    """KPI 指标"""
    total_orders: int
    completed_orders: int
    pending_orders: int
    total_revenue: float
    total_cost: float
    profit_margin: float
    avg_delivery_time: float
    on_time_rate: float
    vehicle_utilization: float
    customer_satisfaction: float


@dataclass
class TrendData:
    """趋势数据"""
    date: str
    orders: int
    revenue: float
    cost: float
    profit: float


class AnalyticsService:
    """数据分析服务"""
    
    def get_dashboard_metrics(self) -> Dict:
        """获取仪表盘关键指标（优化版：减少数据库查询次数）"""
        try:
            from sqlalchemy import func, case
            
            # 单次查询获取订单统计
            order_stats = db.session.query(
                func.count(Order.id).label('total'),
                func.sum(case((Order.status == 'delivered', 1), else_=0)).label('completed'),
                func.sum(case((Order.status.in_(['pending', 'assigned']), 1), else_=0)).label('pending'),
                func.sum(case((Order.status == 'in_transit', 1), else_=0)).label('in_transit'),
                func.sum(case((Order.status == 'delivered', Order.actual_cost), else_=0)).label('revenue')
            ).first()
            
            total_orders = order_stats.total or 0
            completed_orders = order_stats.completed or 0
            pending_orders = order_stats.pending or 0
            in_transit_orders = order_stats.in_transit or 0
            total_revenue = float(order_stats.revenue or 0)
            
            # 成本计算（可配置，默认 70%）
            cost_ratio = 0.7  # 可从配置读取
            total_cost = total_revenue * cost_ratio
            
            profit_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
            
            # 车辆统计 - 单次查询
            vehicle_stats = db.session.query(
                func.count(Vehicle.id).label('total'),
                func.sum(case((Vehicle.status.in_(['available', 'busy']), 1), else_=0)).label('active')
            ).first()
            
            total_vehicles = vehicle_stats.total or 0
            active_vehicles = vehicle_stats.active or 0
            vehicle_utilization = (active_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
            
            # 时间段订单统计 - 单次查询
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            time_stats = db.session.query(
                func.sum(case((func.date(Order.created_at) == today, 1), else_=0)).label('today'),
                func.sum(case((func.date(Order.created_at) >= week_start, 1), else_=0)).label('week'),
                func.sum(case((func.date(Order.created_at) >= month_start, 1), else_=0)).label('month')
            ).first()
            
            today_orders = time_stats.today or 0
            week_orders = time_stats.week or 0
            month_orders = time_stats.month or 0
            
            return {
                'success': True,
                'metrics': {
                    'total_orders': total_orders,
                    'completed_orders': completed_orders,
                    'pending_orders': pending_orders,
                    'in_transit_orders': in_transit_orders,
                    'total_revenue': round(total_revenue, 2),
                    'total_cost': round(total_cost, 2),
                    'profit_margin': round(profit_margin, 1),
                    'vehicle_utilization': round(vehicle_utilization, 1),
                    'today_orders': today_orders,
                    'week_orders': week_orders,
                    'month_orders': month_orders,
                    'avg_cost_per_order': round(total_cost / completed_orders, 2) if completed_orders > 0 else 0
                }
            }
        
        except Exception as e:
            logger.error(f"获取仪表盘指标失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_trend_analysis(
        self, 
        start_date: str = None, 
        end_date: str = None,
        granularity: str = 'daily'
    ) -> Dict:
        """
        获取趋势分析数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            granularity: 粒度 (daily, weekly, monthly)
        """
        try:
            # 默认最近30天
            if not end_date:
                end_date = datetime.now().date()
            else:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if not start_date:
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            # 查询订单数据
            orders = Order.query.filter(
                db.func.date(Order.created_at) >= start_date,
                db.func.date(Order.created_at) <= end_date
            ).all()
            
            # 按日期分组
            daily_data = defaultdict(lambda: {
                'orders': 0,
                'revenue': 0,
                'cost': 0,
                'completed': 0
            })
            
            for order in orders:
                date_str = order.created_at.strftime('%Y-%m-%d')
                daily_data[date_str]['orders'] += 1
                
                cost = order.actual_cost or order.estimated_cost or 0
                daily_data[date_str]['cost'] += cost * 0.7
                daily_data[date_str]['revenue'] += cost
                
                if order.status == 'delivered':
                    daily_data[date_str]['completed'] += 1
            
            # 生成趋势数据
            trend = []
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                data = daily_data.get(date_str, {
                    'orders': 0,
                    'revenue': 0,
                    'cost': 0,
                    'completed': 0
                })
                
                trend.append({
                    'date': date_str,
                    'orders': data['orders'],
                    'completed': data['completed'],
                    'revenue': round(data['revenue'], 2),
                    'cost': round(data['cost'], 2),
                    'profit': round(data['revenue'] - data['cost'], 2)
                })
                
                current_date += timedelta(days=1)
            
            return {
                'success': True,
                'trend': trend,
                'summary': {
                    'total_orders': sum(d['orders'] for d in trend),
                    'total_revenue': round(sum(d['revenue'] for d in trend), 2),
                    'total_cost': round(sum(d['cost'] for d in trend), 2),
                    'total_profit': round(sum(d['profit'] for d in trend), 2),
                    'avg_daily_orders': round(sum(d['orders'] for d in trend) / len(trend), 1) if trend else 0
                }
            }
        
        except Exception as e:
            logger.error(f"获取趋势分析失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_cost_analysis(self, period: str = 'month') -> Dict:
        """
        成本分析
        
        Args:
            period: 分析周期 (week, month, quarter, year)
        """
        try:
            # 计算时间范围
            today = datetime.now().date()
            
            if period == 'week':
                start_date = today - timedelta(days=7)
            elif period == 'month':
                start_date = today - timedelta(days=30)
            elif period == 'quarter':
                start_date = today - timedelta(days=90)
            else:  # year
                start_date = today - timedelta(days=365)
            
            # 查询订单
            orders = Order.query.filter(
                db.func.date(Order.created_at) >= start_date,
                db.func.date(Order.created_at) <= today
            ).all()
            
            # 成本分类
            cost_by_type = defaultdict(float)
            cost_by_route = defaultdict(float)
            cost_by_vehicle = defaultdict(float)
            
            total_cost = 0
            total_distance = 0
            
            for order in orders:
                cost = order.actual_cost or order.estimated_cost or 0
                total_cost += cost
                
                # 按货物类型分类
                cargo_type = order.cargo_type or '其他'
                cost_by_type[cargo_type] += cost
                
                # 按路线分类
                if order.pickup_node and order.delivery_node:
                    route_name = f"{order.pickup_node.name} → {order.delivery_node.name}"
                    cost_by_route[route_name] += cost
                
                # 按车辆分类
                if order.vehicle:
                    cost_by_vehicle[order.vehicle.plate_number] += cost
                
                # 累计距离
                if order.distance:
                    total_distance += order.distance
            
            # 计算燃油成本（估算）
            fuel_cost = total_distance * 0.8 * 7.5  # 0.8元/公里 * 油耗系数
            toll_cost = total_distance * 0.3  # 过路费估算
            labor_cost = total_cost * 0.2  # 人工成本估算
            
            return {
                'success': True,
                'cost_analysis': {
                    'total_cost': round(total_cost, 2),
                    'avg_cost_per_order': round(total_cost / len(orders), 2) if orders else 0,
                    'cost_breakdown': {
                        'fuel': round(fuel_cost, 2),
                        'toll': round(toll_cost, 2),
                        'labor': round(labor_cost, 2),
                        'other': round(total_cost - fuel_cost - toll_cost - labor_cost, 2)
                    },
                    'by_cargo_type': [
                        {'type': k, 'cost': round(v, 2)} 
                        for k, v in sorted(cost_by_type.items(), key=lambda x: -x[1])
                    ][:10],
                    'by_route': [
                        {'route': k, 'cost': round(v, 2)} 
                        for k, v in sorted(cost_by_route.items(), key=lambda x: -x[1])
                    ][:10],
                    'by_vehicle': [
                        {'vehicle': k, 'cost': round(v, 2)} 
                        for k, v in sorted(cost_by_vehicle.items(), key=lambda x: -x[1])
                    ][:10]
                }
            }
        
        except Exception as e:
            logger.error(f"成本分析失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_route_performance(self) -> Dict:
        """获取路线性能分析"""
        try:
            routes = Route.query.filter_by(status='active').all()
            orders = Order.query.filter(
                Order.status == 'delivered',
                Order.actual_cost.isnot(None)
            ).all()
            
            route_stats = []
            
            for route in routes:
                # 统计该路线的订单
                route_orders = [
                    o for o in orders 
                    if o.pickup_node_id == route.start_node_id 
                    and o.delivery_node_id == route.end_node_id
                ]
                
                if route_orders:
                    total_revenue = sum(o.actual_cost or 0 for o in route_orders)
                    avg_time = route.duration or 0
                    
                    route_stats.append({
                        'id': route.id,
                        'name': route.name,
                        'distance': route.distance,
                        'duration': route.duration,
                        'order_count': len(route_orders),
                        'total_revenue': round(total_revenue, 2),
                        'avg_revenue': round(total_revenue / len(route_orders), 2),
                        'efficiency': round(len(route_orders) / max(route.distance / 100, 1), 2)
                    })
            
            # 按订单量排序
            route_stats.sort(key=lambda x: -x['order_count'])
            
            return {
                'success': True,
                'routes': route_stats,
                'summary': {
                    'total_routes': len(route_stats),
                    'total_orders': sum(r['order_count'] for r in route_stats),
                    'total_revenue': round(sum(r['total_revenue'] for r in route_stats), 2)
                }
            }
        
        except Exception as e:
            logger.error(f"路线性能分析失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_vehicle_performance(self) -> Dict:
        """获取车辆性能分析"""
        try:
            vehicles = Vehicle.query.all()
            
            vehicle_stats = []
            
            for vehicle in vehicles:
                # 统计该车辆的订单
                orders = Order.query.filter_by(vehicle_id=vehicle.id).all()
                completed = [o for o in orders if o.status == 'delivered']
                
                total_revenue = sum(o.actual_cost or o.estimated_cost or 0 for o in completed)
                total_distance = sum(o.distance or 0 for o in completed)
                
                # 计算利用率
                utilization = len(orders) / 10 * 100 if vehicle.status == 'available' else 80
                
                vehicle_stats.append({
                    'id': vehicle.id,
                    'plate_number': vehicle.plate_number,
                    'type': vehicle.vehicle_type,
                    'status': vehicle.status,
                    'order_count': len(orders),
                    'completed_count': len(completed),
                    'total_revenue': round(total_revenue, 2),
                    'total_distance': round(total_distance, 2),
                    'utilization': round(min(utilization, 100), 1),
                    'avg_revenue_per_order': round(total_revenue / len(completed), 2) if completed else 0
                })
            
            # 按收入排序
            vehicle_stats.sort(key=lambda x: -x['total_revenue'])
            
            return {
                'success': True,
                'vehicles': vehicle_stats,
                'summary': {
                    'total_vehicles': len(vehicles),
                    'active_vehicles': len([v for v in vehicles if v.status in ['available', 'busy']]),
                    'total_orders': sum(v['order_count'] for v in vehicle_stats),
                    'total_revenue': round(sum(v['total_revenue'] for v in vehicle_stats), 2),
                    'avg_utilization': round(sum(v['utilization'] for v in vehicle_stats) / len(vehicle_stats), 1) if vehicle_stats else 0
                }
            }
        
        except Exception as e:
            logger.error(f"车辆性能分析失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_report(
        self, 
        report_type: str = 'daily',
        start_date: str = None,
        end_date: str = None
    ) -> Dict:
        """
        生成运营报表
        
        Args:
            report_type: 报表类型 (daily, weekly, monthly)
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            # 获取基础数据
            metrics = self.get_dashboard_metrics()
            trend = self.get_trend_analysis(start_date, end_date)
            cost = self.get_cost_analysis('month')
            routes = self.get_route_performance()
            vehicles = self.get_vehicle_performance()
            
            # 生成报表
            report = {
                'success': True,
                'report_info': {
                    'type': report_type,
                    'generated_at': datetime.now().isoformat(),
                    'period': {
                        'start': start_date or trend.get('trend', [{}])[0].get('date', ''),
                        'end': end_date or datetime.now().strftime('%Y-%m-%d')
                    }
                },
                'summary': metrics.get('metrics', {}),
                'trend_analysis': trend.get('summary', {}),
                'cost_analysis': cost.get('cost_analysis', {}),
                'top_routes': routes.get('routes', [])[:5],
                'top_vehicles': vehicles.get('vehicles', [])[:5],
                'recommendations': self._generate_recommendations(metrics, cost, vehicles)
            }
            
            return report
        
        except Exception as e:
            logger.error(f"生成报表失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_recommendations(
        self, 
        metrics: Dict, 
        cost: Dict, 
        vehicles: Dict
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        try:
            # 检查待处理订单
            pending = metrics.get('metrics', {}).get('pending_orders', 0)
            if pending > 10:
                recommendations.append(f"📢 当前有 {pending} 个待处理订单，建议增加调度频次")
            
            # 检查车辆利用率
            utilization = vehicles.get('summary', {}).get('avg_utilization', 0)
            if utilization < 50:
                recommendations.append(f"🚛 车辆平均利用率仅 {utilization}%，建议优化调度策略")
            elif utilization > 90:
                recommendations.append(f"🚛 车辆利用率达 {utilization}%，建议增加车辆")
            
            # 检查成本
            cost_data = cost.get('cost_analysis', {})
            avg_cost = cost_data.get('avg_cost_per_order', 0)
            if avg_cost > 500:
                recommendations.append(f"💰 单均成本 {avg_cost}元，建议优化路线降低成本")
            
            # 检查热门路线
            top_route = cost_data.get('by_route', [{}])[0]
            if top_route.get('cost', 0) > 5000:
                recommendations.append(f"📍 热门路线「{top_route.get('route', '')}」成本较高，建议优化")
            
            if not recommendations:
                recommendations.append("✅ 运营状况良好，继续保持！")
        
        except Exception as e:
            recommendations.append("📊 数据分析中，请稍后查看建议")
        
        return recommendations
    
    def predict_demand(self, days: int = 7) -> Dict:
        """
        预测未来需求
        
        Args:
            days: 预测天数
        """
        try:
            # 获取历史数据
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            orders = Order.query.filter(
                db.func.date(Order.created_at) >= start_date,
                db.func.date(Order.created_at) <= end_date
            ).all()
            
            # 按日期分组
            daily_orders = defaultdict(int)
            for order in orders:
                date_str = order.created_at.strftime('%Y-%m-%d')
                daily_orders[date_str] += 1
            
            # 计算平均值和趋势
            values = list(daily_orders.values())
            if not values:
                values = [0]
            
            avg_orders = sum(values) / len(values)
            
            # 简单线性趋势
            if len(values) >= 7:
                recent = sum(values[-7:]) / 7
                earlier = sum(values[:7]) / 7 if len(values) >= 14 else recent
                trend = (recent - earlier) / max(earlier, 1)
            else:
                trend = 0
            
            # 生成预测
            predictions = []
            for i in range(days):
                future_date = end_date + timedelta(days=i+1)
                predicted = avg_orders * (1 + trend * (i+1) / 7)
                
                # 周末调整
                if future_date.weekday() >= 5:
                    predicted *= 0.8
                
                predictions.append({
                    'date': future_date.strftime('%Y-%m-%d'),
                    'predicted_orders': round(max(predicted, 0)),
                    'confidence': max(0.6, 0.9 - i * 0.05)  # 置信度随天数递减
                })
            
            return {
                'success': True,
                'predictions': predictions,
                'base_metrics': {
                    'avg_daily_orders': round(avg_orders, 1),
                    'trend': '上升' if trend > 0.05 else ('下降' if trend < -0.05 else '平稳'),
                    'trend_value': round(trend * 100, 1)
                }
            }
        
        except Exception as e:
            logger.error(f"需求预测失败: {e}")
            return {'success': False, 'error': str(e)}


# 单例实例
_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """获取数据分析服务实例"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service