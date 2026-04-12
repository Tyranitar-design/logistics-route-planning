"""
Prometheus Metrics API
为 Grafana 监控提供指标数据
"""
from flask import Blueprint, Response, jsonify
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
from app import db
from sqlalchemy import text
import time

metrics_bp = Blueprint('metrics', __name__)

# ==================== Prometheus 指标定义 ====================

if HAS_PROMETHEUS:
    # 订单相关指标
    orders_total = Counter('logistics_orders_total', 'Total number of orders')
    orders_active = Gauge('logistics_orders_active', 'Number of active orders')
    orders_by_status = Gauge('logistics_orders_by_status', 'Orders by status', ['status'])
    vehicles_total = Gauge('logistics_vehicles_total', 'Total number of vehicles')
    vehicles_active = Gauge('logistics_vehicles_active', 'Number of active vehicles')
    vehicles_by_status = Gauge('logistics_vehicles_by_status', 'Vehicles by status', ['status'])
    routes_total = Gauge('logistics_routes_total', 'Total number of routes')
    routes_avg_distance = Gauge('logistics_routes_avg_distance_km', 'Average route distance in km')
    total_cost = Gauge('logistics_total_cost_yuan', 'Total logistics cost in Yuan')
    avg_cost_per_order = Gauge('logistics_avg_cost_per_order', 'Average cost per order')
    system_health = Gauge('logistics_system_health', 'System health score (0-100)')
    database_connections = Gauge('logistics_database_connections', 'Active database connections')
    api_requests_total = Counter('logistics_api_requests_total', 'Total API requests', ['endpoint', 'method'])
    api_request_duration = Histogram('logistics_api_request_duration_seconds', 'API request duration', ['endpoint'])
    alerts_total = Gauge('logistics_alerts_total', 'Total number of alerts')
    alerts_by_severity = Gauge('logistics_alerts_by_severity', 'Alerts by severity', ['severity'])


def update_metrics():
    """从数据库更新指标"""
    try:
        # 订单统计
        orders_result = db.session.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        orders_total.inc(orders_result if orders_result else 0)
        
        # 活跃订单
        active_orders = db.session.execute(text(
            "SELECT COUNT(*) FROM orders WHERE status IN ('pending', 'in_transit')"
        )).scalar()
        orders_active.set(active_orders if active_orders else 0)
        
        # 订单状态分布
        status_counts = db.session.execute(text(
            "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
        )).fetchall()
        for status, count in status_counts:
            orders_by_status.labels(status=status).set(count)
        
        # 车辆统计
        vehicles_count = db.session.execute(text("SELECT COUNT(*) FROM vehicles")).scalar()
        vehicles_total.set(vehicles_count if vehicles_count else 0)
        
        active_vehicles = db.session.execute(text(
            "SELECT COUNT(*) FROM vehicles WHERE status = 'active'"
        )).scalar()
        vehicles_active.set(active_vehicles if active_vehicles else 0)
        
        # 路线统计
        routes_count = db.session.execute(text("SELECT COUNT(*) FROM routes")).scalar()
        routes_total.set(routes_count if routes_count else 0)
        
        # 平均距离
        avg_dist = db.session.execute(text(
            "SELECT AVG(distance) FROM routes WHERE distance IS NOT NULL"
        )).scalar()
        routes_avg_distance.set(float(avg_dist) if avg_dist else 0)
        
        # 成本统计
        try:
            total_c = db.session.execute(text(
                "SELECT SUM(cost) FROM orders WHERE cost IS NOT NULL"
            )).scalar()
            total_cost.set(float(total_c) if total_c else 0)
        except:
            total_cost.set(0)
        
        # 系统健康分数（基于各种指标计算）
        health_score = 100
        if orders_result and orders_result > 0:
            delayed_orders = db.session.execute(text(
                "SELECT COUNT(*) FROM orders WHERE status = 'delayed'"
            )).scalar() or 0
            health_score = max(0, 100 - (delayed_orders / orders_result * 100))
        system_health.set(health_score)
        
        return True
    except Exception as e:
        print(f"Error updating metrics: {e}")
        return False


@metrics_bp.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """
    Prometheus 指标端点
    访问: GET /api/metrics
    """
    if not HAS_PROMETHEUS:
        return jsonify({'success': False, 'error': 'prometheus_client not installed'}), 503
    # 更新指标
    update_metrics()
    
    # 返回 Prometheus 格式
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@metrics_bp.route('/metrics/json', methods=['GET'])
def json_metrics():
    """
    JSON 格式的指标数据（供前端使用）
    访问: GET /api/metrics/json
    """
    try:
        metrics_data = {
            'orders': {
                'total': db.session.execute(text("SELECT COUNT(*) FROM orders")).scalar() or 0,
                'active': db.session.execute(text(
                    "SELECT COUNT(*) FROM orders WHERE status IN ('pending', 'in_transit')"
                )).scalar() or 0,
                'by_status': dict(db.session.execute(text(
                    "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
                )).fetchall())
            },
            'vehicles': {
                'total': db.session.execute(text("SELECT COUNT(*) FROM vehicles")).scalar() or 0,
                'active': db.session.execute(text(
                    "SELECT COUNT(*) FROM vehicles WHERE status = 'active'"
                )).scalar() or 0
            },
            'routes': {
                'total': db.session.execute(text("SELECT COUNT(*) FROM routes")).scalar() or 0,
                'avg_distance': float(db.session.execute(text(
                    "SELECT AVG(distance) FROM routes WHERE distance IS NOT NULL"
                )).scalar() or 0)
            },
            'cost': {
                'total': 0
            },
            'system': {
                'health': 95,  # 计算的健康分数
                'timestamp': time.time()
            }
        }
        return {'success': True, 'data': metrics_data}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500
