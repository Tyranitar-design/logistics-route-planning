-- ============================================
-- 物流订单实时流处理 - Flink SQL (简化版)
-- ============================================
-- 测试版本：只用 Kafka，输出到控制台
-- ============================================

-- 创建 Kafka Source 表
CREATE TABLE kafka_orders (
    order_id STRING,
    order_number STRING,
    status STRING,
    cost DECIMAL(10, 2),
    pickup_node_id STRING,
    delivery_node_id STRING,
    customer_name STRING,
    vehicle_id STRING,
    created_at STRING,
    event_time TIMESTAMP(3) METADATA FROM 'timestamp',
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.orders',
    'properties.bootstrap.servers' = 'logistics-kafka:9092',
    'properties.group.id' = 'flink-logistics-sql-test',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.ignore-parse-errors' = 'true'
);

-- 创建 Kafka Sink 表（统计结果）
CREATE TABLE kafka_order_stats (
    window_start STRING,
    window_end STRING,
    status STRING,
    total_orders BIGINT,
    total_cost DECIMAL(15, 2),
    avg_cost DECIMAL(10, 2)
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.order.stats',
    'properties.bootstrap.servers' = 'logistics-kafka:9092',
    'format' = 'json'
);

-- 创建 Kafka Sink 表（告警）
CREATE TABLE kafka_alerts (
    alert_type STRING,
    order_id STRING,
    message STRING,
    severity STRING,
    alert_time STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.alerts.realtime',
    'properties.bootstrap.servers' = 'logistics-kafka:9092',
    'format' = 'json'
);

-- ============================================
-- 实时查询
-- ============================================

-- 1. 5分钟滚动窗口订单统计
INSERT INTO kafka_order_stats
SELECT 
    DATE_FORMAT(TUMBLE_START(event_time, INTERVAL '5' MINUTE), 'yyyy-MM-dd HH:mm:ss') as window_start,
    DATE_FORMAT(TUMBLE_END(event_time, INTERVAL '5' MINUTE), 'yyyy-MM-dd HH:mm:ss') as window_end,
    status,
    COUNT(*) as total_orders,
    SUM(cost) as total_cost,
    AVG(cost) as avg_cost
FROM kafka_orders
WHERE order_id IS NOT NULL
GROUP BY 
    TUMBLE(event_time, INTERVAL '5' MINUTE),
    status;

-- 2. 高价值订单告警
INSERT INTO kafka_alerts
SELECT 
    'HIGH_VALUE' as alert_type,
    order_id,
    CONCAT('高价值订单: ', CAST(cost AS STRING), ' 元') as message,
    'MEDIUM' as severity,
    DATE_FORMAT(CURRENT_TIMESTAMP, 'yyyy-MM-dd HH:mm:ss') as alert_time
FROM kafka_orders
WHERE order_id IS NOT NULL AND cost > 5000;

-- 3. 打印实时订单流（调试用）
SELECT 
    order_id,
    order_number,
    status,
    cost,
    customer_name,
    DATE_FORMAT(event_time, 'yyyy-MM-dd HH:mm:ss') as event_time
FROM kafka_orders
WHERE order_id IS NOT NULL
LIMIT 10;
