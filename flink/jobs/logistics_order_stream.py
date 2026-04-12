"""
物流订单实时流处理作业
Kafka -> Flink -> Elasticsearch / ClickHouse

功能：
1. 实时订单统计（每5分钟）
2. 异常订单检测（金额过大）
3. 热门路线实时分析
4. 车辆状态监控
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

# PyFlink imports
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction, FilterFunction, KeyedProcessFunction
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink, KafkaRecordSerializationSchema
from pyflink.datastream.connectors.elasticsearch import ElasticsearchSink
from pyflink.common import Types, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema, JsonRowSerializationSchema
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.table import StreamTableEnvironment

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderParser(MapFunction):
    """解析订单 JSON 数据"""

    def map(self, value: str) -> Dict[str, Any]:
        try:
            order = json.loads(value)
            return {
                'order_id': order.get('id'),
                'order_number': order.get('order_number'),
                'status': order.get('status'),
                'cost': float(order.get('cost', 0)),
                'pickup_node_id': order.get('pickup_node_id'),
                'delivery_node_id': order.get('delivery_node_id'),
                'vehicle_id': order.get('vehicle_id'),
                'created_at': order.get('created_at'),
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Failed to parse order: {e}")
            return None


class HighValueOrderFilter(FilterFunction):
    """过滤高价值订单（金额 > 10000）"""

    def filter(self, value: Dict[str, Any]) -> bool:
        return value is not None and value.get('cost', 0) > 10000


class OrderAlertFunction(KeyedProcessFunction):
    """订单异常检测：检测连续高价值订单"""

    def __init__(self):
        self.count_state = None
        self.last_amount_state = None

    def open(self, runtime_context):
        # 状态：连续高价值订单计数
        self.count_state = runtime_context.get_state(
            ValueStateDescriptor("high_value_count", Types.INT())
        )
        # 状态：上次订单金额
        self.last_amount_state = runtime_context.get_state(
            ValueStateDescriptor("last_amount", Types.FLOAT())
        )

    def process_element(self, value: Dict[str, Any], ctx):
        count = self.count_state.value() or 0
        last_amount = self.last_amount_state.value() or 0
        current_amount = value.get('cost', 0)

        # 检测金额突增（超过上次 2 倍）
        if last_amount > 0 and current_amount > last_amount * 2:
            alert = {
                'type': 'AMOUNT_SPIKE',
                'order_id': value.get('order_id'),
                'previous_amount': last_amount,
                'current_amount': current_amount,
                'timestamp': datetime.now().isoformat()
            }
            yield json.dumps(alert)

        # 更新状态
        self.count_state.update(count + 1)
        self.last_amount_state.update(current_amount)


def create_kafka_source(env: StreamExecutionEnvironment, bootstrap_servers: str, topic: str):
    """创建 Kafka 数据源"""
    kafka_source = (
        KafkaSource.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_topics(topic)
        .set_group_id("logistics-flink-consumer")
        .set_starting_offsets("latest")
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )
    return kafka_source


def create_elasticsearch_sink(es_host: str, es_port: int, index_name: str):
    """创建 Elasticsearch Sink"""
    # 注意：实际使用需要配置 Elasticsearch connector
    pass


def main():
    """主函数"""
    # 创建执行环境
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)

    # 启用 Checkpoint（每60秒）
    env.enable_checkpointing(60000)

    # 创建 Table 环境
    table_env = StreamTableEnvironment.create(env)

    # Kafka 配置
    KAFKA_BOOTSTRAP = "kafka:9092"
    ORDER_TOPIC = "logistics.orders"
    VEHICLE_TOPIC = "logistics.vehicles"
    TRACKING_TOPIC = "logistics.tracking"
    ALERT_TOPIC = "logistics.alerts"

    # Elasticsearch 配置
    ES_HOST = "elasticsearch"
    ES_PORT = 9200

    # ClickHouse 配置
    CH_HOST = "clickhouse"
    CH_PORT = 9000

    logger.info("Starting Logistics Flink Job...")

    # 1. 创建 Kafka Source
    kafka_source = create_kafka_source(env, KAFKA_BOOTSTRAP, ORDER_TOPIC)

    # 2. 读取订单流
    orders_stream = (
        env.from_source(
            kafka_source,
            WatermarkStrategy.no_watermarks(),
            "Kafka Orders"
        )
        .map(OrderParser())
        .filter(lambda x: x is not None)
    )

    # 3. 高价值订单检测
    high_value_orders = orders_stream.filter(HighValueOrderFilter())

    # 4. 订单异常检测
    alerts_stream = (
        orders_stream
        .key_by(lambda x: x.get('vehicle_id', 'unknown'))
        .process(OrderAlertFunction())
    )

    # 5. 打印结果（测试用）
    high_value_orders.print("高价值订单: ")
    alerts_stream.print("异常告警: ")

    # 6. 执行作业
    env.execute("Logistics Order Stream Processing")


if __name__ == "__main__":
    main()
