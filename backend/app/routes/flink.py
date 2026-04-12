"""
Flink 实时流处理 API
- 作业管理
- 实时统计
- 告警查询
"""

from flask import Blueprint, jsonify, request
import json
import time
import random
from datetime import datetime, timedelta

flink_bp = Blueprint('flink', __name__)


@flink_bp.route('/status', methods=['GET'])
def get_flink_status():
    """
    获取 Flink 集群状态 - 从真实 Flink API 获取
    """
    import requests
    
    try:
        # 从 Flink REST API 获取真实状态
        response = requests.get('http://localhost:8083/overview', timeout=5)
        data = response.json()
        
        return jsonify({
            'success': True,
            'data': {
                'running': data.get('taskmanagers', 0) > 0,
                'jobmanager': 'http://localhost:8083',
                'taskmanagers': data.get('taskmanagers', 0),
                'slots_total': data.get('slots-total', 0),
                'slots_available': data.get('slots-available', 0),
                'jobs_running': data.get('jobs-running', 0),
                'jobs_finished': data.get('jobs-finished', 0),
                'jobs_cancelled': data.get('jobs-cancelled', 0),
                'jobs_failed': data.get('jobs-failed', 0),
                'flink_version': data.get('flink-version', ''),
                'last_updated': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'running': False,
                'jobmanager': 'http://localhost:8083',
                'taskmanagers': 0,
                'slots_total': 0,
                'slots_available': 0,
                'jobs_running': 0,
                'jobs_finished': 0
            }
        }), 500


@flink_bp.route('/jobs', methods=['GET'])
def get_flink_jobs():
    """
    获取 Flink 作业列表 - 从真实 Flink API 获取
    """
    import requests
    
    try:
        # 获取作业列表
        response = requests.get('http://localhost:8083/jobs', timeout=5)
        jobs_data = response.json()
        
        jobs = []
        for job in jobs_data.get('jobs', []):
            # 获取作业详情
            try:
                detail_response = requests.get(f"http://localhost:8083/jobs/{job['id']}", timeout=5)
                detail = detail_response.json()
                
                # 计算运行时长
                start_time = detail.get('start-time', 0)
                duration = detail.get('duration', 0)
                
                jobs.append({
                    'job_id': job['id'][:12] + '...',
                    'name': detail.get('name', 'Unknown'),
                    'status': job.get('status', 'UNKNOWN'),
                    'start_time': datetime.fromtimestamp(start_time / 1000).isoformat() if start_time else '-',
                    'duration': int(duration / 1000) if duration else 0
                })
            except:
                jobs.append({
                    'job_id': job['id'][:12] + '...',
                    'name': 'Unknown',
                    'status': job.get('status', 'UNKNOWN'),
                    'start_time': '-',
                    'duration': 0
                })
        
        return jsonify({
            'success': True,
            'data': jobs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


@flink_bp.route('/realtime-stats', methods=['GET'])
def get_realtime_stats():
    """
    获取实时统计数据（来自 Flink 处理结果）

    Returns:
        {
            "success": true,
            "data": {
                "orders_last_5min": 12,
                "high_value_orders": 3,
                "active_vehicles": 16,
                "alerts_today": 5
            }
        }
    """
    try:
        # TODO: 从 Elasticsearch 或 Redis 读取 Flink 处理结果

        return jsonify({
            'success': True,
            'data': {
                'orders_last_5min': random.randint(8, 20),
                'high_value_orders': random.randint(1, 5),
                'active_vehicles': 16,
                'alerts_today': random.randint(3, 10),
                'total_processed': 1048,
                'throughput': random.uniform(100, 500),  # 条/秒
                'last_updated': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@flink_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    获取实时告警列表

    Query params:
        limit: 返回条数 (default: 20)
        severity: 告警级别 (all, high, medium, low)

    Returns:
        {
            "success": true,
            "data": [
                {
                    "alert_id": "alert-001",
                    "type": "OVERSPEED",
                    "vehicle_id": 5,
                    "message": "车辆超速: 135 km/h",
                    "severity": "high",
                    "timestamp": "2026-04-10T12:30:00"
                },
                ...
            ]
        }
    """
    try:
        limit = int(request.args.get('limit', 20))
        severity = request.args.get('severity', 'all')

        # TODO: 从 Elasticsearch 读取真实告警数据

        alerts = [
            {
                'alert_id': 'alert-001',
                'type': 'OVERSPEED',
                'vehicle_id': 5,
                'message': f'车辆超速: {random.randint(120, 150)} km/h',
                'severity': 'high',
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat()
            },
            {
                'alert_id': 'alert-002',
                'type': 'AMOUNT_SPIKE',
                'order_id': 'ORD-12345',
                'message': '订单金额异常飙升',
                'severity': 'medium',
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(1, 120))).isoformat()
            },
            {
                'alert_id': 'alert-003',
                'type': 'HIGH_VALUE',
                'order_id': 'ORD-12346',
                'message': '高价值订单: ¥15,000',
                'severity': 'low',
                'timestamp': (datetime.now() - timedelta(minutes=random.randint(1, 180))).isoformat()
            }
        ]

        if severity != 'all':
            alerts = [a for a in alerts if a.get('severity') == severity]

        return jsonify({
            'success': True,
            'data': alerts[:limit]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@flink_bp.route('/order-window', methods=['GET'])
def get_order_window_stats():
    """
    获取窗口订单统计（5分钟滚动窗口）

    Returns:
        {
            "success": true,
            "data": [
                {
                    "window": "19:00-19:05",
                    "status": "pending",
                    "count": 5,
                    "total_cost": 2500.00
                },
                ...
            ]
        }
    """
    try:
        # TODO: 从 Elasticsearch 读取窗口统计结果

        windows = []
        now = datetime.now()

        for i in range(6):  # 最近6个窗口（30分钟）
            window_start = now - timedelta(minutes=(i+1)*5)
            window_end = now - timedelta(minutes=i*5)
            window_label = f"{window_start.strftime('%H:%M')}-{window_end.strftime('%H:%M')}"

            for status in ['pending', 'in_transit', 'delivered']:
                windows.append({
                    'window': window_label,
                    'status': status,
                    'count': random.randint(1, 10),
                    'total_cost': round(random.uniform(500, 5000), 2),
                    'avg_cost': round(random.uniform(100, 500), 2)
                })

        return jsonify({
            'success': True,
            'data': windows
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@flink_bp.route('/top-routes', methods=['GET'])
def get_top_routes():
    """
    获取热门路线实时统计

    Returns:
        {
            "success": true,
            "data": [
                {
                    "route": "北京 -> 上海",
                    "pickup_node": 24,
                    "delivery_node": 26,
                    "order_count": 15,
                    "total_cost": 45000.00
                },
                ...
            ]
        }
    """
    try:
        # TODO: 从 Elasticsearch 读取热门路线统计

        routes = [
            {'route': '北京 -> 上海', 'pickup_node': 24, 'delivery_node': 26, 'order_count': 15, 'total_cost': 45000.00},
            {'route': '上海 -> 广州', 'pickup_node': 25, 'delivery_node': 27, 'order_count': 12, 'total_cost': 38000.00},
            {'route': '北京 -> 广州', 'pickup_node': 24, 'delivery_node': 27, 'order_count': 10, 'total_cost': 52000.00},
            {'route': '广州 -> 深圳', 'pickup_node': 27, 'delivery_node': 28, 'order_count': 8, 'total_cost': 12000.00},
            {'route': '上海 -> 杭州', 'pickup_node': 25, 'delivery_node': 29, 'order_count': 6, 'total_cost': 8000.00}
        ]

        return jsonify({
            'success': True,
            'data': routes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
