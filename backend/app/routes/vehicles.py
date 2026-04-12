#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
车辆管理路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Vehicle
from app.services.kafka_service import send_vehicle_event

vehicles_bp = Blueprint('vehicles', __name__)


@vehicles_bp.route('', methods=['GET'])
@jwt_required()
def get_vehicles():
    """获取车辆列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        keyword = request.args.get('keyword')
        
        query = Vehicle.query
        
        if status:
            query = query.filter_by(status=status)
        
        if keyword:
            query = query.filter(
                (Vehicle.plate_number.contains(keyword)) |
                (Vehicle.driver_name.contains(keyword))
            )
        
        pagination = query.order_by(Vehicle.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'vehicles': [vehicle.to_dict() for vehicle in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicles_bp.route('/<int:vehicle_id>', methods=['GET'])
@jwt_required()
def get_vehicle(vehicle_id):
    """获取单个车辆详情"""
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': '车辆不存在'}), 404
        
        return jsonify({'vehicle': vehicle.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicles_bp.route('', methods=['POST'])
@jwt_required()
def create_vehicle():
    """创建车辆"""
    try:
        data = request.get_json()
        
        # 检查车牌号是否已存在
        if Vehicle.query.filter_by(plate_number=data['plate_number']).first():
            return jsonify({'error': '车牌号已存在'}), 400
        
        vehicle = Vehicle(
            plate_number=data.get('plate_number'),
            vehicle_type=data.get('vehicle_type'),
            brand=data.get('brand'),
            model=data.get('model'),
            load_capacity=data.get('load_capacity'),
            volume_capacity=data.get('volume_capacity'),
            driver_name=data.get('driver_name'),
            driver_phone=data.get('driver_phone'),
            notes=data.get('notes')
        )
        
        db.session.add(vehicle)
        db.session.commit()
        
        # 发送到 Kafka
        try:
            send_vehicle_event(vehicle.to_dict(), 'created')
        except Exception as e:
            print(f'Kafka send failed: {e}')
        
        return jsonify({
            'message': '车辆创建成功',
            'vehicle': vehicle.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@vehicles_bp.route('/<int:vehicle_id>', methods=['PUT'])
@jwt_required()
def update_vehicle(vehicle_id):
    """更新车辆"""
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': '车辆不存在'}), 404
        
        data = request.get_json()
        
        if 'plate_number' in data:
            vehicle.plate_number = data['plate_number']
        if 'vehicle_type' in data:
            vehicle.vehicle_type = data['vehicle_type']
        if 'brand' in data:
            vehicle.brand = data['brand']
        if 'model' in data:
            vehicle.model = data['model']
        if 'load_capacity' in data:
            vehicle.load_capacity = data['load_capacity']
        if 'volume_capacity' in data:
            vehicle.volume_capacity = data['volume_capacity']
        if 'driver_name' in data:
            vehicle.driver_name = data['driver_name']
        if 'driver_phone' in data:
            vehicle.driver_phone = data['driver_phone']
        if 'notes' in data:
            vehicle.notes = data['notes']
        if 'status' in data:
            vehicle.status = data['status']
        
        db.session.commit()
        
        # 发送到 Kafka
        try:
            send_vehicle_event(vehicle.to_dict(), 'updated')
        except Exception as e:
            print(f'Kafka send failed: {e}')
        
        return jsonify({
            'message': '车辆更新成功',
            'vehicle': vehicle.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@vehicles_bp.route('/<int:vehicle_id>', methods=['DELETE'])
@jwt_required()
def delete_vehicle(vehicle_id):
    """删除车辆"""
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': '车辆不存在'}), 404
        
        db.session.delete(vehicle)
        db.session.commit()
        
        return jsonify({'message': '车辆删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@vehicles_bp.route('/available', methods=['GET'])
@jwt_required()
def get_available_vehicles():
    """获取可用车辆列表"""
    try:
        vehicles = Vehicle.query.filter_by(status='available').all()
        return jsonify({
            'vehicles': [vehicle.to_dict() for vehicle in vehicles]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
