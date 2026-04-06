"""
Elasticsearch 搜索 API
提供订单全文搜索功能
"""
from flask import Blueprint, request, jsonify
import requests
import json

es_bp = Blueprint('es_search', __name__)

# Elasticsearch 配置
ES_HOST = 'http://localhost:9200'
ES_INDEX = 'logistics-orders'


@es_bp.route('/search', methods=['GET'])
def search_orders():
    """
    全文搜索订单
    参数: q - 搜索关键词
    """
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 20))
    
    if not query:
        return jsonify({'success': False, 'error': '请输入搜索关键词'}), 400
    
    try:
        # Elasticsearch 查询
        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["order_id", "customer_name", "origin_city", "destination_city", "cargo_type"],
                    "fuzziness": "AUTO"
                }
            },
            "from": (page - 1) * size,
            "size": size,
            "highlight": {
                "fields": {
                    "order_id": {},
                    "customer_name": {},
                    "origin_city": {},
                    "destination_city": {}
                }
            }
        }
        
        # 发送请求到 ES
        response = requests.post(
            f'{ES_HOST}/{ES_INDEX}/_search',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(es_query),
            timeout=10
        )
        
        if response.status_code != 200:
            # 如果 ES 不可用，返回模拟数据
            return mock_search(query, page, size)
        
        result = response.json()
        
        # 解析结果
        hits = result.get('hits', {})
        total = hits.get('total', {}).get('value', 0)
        
        orders = []
        for hit in hits.get('hits', []):
            source = hit.get('_source', {})
            highlight = hit.get('highlight', {})
            
            order = {
                'order_id': source.get('order_id'),
                'customer_name': source.get('customer_name'),
                'origin_city': source.get('origin_city'),
                'destination_city': source.get('destination_city'),
                'cargo_type': source.get('cargo_type'),
                'weight': source.get('weight'),
                'status': source.get('status'),
                'created_at': source.get('created_at'),
                'highlight': highlight
            }
            orders.append(order)
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'size': size,
                'orders': orders
            }
        })
        
    except requests.exceptions.ConnectionError:
        # ES 不可用时返回模拟数据
        return mock_search(query, page, size)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def mock_search(query, page, size):
    """模拟搜索数据（ES 不可用时使用）"""
    # 从数据库获取真实数据
    from app import db
    from sqlalchemy import text
    
    try:
        sql = text("""
            SELECT 
                o.order_id,
                o.customer_name,
                n1.name as origin_city,
                n2.name as destination_city,
                o.cargo_type,
                o.weight,
                o.status,
                o.created_at
            FROM orders o
            LEFT JOIN nodes n1 ON o.origin_id = n1.id
            LEFT JOIN nodes n2 ON o.destination_id = n2.id
            WHERE 
                o.order_id LIKE :q OR
                o.customer_name LIKE :q OR
                n1.name LIKE :q OR
                n2.name LIKE :q OR
                o.cargo_type LIKE :q
            ORDER BY o.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        count_sql = text("""
            SELECT COUNT(*) FROM orders o
            LEFT JOIN nodes n1 ON o.origin_id = n1.id
            LEFT JOIN nodes n2 ON o.destination_id = n2.id
            WHERE 
                o.order_id LIKE :q OR
                o.customer_name LIKE :q OR
                n1.name LIKE :q OR
                n2.name LIKE :q OR
                o.cargo_type LIKE :q
        """)
        
        search_pattern = f'%{query}%'
        offset = (page - 1) * size
        
        orders = db.session.execute(sql, {
            'q': search_pattern,
            'limit': size,
            'offset': offset
        }).fetchall()
        
        total = db.session.execute(count_sql, {'q': search_pattern}).scalar()
        
        result = []
        for order in orders:
            result.append({
                'order_id': order[0],
                'customer_name': order[1],
                'origin_city': order[2],
                'destination_city': order[3],
                'cargo_type': order[4],
                'weight': float(order[5]) if order[5] else 0,
                'status': order[6],
                'created_at': str(order[7]) if order[7] else None,
                'source': 'database'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'size': size,
                'orders': result,
                'source': 'database (ES unavailable)'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@es_bp.route('/suggestions', methods=['GET'])
def get_suggestions():
    """获取搜索建议（自动补全）"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    try:
        # ES 自动补全查询
        es_query = {
            "query": {
                "bool": {
                    "should": [
                        {"prefix": {"order_id": query}},
                        {"prefix": {"customer_name": query}},
                        {"prefix": {"origin_city": query}},
                        {"prefix": {"destination_city": query}}
                    ]
                }
            },
            "size": 5
        }
        
        response = requests.post(
            f'{ES_HOST}/{ES_INDEX}/_search',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(es_query),
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            suggestions = []
            seen = set()
            
            for hit in result.get('hits', {}).get('hits', []):
                source = hit.get('_source', {})
                for field in ['order_id', 'customer_name', 'origin_city', 'destination_city']:
                    value = source.get(field)
                    if value and value not in seen:
                        suggestions.append({
                            'text': value,
                            'field': field
                        })
                        seen.add(value)
            
            return jsonify({'success': True, 'suggestions': suggestions[:10]})
        else:
            return jsonify({'success': True, 'suggestions': []})
            
    except:
        return jsonify({'success': True, 'suggestions': []})


@es_bp.route('/aggregation', methods=['GET'])
def get_aggregation():
    """获取聚合统计数据"""
    try:
        es_query = {
            "size": 0,
            "aggs": {
                "by_origin": {
                    "terms": {"field": "origin_city.keyword", "size": 10}
                },
                "by_destination": {
                    "terms": {"field": "destination_city.keyword", "size": 10}
                },
                "by_cargo_type": {
                    "terms": {"field": "cargo_type.keyword", "size": 10}
                },
                "by_status": {
                    "terms": {"field": "status.keyword", "size": 10}
                }
            }
        }
        
        response = requests.post(
            f'{ES_HOST}/{ES_INDEX}/_search',
            headers={'Content-Type': 'application/json'},
            data=json.dumps(es_query),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            aggs = result.get('aggregations', {})
            
            return jsonify({
                'success': True,
                'data': {
                    'by_origin': aggs.get('by_origin', {}).get('buckets', []),
                    'by_destination': aggs.get('by_destination', {}).get('buckets', []),
                    'by_cargo_type': aggs.get('by_cargo_type', {}).get('buckets', []),
                    'by_status': aggs.get('by_status', {}).get('buckets', [])
                }
            })
        else:
            return jsonify({'success': True, 'data': {}})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
