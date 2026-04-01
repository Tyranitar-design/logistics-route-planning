# -*- coding: utf-8 -*-
"""
供应商管理 API 路由
"""

from flask import Blueprint, request, jsonify
from app.services.supplier_service import (
    SupplierService, SupplierPerformanceService,
    SupplierContractService, SupplierSettlementService, SupplierRiskService
)

supplier_bp = Blueprint('supplier', __name__, url_prefix='/api/suppliers')


# ============ 供应商档案 ============

@supplier_bp.route('', methods=['GET'])
def get_suppliers():
    """获取供应商列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    supplier_type = request.args.get('type')
    kraljic_category = request.args.get('kraljic_category')
    risk_level = request.args.get('risk_level')
    keyword = request.args.get('keyword')

    result = SupplierService.get_list(
        page=page, per_page=per_page,
        status=status, supplier_type=supplier_type,
        kraljic_category=kraljic_category, risk_level=risk_level,
        keyword=keyword
    )

    return jsonify({'code': 0, 'data': result})


@supplier_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """获取供应商统计"""
    result = SupplierService.get_statistics()
    return jsonify({'code': 0, 'data': result})


@supplier_bp.route('/<int:supplier_id>', methods=['GET'])
def get_supplier(supplier_id):
    """获取供应商详情"""
    result = SupplierService.get_by_id(supplier_id)
    if not result:
        return jsonify({'code': 404, 'message': '供应商不存在'}), 404
    return jsonify({'code': 0, 'data': result})


@supplier_bp.route('', methods=['POST'])
def create_supplier():
    """创建供应商"""
    data = request.get_json()
    
    if not data.get('code') or not data.get('name'):
        return jsonify({'code': 400, 'message': '编码和名称不能为空'}), 400

    supplier = SupplierService.create(data)
    return jsonify({'code': 0, 'data': supplier.to_dict(), 'message': '创建成功'})


@supplier_bp.route('/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    """更新供应商"""
    data = request.get_json()
    supplier = SupplierService.update(supplier_id, data)
    
    if not supplier:
        return jsonify({'code': 404, 'message': '供应商不存在'}), 404
    
    return jsonify({'code': 0, 'data': supplier.to_dict(), 'message': '更新成功'})


@supplier_bp.route('/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    """删除供应商"""
    success = SupplierService.delete(supplier_id)
    
    if not success:
        return jsonify({'code': 404, 'message': '供应商不存在'}), 404
    
    return jsonify({'code': 0, 'message': '删除成功'})


# ============ 绩效评估 ============

@supplier_bp.route('/<int:supplier_id>/performance', methods=['GET'])
def get_performance(supplier_id):
    """获取供应商绩效"""
    supplier = SupplierService.get_by_id(supplier_id)
    if not supplier:
        return jsonify({'code': 404, 'message': '供应商不存在'}), 404

    # 获取绩效趋势
    trend = SupplierPerformanceService.get_performance_trend(supplier_id)

    return jsonify({
        'code': 0,
        'data': {
            'supplier': supplier,
            'trend': trend
        }
    })


@supplier_bp.route('/<int:supplier_id>/evaluate', methods=['POST'])
def evaluate_supplier(supplier_id):
    """执行绩效评估"""
    data = request.get_json()
    
    result = SupplierPerformanceService.evaluate(supplier_id, data)
    if not result:
        return jsonify({'code': 404, 'message': '供应商不存在'}), 404
    
    return jsonify({'code': 0, 'data': result, 'message': '评估完成'})


@supplier_bp.route('/performance-matrix', methods=['GET'])
def get_performance_matrix():
    """获取卡拉杰克矩阵分布"""
    result = SupplierPerformanceService.get_kraljic_matrix()
    return jsonify({'code': 0, 'data': result})


# ============ 合同管理 ============

@supplier_bp.route('/<int:supplier_id>/contracts', methods=['GET'])
def get_contracts(supplier_id):
    """获取供应商合同列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    result = SupplierContractService.get_list(
        supplier_id=supplier_id, status=status,
        page=page, per_page=per_page
    )

    return jsonify({'code': 0, 'data': result})


@supplier_bp.route('/<int:supplier_id>/contracts', methods=['POST'])
def create_contract(supplier_id):
    """创建合同"""
    data = request.get_json()
    
    if not data.get('contract_no') or not data.get('start_date') or not data.get('end_date'):
        return jsonify({'code': 400, 'message': '合同编号、开始日期和结束日期不能为空'}), 400

    contract = SupplierContractService.create(supplier_id, data)
    return jsonify({'code': 0, 'data': contract.to_dict(), 'message': '创建成功'})


@supplier_bp.route('/contracts/<int:contract_id>', methods=['PUT'])
def update_contract(contract_id):
    """更新合同"""
    data = request.get_json()
    contract = SupplierContractService.update(contract_id, data)
    
    if not contract:
        return jsonify({'code': 404, 'message': '合同不存在'}), 404
    
    return jsonify({'code': 0, 'data': contract.to_dict(), 'message': '更新成功'})


@supplier_bp.route('/contracts/expiring', methods=['GET'])
def get_expiring_contracts():
    """获取即将到期的合同"""
    days = request.args.get('days', 30, type=int)
    result = SupplierContractService.get_expiring(days)
    return jsonify({'code': 0, 'data': result})


# ============ 对账结算 ============

@supplier_bp.route('/<int:supplier_id>/settlements', methods=['GET'])
def get_settlements(supplier_id):
    """获取结算记录"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    result = SupplierSettlementService.get_list(
        supplier_id=supplier_id, status=status,
        page=page, per_page=per_page
    )

    return jsonify({'code': 0, 'data': result})


@supplier_bp.route('/<int:supplier_id>/settlements', methods=['POST'])
def create_settlement(supplier_id):
    """创建结算单"""
    data = request.get_json()
    
    if not data.get('settlement_no') or not data.get('amount'):
        return jsonify({'code': 400, 'message': '结算单号和金额不能为空'}), 400

    settlement = SupplierSettlementService.create(supplier_id, data)
    return jsonify({'code': 0, 'data': settlement.to_dict(), 'message': '创建成功'})


@supplier_bp.route('/settlements/<int:settlement_id>/confirm', methods=['POST'])
def confirm_settlement(settlement_id):
    """确认对账"""
    data = request.get_json()
    confirm_by = data.get('confirm_by', '系统管理员')

    settlement = SupplierSettlementService.confirm(settlement_id, confirm_by)
    
    if not settlement:
        return jsonify({'code': 404, 'message': '结算单不存在'}), 404
    
    return jsonify({'code': 0, 'data': settlement.to_dict(), 'message': '对账确认成功'})


@supplier_bp.route('/settlements/<int:settlement_id>/pay', methods=['POST'])
def record_payment(settlement_id):
    """记录付款"""
    data = request.get_json()
    amount = data.get('amount')
    invoice_no = data.get('invoice_no')

    if not amount:
        return jsonify({'code': 400, 'message': '付款金额不能为空'}), 400

    settlement = SupplierSettlementService.record_payment(
        settlement_id, amount, invoice_no
    )
    
    if not settlement:
        return jsonify({'code': 404, 'message': '结算单不存在'}), 404
    
    return jsonify({'code': 0, 'data': settlement.to_dict(), 'message': '付款记录成功'})


# ============ 风险监控 ============

@supplier_bp.route('/<int:supplier_id>/risks', methods=['GET'])
def get_risks(supplier_id):
    """获取风险记录"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    risk_level = request.args.get('risk_level')

    result = SupplierRiskService.get_list(
        supplier_id=supplier_id, status=status,
        risk_level=risk_level, page=page, per_page=per_page
    )

    return jsonify({'code': 0, 'data': result})


@supplier_bp.route('/<int:supplier_id>/risks', methods=['POST'])
def report_risk(supplier_id):
    """上报风险"""
    data = request.get_json()
    
    if not data.get('risk_type') or not data.get('risk_level'):
        return jsonify({'code': 400, 'message': '风险类型和等级不能为空'}), 400

    risk = SupplierRiskService.report(supplier_id, data)
    return jsonify({'code': 0, 'data': risk.to_dict(), 'message': '风险上报成功'})


@supplier_bp.route('/risks/<int:risk_id>/mitigate', methods=['POST'])
def mitigate_risk(risk_id):
    """处置风险"""
    data = request.get_json()
    mitigation = data.get('mitigation')
    resolved_by = data.get('resolved_by', '系统管理员')

    if not mitigation:
        return jsonify({'code': 400, 'message': '处置措施不能为空'}), 400

    risk = SupplierRiskService.mitigate(risk_id, mitigation, resolved_by)
    
    if not risk:
        return jsonify({'code': 404, 'message': '风险记录不存在'}), 404
    
    return jsonify({'code': 0, 'data': risk.to_dict(), 'message': '风险处置成功'})


@supplier_bp.route('/risk-dashboard', methods=['GET'])
def get_risk_dashboard():
    """获取风险仪表盘"""
    result = SupplierRiskService.get_dashboard()
    return jsonify({'code': 0, 'data': result})


# ============ 供应商类型和选项 ============

@supplier_bp.route('/types', methods=['GET'])
def get_supplier_types():
    """获取供应商类型选项"""
    types = [
        {'value': '原材料', 'label': '原材料供应商'},
        {'value': '物流', 'label': '物流服务商'},
        {'value': '设备', 'label': '设备供应商'},
        {'value': '服务', 'label': '服务供应商'},
        {'value': '其他', 'label': '其他'}
    ]
    return jsonify({'code': 0, 'data': types})


@supplier_bp.route('/kraljic-categories', methods=['GET'])
def get_kraljic_categories():
    """获取卡拉杰克分类选项"""
    categories = [
        {'value': 'strategic', 'label': '战略型', 'description': '高价值、高风险，需建立战略合作伙伴关系'},
        {'value': 'leverage', 'label': '杠杆型', 'description': '高价值、低风险，可利用竞争获取最优条款'},
        {'value': 'bottleneck', 'label': '瓶颈型', 'description': '低价值、高风险，需确保供应安全'},
        {'value': 'routine', 'label': '常规型', 'description': '低价值、低风险，简化管理降低成本'}
    ]
    return jsonify({'code': 0, 'data': categories})


@supplier_bp.route('/risk-types', methods=['GET'])
def get_risk_types():
    """获取风险类型选项"""
    types = [
        {'value': 'financial', 'label': '财务风险'},
        {'value': 'delivery', 'label': '交付风险'},
        {'value': 'quality', 'label': '质量风险'},
        {'value': 'compliance', 'label': '合规风险'},
        {'value': 'capacity', 'label': '产能风险'},
        {'value': 'other', 'label': '其他风险'}
    ]
    return jsonify({'code': 0, 'data': types})


@supplier_bp.route('/risk-levels', methods=['GET'])
def get_risk_levels():
    """获取风险等级选项"""
    levels = [
        {'value': 'low', 'label': '低风险', 'color': '#67C23A'},
        {'value': 'medium', 'label': '中风险', 'color': '#E6A23C'},
        {'value': 'high', 'label': '高风险', 'color': '#F56C6C'},
        {'value': 'critical', 'label': '严重风险', 'color': '#909399'}
    ]
    return jsonify({'code': 0, 'data': levels})
