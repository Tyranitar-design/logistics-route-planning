"""订单模型"""

from datetime import datetime
from app.models import db


class Order(db.Model):
    """订单模型"""
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # 客户信息
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))

    # 发货信息
    pickup_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    origin_name = db.Column(db.String(100))
    origin_address = db.Column(db.String(200))
    origin_lat = db.Column(db.Float)
    origin_lng = db.Column(db.Float)
    sender_name = db.Column(db.String(50))
    sender_phone = db.Column(db.String(20))

    # 收货信息
    delivery_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    destination_name = db.Column(db.String(100))
    destination_address = db.Column(db.String(200))
    destination_lat = db.Column(db.Float)
    destination_lng = db.Column(db.Float)
    receiver_name = db.Column(db.String(50))
    receiver_phone = db.Column(db.String(20))

    # 货物信息
    cargo_name = db.Column(db.String(100))
    goods_name = db.Column(db.String(100))  # 兼容字段
    cargo_type = db.Column(db.String(50))
    weight = db.Column(db.Float)
    volume = db.Column(db.Float)
    quantity = db.Column(db.Integer)

    # 订单状态
    priority = db.Column(db.String(20), default="normal")
    status = db.Column(db.String(20), default="pending", index=True)

    # 司机/车辆
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))

    # 费用
    freight = db.Column(db.Float)
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)

    # 距离/时间
    distance = db.Column(db.Float)
    actual_distance = db.Column(db.Float)
    estimated_duration = db.Column(db.Float)
    estimated_arrival = db.Column(db.DateTime)

    # 时间记录
    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    arrive_pickup_at = db.Column(db.DateTime)
    pickup_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # 位置记录
    start_lat = db.Column(db.Float)
    start_lng = db.Column(db.Float)
    delivery_lat = db.Column(db.Float)
    delivery_lng = db.Column(db.Float)

    # 签收信息
    actual_receiver = db.Column(db.String(50))
    receiver_phone_confirm = db.Column(db.String(20))
    signature = db.Column(db.Text)
    pickup_photo = db.Column(db.Text)
    delivery_photo = db.Column(db.Text)
    delivery_remark = db.Column(db.Text)

    # 异常记录
    exceptions = db.Column(db.Text)

    # 路线数据
    route_points = db.Column(db.Text)

    # 评分
    rating = db.Column(db.Float)
    feedback = db.Column(db.Text)

    # 其他
    notes = db.Column(db.Text)
    remark = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    pickup_node = db.relationship('Node', foreign_keys=[pickup_node_id])
    delivery_node = db.relationship('Node', foreign_keys=[delivery_node_id])
    vehicle = db.relationship('Vehicle', backref='orders')
    driver = db.relationship('User', backref='orders')

    def to_dict(self):
        return {
            "id": self.id,
            "order_number": self.order_number,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "origin_name": self.origin_name,
            "origin_address": self.origin_address,
            "sender_name": self.sender_name,
            "sender_phone": self.sender_phone,
            "destination_name": self.destination_name,
            "destination_address": self.destination_address,
            "receiver_name": self.receiver_name,
            "receiver_phone": self.receiver_phone,
            "cargo_name": self.cargo_name or self.goods_name,
            "goods_name": self.goods_name or self.cargo_name,
            "weight": self.weight,
            "volume": self.volume,
            "priority": self.priority,
            "status": self.status,
            "driver_id": self.driver_id,
            "vehicle_id": self.vehicle_id,
            "freight": self.freight,
            "distance": self.distance,
            "estimated_duration": self.estimated_duration,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "pickup_at": self.pickup_at.isoformat() if self.pickup_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pickup_node_id": self.pickup_node_id,
            "delivery_node_id": self.delivery_node_id,
            "pickup_node": {"id": self.pickup_node.id, "name": self.pickup_node.name, "city": self.pickup_node.city} if self.pickup_node else None,
            "delivery_node": {"id": self.delivery_node.id, "name": self.delivery_node.name, "city": self.delivery_node.city} if self.delivery_node else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
