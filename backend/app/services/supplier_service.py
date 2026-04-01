# -*- coding: utf-8 -*-
"""
供应商管理服务层
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from sqlalchemy import func, and_, or_
from app import db
from app.models import Supplier, SupplierContract, SupplierSettlement, SupplierRisk


class SupplierService:
    """供应商档案服务"""

    @staticmethod
    def get_list(page: int = 1, per_page: int = 20, 
                 status: str = None, supplier_type: str = None,
                 kraljic_category: str = None, risk_level: str = None,
                 keyword: str = None) -> Dict:
        """获取供应商列表"""
        query = Supplier.query

        if status:
            query = query.filter(Supplier.status == status)
        if supplier_type:
            query = query.filter(Supplier.type == supplier_type)
        if kraljic_category:
            query = query.filter(Supplier.kraljic_category == kraljic_category)
        if risk_level:
            query = query.filter(Supplier.risk_level == risk_level)
        if keyword:
            query = query.filter(or_(
                Supplier.name.contains(keyword),
                Supplier.code.contains(keyword),
                Supplier.contact_person.contains(keyword)
            ))

        total = query.count()
        items = query.order_by(Supplier.created_at.desc()) \
                     .offset((page - 1) * per_page) \
                     .limit(per_page).all()

        return {
            'items': [item.to_dict() for item in items],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }

    @staticmethod
    def get_by_id(supplier_id: int) -> Optional[Dict]:
        """获取供应商详情"""
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return None

        data = supplier.to_dict()

        # 添加统计信息
        data['stats'] = {
            'contract_count': supplier.contracts.count(),
            'active_contract_count': supplier.contracts.filter(
                SupplierContract.status == 'active'
            ).count(),
            'total_settlement': float(db.session.query(
                func.sum(SupplierSettlement.amount)
            ).filter(SupplierSettlement.supplier_id == supplier_id).scalar() or 0),
            'total_paid': float(db.session.query(
                func.sum(SupplierSettlement.paid_amount)
            ).filter(SupplierSettlement.supplier_id == supplier_id).scalar() or 0),
            'active_risk_count': supplier.risks.filter(
                SupplierRisk.status == 'active'
            ).count()
        }

        return data

    @staticmethod
    def create(data: Dict) -> Supplier:
        """创建供应商"""
        supplier = Supplier(
            code=data.get('code'),
            name=data.get('name'),
            type=data.get('type'),
            industry=data.get('industry'),
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            contact_person=data.get('contact_person'),
            license_no=data.get('license_no'),
            license_expire=datetime.strptime(data['license_expire'], '%Y-%m-%d').date() 
                          if data.get('license_expire') else None,
            qualification_level=data.get('qualification_level'),
            bank_name=data.get('bank_name'),
            bank_account=data.get('bank_account'),
            cooperation_start=datetime.strptime(data['cooperation_start'], '%Y-%m-%d').date()
                            if data.get('cooperation_start') else None,
            status=data.get('status', 'active')
        )

        db.session.add(supplier)
        db.session.commit()

        return supplier

    @staticmethod
    def update(supplier_id: int, data: Dict) -> Optional[Supplier]:
        """更新供应商"""
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return None

        for key, value in data.items():
            if hasattr(supplier, key) and key not in ['id', 'created_at']:
                if key in ['license_expire', 'cooperation_start'] and value:
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                setattr(supplier, key, value)

        supplier.updated_at = datetime.utcnow()
        db.session.commit()

        return supplier

    @staticmethod
    def delete(supplier_id: int) -> bool:
        """删除供应商"""
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return False

        db.session.delete(supplier)
        db.session.commit()
        return True

    @staticmethod
    def get_statistics() -> Dict:
        """获取供应商统计"""
        total = Supplier.query.count()
        active = Supplier.query.filter(Supplier.status == 'active').count()

        # 按类型统计
        by_type = db.session.query(
            Supplier.type,
            func.count(Supplier.id)
        ).group_by(Supplier.type).all()

        # 按卡拉杰克矩阵统计
        by_kraljic = db.session.query(
            Supplier.kraljic_category,
            func.count(Supplier.id)
        ).group_by(Supplier.kraljic_category).all()

        # 按风险等级统计
        by_risk = db.session.query(
            Supplier.risk_level,
            func.count(Supplier.id)
        ).group_by(Supplier.risk_level).all()

        return {
            'total': total,
            'active': active,
            'inactive': total - active,
            'by_type': dict(by_type),
            'by_kraljic': dict(by_kraljic),
            'by_risk': dict(by_risk)
        }


class SupplierPerformanceService:
    """供应商绩效评估服务"""

    @staticmethod
    def evaluate(supplier_id: int, scores: Dict) -> Dict:
        """执行绩效评估"""
        supplier = Supplier.query.get(supplier_id)
        if not supplier:
            return None

        quality_score = Decimal(str(scores.get('quality_score', 0)))
        delivery_score = Decimal(str(scores.get('delivery_score', 0)))
        cost_score = Decimal(str(scores.get('cost_score', 0)))
        service_score = Decimal(str(scores.get('service_score', 0)))

        # 计算综合评分（加权平均）
        total_score = (quality_score * Decimal('0.3') + 
                      delivery_score * Decimal('0.25') + 
                      cost_score * Decimal('0.25') + 
                      service_score * Decimal('0.2'))

        # 卡拉杰克矩阵分类
        kraljic_category = SupplierPerformanceService._calculate_kraljic(
            total_score, scores.get('strategic_value', 0.5), 
            scores.get('supply_risk', 0.5)
        )

        # 风险等级
        risk_level = SupplierPerformanceService._calculate_risk_level(total_score)

        supplier.quality_score = quality_score
        supplier.delivery_score = delivery_score
        supplier.cost_score = cost_score
        supplier.service_score = service_score
        supplier.total_score = total_score
        supplier.kraljic_category = kraljic_category
        supplier.risk_level = risk_level
        supplier.last_evaluation_date = date.today()

        db.session.commit()

        return {
            'supplier_id': supplier_id,
            'quality_score': float(quality_score),
            'delivery_score': float(delivery_score),
            'cost_score': float(cost_score),
            'service_score': float(service_score),
            'total_score': float(total_score),
            'kraljic_category': kraljic_category,
            'risk_level': risk_level,
            'evaluation_date': date.today().isoformat()
        }

    @staticmethod
    def _calculate_kraljic(total_score: Decimal, strategic_value: float, 
                          supply_risk: float) -> str:
        """计算卡拉杰克矩阵分类"""
        # 综合评分反映价值
        value = float(total_score) / 100 + strategic_value
        risk = supply_risk

        if value >= 1.0 and risk >= 0.5:
            return 'strategic'  # 战略型
        elif value >= 1.0 and risk < 0.5:
            return 'leverage'   # 杠杆型
        elif value < 1.0 and risk >= 0.5:
            return 'bottleneck' # 瓶颈型
        else:
            return 'routine'    # 常规型

    @staticmethod
    def _calculate_risk_level(total_score: Decimal) -> str:
        """根据综合评分计算风险等级"""
        score = float(total_score)
        if score >= 80:
            return 'low'
        elif score >= 60:
            return 'medium'
        elif score >= 40:
            return 'high'
        else:
            return 'critical'

    @staticmethod
    def get_kraljic_matrix() -> Dict:
        """获取卡拉杰克矩阵分布"""
        suppliers = Supplier.query.filter(
            Supplier.kraljic_category.isnot(None)
        ).all()

        matrix = {
            'strategic': [],   # 战略型
            'leverage': [],    # 杠杆型
            'bottleneck': [],  # 瓶颈型
            'routine': []      # 常规型
        }

        for supplier in suppliers:
            category = supplier.kraljic_category
            if category in matrix:
                matrix[category].append(supplier.to_dict())

        return {
            'matrix': matrix,
            'counts': {
                'strategic': len(matrix['strategic']),
                'leverage': len(matrix['leverage']),
                'bottleneck': len(matrix['bottleneck']),
                'routine': len(matrix['routine'])
            }
        }

    @staticmethod
    def get_performance_trend(supplier_id: int, months: int = 12) -> List[Dict]:
        """获取绩效趋势（模拟数据）"""
        # 实际项目中应该从评估历史表获取
        trend = []
        for i in range(months, 0, -1):
            trend.append({
                'month': (date.today().replace(day=1) - 
                         timedelta(days=(i-1)*30)).strftime('%Y-%m'),
                'quality_score': 75 + (i % 10) * 2,
                'delivery_score': 80 + (i % 8) * 1.5,
                'cost_score': 70 + (i % 12) * 2,
                'service_score': 72 + (i % 6) * 3
            })
        return trend


class SupplierContractService:
    """供应商合同服务"""

    @staticmethod
    def get_list(supplier_id: int = None, status: str = None, 
                 page: int = 1, per_page: int = 20) -> Dict:
        """获取合同列表"""
        query = SupplierContract.query

        if supplier_id:
            query = query.filter(SupplierContract.supplier_id == supplier_id)
        if status:
            query = query.filter(SupplierContract.status == status)

        total = query.count()
        items = query.order_by(SupplierContract.created_at.desc()) \
                     .offset((page - 1) * per_page) \
                     .limit(per_page).all()

        return {
            'items': [item.to_dict() for item in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def create(supplier_id: int, data: Dict) -> SupplierContract:
        """创建合同"""
        contract = SupplierContract(
            supplier_id=supplier_id,
            contract_no=data.get('contract_no'),
            contract_type=data.get('contract_type'),
            title=data.get('title'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
            amount=Decimal(str(data.get('amount', 0))),
            payment_terms=data.get('payment_terms'),
            service_terms=data.get('service_terms'),
            penalty_terms=data.get('penalty_terms'),
            status=data.get('status', 'draft')
        )

        db.session.add(contract)
        db.session.commit()

        return contract

    @staticmethod
    def update(contract_id: int, data: Dict) -> Optional[SupplierContract]:
        """更新合同"""
        contract = SupplierContract.query.get(contract_id)
        if not contract:
            return None

        for key, value in data.items():
            if hasattr(contract, key) and key not in ['id', 'created_at']:
                if key in ['start_date', 'end_date'] and value:
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                elif key == 'amount' and value:
                    value = Decimal(str(value))
                setattr(contract, key, value)

        contract.updated_at = datetime.utcnow()
        db.session.commit()

        return contract

    @staticmethod
    def get_expiring(days: int = 30) -> List[Dict]:
        """获取即将到期的合同"""
        expiry_date = date.today() + timedelta(days=days)

        contracts = SupplierContract.query.filter(
            SupplierContract.status == 'active',
            SupplierContract.end_date <= expiry_date,
            SupplierContract.end_date >= date.today()
        ).order_by(SupplierContract.end_date).all()

        return [c.to_dict() for c in contracts]


class SupplierSettlementService:
    """供应商结算服务"""

    @staticmethod
    def get_list(supplier_id: int = None, status: str = None,
                 page: int = 1, per_page: int = 20) -> Dict:
        """获取结算列表"""
        query = SupplierSettlement.query

        if supplier_id:
            query = query.filter(SupplierSettlement.supplier_id == supplier_id)
        if status:
            query = query.filter(SupplierSettlement.status == status)

        total = query.count()
        items = query.order_by(SupplierSettlement.created_at.desc()) \
                     .offset((page - 1) * per_page) \
                     .limit(per_page).all()

        return {
            'items': [item.to_dict() for item in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def create(supplier_id: int, data: Dict) -> SupplierSettlement:
        """创建结算单"""
        settlement = SupplierSettlement(
            supplier_id=supplier_id,
            contract_id=data.get('contract_id'),
            settlement_no=data.get('settlement_no'),
            period_start=datetime.strptime(data['period_start'], '%Y-%m-%d').date() 
                        if data.get('period_start') else None,
            period_end=datetime.strptime(data['period_end'], '%Y-%m-%d').date()
                      if data.get('period_end') else None,
            amount=Decimal(str(data.get('amount', 0))),
            status='pending',
            remark=data.get('remark')
        )

        db.session.add(settlement)
        db.session.commit()

        return settlement

    @staticmethod
    def confirm(settlement_id: int, confirm_by: str) -> Optional[SupplierSettlement]:
        """确认对账"""
        settlement = SupplierSettlement.query.get(settlement_id)
        if not settlement:
            return None

        settlement.status = 'confirmed'
        settlement.confirm_date = date.today()
        settlement.confirm_by = confirm_by

        db.session.commit()
        return settlement

    @staticmethod
    def record_payment(settlement_id: int, amount: float, 
                       invoice_no: str = None) -> Optional[SupplierSettlement]:
        """记录付款"""
        settlement = SupplierSettlement.query.get(settlement_id)
        if not settlement:
            return None

        settlement.paid_amount = (settlement.paid_amount or 0) + Decimal(str(amount))
        if invoice_no:
            settlement.invoice_no = invoice_no
            settlement.invoice_date = date.today()

        if settlement.paid_amount >= settlement.amount:
            settlement.status = 'paid'

        db.session.commit()
        return settlement


class SupplierRiskService:
    """供应商风险服务"""

    @staticmethod
    def get_list(supplier_id: int = None, status: str = None,
                 risk_level: str = None, page: int = 1, per_page: int = 20) -> Dict:
        """获取风险列表"""
        query = SupplierRisk.query

        if supplier_id:
            query = query.filter(SupplierRisk.supplier_id == supplier_id)
        if status:
            query = query.filter(SupplierRisk.status == status)
        if risk_level:
            query = query.filter(SupplierRisk.risk_level == risk_level)

        total = query.count()
        items = query.order_by(SupplierRisk.created_at.desc()) \
                     .offset((page - 1) * per_page) \
                     .limit(per_page).all()

        return {
            'items': [item.to_dict() for item in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def report(supplier_id: int, data: Dict) -> SupplierRisk:
        """上报风险"""
        risk = SupplierRisk(
            supplier_id=supplier_id,
            risk_type=data.get('risk_type'),
            risk_level=data.get('risk_level'),
            risk_score=Decimal(str(data.get('risk_score', 0))),
            description=data.get('description'),
            impact=data.get('impact'),
            mitigation=data.get('mitigation'),
            reported_by=data.get('reported_by'),
            status='active'
        )

        db.session.add(risk)

        # 更新供应商风险等级
        supplier = Supplier.query.get(supplier_id)
        if supplier:
            level_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            current_level = supplier.risk_level or 'low'
            new_level = data.get('risk_level')

            if level_order.get(new_level, 0) > level_order.get(current_level, 0):
                supplier.risk_level = new_level

        db.session.commit()
        return risk

    @staticmethod
    def mitigate(risk_id: int, mitigation: str, resolved_by: str) -> Optional[SupplierRisk]:
        """处置风险"""
        risk = SupplierRisk.query.get(risk_id)
        if not risk:
            return None

        risk.mitigation = mitigation
        risk.status = 'mitigated'
        risk.resolved_at = datetime.utcnow()
        risk.resolved_by = resolved_by

        db.session.commit()
        return risk

    @staticmethod
    def get_dashboard() -> Dict:
        """获取风险仪表盘"""
        total_risks = SupplierRisk.query.count()
        active_risks = SupplierRisk.query.filter(SupplierRisk.status == 'active').count()

        # 按风险等级统计
        by_level = db.session.query(
            SupplierRisk.risk_level,
            func.count(SupplierRisk.id)
        ).filter(SupplierRisk.status == 'active') \
         .group_by(SupplierRisk.risk_level).all()

        # 按风险类型统计
        by_type = db.session.query(
            SupplierRisk.risk_type,
            func.count(SupplierRisk.id)
        ).filter(SupplierRisk.status == 'active') \
         .group_by(SupplierRisk.risk_type).all()

        # 高风险供应商
        high_risk_suppliers = Supplier.query.filter(
            Supplier.risk_level.in_(['high', 'critical'])
        ).all()

        return {
            'total_risks': total_risks,
            'active_risks': active_risks,
            'mitigated_risks': total_risks - active_risks,
            'by_level': dict(by_level),
            'by_type': dict(by_type),
            'high_risk_suppliers': [s.to_dict() for s in high_risk_suppliers]
        }
