#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
节点管理路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.models import db, Node
from app.schemas import NodeCreate, NodeUpdate, NodeResponse
from app.services.amap_service import get_amap_service
from app.services.node_coordinate_service import build_resolution_candidates, resolve_node_coordinates

nodes_bp = Blueprint('nodes', __name__)


def _build_resolution_query(node: Node) -> str:
    candidates = build_resolution_candidates(node)
    return candidates[0] if candidates else ''


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
    """创建节点 - 使用 Schema 验证"""
    try:
        data = request.get_json()
        
        # 使用 Schema 验证
        try:
            node_data = NodeCreate(**data)
        except ValidationError as e:
            return jsonify({'error': '参数验证失败', 'details': e.errors()}), 400
        
        node = Node(
            name=node_data.name,
            code=node_data.code,
            type=node_data.type,
            province=node_data.province,
            city=node_data.city,
            district=node_data.district,
            address=node_data.address,
            longitude=node_data.longitude,
            latitude=node_data.latitude,
            contact_name=node_data.contact_name,
            contact_phone=node_data.contact_phone,
            capacity=node_data.capacity,
            notes=node_data.notes
        )
        
        db.session.add(node)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '节点创建成功',
            'node': NodeResponse.model_validate(node).model_dump()
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


@nodes_bp.route('/coordinate-audit', methods=['GET'])
@jwt_required()
def coordinate_audit():
    """审计缺失坐标的节点"""
    try:
        nodes = Node.query.order_by(Node.created_at.desc()).all()
        missing = []

        for node in nodes:
            if node.longitude is None or node.latitude is None:
                missing.append({
                    'id': node.id,
                    'name': node.name,
                    'province': node.province,
                    'city': node.city,
                    'district': node.district,
                    'address': node.address,
                    'resolution_query': _build_resolution_query(node),
                    'resolution_candidates': build_resolution_candidates(node),
                })

        return jsonify({
            'success': True,
            'summary': {
                'total_nodes': len(nodes),
                'missing_coordinates': len(missing),
            },
            'nodes': missing,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@nodes_bp.route('/<int:node_id>/resolve-coordinates', methods=['POST'])
@jwt_required()
def resolve_coordinates(node_id):
    """使用高德地理编码为单节点回填坐标"""
    try:
        node = Node.query.get(node_id)
        if not node:
            return jsonify({'success': False, 'error': '节点不存在'}), 404

        resolution_candidates = build_resolution_candidates(node)
        if not resolution_candidates:
            return jsonify({
                'success': False,
                'error': '节点缺少可用于地理编码的地址信息'
            }), 400

        service = get_amap_service()
        result = resolve_node_coordinates(node, service)

        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error'),
                'provider': result.get('provider'),
                'provider_status': result.get('provider_status'),
                'degraded': result.get('degraded'),
                'fallback_reason': result.get('fallback_reason'),
                'authenticity': result.get('authenticity'),
                'resolution_query': _build_resolution_query(node),
                'resolution_query_used': result.get('resolution_query_used'),
                'resolution_attempts': result.get('resolution_attempts', []),
                'resolution_candidates': resolution_candidates,
            }), 422

        node.longitude = result.get('longitude')
        node.latitude = result.get('latitude')
        if result.get('province') and not node.province:
            node.province = result.get('province')
        if result.get('city') and not node.city:
            node.city = result.get('city')
        if result.get('district') and not node.district:
            node.district = result.get('district')
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '节点坐标回填成功',
            'node': node.to_dict(),
            'provider': result.get('provider'),
            'provider_status': result.get('provider_status'),
            'degraded': result.get('degraded'),
            'fallback_reason': result.get('fallback_reason'),
            'authenticity': result.get('authenticity'),
            'resolution_query': _build_resolution_query(node),
            'resolution_query_used': result.get('resolution_query_used'),
            'resolution_attempts': result.get('resolution_attempts', []),
            'resolution_candidates': resolution_candidates,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
