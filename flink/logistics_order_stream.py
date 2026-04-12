#!/usr/bin/env python3
"""
物流订单实时流处理 - Flink Job
=====================================
从 Kafka 读取订单事件，实时处理并写入 ES/ClickHouse

功能：
1. 实时订单统计（每5分钟窗口）
2. 异常订单检测（金额突增、超时预警）
3. 热门路线分析（滑动窗口 TopN）
4. 写入 Elasticsearch 供搜索
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Tuple

# PyFlink imports
from pyflink.common import Configuration, WatermarkStrategy, Duration
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.datastream.connectors.elasticsearch import Elasticsearch7SinkBuilder
from pyflink.datastream.functions import MapFunction, ProcessWindowFunction, KeyedProcessFunction
from pyflink.datastream.window import TumblingEventTimeWindows, SlidingEventTimeWindows, Time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# 数据解析函数
# ============================================

class OrderParser(MapFunction):
    """解析 Kafka 中的订单 JSON 数据"""
    
    def map(self, value: str) -> Dict[str, Any]:
        try:
            order = json.loads(value)
            return {
                'order_id': order.get('id') or order.get('order_id'),
                'order_number': order.get('order_number'),
                'status': order.get('status', 'pending'),
                'cost': float(order.get('cost', 0)),
                'pickup_node_id': order.get('pickup_node_id'),
                'delivery_node_id': order.get('delivery_node_id'),
                'created_at': order.get('created_at'),
                'customer_name': order.get('customer_name', ''),
                'vehicle_id': order.get('vehicle_id'),
                'event_time': order.get('event_time') or order.get('created_at') or datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"解析订单失败: {e}, 原始数据: {value[:100]}")
            return {
                'order_id': None,
                'error': str(e)
            }


# ============================================
# 窗口统计函数
# ============================================

class OrderStatsFunction(ProcessWindowFunction):
    """窗口内订单统计"""
    
    def process(self, key, context, elements):
        # 统计窗口内的订单
        total_orders = 0
        total_cost = 0.0
        statuses = {}
        
        for order in elements:
            if order.get('order_id'):
                total_orders += 1
                total_cost += order.get('cost', 0)
                status = order.get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
        
        window_end = context.window().max_timestamp()
        
        return [{
            'window_end': window_end,
            'key': key,
            'total_orders': total_orders,
            'total_cost': round(total_cost, 2),
            'avg_cost': round(total_cost / total_orders, 2) if total_orders > 0 else 0,
            'status_distribution': statuses,
            'processed_at': datetime.now().isoformat()
        }]


# ============================================
# 异常检测函数
# ============================================

class AnomalyDetector(KeyedProcessFunction):
    """检测异常订单（金额突增、频繁变更等）"""
    
    def __init__(self):
        self.last_cost_state = None
        self.order_count_state = None
    
    def open(self, runtime_context):
        # 状态：最近订单金额
        from pyflink.datastream.state import ValueStateDescriptor
        self.last_cost_state = runtime_context.get_state(
            ValueStateDescriptor("last_cost", Types.FLOAT())
        )
        self.order_count_state = runtime_context.get_state(
            ValueStateDescriptor("order_count", Types.INT())
        )
    
    def process_element(self, value, ctx):
        alerts = []
        
        if not value.get('order_id'):
            return
        
        current_cost = float(value.get('cost', 0))
        last_cost = self.last_cost_state.value() or 0
        order_count = self.order_count_state.value() or 0
        
        # 检测1：金额突增（超过2倍）
        if last_cost > 0 and current_cost > last_cost * 2:
            alerts.append({
                'type': 'COST_SPIKE',
                'order_id': value['order_id'],
                'message': f"订单金额突增: {last_cost:.2f} → {current_cost:.2f}",
                'severity': 'HIGH',
                'timestamp': datetime.now().isoformat()
            })
        
        # 检测2：超大金额订单（超过10000）
        if current_cost > 10000:
            alerts.append({
                'type': 'HIGH_VALUE',
                'order_id': value['order_id'],
                'message': f"高价值订单: ¥{current_cost:.2f}",
                'severity': 'MEDIUM',
                'timestamp': datetime.now().isoformat()
            })
        
        # 更新状态
        self.last_cost_state.update(current_cost)
        self.order_count_state.update(order_count + 1)
        
        # 发送告警
        for alert in alerts:
            yield json.dumps(alert, ensure_ascii=False)


# ============================================
# 主作业
# ============================================

def create_kafka_source(bootstrap_servers: str = "kafka:9092", topic: str = "logistics.orders"):
    """创建 Kafka Source"""
    return (
        KafkaSource.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_topics(topic)
        .set_group_id("flink-logistics-processor")
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )


def create_es_sink(es_hosts: list = ["http://elasticsearch:9200"]):
    """创建 Elasticsearch Sink"""
    # ES Sink 需要 elasticsearch connector JAR
    from pyflink.datastream.connectors.elasticsearch import Elasticsearch7SinkBuilder
    
    return (
        Elasticsearch7SinkBuilder()
        .set_hosts(es_hosts)
        .set_emitter(lambda element, ctx: {
            "index": "logistics-orders-realtime",
            "id": element.get('order_id', ''),
            "source": element
        })
        .build()
    )


def main():
    # ============================================
    # 1. 创建执行环境
    # ============================================
    env = StreamExecutionEnvironment.get_execution_environment()
    
    # 配置 Checkpoint（Exactly-Once）
    env.enable_checkpointing(60000)  # 每60秒
    env.get_checkpoint_config().set_checkpointing_mode("EXACTLY_ONCE")
    env.get_checkpoint_config().set_min_pause_between_checkpoints(30000)
    env.get_checkpoint_config().set_checkpoint_timeout(600000)
    
    # 并行度
    env.set_parallelism(1)
    
    logger.info("Flink 执行环境已配置")
    
    # ============================================
    # 2. 从 Kafka 读取订单流
    # ============================================
    kafka_source = create_kafka_source(
        bootstrap_servers="logistics-kafka:9092",
        topic="logistics.orders"
    )
    
    orders_stream = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(),  # 使用处理时间
        "Kafka Orders Source"
    )
    
    logger.info("Kafka Source 已创建")
    
    # ============================================
    # 3. 解析订单数据
    # ============================================
    parsed_orders = orders_stream.map(
        OrderParser(),
        output_type=Types.MAP(Types.STRING(), Types.STRING())
    )
    
    # 过滤无效数据
    valid_orders = parsed_orders.filter(
        lambda order: order.get('order_id') is not None
    )
    
    logger.info("订单数据解析器已配置")
    
    # ============================================
    # 4. 实时统计（5分钟滚动窗口）
    # ============================================
    # 按状态分组统计
    order_stats = (
        valid_orders
        .key_by(lambda order: order.get('status', 'unknown'))
        .window(TumblingEventTimeWindows.of(Time.minutes(5)))
        .process(OrderStatsFunction(), Types.MAP(Types.STRING(), Types.STRING()))
    )
    
    # 输出统计结果
    order_stats.print("📊 订单统计")
    
    logger.info("窗口统计已配置")
    
    # ============================================
    # 5. 异常检测
    # ============================================
    # 按订单ID分组，检测异常
    alerts = (
        valid_orders
        .key_by(lambda order: order.get('order_id', 'unknown'))
        .process(AnomalyDetector(), Types.STRING())
    )
    
    # 输出告警
    alerts.print("⚠️ 告警")
    
    logger.info("异常检测已配置")
    
    # ============================================
    # 6. 热门路线分析（滑动窗口：每1分钟统计最近5分钟）
    # ============================================
    def extract_route(order):
        pickup = order.get('pickup_node_id', 'unknown')
        delivery = order.get('delivery_node_id', 'unknown')
        return f"{pickup}->{delivery}"
    
    route_stats = (
        valid_orders
        .key_by(extract_route)
        .window(SlidingEventTimeWindows.of(Time.minutes(5), Time.minutes(1)))
        .process(OrderStatsFunction(), Types.MAP(Types.STRING(), Types.STRING()))
    )
    
    route_stats.print("🛣️ 路线统计")
    
    logger.info("热门路线分析已配置")
    
    # ============================================
    # 7. 执行作业
    # ============================================
    logger.info("🚀 启动 Flink 作业: logistics-order-stream")
    env.execute("logistics-order-stream")


if __name__ == "__main__":
    main()
