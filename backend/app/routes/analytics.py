#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据分析 API 路由
"""

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.analytics_service import get_analytics_service
from app.services.shipment_cost_analytics_service import get_shipment_cost_analytics_service
import logging
import io
from app.utils.rate_limiter import rate_limit, RateLimits

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@rate_limit(**RateLimits.API)
def get_dashboard():
    """获取仪表盘数据"""
    try:
        service = get_analytics_service()
        result = service.get_dashboard_metrics()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/operations-summary', methods=['GET', 'POST'])
@jwt_required()
def get_operations_summary():
    """
    获取真实 shipment_facts 驱动的运营/成本总览。

    Query/Body:
        limit: 最大扫描 shipment_facts 数
        trend_days: 趋势窗口天数
        lane_limit: 返回 Top OD/城市数
        city: 可选城市过滤
    """
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
        else:
            payload = {
                'limit': request.args.get('limit', 50000, type=int),
                'trend_days': request.args.get('trend_days', 30, type=int),
                'lane_limit': request.args.get('lane_limit', 8, type=int),
                'city': request.args.get('city') or request.args.get('destination_city'),
            }
        result = get_shipment_cost_analytics_service().operations_summary(payload)
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取真实运营成本总览失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/operations-scorecard', methods=['GET', 'POST'])
@jwt_required()
def get_operations_scorecard():
    """
    获取真实 shipment_facts 驱动的运营/成本 readiness scorecard。

    Query/Body:
        limit: 最大扫描 shipment_facts 数
        trend_days: 趋势窗口天数
        lane_limit: 返回 Top OD/城市数
        city: 可选城市过滤
    """
    try:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
        else:
            payload = {
                'limit': request.args.get('limit', 50000, type=int),
                'trend_days': request.args.get('trend_days', 30, type=int),
                'lane_limit': request.args.get('lane_limit', 8, type=int),
                'city': request.args.get('city') or request.args.get('destination_city'),
            }
        result = get_shipment_cost_analytics_service().operations_scorecard(payload)
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取真实运营成本评分卡失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _interactive_payload(default_limit=5000, default_trend_days=30, default_lane_limit=10):
    if request.method == 'POST':
        raw = request.get_json(silent=True) or {}
    else:
        raw = dict(request.args)

    runtime_profile = str(raw.get('runtime_profile') or 'interactive').lower()
    runtime_profile = 'full' if runtime_profile == 'full' else 'interactive'
    max_limit = 50000 if runtime_profile == 'full' else 5000

    def as_int(name, default, low, high):
        try:
            value = int(raw.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))

    return {
        'runtime_profile': runtime_profile,
        'limit': as_int('limit', default_limit, 1, max_limit),
        'trend_days': as_int('trend_days', default_trend_days, 7, 120),
        'lane_limit': as_int('lane_limit', default_lane_limit, 3, 30),
        'horizon_days': as_int('horizon_days', 7, 1, 60),
        'anomaly_limit': as_int('anomaly_limit', 20, 1, 100),
        'city': raw.get('city') or raw.get('destination_city'),
    }


def _safe_component(name, factory, degraded_value):
    try:
        result = factory()
        if isinstance(result, dict):
            return result
        return degraded_value
    except Exception as exc:
        logger.exception("企业摘要组件 %s 降级: %s", name, exc)
        value = dict(degraded_value)
        value.update({
            'success': False,
            'provider_status': 'degraded',
            'fallback_reason': f'{name.upper()}_COMPONENT_FAILED',
            'error': exc.__class__.__name__,
        })
        return value


def _forecast_points(forecast):
    points = []
    for item in (forecast.get('forecast') or []):
        value = item.get('predicted_orders', item.get('value', 0))
        points.append({
            'date': item.get('date') or item.get('bucket_start'),
            'bucket_start': item.get('bucket_start') or item.get('date'),
            'value': value,
            'predicted_orders': value,
            'lower': item.get('lower_bound', item.get('lower', value)),
            'upper': item.get('upper_bound', item.get('upper', value)),
            'method': item.get('method') or forecast.get('model'),
            'time_granularity': item.get('time_granularity') or forecast.get('time_granularity'),
        })
    return points


def _component_name(component):
    names = {
        'transport_base': '基础运输',
        'fuel_and_toll_estimate': '燃油路桥',
        'handling_service_estimate': '装卸服务',
        'insurance_and_other': '保险其他',
    }
    return names.get(component, component)


def _enterprise_recommendations(operations, prediction, anomaly, capabilities):
    recommendations = []
    recommendations.extend(operations.get('recommendations') or [])
    recommendations.extend(prediction.get('recommendations') or [])
    recommendations.extend(anomaly.get('recommendations') or [])
    recommendations.extend(capabilities.get('recommendations') or [])
    if not recommendations:
        recommendations.append('真实 shipment_facts 指标已可用；建议先以 interactive 模式做页面分析，深度训练继续走后台 shadow job。')
    return recommendations[:8]


@analytics_bp.route('/enterprise-summary', methods=['GET', 'POST'])
@jwt_required()
def get_enterprise_summary():
    """Aggregate real shipment_facts analytics for upgraded Vue pages.

    This endpoint is intentionally defensive: optional AI/optimization
    components degrade independently so dashboards do not fall back to random
    mock data or crash because one heavy shadow component is unavailable.
    """
    payload = _interactive_payload()
    base_payload = {
        'runtime_profile': payload['runtime_profile'],
        'limit': payload['limit'],
        'trend_days': payload['trend_days'],
        'lane_limit': payload['lane_limit'],
        'city': payload['city'],
    }

    operations = _safe_component(
        'operations',
        lambda: get_shipment_cost_analytics_service().operations_summary(base_payload),
        {'success': False, 'data_source': 'shipment_fact', 'kpis': {}, 'trend': [], 'top_lanes': []},
    )
    operations_scorecard = _safe_component(
        'operations_scorecard',
        lambda: get_shipment_cost_analytics_service().operations_scorecard(base_payload),
        {'success': False, 'data_source': 'shipment_fact', 'summary': {}, 'components': []},
    )

    prediction = _safe_component(
        'prediction',
        lambda: __import__(
            'app.services.shipment_prediction_service',
            fromlist=['get_shipment_prediction_service'],
        ).get_shipment_prediction_service().forecast_demand(
            days=payload['horizon_days'],
            city=payload['city'],
            limit=payload['limit'],
            time_granularity='auto',
            series_source='shipped_at',
        ),
        {'success': False, 'data_source': 'shipment_fact', 'forecast': [], 'series_summary': {}},
    )
    prediction_status = _safe_component(
        'prediction_status',
        lambda: __import__(
            'app.services.shipment_prediction_service',
            fromlist=['get_shipment_prediction_service'],
        ).get_shipment_prediction_service().model_status(),
        {'success': False, 'data_source': 'shipment_fact', 'models': [], 'latest_jobs': []},
    )

    anomaly_payload = {
        'runtime_profile': payload['runtime_profile'],
        'limit': payload['limit'],
        'anomaly_limit': payload['anomaly_limit'],
        'use_ml': False,
    }
    anomaly = _safe_component(
        'anomaly',
        lambda: __import__(
            'app.services.shipment_anomaly_service',
            fromlist=['get_shipment_anomaly_service'],
        ).get_shipment_anomaly_service().scorecard(anomaly_payload),
        {'success': False, 'data_source': 'shipment_fact', 'summary': {}, 'components': [], 'evidence': {}},
    )
    capabilities = _safe_component(
        'capabilities',
        lambda: __import__(
            'app.services.optional_capability_service',
            fromlist=['get_optional_capability_service'],
        ).get_optional_capability_service().check(run_smoke=False),
        {'success': False, 'provider_status': 'degraded', 'summary': {}, 'capabilities': []},
    )

    kpis = operations.get('kpis') or {}
    op_summary = operations.get('summary') or {}
    anomaly_summary = anomaly.get('summary') or {}
    capability_summary = capabilities.get('summary') or {}
    provider_status = 'ok'
    fallback_reasons = []
    for item in [operations, operations_scorecard, prediction, prediction_status, anomaly, capabilities]:
        if item.get('provider_status') == 'degraded' or item.get('success') is False:
            provider_status = 'degraded'
        reason = item.get('fallback_reason')
        if reason:
            fallback_reasons.append(str(reason))

    cost_components = [
        {
            'name': _component_name(item.get('component')),
            'component': item.get('component'),
            'value': item.get('amount', 0),
            'amount': item.get('amount', 0),
            'percent': round(float(item.get('share') or 0) * 100, 2),
            'share': item.get('share', 0),
            'source': item.get('source'),
        }
        for item in (operations.get('cost_components') or [])
    ]
    top_lanes = operations.get('top_lanes') or []
    city_breakdown = operations.get('city_breakdown') or []
    forecast_points = _forecast_points(prediction)

    total_shipments = int(kpis.get('total_shipments') or op_summary.get('records_scanned') or 0)
    exception_rate = float(kpis.get('exception_rate') or 0)
    on_time_rate = kpis.get('on_time_rate')

    response = {
        'success': True,
        'data_source': 'shipment_fact',
        'provider_status': provider_status,
        'fallback_reason': ';'.join(fallback_reasons) if fallback_reasons else None,
        'authenticity_level': 'B' if provider_status == 'ok' else 'C',
        'runtime_profile': payload['runtime_profile'],
        'runtime_limits': {
            'limit': payload['limit'],
            'trend_days': payload['trend_days'],
            'lane_limit': payload['lane_limit'],
            'horizon_days': payload['horizon_days'],
            'anomaly_limit': payload['anomaly_limit'],
        },
        'summary': {
            'total_orders': total_shipments,
            'shipment_facts_total': total_shipments,
            'records_scanned': op_summary.get('records_scanned', total_shipments),
            'total_cost': kpis.get('total_freight', 0),
            'total_freight': kpis.get('total_freight', 0),
            'avg_cost': kpis.get('avg_freight_per_paid_shipment') or kpis.get('avg_freight_per_shipment') or 0,
            'on_time_rate': on_time_rate,
            'completion_rate': kpis.get('delivery_completion_rate', 0),
            'exception_rate': exception_rate,
            'high_risk_count': (anomaly_summary.get('by_level') or {}).get('critical', 0)
                + (anomaly_summary.get('by_level') or {}).get('high', 0),
            'anomaly_count': anomaly_summary.get('anomaly_count', 0),
            'readiness_score': (operations_scorecard.get('summary') or {}).get('readiness_score'),
            'capability_available': capability_summary.get('available'),
            'capability_total': capability_summary.get('total'),
        },
        'kpis': kpis,
        'scorecard': operations_scorecard,
        'trend': operations.get('trend') or [],
        'top_lanes': top_lanes,
        'city_breakdown': city_breakdown,
        'cost_components': cost_components,
        'prediction': {
            'success': prediction.get('success', True),
            'provider_status': prediction.get('provider_status'),
            'fallback_reason': prediction.get('fallback_reason'),
            'forecast_status': prediction.get('forecast_status'),
            'model_family': prediction.get('model_family'),
            'model_stage': prediction.get('model_stage'),
            'time_granularity': prediction.get('time_granularity'),
            'series_summary': prediction.get('series_summary') or {},
            'forecast': prediction.get('forecast') or [],
            'predictions': forecast_points,
            'models': prediction_status.get('models') or [],
            'latest_jobs': prediction_status.get('latest_jobs') or [],
        },
        'anomaly': anomaly,
        'capabilities': capabilities,
        'recommendations': _enterprise_recommendations(operations, prediction, anomaly, capabilities),
        'truth_contract': {
            'business_mutation': 'none',
            'primary_source': 'shipment_facts',
            'cost_source': 'shipment_facts.freight',
            'prediction_boundary': 'time_series_baseline_online; deep models background/shadow until readiness passes',
            'rl_boundary': 'shadow_rerank_only; dispatch solver owns hard constraints',
        },
    }
    return jsonify(response)


@analytics_bp.route('/trend', methods=['GET'])
@jwt_required()
def get_trend():
    """
    获取趋势分析
    
    Query params:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        granularity: 粒度 (daily, weekly, monthly)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        granularity = request.args.get('granularity', 'daily')
        
        service = get_analytics_service()
        result = service.get_trend_analysis(start_date, end_date, granularity)
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取趋势分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/cost', methods=['GET'])
@jwt_required()
def get_cost_analysis():
    """
    获取成本分析
    
    Query params:
        period: 分析周期 (week, month, quarter, year)
    """
    try:
        period = request.args.get('period', 'month')
        
        service = get_analytics_service()
        result = service.get_cost_analysis(period)
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取成本分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/routes', methods=['GET'])
@jwt_required()
def get_route_performance():
    """获取路线性能分析"""
    try:
        service = get_analytics_service()
        result = service.get_route_performance()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取路线性能分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/vehicles', methods=['GET'])
@jwt_required()
def get_vehicle_performance():
    """获取车辆性能分析"""
    try:
        service = get_analytics_service()
        result = service.get_vehicle_performance()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取车辆性能分析失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/report', methods=['GET'])
@jwt_required()
def generate_report():
    """
    生成运营报表
    
    Query params:
        type: 报表类型 (daily, weekly, monthly)
        start_date: 开始日期
        end_date: 结束日期
    """
    try:
        report_type = request.args.get('type', 'daily')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        service = get_analytics_service()
        result = service.generate_report(report_type, start_date, end_date)
        return jsonify(result)
    except Exception as e:
        logger.error(f"生成报表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/predict', methods=['GET'])
@jwt_required()
def predict_demand():
    """
    预测需求
    
    Query params:
        days: 预测天数 (默认7天)
    """
    try:
        days = request.args.get('days', 7, type=int)
        days = min(max(days, 1), 30)  # 限制1-30天
        
        service = get_analytics_service()
        result = service.predict_demand(days)
        return jsonify(result)
    except Exception as e:
        logger.error(f"预测需求失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/export/excel', methods=['GET'])
@jwt_required()
def export_excel():
    """
    导出 Excel 报表
    
    Query params:
        type: 报表类型 (daily, weekly, monthly)
        start_date: 开始日期
        end_date: 结束日期
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        
        report_type = request.args.get('type', 'daily')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        service = get_analytics_service()
        report = service.generate_report(report_type, start_date, end_date)
        
        if not report.get('success'):
            return jsonify(report), 400
        
        # 创建 Excel 工作簿
        wb = Workbook()
        
        # 概览页
        ws_summary = wb.active
        ws_summary.title = '运营概览'
        
        # 标题样式
        title_font = Font(size=16, bold=True)
        header_font = Font(size=12, bold=True)
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        
        # 报表标题
        ws_summary['A1'] = f'物流系统运营报表 - {report_type}'
        ws_summary['A1'].font = title_font
        ws_summary.merge_cells('A1:D1')
        
        # 生成时间
        ws_summary['A2'] = f"生成时间: {report['report_info']['generated_at']}"
        
        # 关键指标
        metrics = report.get('summary', {})
        ws_summary['A4'] = '关键指标'
        ws_summary['A4'].font = header_font
        
        metric_names = {
            'total_orders': '总订单数',
            'completed_orders': '已完成订单',
            'pending_orders': '待处理订单',
            'total_revenue': '总收入(元)',
            'total_cost': '总成本(元)',
            'profit_margin': '利润率(%)',
            'vehicle_utilization': '车辆利用率(%)',
            'today_orders': '今日订单',
            'week_orders': '本周订单',
            'month_orders': '本月订单'
        }
        
        row = 5
        for key, label in metric_names.items():
            ws_summary[f'A{row}'] = label
            ws_summary[f'B{row}'] = metrics.get(key, 0)
            row += 1
        
        # 趋势数据页
        ws_trend = wb.create_sheet('趋势数据')
        trend_data = report.get('trend_analysis', {})
        
        ws_trend['A1'] = '趋势分析'
        ws_trend['A1'].font = header_font
        
        ws_trend['A3'] = '总订单'
        ws_trend['B3'] = trend_data.get('total_orders', 0)
        ws_trend['A4'] = '总收入'
        ws_trend['B4'] = trend_data.get('total_revenue', 0)
        ws_trend['A5'] = '总成本'
        ws_trend['B5'] = trend_data.get('total_cost', 0)
        ws_trend['A6'] = '总利润'
        ws_trend['B6'] = trend_data.get('total_profit', 0)
        
        # 成本分析页
        ws_cost = wb.create_sheet('成本分析')
        cost_data = report.get('cost_analysis', {})
        
        ws_cost['A1'] = '成本分析'
        ws_cost['A1'].font = header_font
        
        ws_cost['A3'] = '总成本'
        ws_cost['B3'] = cost_data.get('total_cost', 0)
        ws_cost['A4'] = '单均成本'
        ws_cost['B4'] = cost_data.get('avg_cost_per_order', 0)
        
        breakdown = cost_data.get('cost_breakdown', {})
        ws_cost['A6'] = '成本构成'
        ws_cost['A7'] = '燃油成本'
        ws_cost['B7'] = breakdown.get('fuel', 0)
        ws_cost['A8'] = '过路费'
        ws_cost['B8'] = breakdown.get('toll', 0)
        ws_cost['A9'] = '人工成本'
        ws_cost['B9'] = breakdown.get('labor', 0)
        
        # 优化建议页
        ws_reco = wb.create_sheet('优化建议')
        recommendations = report.get('recommendations', [])
        
        ws_reco['A1'] = '优化建议'
        ws_reco['A1'].font = header_font
        
        for i, rec in enumerate(recommendations, start=3):
            ws_reco[f'A{i}'] = rec
        
        # 调整列宽
        for ws in [ws_summary, ws_trend, ws_cost, ws_reco]:
            for col in range(1, 5):
                ws.column_dimensions[get_column_letter(col)].width = 20
        
        # 保存到内存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # 返回文件
        filename = f"logistics_report_{report_type}_{start_date or 'latest'}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except ImportError:
        return jsonify({
            'success': False, 
            'error': 'Excel 导出需要安装 openpyxl: pip install openpyxl'
        }), 500
    except Exception as e:
        logger.error(f"导出 Excel 失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/export/pdf', methods=['GET'])
@jwt_required()
def export_pdf():
    """
    导出 PDF 报表
    
    Query params:
        type: 报表类型 (daily, weekly, monthly)
        start_date: 开始日期
        end_date: 结束日期
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        
        report_type = request.args.get('type', 'daily')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        service = get_analytics_service()
        report = service.generate_report(report_type, start_date, end_date)
        
        if not report.get('success'):
            return jsonify(report), 400
        
        # 创建 PDF
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4, 
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14)
        
        elements = []
        
        # 标题
        elements.append(Paragraph(f'物流系统运营报表 - {report_type}', title_style))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(f"生成时间: {report['report_info']['generated_at']}", styles['Normal']))
        elements.append(Spacer(1, 1*cm))
        
        # 关键指标表格
        elements.append(Paragraph('关键指标', heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        metrics = report.get('summary', {})
        metric_names = {
            '总订单数': metrics.get('total_orders', 0),
            '已完成订单': metrics.get('completed_orders', 0),
            '待处理订单': metrics.get('pending_orders', 0),
            '总收入(元)': metrics.get('total_revenue', 0),
            '总成本(元)': metrics.get('total_cost', 0),
            '利润率(%)': metrics.get('profit_margin', 0)
        }
        
        table_data = [['指标', '数值']]
        for key, value in metric_names.items():
            table_data.append([key, str(value)])
        
        table = Table(table_data, colWidths=[8*cm, 6*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 1*cm))
        
        # 优化建议
        elements.append(Paragraph('优化建议', heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        recommendations = report.get('recommendations', [])
        for rec in recommendations:
            elements.append(Paragraph(f'• {rec}', styles['Normal']))
        
        # 生成 PDF
        doc.build(elements)
        output.seek(0)
        
        filename = f"logistics_report_{report_type}_{start_date or 'latest'}.pdf"
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'PDF 导出需要安装 reportlab: pip install reportlab'
        }), 500
    except Exception as e:
        logger.error(f"导出 PDF 失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
