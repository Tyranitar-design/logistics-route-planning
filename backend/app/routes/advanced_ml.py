"""
高级预测 API 路由
- LSTM + Prophet 预测
- 异常检测
- 融合预测
"""

from flask import Blueprint, request, jsonify
from app.services.advanced_prediction_service import advanced_prediction_service

advanced_ml_bp = Blueprint('advanced_ml', __name__, url_prefix='/api/advanced-ml')


@advanced_ml_bp.route('/train', methods=['POST'])
def train_models():
    """
    训练所有预测模型
    
    Request Body:
        days: 训练数据天数（默认180天）
    
    Returns:
        训练结果统计
    """
    data = request.get_json() or {}
    days = data.get('days', 180)
    
    try:
        stats = advanced_prediction_service.train(days)
        return jsonify({
            'success': True,
            'message': '高级预测模型训练完成',
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'训练失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/predict/lstm', methods=['GET'])
def predict_lstm():
    """
    LSTM 预测
    
    Query Parameters:
        days: 预测天数（默认7天）
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        result = advanced_prediction_service.predict_lstm(days)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/predict/prophet', methods=['GET'])
def predict_prophet():
    """
    Prophet 预测
    
    Query Parameters:
        days: 预测天数（默认7天）
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        result = advanced_prediction_service.predict_prophet(days)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/predict/ensemble', methods=['GET'])
def predict_ensemble():
    """
    融合预测（LSTM + Prophet）
    
    Query Parameters:
        days: 预测天数（默认7天）
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        result = advanced_prediction_service.predict_ensemble(days)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/predict/with-anomaly', methods=['GET'])
def predict_with_anomaly():
    """
    预测 + 异常预警
    
    Query Parameters:
        days: 预测天数（默认7天）
    """
    days = request.args.get('days', 7, type=int)
    
    try:
        result = advanced_prediction_service.get_prediction_with_anomaly_alert(days)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/anomaly/detect', methods=['POST'])
def detect_anomalies():
    """
    异常检测
    
    Request Body:
        data: 数据列表（可选，不提供则使用历史数据）
    """
    data = request.get_json()
    recent_data = data.get('data', None) if data else None
    
    try:
        result = advanced_prediction_service.detect_anomalies(recent_data)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检测失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/predict/by-region', methods=['GET'])
def predict_by_region():
    """
    按区域预测
    
    Query Parameters:
        days: 预测天数（默认7天）
        region: 区域（可选）
    """
    days = request.args.get('days', 7, type=int)
    region = request.args.get('region', None)
    
    try:
        result = advanced_prediction_service.predict_by_region(days, region)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@advanced_ml_bp.route('/status', methods=['GET'])
def get_status():
    """
    获取模型状态
    """
    return jsonify({
        'success': True,
        'is_trained': advanced_prediction_service.is_trained,
        'data_records': len(advanced_prediction_service.historical_data),
        'available_models': {
            'lstm': True,
            'prophet': True,
            'anomaly_detector': True
        }
    })


def register_advanced_ml_routes(app):
    """注册高级 ML 路由"""
    app.register_blueprint(advanced_ml_bp)