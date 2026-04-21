"""
轻量级大数据服务 - 替代 Kafka/Spark/Flink
适用于 2GB 内存服务器

功能：
1. Redis Stream 替代 Kafka（消息队列）
2. Celery + Redis 替代 Spark（任务队列）
3. 异步任务替代 Flink（实时处理）
"""

import redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
import numpy as np

# Redis 连接
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


class LightweightMessageQueue:
    """
    轻量级消息队列 - Redis Stream 替代 Kafka
    """
    
    def __init__(self, stream_name: str):
        self.stream_name = stream_name
        self.consumer_group = f"{stream_name}_group"
        
        # 创建消费者组（如果不存在）
        try:
            redis_client.xgroup_create(
                self.stream_name, 
                self.consumer_group, 
                id='0', 
                mkstream=True
            )
        except redis.exceptions.ResponseError:
            pass  # 组已存在
    
    def produce(self, message: Dict[str, Any]) -> str:
        """
        生产消息（类似 Kafka Producer）
        """
        message['timestamp'] = datetime.now().isoformat()
        message_id = redis_client.xadd(self.stream_name, message)
        return message_id
    
    def consume(self, count: int = 10, block: int = 1000) -> List[Dict]:
        """
        消费消息（类似 Kafka Consumer）
        """
        messages = redis_client.xreadgroup(
            groupname=self.consumer_group,
            consumername='consumer_1',
            streams={self.stream_name: '>'},
            count=count,
            block=block
        )
        
        result = []
        for stream_name, stream_messages in messages or []:
            for message_id, message_data in stream_messages:
                result.append({
                    'id': message_id,
                    'data': message_data
                })
                # 确认消息
                redis_client.xack(self.stream_name, self.consumer_group, message_id)
        
        return result
    
    def get_stats(self) -> Dict:
        """
        获取队列统计信息
        """
        info = redis_client.xinfo_stream(self.stream_name)
        return {
            'length': info['length'],
            'first_entry': info.get('first_entry', [None, None]),
            'last_entry': info.get('last_entry', [None, None]),
            'groups': len(info.get('groups', []))
        }


class LightweightStreamProcessor:
    """
    轻量级流处理器 - 替代 Flink
    """
    
    def __init__(self):
        self.order_stream = LightweightMessageQueue('orders_stream')
        self.tracking_stream = LightweightMessageQueue('tracking_stream')
        self.alerts_stream = LightweightMessageQueue('alerts_stream')
    
    async def process_orders_realtime(self):
        """
        实时处理订单流
        """
        while True:
            orders = self.order_stream.consume(count=10, block=100)
            
            for order in orders:
                # 实时分析
                analysis_result = await self._analyze_order(order['data'])
                
                # 如果检测到异常，发送告警
                if analysis_result.get('is_abnormal'):
                    self.alerts_stream.produce({
                        'type': 'order_anomaly',
                        'order_id': order['data'].get('order_id'),
                        'reason': analysis_result.get('reason'),
                        'timestamp': datetime.now().isoformat()
                    })
            
            await asyncio.sleep(0.1)
    
    async def _analyze_order(self, order_data: Dict) -> Dict:
        """
        分析订单（模拟 Flink 实时分析）
        """
        # 模拟异常检测
        is_abnormal = random.random() < 0.05  # 5% 概率异常
        
        return {
            'is_abnormal': is_abnormal,
            'reason': '订单金额异常' if is_abnormal else None,
            'processed_at': datetime.now().isoformat()
        }
    
    async def process_tracking_realtime(self):
        """
        实时处理轨迹流
        """
        while True:
            tracks = self.tracking_stream.consume(count=10, block=100)
            
            for track in tracks:
                # 实时 ETA 计算
                eta = await self._calculate_eta(track['data'])
                
                # 更新 Redis 缓存
                redis_client.setex(
                    f"eta:{track['data'].get('vehicle_id')}",
                    300,  # 5分钟过期
                    json.dumps(eta)
                )
            
            await asyncio.sleep(0.1)
    
    async def _calculate_eta(self, track_data: Dict) -> Dict:
        """
        计算 ETA（模拟 Flink 实时计算）
        """
        # 模拟 ETA 计算
        base_eta = random.randint(10, 60)  # 10-60分钟
        
        return {
            'vehicle_id': track_data.get('vehicle_id'),
            'eta_minutes': base_eta,
            'distance_km': round(base_eta * 0.5, 1),
            'calculated_at': datetime.now().isoformat()
        }


class LightweightBatchProcessor:
    """
    轻量级批处理器 - 替代 Spark
    """
    
    @staticmethod
    def analyze_delivery_history(days: int = 30) -> Dict:
        """
        分析历史配送数据（模拟 Spark 离线分析）
        """
        # 生成模拟数据
        np.random.seed(42)
        
        # 每日订单量
        daily_orders = np.random.poisson(1000, days)
        
        # 平均配送时长
        avg_delivery_time = np.random.normal(35, 10, days)
        
        # 区域分布
        regions = ['北京', '上海', '广州', '深圳', '杭州']
        region_distribution = np.random.dirichlet(np.ones(5), days)
        
        return {
            'period': f'最近{days}天',
            'total_orders': int(daily_orders.sum()),
            'avg_daily_orders': float(daily_orders.mean()),
            'avg_delivery_time': float(avg_delivery_time.mean()),
            'region_stats': {
                regions[i]: float(region_distribution[:, i].mean() * 100)
                for i in range(len(regions))
            },
            'trend': {
                'orders_trend': '上升' if daily_orders[-7:].mean() > daily_orders[:7].mean() else '下降',
                'time_trend': '改善' if avg_delivery_time[-7:].mean() < avg_delivery_time[:7].mean() else '恶化'
            },
            'analyzed_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def predict_demand(days: int = 7) -> Dict:
        """
        需求预测（模拟 Spark ML 模型）
        """
        # 生成预测数据
        np.random.seed(42)
        
        predictions = []
        base_demand = 1000
        
        for i in range(days):
            # 添加趋势和季节性
            trend = i * 10
            seasonal = np.sin(i * 2 * np.pi / 7) * 100
            noise = np.random.normal(0, 50)
            
            predicted_demand = int(base_demand + trend + seasonal + noise)
            confidence = 0.85 + np.random.uniform(0, 0.1)
            
            predictions.append({
                'date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
                'predicted_orders': max(0, predicted_demand),
                'confidence': round(confidence, 2)
            })
        
        return {
            'prediction_period': f'{days}天',
            'predictions': predictions,
            'model_accuracy': 0.87,
            'predicted_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def generate_heatmap_data() -> Dict:
        """
        生成热力图数据
        """
        # 模拟全国配送热度
        cities = [
            {'name': '北京', 'lat': 39.9, 'lng': 116.4, 'intensity': random.randint(800, 1200)},
            {'name': '上海', 'lat': 31.2, 'lng': 121.5, 'intensity': random.randint(900, 1300)},
            {'name': '广州', 'lat': 23.1, 'lng': 113.3, 'intensity': random.randint(700, 1100)},
            {'name': '深圳', 'lat': 22.5, 'lng': 114.1, 'intensity': random.randint(750, 1150)},
            {'name': '杭州', 'lat': 30.3, 'lng': 120.2, 'intensity': random.randint(600, 1000)},
            {'name': '成都', 'lat': 30.7, 'lng': 104.1, 'intensity': random.randint(500, 900)},
            {'name': '武汉', 'lat': 30.6, 'lng': 114.3, 'intensity': random.randint(550, 950)},
            {'name': '西安', 'lat': 34.3, 'lng': 109.0, 'intensity': random.randint(400, 800)},
            {'name': '南京', 'lat': 32.1, 'lng': 118.8, 'intensity': random.randint(500, 900)},
            {'name': '重庆', 'lat': 29.6, 'lng': 106.5, 'intensity': random.randint(450, 850)},
        ]
        
        return {
            'cities': cities,
            'max_intensity': max(c['intensity'] for c in cities),
            'generated_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def detect_anomalies() -> Dict:
        """
        异常检测（模拟 Flink 实时检测）
        """
        # 模拟异常数据
        anomalies = []
        
        if random.random() < 0.3:  # 30% 概率有异常
            anomaly_types = ['配送超时', '路径异常', '车辆故障', '订单取消率过高']
            for _ in range(random.randint(1, 3)):
                anomalies.append({
                    'type': random.choice(anomaly_types),
                    'severity': random.choice(['low', 'medium', 'high']),
                    'location': random.choice(['北京', '上海', '广州', '深圳']),
                    'detected_at': datetime.now().isoformat()
                })
        
        return {
            'has_anomaly': len(anomalies) > 0,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies,
            'checked_at': datetime.now().isoformat()
        }


class BigDataSimulator:
    """
    大数据模拟器 - 生成真实感的数据
    """
    
    @staticmethod
    def simulate_kafka_metrics() -> Dict:
        """
        模拟 Kafka 指标
        """
        return {
            'topics': [
                {'name': 'logistics.orders', 'partitions': 3, 'messages_per_sec': random.randint(100, 500)},
                {'name': 'logistics.tracking', 'partitions': 3, 'messages_per_sec': random.randint(50, 200)},
                {'name': 'logistics.alerts', 'partitions': 2, 'messages_per_sec': random.randint(10, 50)},
            ],
            'total_throughput': random.randint(80000, 120000),  # 消息/秒
            'consumer_lag': random.randint(0, 100),
            'brokers': 3,
            'status': 'healthy'
        }
    
    @staticmethod
    def simulate_spark_jobs() -> Dict:
        """
        模拟 Spark 作业
        """
        return {
            'active_jobs': [
                {
                    'id': 'job_001',
                    'name': '配送数据分析',
                    'status': 'running',
                    'progress': random.randint(30, 90),
                    'duration': f'{random.randint(1, 10)}分钟'
                },
                {
                    'id': 'job_002',
                    'name': '需求预测模型训练',
                    'status': 'completed',
                    'progress': 100,
                    'duration': f'{random.randint(5, 20)}分钟'
                }
            ],
            'completed_today': random.randint(10, 30),
            'avg_job_duration': f'{random.randint(3, 15)}分钟'
        }
    
    @staticmethod
    def simulate_flink_jobs() -> Dict:
        """
        模拟 Flink 作业
        """
        return {
            'running_jobs': [
                {
                    'name': '实时订单流处理',
                    'status': 'RUNNING',
                    'uptime': f'{random.randint(1, 24)}小时',
                    'records_in': random.randint(10000, 100000),
                    'records_out': random.randint(9000, 90000)
                },
                {
                    'name': '实时异常检测',
                    'status': 'RUNNING',
                    'uptime': f'{random.randint(1, 24)}小时',
                    'records_in': random.randint(5000, 50000),
                    'records_out': random.randint(4000, 45000)
                }
            ],
            'latency_ms': random.randint(10, 100),
            'throughput': f'{random.randint(50000, 150000)}条/秒'
        }
    
    @staticmethod
    def get_realtime_dashboard_data() -> Dict:
        """
        获取实时大屏数据（模拟大数据分析结果）
        """
        return {
            'kafka': BigDataSimulator.simulate_kafka_metrics(),
            'spark': BigDataSimulator.simulate_spark_jobs(),
            'flink': BigDataSimulator.simulate_flink_jobs(),
            'delivery_analysis': LightweightBatchProcessor.analyze_delivery_history(),
            'demand_prediction': LightweightBatchProcessor.predict_demand(),
            'heatmap': LightweightBatchProcessor.generate_heatmap_data(),
            'anomalies': LightweightBatchProcessor.detect_anomalies(),
            'updated_at': datetime.now().isoformat()
        }


# API 接口函数
def get_bigdata_overview():
    """获取大数据概览"""
    return BigDataSimulator.get_realtime_dashboard_data()


def get_stream_stats():
    """获取流处理统计"""
    mq = LightweightMessageQueue('orders_stream')
    return mq.get_stats()


def produce_test_message():
    """发送测试消息"""
    mq = LightweightMessageQueue('orders_stream')
    message_id = mq.produce({
        'order_id': f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'customer': '测试客户',
        'amount': round(random.uniform(50, 500), 2)
    })
    return {'message_id': message_id, 'status': 'sent'}


if __name__ == '__main__':
    # 测试
    print("=== 大数据模拟器测试 ===")
    print(json.dumps(get_bigdata_overview(), indent=2, ensure_ascii=False))
