-- 物流订单实时流处理 SQL 作业
-- 持久运行的 Kafka -> Kafka 流处理

-- 创建 Kafka 源表
CREATE TABLE kafka_orders (
    order_id STRING,
    event_type STRING,
    cost DOUBLE,
    status STRING,
    `timestamp` STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.orders',
    'properties.bootstrap.servers' = 'logistics-kafka:9092',
    'properties.group.id' = 'flink-order-processor-persistent',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);

-- 创建 Kafka 输出表
CREATE TABLE kafka_order_stats (
    order_id STRING,
    event_type STRING,
    cost DOUBLE,
    status STRING,
    processed_at STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.order.stats',
    'properties.bootstrap.servers' = 'logistics-kafka:9092',
    'format' = 'json'
);

-- 启动流处理作业
INSERT INTO kafka_order_stats
SELECT 
    order_id,
    event_type,
    cost,
    status,
    CURRENT_TIMESTAMP as processed_at
FROM kafka_orders
WHERE order_id IS NOT NULL;
