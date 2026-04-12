"""供应商相关模型"""

from datetime import datetime
from app.models import db


class Supplier(db.Model):
    """供应商档案"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))
    industry = db.Column(db.String(100))
    address = db.Column(db.Text)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    license_no = db.Column(db.String(100))
    license_expire = db.Column(db.Date)
    qualification_level = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(50))
    cooperation_start = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')
    kraljic_category = db.Column(db.String(50))
    quality_score = db.Column(db.Numeric(5, 2))
    delivery_score = db.Column(db.Numeric(5, 2))
    cost_score = db.Column(db.Numeric(5, 2))
    service_score = db.Column(db.Numeric(5, 2))
    total_score = db.Column(db.Numeric(5, 2))
    risk_level = db.Column(db.String(20))
    last_evaluation_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contracts = db.relationship('SupplierContract', backref='supplier', lazy='dynamic')
    settlements = db.relationship('SupplierSettlement', backref='supplier', lazy='dynamic')
    risks = db.relationship('SupplierRisk', backref='supplier', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'type': self.type,
            'industry': self.industry,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'contact_person': self.contact_person,
            'license_no': self.license_no,
            'license_expire': self.license_expire.isoformat() if self.license_expire else None,
            'qualification_level': self.qualification_level,
            'bank_name': self.bank_name,
            'bank_account': self.bank_account,
            'cooperation_start': self.cooperation_start.isoformat() if self.cooperation_start else None,
            'status': self.status,
            'kraljic_category': self.kraljic_category,
            'quality_score': float(self.quality_score) if self.quality_score else None,
            'delivery_score': float(self.delivery_score) if self.delivery_score else None,
            'cost_score': float(self.cost_score) if self.cost_score else None,
            'service_score': float(self.service_score) if self.service_score else None,
            'total_score': float(self.total_score) if self.total_score else None,
            'risk_level': self.risk_level,
            'last_evaluation_date': self.last_evaluation_date.isoformat() if self.last_evaluation_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SupplierContract(db.Model):
    """供应商合同"""
    __tablename__ = 'supplier_contracts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    contract_no = db.Column(db.String(50), unique=True, nullable=False)
    contract_type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(15, 2))
    payment_terms = db.Column(db.Text)
    service_terms = db.Column(db.Text)
    penalty_terms = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    attachments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'contract_no': self.contract_no,
            'contract_type': self.contract_type,
            'title': self.title,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'amount': float(self.amount) if self.amount else None,
            'payment_terms': self.payment_terms,
            'service_terms': self.service_terms,
            'penalty_terms': self.penalty_terms,
            'status': self.status,
            'attachments': self.attachments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SupplierSettlement(db.Model):
    """供应商结算"""
    __tablename__ = 'supplier_settlements'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    contract_id = db.Column(db.Integer, db.ForeignKey('supplier_contracts.id'))
    settlement_no = db.Column(db.String(50), unique=True, nullable=False)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(15, 2), default=0)
    status = db.Column(db.String(20), default='pending')
    invoice_no = db.Column(db.String(100))
    invoice_date = db.Column(db.Date)
    confirm_date = db.Column(db.Date)
    confirm_by = db.Column(db.String(100))
    remark = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = db.relationship('SupplierContract', backref='settlements')

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'contract_id': self.contract_id,
            'contract_no': self.contract.contract_no if self.contract else None,
            'settlement_no': self.settlement_no,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'amount': float(self.amount) if self.amount else None,
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'status': self.status,
            'invoice_no': self.invoice_no,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'confirm_date': self.confirm_date.isoformat() if self.confirm_date else None,
            'confirm_by': self.confirm_by,
            'remark': self.remark,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SupplierRisk(db.Model):
    """供应商风险"""
    __tablename__ = 'supplier_risks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    risk_type = db.Column(db.String(50), nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    risk_score = db.Column(db.Numeric(5, 2))
    description = db.Column(db.Text)
    impact = db.Column(db.Text)
    mitigation = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    reported_by = db.Column(db.String(100))
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'risk_type': self.risk_type,
            'risk_level': self.risk_level,
            'risk_score': float(self.risk_score) if self.risk_score else None,
            'description': self.description,
            'impact': self.impact,
            'mitigation': self.mitigation,
            'status': self.status,
            'reported_by': self.reported_by,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
