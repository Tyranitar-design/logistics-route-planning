"""
数据模型统一出口
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 在 models 中定义唯一的 db 实例
db = SQLAlchemy()


# ==================== 用户模型 ====================
class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default="user")
    status = db.Column(db.String(20), default="active")  # active, inactive, banned
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "real_name": self.real_name,
            "phone": self.phone,
            "role": self.role,
            "status": self.status,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 节点模型 ====================
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
    contact_name = db.Column(db.String(50))  # 兼容 routes/nodes.py
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


# ==================== 车辆模型 ====================
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
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 绑定司机
    driver_name = db.Column(db.String(50))
    driver_phone = db.Column(db.String(20))
    current_location = db.Column(db.String(100))
    current_lat = db.Column(db.Float)  # 当前纬度
    current_lng = db.Column(db.Float)  # 当前经度
    status = db.Column(db.String(20), default="available")  # available, in_use, maintenance, online, offline, busy
    notes = db.Column(db.Text)
    last_update = db.Column(db.DateTime)  # 最后更新时间
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
            "status": self.status,
            "notes": self.notes,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 订单模型 ====================
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
    freight = db.Column(db.Float)  # 运费
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    
    # 距离/时间
    distance = db.Column(db.Float)
    actual_distance = db.Column(db.Float)
    estimated_duration = db.Column(db.Float)  # 预计时长（分钟）
    estimated_arrival = db.Column(db.DateTime)  # 预计到达时间
    
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
    signature = db.Column(db.Text)  # 签名图片
    pickup_photo = db.Column(db.Text)  # 取货照片
    delivery_photo = db.Column(db.Text)  # 送达照片
    delivery_remark = db.Column(db.Text)
    
    # 异常记录
    exceptions = db.Column(db.Text)  # JSON
    
    # 路线数据
    route_points = db.Column(db.Text)  # JSON 格式的路线点
    
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
            "origin_lat": self.origin_lat,
            "origin_lng": self.origin_lng,
            "sender_name": self.sender_name,
            "sender_phone": self.sender_phone,
            "destination_name": self.destination_name,
            "destination_address": self.destination_address,
            "destination_lat": self.destination_lat,
            "destination_lng": self.destination_lng,
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
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 路线模型 ====================
class Route(db.Model):
    """路线模型"""
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    start_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    end_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    distance = db.Column(db.Float)
    duration = db.Column(db.Float)  # 预计时长（小时）
    estimated_time = db.Column(db.Float)
    toll_cost = db.Column(db.Float)
    fuel_cost = db.Column(db.Float)
    route_data = db.Column(db.Text)
    status = db.Column(db.String(20), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    start_node = db.relationship('Node', foreign_keys=[start_node_id])
    end_node = db.relationship('Node', foreign_keys=[end_node_id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_node_id": self.start_node_id,
            "end_node_id": self.end_node_id,
            "start_node": {"id": self.start_node.id, "name": self.start_node.name} if self.start_node else None,
            "end_node": {"id": self.end_node.id, "name": self.end_node.name} if self.end_node else None,
            "origin": self.origin,
            "destination": self.destination,
            "distance": self.distance,
            "duration": self.duration,
            "estimated_time": self.estimated_time,
            "toll_cost": self.toll_cost,
            "fuel_cost": self.fuel_cost,
            "total_cost": (self.toll_cost or 0) + (self.fuel_cost or 0),
            "route_data": self.route_data,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================== 油价数据模型 ====================
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


# ==================== 任务模型（司机端）====================
class Task(db.Model):
    """任务模型 - 司机配送任务"""
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    
    # 任务状态
    status = db.Column(db.String(20), default="pending")  # pending, accepted, in_progress, picked_up, completed, cancelled
    
    # 时间记录
    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    arrive_pickup_at = db.Column(db.DateTime)
    pickup_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 取货信息
    pickup_lat = db.Column(db.Float)
    pickup_lng = db.Column(db.Float)
    pickup_photo = db.Column(db.Text)  # 取货照片
    
    # 送达信息
    delivery_lat = db.Column(db.Float)
    delivery_lng = db.Column(db.Float)
    delivery_photo = db.Column(db.Text)  # 送达照片
    delivery_remark = db.Column(db.Text)
    
    # 签收信息
    actual_receiver = db.Column(db.String(50))  # 实际收货人
    receiver_phone_confirm = db.Column(db.String(20))
    signature = db.Column(db.Text)  # 签名图片 base64
    
    # 异常记录 (JSON)
    exceptions = db.Column(db.Text)
    
    # 评分
    rating = db.Column(db.Float)
    feedback = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
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


# ==================== 位置历史模型 ====================
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

    # 关联
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


# ==================== 消息模型 ====================
class Message(db.Model):
    """消息模型 - 派单通知、系统消息"""
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    
    type = db.Column(db.String(20), nullable=False)  # dispatch, system, notice, alert
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    
    related_id = db.Column(db.Integer)  # 关联的订单ID等
    extra_data = db.Column(db.Text)  # JSON 格式的额外数据
    
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 关联
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


# ==================== 照片模型 ====================
class Photo(db.Model):
    """照片模型 - 取货/送达照片"""
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    type = db.Column(db.String(20))  # pickup, delivery, exception, general
    url = db.Column(db.String(500))
    path = db.Column(db.String(500))
    filename = db.Column(db.String(100))
    
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
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


# ==================== 供应商模型 ====================
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


# 导入审计日志模型
from app.models.audit import AuditLog
