"""
库存优化 API 路由
"""

from flask import Blueprint, request, jsonify
from app.services.inventory_optimization_service import inventory_service

inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')


@inventory_bp.route('/optimize', methods=['POST'])
def optimize_inventory():
    """
    综合库存优化
    
    Request Body:
        item_id: 物品ID
        annual_demand: 年需求量
        ordering_cost: 每次订货成本
        holding_cost_rate: 持有成本率
        unit_price: 单价
        lead_time: 提前期（天）
        demand_std: 需求标准差
        service_level: 服务水平（默认0.95）
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供库存参数'
        }), 400
    
    try:
        result = inventory_service.optimize_inventory(
            item_id=data.get('item_id'),
            annual_demand=data.get('annual_demand'),
            ordering_cost=data.get('ordering_cost'),
            holding_cost_rate=data.get('holding_cost_rate'),
            unit_price=data.get('unit_price', 1.0),
            lead_time=data.get('lead_time'),
            demand_std=data.get('demand_std'),
            service_level=data.get('service_level', 0.95)
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


@inventory_bp.route('/eoq', methods=['POST'])
def calculate_eoq():
    """
    计算 EOQ
    
    Request Body:
        annual_demand: 年需求量
        ordering_cost: 每次订货成本
        holding_cost_per_unit: 单位持有成本
        unit_price: 单价
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供 EOQ 参数'
        }), 400
    
    try:
        result = inventory_service.eoq.calculate_eoq(
            annual_demand=data.get('annual_demand'),
            ordering_cost=data.get('ordering_cost'),
            holding_cost_per_unit=data.get('holding_cost_per_unit'),
            unit_price=data.get('unit_price', 1.0)
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'计算失败: {str(e)}'
        }), 500


@inventory_bp.route('/safety-stock', methods=['POST'])
def calculate_safety_stock():
    """
    计算安全库存
    
    Request Body:
        avg_demand: 平均日需求量
        demand_std: 需求标准差
        lead_time: 提前期（天）
        lead_time_std: 提前期标准差（可选）
        service_level: 服务水平
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供安全库存参数'
        }), 400
    
    try:
        result = inventory_service.safety_stock.calculate_safety_stock(
            avg_demand=data.get('avg_demand'),
            demand_std=data.get('demand_std'),
            lead_time=data.get('lead_time'),
            lead_time_std=data.get('lead_time_std', 0),
            service_level=data.get('service_level', 0.95)
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'计算失败: {str(e)}'
        }), 500


@inventory_bp.route('/turnover-analysis', methods=['POST'])
def analyze_turnover():
    """
    库存周转分析
    
    Request Body:
        items: 物品列表 [{'id': '', 'avg_inventory': 0, 'annual_usage': 0}]
    """
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({
            'success': False,
            'message': '请提供物品列表'
        }), 400
    
    try:
        result = inventory_service.analyze_inventory_turnover(data['items'])
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'分析失败: {str(e)}'
        }), 500


@inventory_bp.route('/alerts', methods=['POST'])
def get_alerts():
    """
    库存预警
    
    Request Body:
        items: 物品列表 [{'id': '', 'current_inventory': 0, 'reorder_point': 0, 'safety_stock': 0}]
    """
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({
            'success': False,
            'message': '请提供物品列表'
        }), 400
    
    try:
        result = inventory_service.get_inventory_alerts(data['items'])
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取预警失败: {str(e)}'
        }), 500


@inventory_bp.route('/vmi/setup', methods=['POST'])
def setup_vmi():
    """
    设置 VMI 参数
    
    Request Body:
        supplier_id: 供应商ID
        min_inventory: 最小库存
        max_inventory: 最大库存
        replenishment_frequency: 补货频率（天）
        lead_time: 提前期
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供 VMI 参数'
        }), 400
    
    try:
        result = inventory_service.vmi.setup_vmi(
            supplier_id=data.get('supplier_id'),
            min_inventory=data.get('min_inventory'),
            max_inventory=data.get('max_inventory'),
            replenishment_frequency=data.get('replenishment_frequency'),
            lead_time=data.get('lead_time')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'设置失败: {str(e)}'
        }), 500


@inventory_bp.route('/vmi/replenishment', methods=['POST'])
def calculate_replenishment():
    """
    计算 VMI 补货量
    
    Request Body:
        supplier_id: 供应商ID
        current_inventory: 当前库存
        avg_daily_demand: 平均日需求
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': '请提供补货参数'
        }), 400
    
    try:
        result = inventory_service.vmi.calculate_replenishment(
            supplier_id=data.get('supplier_id'),
            current_inventory=data.get('current_inventory'),
            avg_daily_demand=data.get('avg_daily_demand')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'计算失败: {str(e)}'
        }), 500


def register_inventory_routes(app):
    """注册库存路由"""
    app.register_blueprint(inventory_bp)