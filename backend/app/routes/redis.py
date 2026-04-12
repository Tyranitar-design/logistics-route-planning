"""
Redis 缓存 API
- 热门路线排行
- 实时统计
- 缓存状态
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.redis_service import (
    get_popular_routes,
    get_order_count,
    get_cached_dashboard_stats,
    cache_dashboard_stats,
    get_redis_info,
    is_redis_connected,
    get_search_history,
    add_search_history
)

redis_bp = Blueprint('redis', __name__)


@redis_bp.route('/status', methods=['GET'])
@jwt_required()
def redis_status():
    """获取 Redis 连接状态"""
    return jsonify({
        'success': True,
        'data': get_redis_info()
    })


@redis_bp.route('/popular-routes', methods=['GET'])
@jwt_required()
def popular_routes():
    """
    获取热门路线排行
    
    Query Params:
        limit: 返回数量，默认10
    """
    limit = request.args.get('limit', 10, type=int)
    routes = get_popular_routes(limit)
    
    return jsonify({
        'success': True,
        'data': routes
    })


@redis_bp.route('/order-count', methods=['GET'])
@jwt_required()
def order_count():
    """
    获取订单计数
    
    Query Params:
        region: 区域名称，默认 total
        date: 日期，默认今日，传 "total" 获取总计
    """
    region = request.args.get('region', 'total')
    date = request.args.get('date')
    
    count = get_order_count(region, date)
    
    return jsonify({
        'success': True,
        'data': {
            'region': region,
            'date': date,
            'count': count
        }
    })


@redis_bp.route('/dashboard-cache', methods=['GET'])
def get_dashboard_cache():
    """获取缓存的仪表盘数据"""
    stats = get_cached_dashboard_stats()
    
    if stats:
        return jsonify({
            'success': True,
            'cached': True,
            'data': stats
        })
    else:
        return jsonify({
            'success': True,
            'cached': False,
            'data': None
        })


@redis_bp.route('/search-history', methods=['GET'])
def search_history():
    """
    获取搜索历史
    
    Query Params:
        user_id: 用户ID
        limit: 返回数量，默认10
    """
    user_id = request.args.get('user_id', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    history = get_search_history(user_id, limit)
    
    return jsonify({
        'success': True,
        'data': history
    })


@redis_bp.route('/search-history', methods=['POST'])
def add_search():
    """添加搜索历史"""
    data = request.get_json()
    user_id = data.get('user_id', 1)
    query = data.get('query')
    
    if not query:
        return jsonify({
            'success': False,
            'error': '缺少搜索词'
        }), 400
    
    add_search_history(user_id, query)
    
    return jsonify({
        'success': True,
        'message': '搜索历史已保存'
    })
