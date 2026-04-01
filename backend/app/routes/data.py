#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据导入导出路由
"""

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from io import BytesIO
import os
import tempfile

from app.models import db, Node, Order, Route, Vehicle
from app.services.export_service import ExportService
from app.services.import_service import ImportService

data_bp = Blueprint('data', __name__)


# ==================== 数据导入 ====================

@data_bp.route('/import/nodes', methods=['POST'])
@jwt_required()
def import_nodes():
    """导入节点数据"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': '请上传 Excel 文件（.xlsx 或 .xls）'}), 400
        
        service = ImportService()
        result = service.import_nodes(file)
        
        return jsonify({
            'success': True,
            'success_count': result['success_count'],
            'fail_count': result['fail_count'],
            'errors': result.get('errors', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/import/orders', methods=['POST'])
@jwt_required()
def import_orders():
    """导入订单数据"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': '请上传 Excel 文件（.xlsx 或 .xls）'}), 400
        
        service = ImportService()
        result = service.import_orders(file)
        
        return jsonify({
            'success': True,
            'success_count': result['success_count'],
            'fail_count': result['fail_count'],
            'errors': result.get('errors', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/import/routes', methods=['POST'])
@jwt_required()
def import_routes():
    """导入路线数据"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未上传文件'}), 400
        
        file = request.files['file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': '请上传 Excel 文件（.xlsx 或 .xls）'}), 400
        
        service = ImportService()
        result = service.import_routes(file)
        
        return jsonify({
            'success': True,
            'success_count': result['success_count'],
            'fail_count': result['fail_count'],
            'errors': result.get('errors', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 数据导出 ====================

@data_bp.route('/export', methods=['GET'])
@jwt_required()
def export_data():
    """导出数据"""
    try:
        export_type = request.args.get('type', 'nodes')
        export_format = request.args.get('format', 'xlsx')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        service = ExportService()
        
        if export_type == 'transport_report':
            file_data, filename = service.export_transport_report(
                start_date=start_date,
                end_date=end_date,
                format=export_format
            )
        else:
            file_data, filename = service.export_data(
                data_type=export_type,
                format=export_format
            )
        
        return send_file(
            file_data,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if export_format == 'xlsx' else 'text/csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@data_bp.route('/template/<template_type>', methods=['GET'])
@jwt_required()
def download_template(template_type):
    """下载导入模板"""
    try:
        service = ExportService()
        file_data, filename = service.generate_template(template_type)
        
        return send_file(
            file_data,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 数据备份 ====================

@data_bp.route('/backup', methods=['POST'])
@jwt_required()
def backup_database():
    """备份数据库"""
    try:
        service = ExportService()
        file_data, filename = service.backup_database()
        
        return send_file(
            file_data,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
