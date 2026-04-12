#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Spark Streaming 实时数据处理
从 Kafka 读取数据并进行实时分析
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Spark Session 配置
spark = SparkSession.builder \
    .appName("LogisticsRealtimeAnalytics") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .config("spark.streaming.kafka.maxRatePerPartition", 1000) \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = "logistics-kafka:9092"
KAFKA_TOPICS = ["logistics.orders", "logistics.vehicles", "logistics.tracking"]

# 定义 Schema
order_schema = StructType([
    StructField("event_type", StringType(), True),
    StructField("order_id", LongType(), True),
    StructField("customer_name", StringType(), True),
    StructField("origin", StringType(), True),
    StructField("destination", StringType(), True),
    StructField("status", StringType(), True),
    StructField("cost", DoubleType(), True),
    StructField("weight", DoubleType(), True),
    StructField("distance", DoubleType(), True),
    StructField("timestamp", StringType(), True)
])

vehicle_schema = StructType([
    StructField("event_type", StringType(), True),
    StructField("vehicle_id", LongType(), True),
    StructField("plate_number", StringType(), True),
    StructField("status", StringType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("speed", DoubleType(), True),
    StructField("fuel_level", DoubleType(), True),
    StructField("timestamp", StringType(), True)
])


def process_orders(df, epoch_id):
    """处理订单数据"""
    if df.count() > 0:
        print(f"\n=== 订单数据 (Epoch {epoch_id}) ===")
        df.select("order_id", "customer_name", "origin", "destination", "cost").show(5, truncate=False)
        
        # 统计
        stats = df.groupBy("status").count()
        print("订单状态分布:")
        stats.show()


def process_vehicles(df, epoch_id):
    """处理车辆数据"""
    if df.count() > 0:
        print(f"\n=== 车辆数据 (Epoch {epoch_id}) ===")
        df.select("vehicle_id", "plate_number", "status", "speed").show(5, truncate=False)
        
        # 平均速度
        avg_speed = df.agg(avg("speed").alias("avg_speed"))
        print("平均速度:")
        avg_speed.show()


def main():
    """主函数"""
    print("=" * 50)
    print("  物流实时数据分析 - Spark Streaming")
    print("=" * 50)
    
    # 读取订单数据
    orders_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "logistics.orders") \
        .option("startingOffsets", "latest") \
        .load()
    
    # 解析 JSON
    orders_parsed = orders_df.select(
        from_json(col("value").cast("string"), order_schema).alias("data")
    ).select("data.*")
    
    # 处理订单流
    orders_query = orders_parsed.writeStream \
        .foreachBatch(process_orders) \
        .trigger(processingTime="10 seconds") \
        .start()
    
    # 读取车辆数据
    vehicles_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "logistics.vehicles") \
        .option("startingOffsets", "latest") \
        .load()
    
    # 解析 JSON
    vehicles_parsed = vehicles_df.select(
        from_json(col("value").cast("string"), vehicle_schema).alias("data")
    ).select("data.*")
    
    # 处理车辆流
    vehicles_query = vehicles_parsed.writeStream \
        .foreachBatch(process_vehicles) \
        .trigger(processingTime="10 seconds") \
        .start()
    
    print("\n✅ Spark Streaming 已启动!")
    print("   订单流: logistics.orders")
    print("   车辆流: logistics.vehicles")
    print("   按 Ctrl+C 停止\n")
    
    # 等待终止
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
