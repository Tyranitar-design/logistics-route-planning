#!/usr/bin/env python3
"""
物流订单实时流处理 - PyFlink 版本
持续运行的 Flink 作业，从 Kafka 读取订单数据并实时统计
"""
import json
from datetime import datetime
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import KeyedProcessFunction
from pyflink.common.typeinfo import Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink, KafkaRecordSerializationSchema
from pyflink.datastream.connectors.kafka import KafkaOffsetsInitializer, DeliveryGuarantee


def create_kafka_source():
    """创建 Kafka 数据源"""
    return (
        KafkaSource.builder()
        .set_bootstrap_servers("localhost:9092")
        .set_topics("logistics.orders")
        .set_group_id("flink-order-stats")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )


def create_kafka_sink(topic: str):
    """创建 Kafka 输出"""
    return (
        KafkaSink.builder()
        .set_bootstrap_servers("localhost:9092")
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(topic)
            .set_value_serialization_string(SimpleStringSchema())
            .build()
        )
        .set_delivery_guarantee(DeliveryGuarantee.AT_LEAST_ONCE)
        .build()
    )


def parse_order(json_str: str):
    """解析订单 JSON"""
    try:
        data = json.loads(json_str)
        return (
            data.get('order_id', 'unknown'),
            data.get('event_type', 'unknown'),
            float(data.get('cost', 0)),
            data.get('status', 'unknown'),
        )
    except:
        return ('unknown', 'unknown', 0.0, 'unknown')


def main():
    """主函数 - Flink 流处理作业"""
    print("=" * 60)
    print("   物流订单实时流处理作业 - PyFlink")
    print("=" * 60)
    
    # 创建流处理环境
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    
    # 添加 Kafka connector JAR
    import os
    jar_path = r"D:\物流路径规划系统项目\flink\lib\flink-sql-connector-kafka.jar"
    if os.path.exists(jar_path):
        env.add_jars(f"file://{jar_path}")
        print(f"[OK] 已加载 Kafka connector: {jar_path}")
    
    # 启用 checkpoint（每 60 秒一次）
    env.enable_checkpointing(60000)
    
    print("[1/4] 创建 Kafka 数据源...")
    # 从 Kafka 读取订单数据
    kafka_source = create_kafka_source()
    order_stream = env.from_source(
        kafka_source,
        KafkaOffsetsInitializer.latest(),
        "kafka-orders-source"
    )
    
    print("[2/4] 处理订单流...")
    # 解析 JSON 并过滤有效订单
    parsed_stream = order_stream.map(
        parse_order,
        output_type=Types.TUPLE([Types.STRING(), Types.STRING(), Types.FLOAT(), Types.STRING()])
    ).filter(lambda x: x[0] != 'unknown')
    
    print("[3/4] 实时统计...")
    # 实时统计：每收到订单就输出统计信息
    def stats_mapper(order_tuple):
        order_id, event_type, cost, status = order_tuple
        stats = {
            'timestamp': datetime.now().isoformat(),
            'order_id': order_id,
            'event_type': event_type,
            'cost': cost,
            'status': status,
            'processed_by': 'pyflink-worker'
        }
        return json.dumps(stats, ensure_ascii=False)
    
    stats_stream = parsed_stream.map(stats_mapper)
    
    print("[4/4] 输出到 Kafka...")
    # 输出到 Kafka
    kafka_sink = create_kafka_sink("logistics.order.stats")
    stats_stream.sink_to(kafka_sink)
    
    # 同时打印到控制台（用于调试）
    stats_stream.print()
    
    print("\n[OK] 作业已提交，开始实时处理...")
    print("     输入: logistics.orders")
    print("     输出: logistics.order.stats")
    print("     按 Ctrl+C 停止\n")
    
    # 执行作业
    env.execute("Logistics Order Stream Processor")


if __name__ == "__main__":
    main()
