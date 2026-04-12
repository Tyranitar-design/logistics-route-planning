"""
订单路由
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from datetime import datetime

from app.models import db, Order, User, Node
from app.schemas import OrderCreate, OrderUpdate, OrderResponse
from app.services.order_route_service import get_order_route_service
from app.services.kafka_service import send_order_event
from app.utils.rate_limiter import rate_limit, RateLimits

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('', methods=['GET'])
@orders_bp.route('/', methods=['GET'])
@jwt_required()
@rate_limit(**RateLimits.API)
def get_orders():
    """获取订单列表"""
    current_user_id = int(get_jwt_identity())
    
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status')
    search = request.args.get('search')
    
    # 构建查询
    query = Order.query
    
    if status:
        query = query.filter(Order.status == status)
    
    if search:
        query = query.filter(
            (Order.order_number.ilike(f'%{search}%')) |
            (Order.customer_name.ilike(f'%{search}%'))
        )
    
    # 分页
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    orders = [order.to_dict() for order in pagination.items]
    
    return jsonify({
        'orders': orders,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@orders_bp.route('', methods=['POST'])
@orders_bp.route('/', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=30, window_seconds=60, key_func=lambda: f"create_order:{get_jwt_identity()}")
def create_order():
    """创建订单 - 使用 Schema 验证"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # 生成订单号
    order_number = f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}'
    
    # 确保 order_number 在 data 中
    data['order_number'] = order_number
    
    # 使用 Schema 验证
    try:
        order_data = OrderCreate(**data)
    except ValidationError as e:
        return jsonify({'error': '参数验证失败', 'details': e.errors()}), 400
    
    order = Order(
        order_number=order_number,
        customer_name=order_data.customer_name,
        customer_phone=order_data.customer_phone,
        pickup_node_id=order_data.pickup_node_id,
        delivery_node_id=order_data.delivery_node_id,
        origin_name=order_data.origin_name,
        destination_name=order_data.destination_name,
        cargo_name=order_data.cargo_name,
        cargo_type=order_data.cargo_type,
        weight=order_data.weight,
        volume=order_data.volume,
        priority=order_data.priority,
        notes=order_data.notes,
        status='pending',
        created_by=current_user_id
    )
    
    db.session.add(order)
    db.session.commit()
    
    # 同步到 Redis
    try:
        from app.services.redis_service import increment_order_count
        increment_order_count('total')
        print('[Redis] Order count updated')
    except Exception as e:
        print(f'[Redis] Sync failed: {e}')
    
    # 发送到 Kafka
    try:
        send_order_event(order.to_dict(), 'created')
    except Exception as e:
        print(f'Kafka send failed: {e}')
    
    return jsonify({
        'success': True,
        'message': '订单创建成功',
        'order': OrderResponse.model_validate(order).model_dump()
    }), 201

@orders_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """获取单个订单详情"""
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    
    return jsonify({'order': order.to_dict()})

@orders_bp.route('/<int:order_id>', methods=['PUT'])
@jwt_required()
@rate_limit(max_requests=20, window_seconds=60, key_func=lambda: f"update_order:{get_jwt_identity()}")
def update_order(order_id):
    """更新订单"""
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    
    data = request.get_json()
    
    # 更新字段
    updatable_fields = ['customer_name', 'customer_phone', 'pickup_node_id',
                        'delivery_node_id', 'cargo_name', 'cargo_type',
                        'weight', 'volume', 'status', 'priority', 'notes']
    
    for field in updatable_fields:
        if field in data:
            setattr(order, field, data[field])
    
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    # 发送状态更新到 Kafka
    try:
        send_order_event(order.to_dict(), 'updated')
    except Exception as e:
        print(f'Kafka send failed: {e}')
    
    return jsonify({
        'message': '订单更新成功',
        'order': order.to_dict()
    })

@orders_bp.route('/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    """删除订单"""
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': '订单不存在'}), 404
    
    db.session.delete(order)
    db.session.commit()
    
    return jsonify({'message': '订单删除成功'})

@orders_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_order_stats():
    """获取订单统计"""
    total = Order.query.count()
    pending = Order.query.filter(Order.status == 'pending').count()
    in_progress = Order.query.filter(Order.status == 'in_progress').count()
    completed = Order.query.filter(Order.status == 'completed').count()
    cancelled = Order.query.filter(Order.status == 'cancelled').count()
    
    return jsonify({
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled
    })


@orders_bp.route('/<int:order_id>/recommend-route', methods=['GET'])
@jwt_required()
def recommend_order_route(order_id):
    """
    为订单推荐路线
    
    Query params:
        prefer_source: 偏好数据源 (auto/local/amap，默认auto)
    """
    try:
        prefer_source = request.args.get('prefer_source', 'auto')
        
        service = get_order_route_service()
        result = service.recommend_for_order(order_id=order_id, prefer_source=prefer_source)
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'order_id': result.order_id,
                    'origin': result.origin,
                    'destination': result.destination,
                    'local_route': result.local_route,
                    'amap_route': result.amap_route,
                    'recommended_route': result.recommended_route,
                    'recommendation_reason': result.recommendation_reason
                }
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@orders_bp.route('/recommend-route', methods=['POST'])
@jwt_required()
def recommend_route_for_nodes():
    """
    根据起点终点推荐路线（创建订单前预览）
    
    Body:
        origin_id: 起点节点ID
        destination_id: 终点节点ID
        weight: 货物重量（可选）
        prefer_source: 偏好数据源 (auto/local/amap，默认auto)
    """
    try:
        data = request.get_json()
        
        origin_id = data.get('origin_id')
        destination_id = data.get('destination_id')
        weight = data.get('weight', 0)
        prefer_source = data.get('prefer_source', 'auto')
        
        if not origin_id or not destination_id:
            return jsonify({'success': False, 'error': '请提供起点和终点'}), 400
        
        service = get_order_route_service()
        result = service.recommend_for_order(
            origin_id=origin_id,
            destination_id=destination_id,
            weight=weight,
            prefer_source=prefer_source
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'origin': result.origin,
                    'destination': result.destination,
                    'local_route': result.local_route,
                    'amap_route': result.amap_route,
                    'recommended_route': result.recommended_route,
                    'recommendation_reason': result.recommendation_reason
                }
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@orders_bp.route('/<int:order_id>/apply-route', methods=['POST'])
@jwt_required()
def apply_route_to_order(order_id):
    """
    将推荐路线应用到订单
    
    Body:
        route_data: 路线数据
    """
    try:
        data = request.get_json()
        route_data = data.get('route_data', {})
        
        service = get_order_route_service()
        result = service.apply_route_to_order(order_id, route_data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@orders_bp.route('/<int:order_id>/available-vehicles', methods=['GET'])
@jwt_required()
def get_available_vehicles_for_order(order_id):
    """
    获取订单可用的车辆列表
    
    Query params:
        weight: 货物重量
        volume: 货物体积
    """
    try:
        order = Order.query.get_or_404(order_id)
        
        weight = request.args.get('weight', order.weight or 0, type=float)
        volume = request.args.get('volume', order.volume or 0, type=float)
        
        service = get_order_route_service()
        vehicles = service.get_available_vehicles_for_route(
            order.pickup_node_id,
            order.delivery_node_id,
            weight,
            volume
        )
        
        return jsonify({
            'success': True,
            'data': {
                'vehicles': vehicles,
                'total': len(vehicles)
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
