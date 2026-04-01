"""
多式联运 API 路由
"""

from flask import Blueprint, request, jsonify
from app.services.multimodal_transport_service import multimodal_service, TransportMode

multimodal_bp = Blueprint('multimodal', __name__, url_prefix='/api/multimodal')


@multimodal_bp.route('/modes', methods=['GET'])
def get_modes():
    """
    获取所有运输方式
    """
    return jsonify({
        'success': True,
        'data': TransportMode.list_modes()
    })


@multimodal_bp.route('/estimate', methods=['GET'])
def estimate_transport():
    """
    估算所有运输方式
    
    Query Parameters:
        distance: 距离（公里）
        weight: 货物重量（吨）
    """
    distance = request.args.get('distance', 100, type=float)
    weight = request.args.get('weight', 1, type=float)
    
    try:
        result = multimodal_service.estimate_all_modes(distance, weight)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'估算失败: {str(e)}'
        }), 500


@multimodal_bp.route('/optimize-route', methods=['POST'])
def optimize_route():
    """
    优化多式联运路线
    
    Request Body:
        origin: 起点
        destination: 终点
        distance: 总距离
        weight: 货物重量
        time_limit: 时间限制（可选）
        cost_limit: 成本限制（可选）
        priority: 优先级 (fast, cheap, balanced, green)
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供路线参数'
        }), 400
    
    try:
        result = multimodal_service.plan_shipment(
            origin=data.get('origin'),
            destination=data.get('destination'),
            distance=data.get('distance'),
            weight=data.get('weight'),
            time_limit=data.get('time_limit'),
            priority=data.get('priority', 'balanced')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'优化失败: {str(e)}'
        }), 500


@multimodal_bp.route('/last-mile/optimize', methods=['POST'])
def optimize_last_mile():
    """
    优化最后一公里配送
    
    Request Body:
        depot: {'lat': x, 'lon': y}
        customers: [{'id': 1, 'lat': x, 'lon': y, 'demand': d}]
        vehicle_type: 车辆类型
    """
    data = request.get_json()
    
    if not data or 'depot' not in data or 'customers' not in data:
        return jsonify({
            'success': False,
            'message': '请提供仓库和客户信息'
        }), 400
    
    try:
        result = multimodal_service.last_mile.optimize_last_mile(
            depot=data.get('depot'),
            customers=data.get('customers'),
            vehicle_type=data.get('vehicle_type', 'van')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'优化失败: {str(e)}'
        }), 500


@multimodal_bp.route('/last-mile/compare-vehicles', methods=['POST'])
def compare_vehicles():
    """
    比较不同车辆类型
    
    Request Body:
        depot: {'lat': x, 'lon': y}
        customers: 客户列表
    """
    data = request.get_json()
    
    if not data or 'depot' not in data or 'customers' not in data:
        return jsonify({
            'success': False,
            'message': '请提供仓库和客户信息'
        }), 400
    
    try:
        result = multimodal_service.last_mile.compare_vehicle_options(
            depot=data.get('depot'),
            customers=data.get('customers')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'比较失败: {str(e)}'
        }), 500


@multimodal_bp.route('/last-mile/multi-vehicle', methods=['POST'])
def optimize_multi_vehicle():
    """
    多车辆配送优化
    
    Request Body:
        depot: {'lat': x, 'lon': y}
        customers: 客户列表
        num_vehicles: 车辆数量
        vehicle_capacity: 车辆容量
    """
    data = request.get_json()
    
    if not data or 'depot' not in data or 'customers' not in data:
        return jsonify({
            'success': False,
            'message': '请提供仓库和客户信息'
        }), 400
    
    try:
        result = multimodal_service.last_mile.optimize_multi_vehicle(
            depot=data.get('depot'),
            customers=data.get('customers'),
            num_vehicles=data.get('num_vehicles', 3),
            vehicle_capacity=data.get('vehicle_capacity', 50)
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'优化失败: {str(e)}'
        }), 500


@multimodal_bp.route('/transfer-nodes', methods=['POST'])
def find_transfer_nodes():
    """
    查找转运节点
    
    Request Body:
        origin: [lat, lon]
        destination: [lat, lon]
        mode_from: 起始运输方式
        mode_to: 目标运输方式
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供参数'
        }), 400
    
    try:
        result = multimodal_service.multimodal.find_transfer_nodes(
            origin=tuple(data.get('origin')),
            destination=tuple(data.get('destination')),
            mode_from=data.get('mode_from', 'road'),
            mode_to=data.get('mode_to', 'rail')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查找失败: {str(e)}'
        }), 500


def register_multimodal_routes(app):
    """注册多式联运路由"""
    app.register_blueprint(multimodal_bp)