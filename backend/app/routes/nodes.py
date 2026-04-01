#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
节点管理路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Node

nodes_bp = Blueprint('nodes', __name__)


@nodes_bp.route('', methods=['GET'])
@jwt_required()
def get_nodes():
    """获取节点列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        node_type = request.args.get('type')
        keyword = request.args.get('keyword')
        
        query = Node.query
        
        if node_type:
            query = query.filter_by(type=node_type)
        
        if keyword:
            query = query.filter(Node.name.contains(keyword))
        
        pagination = query.order_by(Node.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'nodes': [node.to_dict() for node in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@nodes_bp.route('/<int:node_id>', methods=['GET'])
@jwt_required()
def get_node(node_id):
    """获取单个节点详情"""
    try:
        node = Node.query.get(node_id)
        if not node:
            return jsonify({'error': '节点不存在'}), 404
        
        return jsonify({'node': node.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@nodes_bp.route('', methods=['POST'])
@jwt_required()
def create_node():
    """创建节点"""
    try:
        data = request.get_json()
        
        node = Node(
            name=data.get('name'),
            type=data.get('type', 'customer'),
            address=data.get('address'),
            longitude=data.get('longitude'),
            latitude=data.get('latitude'),
            contact_name=data.get('contact_name'),
            contact_phone=data.get('contact_phone'),
            capacity=data.get('capacity'),
            notes=data.get('notes')
        )
        
        db.session.add(node)
        db.session.commit()
        
        return jsonify({
            'message': '节点创建成功',
            'node': node.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@nodes_bp.route('/<int:node_id>', methods=['PUT'])
@jwt_required()
def update_node(node_id):
    """更新节点"""
    try:
        node = Node.query.get(node_id)
        if not node:
            return jsonify({'error': '节点不存在'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            node.name = data['name']
        if 'type' in data:
            node.type = data['type']
        if 'address' in data:
            node.address = data['address']
        if 'longitude' in data:
            node.longitude = data['longitude']
        if 'latitude' in data:
            node.latitude = data['latitude']
        if 'contact_name' in data:
            node.contact_name = data['contact_name']
        if 'contact_phone' in data:
            node.contact_phone = data['contact_phone']
        if 'capacity' in data:
            node.capacity = data['capacity']
        if 'notes' in data:
            node.notes = data['notes']
        if 'status' in data:
            node.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'message': '节点更新成功',
            'node': node.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@nodes_bp.route('/<int:node_id>', methods=['DELETE'])
@jwt_required()
def delete_node(node_id):
    """删除节点"""
    try:
        node = Node.query.get(node_id)
        if not node:
            return jsonify({'error': '节点不存在'}), 404
        
        db.session.delete(node)
        db.session.commit()
        
        return jsonify({'message': '节点删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@nodes_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_nodes():
    """获取所有节点（用于下拉选择）"""
    try:
        nodes = Node.query.filter_by(status='active').all()
        return jsonify({
            'nodes': [node.to_dict() for node in nodes]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
