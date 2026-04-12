"""
物流订单数据分析 - Spark 批处理作业
功能：从 Kafka 读取订单数据，进行统计分析
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spark_session():
    """创建 Spark Session"""
    return SparkSession.builder \
        .appName("LogisticsOrderAnalytics") \
        .master("spark://spark-master:7077") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()

def define_order_schema():
    """定义订单数据结构"""
    return StructType([
        StructField("order_id", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("status", StringType(), True),
        StructField("cost", DoubleType(), True),
        StructField("timestamp", StringType(), True),
        StructField("customer_id", StringType(), True),
        StructField("origin_node", StringType(), True),
        StructField("destination_node", StringType(), True)
    ])

def analyze_orders(spark, kafka_bootstrap_servers="172.18.0.6:9092"):
    """分析订单数据"""
    
    # 定义 schema
    schema = define_order_schema()
    
    # 从 Kafka 读取数据
    logger.info("Reading from Kafka topic: logistics.orders")
    
    df = spark.read \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "logistics.orders") \
        .option("startingOffsets", "earliest") \
        .load()
    
    # 解析 JSON 数据
    orders_df = df.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select("data.*")
    
    # 1. 按状态统计订单数量
    status_counts = orders_df.groupBy("status").count()
    logger.info("=== Order Status Counts ===")
    status_counts.show()
    
    # 2. 计算总成本
    total_cost = orders_df.agg(sum("cost").alias("total_cost"))
    logger.info("=== Total Cost ===")
    total_cost.show()
    
    # 3. 按客户统计订单数量和总成本
    customer_stats = orders_df.groupBy("customer_id") \
        .agg(
            count("*").alias("order_count"),
            sum("cost").alias("total_cost"),
            avg("cost").alias("avg_cost")
        )
    logger.info("=== Customer Statistics ===")
    customer_stats.show()
    
    # 4. 按路线统计（起点->终点）
    route_stats = orders_df.groupBy("origin_node", "destination_node") \
        .agg(
            count("*").alias("order_count"),
            sum("cost").alias("total_revenue")
        )
    logger.info("=== Route Statistics ===")
    route_stats.show()
    
    return {
        "status_counts": status_counts,
        "total_cost": total_cost,
        "customer_stats": customer_stats,
        "route_stats": route_stats
    }

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("  Logistics Order Analytics - Spark Job")
    logger.info("=" * 50)
    
    # 创建 Spark Session
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # 执行分析
        results = analyze_orders(spark)
        logger.info("Analysis completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        raise
    finally:
        spark.stop()
        logger.info("Spark session stopped.")

if __name__ == "__main__":
    main()
