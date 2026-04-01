# 司机服务

from datetime import datetime, date, timedelta
from app import db
from app.models import User, Order, Vehicle, Task, LocationHistory, Message, Photo
from sqlalchemy import func, and_, or_
import uuid


class DriverService:
    """司机相关业务逻辑"""
    
    def get_driver_by_user_id(self, user_id):
        """根据用户ID获取司机信息"""
        user = User.query.get(user_id)
        if not user:
            return None
        
        # 获取车辆信息
        vehicle = Vehicle.query.filter_by(driver_id=user_id).first()
        
        return {
            'id': user.id,
            'name': user.real_name,
            'phone': user.phone,
            'avatar': user.avatar,
            'status': user.status,
            'vehicle': {
                'id': vehicle.id,
                'plate_number': vehicle.plate_number,
                'vehicle_type': vehicle.vehicle_type,
                'status': vehicle.status
            } if vehicle else None
        }
    
    def get_vehicle_by_driver(self, user_id):
        """获取司机的车辆信息"""
        vehicle = Vehicle.query.filter_by(driver_id=user_id).first()
        
        if not vehicle:
            return None
        
        return {
            'id': vehicle.id,
            'plate_number': vehicle.plate_number,
            'vehicle_type': vehicle.vehicle_type,
            'capacity': vehicle.capacity,
            'status': vehicle.status,
            'current_location': vehicle.current_location,
            'last_update': vehicle.last_update.isoformat() if vehicle.last_update else None
        }
    
    def update_vehicle_status(self, user_id, status):
        """更新车辆状态"""
        vehicle = Vehicle.query.filter_by(driver_id=user_id).first()
        
        if vehicle:
            vehicle.status = status
            vehicle.last_update = datetime.now()
            db.session.commit()
    
    def get_today_stats(self, user_id):
        """获取今日统计"""
        today = date.today()
        tomorrow = date.today()
        
        # 今日完成订单
        completed_orders = Order.query.filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                func.date(Order.completed_at) == today
            )
        ).count()
        
        # 今日收入
        income_result = db.session.query(
            func.sum(Order.freight)
        ).filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                func.date(Order.completed_at) == today
            )
        ).scalar()
        total_income = float(income_result or 0)
        
        # 今日里程
        distance_result = db.session.query(
            func.sum(Order.actual_distance)
        ).filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                func.date(Order.completed_at) == today
            )
        ).scalar()
        total_distance = float(distance_result or 0)
        
        # 准时率（近30天）
        total_count = Order.query.filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                Order.completed_at >= datetime.now() - timedelta(days=30)
            )
        ).count()
        
        ontime_count = Order.query.filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                Order.completed_at <= Order.estimated_arrival,
                Order.completed_at >= datetime.now() - timedelta(days=30)
            )
        ).count()
        
        ontime_rate = round(ontime_count / total_count * 100, 1) if total_count > 0 else 100
        
        return {
            'completedOrders': completed_orders,
            'totalIncome': total_income,
            'totalDistance': total_distance,
            'onTimeRate': ontime_rate
        }
    
    def get_income_stats(self, user_id, days=30):
        """获取收入统计"""
        from datetime import timedelta
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 总收入
        total_income = db.session.query(
            func.sum(Order.freight)
        ).filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                Order.completed_at >= start_date
            )
        ).scalar() or 0
        
        # 总订单数
        total_orders = Order.query.filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                Order.completed_at >= start_date
            )
        ).count()
        
        # 总里程
        total_distance = db.session.query(
            func.sum(Order.actual_distance)
        ).filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                Order.completed_at >= start_date
            )
        ).scalar() or 0
        
        # 评分
        avg_rating = db.session.query(
            func.avg(Order.rating)
        ).filter(
            and_(
                Order.driver_id == user_id,
                Order.status == 'completed',
                Order.rating.isnot(None),
                Order.completed_at >= start_date
            )
        ).scalar() or 5.0
        
        return {
            'totalOrders': total_orders,
            'totalIncome': float(total_income),
            'totalDistance': float(total_distance),
            'onTimeRate': 95.0,  # 默认值
            'rating': round(float(avg_rating), 1)
        }
    
    # ==================== 派单通知 ====================
    
    def get_dispatch_notifications(self, user_id, page=1, page_size=20):
        """获取派单通知"""
        notifications = Message.query.filter(
            and_(
                Message.receiver_id == user_id,
                Message.type == 'dispatch',
                Message.is_read == False
            )
        ).order_by(Message.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        total = Message.query.filter(
            and_(
                Message.receiver_id == user_id,
                Message.type == 'dispatch',
                Message.is_read == False
            )
        ).count()
        
        return {
            'list': [{
                'id': n.id,
                'title': n.title,
                'content': n.content,
                'order_id': n.related_id,
                'created_at': n.created_at.isoformat(),
                'is_read': n.is_read
            } for n in notifications],
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def accept_dispatch(self, user_id, dispatch_id):
        """接受派单"""
        notification = Message.query.get(dispatch_id)
        
        if not notification or notification.receiver_id != user_id:
            raise Exception('派单不存在')
        
        order_id = notification.related_id
        order = Order.query.get(order_id)
        
        if not order:
            raise Exception('订单不存在')
        
        # 更新订单状态
        order.status = 'accepted'
        order.driver_id = user_id
        order.accepted_at = datetime.now()
        
        # 标记通知已读
        notification.is_read = True
        
        db.session.commit()
        
        return {
            'order_id': order_id,
            'status': 'accepted'
        }
    
    def reject_dispatch(self, user_id, dispatch_id, reason=''):
        """拒绝派单"""
        notification = Message.query.get(dispatch_id)
        
        if not notification or notification.receiver_id != user_id:
            raise Exception('派单不存在')
        
        # 标记通知已读
        notification.is_read = True
        notification.extra_data = {'rejected': True, 'reason': reason}
        
        db.session.commit()
    
    # ==================== 运输任务 ====================
    
    def get_transport_tasks(self, user_id, status=None, date=None):
        """获取运输任务"""
        query = Order.query.filter(Order.driver_id == user_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        if date:
            query = query.filter(func.date(Order.created_at) == date)
        
        orders = query.order_by(Order.created_at.desc()).limit(50).all()
        
        return [{
            'id': o.id,
            'order_number': o.order_number,
            'status': o.status,
            'origin_address': o.origin_address,
            'destination_address': o.destination_address,
            'origin_lat': o.origin_lat,
            'origin_lng': o.origin_lng,
            'destination_lat': o.destination_lat,
            'destination_lng': o.destination_lng,
            'distance': o.distance,
            'freight': float(o.freight) if o.freight else 0,
            'goods_name': o.goods_name,
            'weight': o.weight,
            'sender_name': o.sender_name,
            'sender_phone': o.sender_phone,
            'receiver_name': o.receiver_name,
            'receiver_phone': o.receiver_phone,
            'created_at': o.created_at.isoformat() if o.created_at else None,
            'estimated_arrival': o.estimated_arrival.isoformat() if o.estimated_arrival else None
        } for o in orders]
    
    def get_task_detail(self, user_id, task_id):
        """获取任务详情"""
        order = Order.query.filter(
            and_(
                Order.id == task_id,
                Order.driver_id == user_id
            )
        ).first()
        
        if not order:
            return None
        
        return {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'origin': {
                'address': order.origin_address,
                'name': order.origin_name,
                'lat': order.origin_lat,
                'lng': order.origin_lng,
                'contact': order.sender_name,
                'phone': order.sender_phone
            },
            'destination': {
                'address': order.destination_address,
                'name': order.destination_name,
                'lat': order.destination_lat,
                'lng': order.destination_lng,
                'contact': order.receiver_name,
                'phone': order.receiver_phone
            },
            'goods': {
                'name': order.goods_name,
                'weight': order.weight,
                'volume': order.volume,
                'quantity': order.quantity
            },
            'freight': float(order.freight) if order.freight else 0,
            'distance': order.distance,
            'estimated_duration': order.estimated_duration,
            'remark': order.remark,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'accepted_at': order.accepted_at.isoformat() if order.accepted_at else None,
            'pickup_at': order.pickup_at.isoformat() if order.pickup_at else None,
            'completed_at': order.completed_at.isoformat() if order.completed_at else None
        }
    
    def start_task(self, user_id, task_id, latitude=None, longitude=None):
        """开始任务"""
        order = Order.query.filter(
            and_(
                Order.id == task_id,
                Order.driver_id == user_id,
                Order.status == 'accepted'
            )
        ).first()
        
        if not order:
            raise Exception('任务不存在或状态不正确')
        
        order.status = 'in_progress'
        order.started_at = datetime.now()
        
        # 记录开始位置
        if latitude and longitude:
            order.start_lat = latitude
            order.start_lng = longitude
        
        db.session.commit()
        
        return {
            'status': 'in_progress',
            'started_at': order.started_at.isoformat()
        }
    
    def arrive_pickup(self, user_id, task_id, latitude=None, longitude=None):
        """到达取货点"""
        order = Order.query.filter(
            and_(
                Order.id == task_id,
                Order.driver_id == user_id,
                Order.status == 'in_progress'
            )
        ).first()
        
        if not order:
            raise Exception('任务不存在或状态不正确')
        
        order.status = 'arrived_pickup'
        order.arrive_pickup_at = datetime.now()
        
        db.session.commit()
        
        return {
            'status': 'arrived_pickup',
            'arrive_pickup_at': order.arrive_pickup_at.isoformat()
        }
    
    def confirm_pickup(self, user_id, task_id, photo=None):
        """确认取货"""
        order = Order.query.filter(
            and_(
                Order.id == task_id,
                Order.driver_id == user_id,
                Order.status == 'arrived_pickup'
            )
        ).first()
        
        if not order:
            raise Exception('任务不存在或状态不正确')
        
        order.status = 'picked_up'
        order.pickup_at = datetime.now()
        
        # 保存取货照片
        if photo:
            # 这里应该保存照片到文件系统或云存储
            order.pickup_photo = photo
        
        db.session.commit()
        
        return {
            'status': 'picked_up',
            'pickup_at': order.pickup_at.isoformat()
        }
    
    # ==================== 电子签收 ====================
    
    def deliver_task(self, user_id, task_id, **kwargs):
        """送达签收"""
        order = Order.query.filter(
            and_(
                Order.id == task_id,
                Order.driver_id == user_id,
                Order.status == 'picked_up'
            )
        ).first()
        
        if not order:
            raise Exception('任务不存在或状态不正确')
        
        order.status = 'completed'
        order.completed_at = datetime.now()
        order.actual_receiver = kwargs.get('receiver_name')
        order.receiver_phone_confirm = kwargs.get('receiver_phone')
        order.delivery_lat = kwargs.get('latitude')
        order.delivery_lng = kwargs.get('longitude')
        order.delivery_remark = kwargs.get('remark', '')
        
        # 保存签名和照片
        if kwargs.get('signature'):
            order.signature = kwargs.get('signature')
        if kwargs.get('photo'):
            order.delivery_photo = kwargs.get('photo')
        
        db.session.commit()
        
        return {
            'status': 'completed',
            'completed_at': order.completed_at.isoformat(),
            'order_id': task_id
        }
    
    def report_exception(self, user_id, task_id, **kwargs):
        """上报异常"""
        order = Order.query.filter(
            and_(
                Order.id == task_id,
                Order.driver_id == user_id
            )
        ).first()
        
        if not order:
            raise Exception('任务不存在')
        
        # 创建异常记录
        exception = {
            'order_id': task_id,
            'driver_id': user_id,
            'type': kwargs.get('exception_type'),
            'description': kwargs.get('description'),
            'photos': kwargs.get('photos', []),
            'created_at': datetime.now().isoformat()
        }
        
        # 可以创建专门的异常表，这里简化处理
        if not order.exceptions:
            order.exceptions = []
        order.exceptions.append(exception)
        
        db.session.commit()
        
        return exception
    
    # ==================== 消息 ====================
    
    def get_messages(self, user_id, msg_type=None, page=1, page_size=20):
        """获取消息列表"""
        query = Message.query.filter(Message.receiver_id == user_id)
        
        if msg_type:
            query = query.filter(Message.type == msg_type)
        
        messages = query.order_by(Message.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        total = query.count()
        
        return {
            'list': [{
                'id': m.id,
                'type': m.type,
                'title': m.title,
                'content': m.content,
                'is_read': m.is_read,
                'created_at': m.created_at.isoformat()
            } for m in messages],
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    def mark_message_read(self, user_id, message_id):
        """标记消息已读"""
        message = Message.query.filter(
            and_(
                Message.id == message_id,
                Message.receiver_id == user_id
            )
        ).first()
        
        if message:
            message.is_read = True
            db.session.commit()
    
    def get_unread_count(self, user_id):
        """获取未读消息数量"""
        return Message.query.filter(
            and_(
                Message.receiver_id == user_id,
                Message.is_read == False
            )
        ).count()
    
    def send_dispatch_notification(self, driver_id, order_id, order_info):
        """发送派单通知"""
        message = Message(
            receiver_id=driver_id,
            type='dispatch',
            title='新派单通知',
            content=f'您有新的配送任务：{order_info.get("order_number")}，从{order_info.get("origin_address")}到{order_info.get("destination_address")}',
            related_id=order_id,
            created_at=datetime.now()
        )
        
        db.session.add(message)
        db.session.commit()
        
        return message.id