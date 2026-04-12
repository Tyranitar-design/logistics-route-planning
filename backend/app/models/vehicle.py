"""车辆模型"""

from datetime import datetime
from app.models import db


class Vehicle(db.Model):
    """车辆模型"""
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    vehicle_type = db.Column(db.String(20))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    load_capacity = db.Column(db.Float)  # 载重（吨）
    volume_capacity = db.Column(db.Float)  # 容积（立方米）
    capacity = db.Column(db.Float, default=0)  # 兼容字段
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    driver_name = db.Column(db.String(50))
    driver_phone = db.Column(db.String(20))
    current_location = db.Column(db.String(100))
    current_lat = db.Column(db.Float)
    current_lng = db.Column(db.Float)
    status = db.Column(db.String(20), default="available")
    notes = db.Column(db.Text)
    last_update = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    driver = db.relationship('User', backref='vehicle')

    def to_dict(self):
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "vehicle_type": self.vehicle_type,
            "brand": self.brand,
            "model": self.model,
            "load_capacity": self.load_capacity,
            "volume_capacity": self.volume_capacity,
            "capacity": self.capacity or self.load_capacity,
            "driver_id": self.driver_id,
            "driver_name": self.driver_name,
            "driver_phone": self.driver_phone,
            "current_location": self.current_location,
            "current_lat": self.current_lat,
            "current_lng": self.current_lng,
            "status": self.status,
            "notes": self.notes,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
