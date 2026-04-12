#!/usr/bin/env python3
"""
物流订单实时流处理 - PyFlink Table API 版本
使用 Table API 和 SQL 进行流处理
"""
import os
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.datastream import StreamExecutionEnvironment


def main():
    """主函数 - Flink SQL 流处理作业"""
    print("=" * 60)
    print("   物流订单实时流处理作业 - PyFlink Table API")
    print("=" * 60)
    
    # 创建流处理环境
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.enable_checkpointing(60000)
    
    # 创建 Table 环境
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, settings)
    
    # 添加 Kafka connector JAR
    jar_path = r"D:\物流路径规划系统项目\flink\lib\flink-sql-connector-kafka.jar"
    if os.path.exists(jar_path):
        t_env.get_config().set("pipeline.jars", f"file://{jar_path}")
        print(f"[OK] 已加载 Kafka connector")
    
    # 创建 Kafka 源表
    print("[1/3] 创建 Kafka 源表...")
    t_env.execute_sql("""
        CREATE TABLE kafka_orders (
            order_id STRING,
            event_type STRING,
            cost DOUBLE,
            status STRING,
            `timestamp` STRING
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'logistics.orders',
            'properties.bootstrap.servers' = 'localhost:9092',
            'properties.group.id' = 'flink-order-processor',
            'scan.startup.mode' = 'latest-offset',
            'format' = 'json'
        )
    """)
    
    # 创建 Kafka 输出表
    print("[2/3] 创建 Kafka 输出表...")
    t_env.execute_sql("""
        CREATE TABLE kafka_order_stats (
            order_id STRING,
            event_type STRING,
            cost DOUBLE,
            status STRING,
            processed_at STRING
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'logistics.order.stats',
            'properties.bootstrap.servers' = 'localhost:9092',
            'format' = 'json'
        )
    """)
    
    # 执行流处理 - 从源表读取，处理后写入输出表
    print("[3/3] 启动流处理...")
    
    # 方式1：简单转发 + 添加处理时间
    result = t_env.execute_sql("""
        INSERT INTO kafka_order_stats
        SELECT 
            order_id,
            event_type,
            cost,
            status,
            CURRENT_TIMESTAMP as processed_at
        FROM kafka_orders
        WHERE order_id IS NOT NULL
    """)
    
    print("\n[OK] 流处理作业已启动!")
    print("     输入: logistics.orders")
    print("     输出: logistics.order.stats")
    print("     作业将持续运行，按 Ctrl+C 停止\n")
    
    # 等待作业完成（实际上是持续运行）
    result.wait()


if __name__ == "__main__":
    main()
