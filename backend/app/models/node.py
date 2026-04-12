"""节点模型"""

from datetime import datetime
from app.models import db


class Node(db.Model):
    """节点模型（仓库、配送站、中转站、客户点）"""
    __tablename__ = "nodes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    type = db.Column(db.String(20), nullable=False)  # warehouse, distribution, customer
    province = db.Column(db.String(50))
    city = db.Column(db.String(50))
    district = db.Column(db.String(50))
    address = db.Column(db.String(200))
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    contact_name = db.Column(db.String(50))
    contact_person = db.Column(db.String(50))  # 兼容旧字段
    contact_phone = db.Column(db.String(20))
    capacity = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "type": self.type,
            "province": self.province,
            "city": self.city,
            "district": self.district,
            "address": self.address,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "contact_name": self.contact_name or self.contact_person,
            "contact_phone": self.contact_phone,
            "capacity": self.capacity,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
