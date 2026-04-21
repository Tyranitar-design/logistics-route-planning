"""
轻量级大数据 API 路由
为前端提供大数据模拟数据展示
"""

from flask import Blueprint, jsonify, request
from app.services.lightweight_bigdata import (
    get_bigdata_overview,
    get_stream_stats,
    produce_test_message,
    BigDataSimulator,
    LightweightBatchProcessor
)

bigdata_bp = Blueprint('bigdata', __name__, url_prefix='/api/bigdata')


@bigdata_bp.route('/overview', methods=['GET'])
def get_overview():
    """获取大数据概览"""
    try:
        data = get_bigdata_overview()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/kafka', methods=['GET'])
def get_kafka_metrics():
    """获取 Kafka 指标"""
    try:
        data = BigDataSimulator.simulate_kafka_metrics()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/spark', methods=['GET'])
def get_spark_jobs():
    """获取 Spark 作业状态"""
    try:
        data = BigDataSimulator.simulate_spark_jobs()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/flink', methods=['GET'])
def get_flink_jobs():
    """获取 Flink 作业状态"""
    try:
        data = BigDataSimulator.simulate_flink_jobs()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/delivery-analysis', methods=['GET'])
def get_delivery_analysis():
    """获取配送分析"""
    try:
        days = request.args.get('days', 30, type=int)
        data = LightweightBatchProcessor.analyze_delivery_history(days)
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/demand-prediction', methods=['GET'])
def get_demand_prediction():
    """获取需求预测"""
    try:
        days = request.args.get('days', 7, type=int)
        data = LightweightBatchProcessor.predict_demand(days)
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/heatmap', methods=['GET'])
def get_heatmap():
    """获取热力图数据"""
    try:
        data = LightweightBatchProcessor.generate_heatmap_data()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/anomalies', methods=['GET'])
def get_anomalies():
    """获取异常检测"""
    try:
        data = LightweightBatchProcessor.detect_anomalies()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/stream/test', methods=['POST'])
def test_stream():
    """测试消息流"""
    try:
        data = produce_test_message()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/stream/stats', methods=['GET'])
def get_stream_statistics():
    """获取流统计"""
    try:
        data = get_stream_stats()
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@bigdata_bp.route('/status', methods=['GET'])
def get_status():
    """获取大数据服务状态"""
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'service': 'Lightweight BigData Service',
            'status': 'running',
            '替代技术': 'Redis Stream + Async + Simulation',
            'kafka_status': 'simulated',
            'spark_status': 'simulated',
            'flink_status': 'simulated',
            'redis_connection': 'ok',
            'uptime': '运行中'
        }
    })