# 司机端 API 路由

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.driver_service import DriverService
from app.services.location_service import LocationService
import base64
import os
from datetime import datetime

driver_bp = Blueprint('driver', __name__)
driver_service = DriverService()
location_service = LocationService()


@driver_bp.route('/info', methods=['GET'])
@jwt_required()
def get_driver_info():
    """获取司机信息"""
    try:
        user_id = get_jwt_identity()
        driver_info = driver_service.get_driver_by_user_id(user_id)
        
        if not driver_info:
            return jsonify({
                'code': 404,
                'message': '司机信息不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'data': driver_info
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/vehicle', methods=['GET'])
@jwt_required()
def get_vehicle_info():
    """获取车辆信息"""
    try:
        user_id = get_jwt_identity()
        vehicle_info = driver_service.get_vehicle_by_driver(user_id)
        
        return jsonify({
            'code': 200,
            'data': vehicle_info
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/vehicle/status', methods=['PUT'])
@jwt_required()
def update_vehicle_status():
    """更新车辆状态"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['online', 'offline', 'busy']:
            return jsonify({
                'code': 400,
                'message': '无效的状态值'
            }), 400
        
        driver_service.update_vehicle_status(user_id, status)
        
        return jsonify({
            'code': 200,
            'message': '状态更新成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/stats/today', methods=['GET'])
@jwt_required()
def get_today_stats():
    """获取今日统计数据"""
    try:
        user_id = get_jwt_identity()
        stats = driver_service.get_today_stats(user_id)
        
        return jsonify({
            'code': 200,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/stats/income', methods=['GET'])
@jwt_required()
def get_income_stats():
    """获取收入统计"""
    try:
        user_id = get_jwt_identity()
        days = request.args.get('days', 30, type=int)
        
        stats = driver_service.get_income_stats(user_id, days)
        
        return jsonify({
            'code': 200,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 派单通知 ====================

@driver_bp.route('/dispatch/notifications', methods=['GET'])
@jwt_required()
def get_dispatch_notifications():
    """获取派单通知列表"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        result = driver_service.get_dispatch_notifications(user_id, page, page_size)
        
        return jsonify({
            'code': 200,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/dispatch/<int:dispatch_id>/accept', methods=['POST'])
@jwt_required()
def accept_dispatch(dispatch_id):
    """接受派单"""
    try:
        user_id = get_jwt_identity()
        
        result = driver_service.accept_dispatch(user_id, dispatch_id)
        
        return jsonify({
            'code': 200,
            'message': '接单成功',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/dispatch/<int:dispatch_id>/reject', methods=['POST'])
@jwt_required()
def reject_dispatch(dispatch_id):
    """拒绝派单"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        reason = data.get('reason', '')
        
        driver_service.reject_dispatch(user_id, dispatch_id, reason)
        
        return jsonify({
            'code': 200,
            'message': '已拒绝派单'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 运输任务 ====================

@driver_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_transport_tasks():
    """获取运输任务列表"""
    try:
        user_id = get_jwt_identity()
        status = request.args.get('status')
        date = request.args.get('date')
        
        tasks = driver_service.get_transport_tasks(user_id, status, date)
        
        return jsonify({
            'code': 200,
            'data': {
                'list': tasks,
                'total': len(tasks)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_detail(task_id):
    """获取任务详情"""
    try:
        user_id = get_jwt_identity()
        task = driver_service.get_task_detail(user_id, task_id)
        
        if not task:
            return jsonify({
                'code': 404,
                'message': '任务不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'data': task
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/tasks/<int:task_id>/start', methods=['POST'])
@jwt_required()
def start_task(task_id):
    """开始任务"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # 获取当前位置
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        result = driver_service.start_task(user_id, task_id, latitude, longitude)
        
        return jsonify({
            'code': 200,
            'message': '任务已开始',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/tasks/<int:task_id>/arrive', methods=['POST'])
@jwt_required()
def arrive_pickup(task_id):
    """到达取货点"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        result = driver_service.arrive_pickup(user_id, task_id, latitude, longitude)
        
        return jsonify({
            'code': 200,
            'message': '已到达取货点',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/tasks/<int:task_id>/pickup', methods=['POST'])
@jwt_required()
def confirm_pickup(task_id):
    """确认取货"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # 照片（base64）
        photo = data.get('photo')
        
        result = driver_service.confirm_pickup(user_id, task_id, photo)
        
        return jsonify({
            'code': 200,
            'message': '取货确认成功',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 电子签收 ====================

@driver_bp.route('/tasks/<int:task_id>/delivery', methods=['POST'])
@jwt_required()
def deliver_task(task_id):
    """送达签收"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # 签收信息
        receiver_name = data.get('receiver_name')
        receiver_phone = data.get('receiver_phone')
        signature = data.get('signature')  # 签名图片 base64
        photo = data.get('photo')  # 现场照片 base64
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        remark = data.get('remark', '')
        
        if not receiver_name:
            return jsonify({
                'code': 400,
                'message': '请填写收货人姓名'
            }), 400
        
        result = driver_service.deliver_task(
            user_id, task_id,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            signature=signature,
            photo=photo,
            latitude=latitude,
            longitude=longitude,
            remark=remark
        )
        
        return jsonify({
            'code': 200,
            'message': '签收成功',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/tasks/<int:task_id>/exception', methods=['POST'])
@jwt_required()
def report_exception(task_id):
    """上报异常"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        exception_type = data.get('type')  # damage, lost, reject, other
        description = data.get('description', '')
        photos = data.get('photos', [])  # 照片列表
        
        result = driver_service.report_exception(
            user_id, task_id,
            exception_type=exception_type,
            description=description,
            photos=photos
        )
        
        return jsonify({
            'code': 200,
            'message': '异常已上报',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 照片上传 ====================

@driver_bp.route('/upload/photo', methods=['POST'])
@jwt_required()
def upload_photo():
    """上传照片"""
    try:
        if 'photo' not in request.files:
            return jsonify({
                'code': 400,
                'message': '请选择照片'
            }), 400
        
        file = request.files['photo']
        task_id = request.form.get('task_id')
        photo_type = request.form.get('type', 'general')  # pickup, delivery, exception
        
        # 保存照片
        upload_dir = os.path.join('uploads', 'photos', str(task_id or 'general'))
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{photo_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # 返回访问 URL
        photo_url = f"/uploads/photos/{task_id or 'general'}/{filename}"
        
        return jsonify({
            'code': 200,
            'data': {
                'url': photo_url,
                'filename': filename
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 轨迹上报 ====================

@driver_bp.route('/location/report', methods=['POST'])
@jwt_required()
def report_location():
    """上报位置"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy', 0)
        speed = data.get('speed', 0)
        direction = data.get('direction', 0)
        task_id = data.get('task_id')
        
        if not latitude or not longitude:
            return jsonify({
                'code': 400,
                'message': '缺少位置信息'
            }), 400
        
        location_service.save_location(
            driver_id=user_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            direction=direction,
            task_id=task_id
        )
        
        return jsonify({
            'code': 200,
            'message': '位置上报成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/location/history', methods=['GET'])
@jwt_required()
def get_location_history():
    """获取轨迹历史"""
    try:
        user_id = get_jwt_identity()
        task_id = request.args.get('task_id', type=int)
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        history = location_service.get_location_history(
            driver_id=user_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return jsonify({
            'code': 200,
            'data': history
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


# ==================== 消息推送 ====================

@driver_bp.route('/messages', methods=['GET'])
@jwt_required()
def get_messages():
    """获取消息列表"""
    try:
        user_id = get_jwt_identity()
        msg_type = request.args.get('type')  # dispatch, system, notice
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        result = driver_service.get_messages(user_id, msg_type, page, page_size)
        
        return jsonify({
            'code': 200,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/messages/<int:message_id>/read', methods=['POST'])
@jwt_required()
def mark_message_read(message_id):
    """标记消息已读"""
    try:
        user_id = get_jwt_identity()
        
        driver_service.mark_message_read(user_id, message_id)
        
        return jsonify({
            'code': 200,
            'message': '已标记为已读'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500


@driver_bp.route('/messages/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """获取未读消息数量"""
    try:
        user_id = get_jwt_identity()
        
        count = driver_service.get_unread_count(user_id)
        
        return jsonify({
            'code': 200,
            'data': {
                'count': count
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        }), 500