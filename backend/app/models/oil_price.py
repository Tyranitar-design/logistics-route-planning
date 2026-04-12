"""油价数据模型"""

from datetime import datetime
from app.models import db


class OilPrice(db.Model):
    """油价数据模型"""
    __tablename__ = "oil_prices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    province = db.Column(db.String(50), nullable=False, index=True)
    fuel_type = db.Column(db.String(20), nullable=False)
    fuel_category = db.Column(db.String(20))
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default="元/升")
    source = db.Column(db.String(50), default="unknown")
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "province": self.province,
            "fuel_type": self.fuel_type,
            "fuel_category": self.fuel_category,
            "price": self.price,
            "unit": self.unit,
            "source": self.source,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }
