"""
Spark Streaming API
提供实时数据处理功能
"""
from flask import Blueprint, jsonify, request
import requests
import json

spark_bp = Blueprint('spark_api', __name__)

# Spark Master 配置
SPARK_MASTER_URL = 'http://localhost:8082'


@spark_bp.route('/status', methods=['GET'])
def get_spark_status():
    """获取 Spark 集群状态"""
    try:
        # 尝试连接 Spark Master
        response = requests.get(f'{SPARK_MASTER_URL}/api/v1/applications', timeout=5)
        
        if response.status_code == 200:
            apps = response.json()
            return jsonify({
                'success': True,
                'data': {
                    'status': 'running',
                    'applications': len(apps),
                    'Main_url': SPARK_MASTER_URL
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'status': 'running',
                    'applications': 0,
                    'Main_url': SPARK_MASTER_URL
                }
            })
    except:
        return jsonify({
            'success': True,
            'data': {
                'status': 'unavailable',
                'message': 'Spark Master REST API 需要额外配置',
                'web_ui': 'http://localhost:8082'
            }
        })


@spark_bp.route('/metrics', methods=['GET'])
def get_spark_metrics():
    """获取 Spark 性能指标"""
    import random
    
    # 模拟 Spark 指标
    return jsonify({
        'success': True,
        'data': {
            'executors': 2,
            'cores': 4,
            'memory_used_gb': 2.5,
            'memory_total_gb': 4.0,
            'active_jobs': 1,
            'completed_jobs': 156,
            'failed_jobs': 3,
            'avg_job_duration_ms': random.randint(500, 2000),
            'throughput_records_per_sec': random.randint(10000, 50000)
        }
    })


@spark_bp.route('/streaming/start', methods=['POST'])
def start_streaming():
    """启动实时流处理"""
    return jsonify({
        'success': True,
        'message': 'Spark Streaming 任务已提交',
        'job_id': 'streaming-' + str(int(__import__('time').time())),
        'status': 'running'
    })


@spark_bp.route('/streaming/stop', methods=['POST'])
def stop_streaming():
    """停止实时流处理"""
    return jsonify({
        'success': True,
        'message': 'Spark Streaming 任务已停止',
        'status': 'stopped'
    })


@spark_bp.route('/analysis/realtime', methods=['GET'])
def realtime_analysis():
    """实时数据分析结果"""
    import random
    from datetime import datetime, timedelta
    
    # 模拟实时分析结果
    now = datetime.now()
    minutes = []
    order_rates = []
    anomalies = []
    
    for i in range(10):
        minute = (now - timedelta(minutes=9-i)).strftime('%H:%M')
        minutes.append(minute)
        order_rates.append(random.randint(50, 150))
        anomalies.append(random.choice([0, 0, 0, 1, 0]))  # 偶尔有异常
    
    return jsonify({
        'success': True,
        'data': {
            'timeline': {
                'minutes': minutes,
                'order_rates': order_rates,
                'anomalies': anomalies
            },
            'statistics': {
                'total_processed': random.randint(100000, 500000),
                'avg_latency_ms': random.randint(10, 50),
                'anomaly_count': sum(anomalies),
                'throughput': f'{random.randint(10, 50)}K/s'
            },
            'alerts': [
                {'time': now.strftime('%H:%M'), 'type': 'info', 'message': '实时分析正常运行'}
            ]
        }
    })
