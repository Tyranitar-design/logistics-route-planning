"""任务、位置、消息模型"""

from datetime import datetime
from app.models import db


class Task(db.Model):
    """任务模型 - 司机配送任务"""
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    status = db.Column(db.String(20), default="pending")

    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    arrive_pickup_at = db.Column(db.DateTime)
    pickup_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    pickup_lat = db.Column(db.Float)
    pickup_lng = db.Column(db.Float)
    pickup_photo = db.Column(db.Text)

    delivery_lat = db.Column(db.Float)
    delivery_lng = db.Column(db.Float)
    delivery_photo = db.Column(db.Text)
    delivery_remark = db.Column(db.Text)

    actual_receiver = db.Column(db.String(50))
    receiver_phone_confirm = db.Column(db.String(20))
    signature = db.Column(db.Text)
    exceptions = db.Column(db.Text)

    rating = db.Column(db.Float)
    feedback = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = db.relationship('Order', backref='tasks')
    driver = db.relationship('User', backref='tasks')
    vehicle = db.relationship('Vehicle', backref='tasks')

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "driver_id": self.driver_id,
            "vehicle_id": self.vehicle_id,
            "status": self.status,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "pickup_at": self.pickup_at.isoformat() if self.pickup_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "actual_receiver": self.actual_receiver,
            "rating": self.rating,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LocationHistory(db.Model):
    """位置历史 - 司机轨迹"""
    __tablename__ = "location_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, default=0)
    speed = db.Column(db.Float, default=0)
    direction = db.Column(db.Float, default=0)
    altitude = db.Column(db.Float)

    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    driver = db.relationship('User', backref='locations')
    order = db.relationship('Order', backref='locations')

    def to_dict(self):
        return {
            "id": self.id,
            "driver_id": self.driver_id,
            "order_id": self.order_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "speed": self.speed,
            "direction": self.direction,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class Message(db.Model):
    """消息模型 - 派单通知、系统消息"""
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)

    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)

    related_id = db.Column(db.Integer)
    extra_data = db.Column(db.Text)

    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "related_id": self.related_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Photo(db.Model):
    """照片模型 - 取货/送达照片"""
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    type = db.Column(db.String(20))
    url = db.Column(db.String(500))
    path = db.Column(db.String(500))
    filename = db.Column(db.String(100))

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    task = db.relationship('Task', backref='photos')
    order = db.relationship('Order', backref='photos')
    driver = db.relationship('User', backref='photos')

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "order_id": self.order_id,
            "type": self.type,
            "url": self.url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
