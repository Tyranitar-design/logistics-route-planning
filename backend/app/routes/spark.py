"""
Spark 分析结果 API
- 需求预测
- 供应链分析
"""

from flask import Blueprint, jsonify
import json
import os

spark_bp = Blueprint('spark', __name__)

DATA_DIR = '/opt/data'  # Spark 输出目录


@spark_bp.route('/demand-forecast', methods=['GET'])
def get_demand_forecast():
    """
    获取需求预测结果
    
    Returns:
        {
            "success": true,
            "data": [
                {"date": "2026-04-06", "region": "北京", "demand": 156},
                ...
            ]
        }
    """
    try:
        # 读取 Spark 输出的预测结果
        forecast_file = os.path.join(DATA_DIR, 'demand_forecast.json')
        
        if os.path.exists(forecast_file):
            with open(forecast_file, 'r', encoding='utf-8') as f:
                predictions = json.load(f)
        else:
            # 如果没有 Spark 结果，返回模拟数据
            predictions = _generate_mock_forecast()
        
        # 按日期分组
        result = {}
        for item in predictions:
            date = item.get('date')
            if date not in result:
                result[date] = []
            result[date].append({
                'region': item.get('region'),
                'demand': int(item.get('prediction', 0))
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': _generate_mock_forecast()
        })


@spark_bp.route('/supply-chain', methods=['GET'])
def get_supply_chain_analysis():
    """
    获取供应链分析结果
    
    Returns:
        {
            "success": true,
            "data": {
                "bottlenecks": [...],
                "suggestions": [...]
            }
        }
    """
    try:
        analysis_file = os.path.join(DATA_DIR, 'supply_chain_analysis.json')
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
        else:
            analysis = _generate_mock_analysis()
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': _generate_mock_analysis()
        })


@spark_bp.route('/vehicle-suggestions', methods=['GET'])
def get_vehicle_suggestions():
    """
    获取车辆调配建议
    """
    try:
        forecast_data = _generate_mock_forecast()
        
        # 按区域汇总
        region_demand = {}
        for item in forecast_data:
            region = item.get('region')
            demand = item.get('prediction', 0)
            if region not in region_demand:
                region_demand[region] = []
            region_demand[region].append(demand)
        
        # 计算建议
        suggestions = []
        for region, demands in region_demand.items():
            avg_demand = sum(demands) / len(demands)
            vehicles = max(1, int(avg_demand // 20))
            
            if avg_demand > 150:
                status = 'high'
                note = '需求高峰，建议增加临时车辆'
            elif avg_demand > 100:
                status = 'medium'
                note = '需求较高，保持正常运营'
            else:
                status = 'normal'
                note = '需求平稳'
            
            suggestions.append({
                'region': region,
                'avg_demand': round(avg_demand),
                'vehicles_suggested': vehicles,
                'status': status,
                'note': note
            })
        
        # 按需求排序
        suggestions.sort(key=lambda x: x['avg_demand'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': suggestions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def _generate_mock_forecast():
    """生成模拟预测数据"""
    from datetime import datetime, timedelta
    
    regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']
    base_demand = {'北京': 150, '上海': 180, '广州': 120, '深圳': 100, 
                   '杭州': 90, '成都': 70, '武汉': 60, '西安': 50}
    
    predictions = []
    base_date = datetime.now()
    
    for i in range(1, 8):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        for region in regions:
            import random
            demand = base_demand[region] + random.randint(-20, 30)
            
            # 周末增加
            weekday = (base_date + timedelta(days=i)).weekday()
            if weekday >= 5:
                demand = int(demand * 1.3)
            
            predictions.append({
                'date': date,
                'region': region,
                'prediction': demand
            })
    
    return predictions


def _generate_mock_analysis():
    """生成模拟分析数据"""
    return {
        'bottlenecks': [
            {'id': 'N001', 'name': '北京仓库', 'score': 0.85, 'utilization': 0.92},
            {'id': 'N002', 'name': '上海仓库', 'score': 0.78, 'utilization': 0.88}
        ],
        'suggestions': [
            '北京仓库容量使用率过高，建议扩容',
            '增加北京-上海之间的备用路线'
        ],
        'node_count': 12,
        'edge_count': 12
    }
