#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户认证路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import datetime
from pydantic import ValidationError

from app.models import db, User
from app.schemas import UserLogin, UserCreate, UserResponse
from app.utils.rate_limiter import rate_limit, RateLimits, get_client_ip
from app.services.audit_service import audit_service, AuditAction, AuditModule

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
@rate_limit(**RateLimits.LOGIN)
def login():
    """用户登录 - 使用 Schema 验证"""
    try:
        data = request.get_json()
        
        # 使用 Schema 验证
        try:
            login_data = UserLogin(**data)
            username = login_data.username
            password = login_data.password
        except ValidationError as e:
            return jsonify({'error': '参数验证失败', 'details': e.errors()}), 400
        
        ip_address = get_client_ip()
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.verify_password(password):
            audit_service.log_login(user_id=None, username=username, success=False, ip_address=ip_address)
            return jsonify({'error': '用户名或密码错误'}), 401
        
        if user.status != 'active':
            audit_service.log_login(user_id=user.id, username=username, success=False, ip_address=ip_address)
            return jsonify({'error': '账号已被禁用'}), 403
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        audit_service.log_login(user_id=user.id, username=username, success=True, ip_address=ip_address)
        
        # 创建token
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        # 使用 Schema 返回响应
        return jsonify({
            'success': True,
            'message': '登录成功',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': UserResponse.model_validate(user).model_dump()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新token"""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))  # 转换回整数
    
    if not user or user.status != 'active':
        return jsonify({'error': '用户不存在或已被禁用'}), 401
    
    access_token = create_access_token(identity=str(user_id))
    return jsonify({'access_token': access_token})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    return jsonify({'user': user.to_dict()})


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': '用户名已存在'}), 400
        
        # 检查邮箱是否已存在
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({'error': '邮箱已被注册'}), 400
        
        user = User(
            username=data['username'],
            email=data.get('email'),
            real_name=data.get('real_name'),
            phone=data.get('phone'),
            role=data.get('role', 'operator'),
            status='active'
        )
        user.password = data['password']
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': '注册成功',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not user.verify_password(old_password):
            return jsonify({'error': '原密码错误'}), 400
        
        user.password = new_password
        db.session.commit()
        
        return jsonify({'message': '密码修改成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """获取用户列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        keyword = request.args.get('keyword')
        
        query = User.query
        
        if keyword:
            query = query.filter(
                (User.username.contains(keyword)) |
                (User.real_name.contains(keyword)) |
                (User.email.contains(keyword))
            )
        
        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users', methods=['POST'])
@jwt_required()
def create_user():
    """创建用户"""
    try:
        data = request.get_json()
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=data.get('username')).first():
            return jsonify({'error': '用户名已存在'}), 400
        
        # 检查邮箱是否已存在
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({'error': '邮箱已被注册'}), 400
        
        user = User(
            username=data.get('username'),
            email=data.get('email'),
            real_name=data.get('real_name'),
            phone=data.get('phone'),
            role=data.get('role', 'operator'),
            status=data.get('status', 'active')
        )
        user.password = data.get('password', '123456')  # 默认密码
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': '用户创建成功',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """更新用户"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        data = request.get_json()
        
        if 'email' in data:
            user.email = data['email']
        if 'real_name' in data:
            user.real_name = data['real_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'role' in data:
            user.role = data['role']
        if 'status' in data:
            user.status = data['status']
        if 'password' in data and data['password']:
            user.password = data['password']
        
        db.session.commit()
        
        return jsonify({
            'message': '用户更新成功',
            'user': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """删除用户"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        
        # 不能删除自己
        current_user_id = int(get_jwt_identity())
        if user_id == current_user_id:
            return jsonify({'error': '不能删除自己的账号'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': '用户删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
