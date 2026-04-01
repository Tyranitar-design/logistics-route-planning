"""
机器学习预测 API 路由
"""

from flask import Blueprint, request, jsonify
from app.services.ml_prediction_service import demand_predictor, smart_optimizer

ml_bp = Blueprint('ml', __name__, url_prefix='/api/ml')


@ml_bp.route('/train', methods=['POST'])
def train_model():
    """
    训练预测模型
    
    Request Body:
        days: 训练数据天数（默认90天）
    
    Returns:
        训练结果统计
    """
    data = request.get_json() or {}
    days = data.get('days', 90)
    
    try:
        stats = demand_predictor.train(days)
        return jsonify({
            'success': True,
            'message': '模型训练成功',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'训练失败: {str(e)}'
        }), 500


@ml_bp.route('/predict', methods=['GET'])
def predict_demand():
    """
    预测需求
    
    Query Parameters:
        days: 预测天数（默认7天）
        region: 指定区域（可选）
    
    Returns:
        预测结果列表
    """
    days = request.args.get('days', 7, type=int)
    region = request.args.get('region', None)
    
    try:
        predictions = demand_predictor.predict(days, region)
        return jsonify({
            'success': True,
            'predictions': predictions,
            'total': len(predictions)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@ml_bp.route('/predict/aggregated', methods=['GET'])
def predict_aggregated():
    """
    获取聚合预测结果
    
    Query Parameters:
        days: 预测天数（默认7天）
    
    Returns:
        按日期汇总的预测结果
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        result = demand_predictor.predict_aggregated(days)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@ml_bp.route('/merge-suggestions', methods=['GET'])
def get_merge_suggestions():
    """
    获取合并配送建议
    
    Query Parameters:
        threshold: 最小订单数阈值（默认10）
    
    Returns:
        合并配送建议列表
    """
    threshold = request.args.get('threshold', 10, type=int)
    
    try:
        suggestions = demand_predictor.get_merge_suggestions(threshold)
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'total': len(suggestions)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取建议失败: {str(e)}'
        }), 500


@ml_bp.route('/vehicle-allocation', methods=['GET'])
def get_vehicle_allocation():
    """
    获取车辆调配建议
    
    Query Parameters:
        days: 预测天数（默认7天）
    
    Returns:
        车辆调配建议
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        allocation = demand_predictor.get_vehicle_allocation(days)
        return jsonify({
            'success': True,
            'data': allocation
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取建议失败: {str(e)}'
        }), 500


@ml_bp.route('/optimize-dispatch', methods=['POST'])
def optimize_dispatch():
    """
    智能调度优化
    
    Request Body:
        orders: 待调度订单列表
        vehicles: 可用车辆列表
    
    Returns:
        优化后的调度方案
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供订单和车辆数据'
        }), 400
    
    orders = data.get('orders', [])
    vehicles = data.get('vehicles', [])
    
    try:
        result = smart_optimizer.optimize(orders, vehicles)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'优化失败: {str(e)}'
        }), 500


@ml_bp.route('/model/status', methods=['GET'])
def get_model_status():
    """
    获取模型状态
    """
    return jsonify({
        'success': True,
        'is_trained': demand_predictor.is_trained,
        'data_records': len(demand_predictor.historical_data)
    })


def register_ml_routes(app):
    """注册 ML 路由"""
    app.register_blueprint(ml_bp)