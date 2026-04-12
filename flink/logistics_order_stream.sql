-- ============================================
-- 物流订单实时流处理 - Flink SQL
-- ============================================
-- 功能：从 Kafka 读取订单，实时统计，写入 ES
-- 执行方式：sql-client.sh -f logistics_order_stream.sql
-- ============================================

-- 1. 创建 Kafka Source 表
CREATE TABLE kafka_orders (
    order_id STRING,
    order_number STRING,
    status STRING,
    cost DECIMAL(10, 2),
    pickup_node_id STRING,
    delivery_node_id STRING,
    customer_name STRING,
    vehicle_id STRING,
    created_at TIMESTAMP(3),
    event_time TIMESTAMP(3) METADATA FROM 'timestamp',
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.orders',
    'properties.bootstrap.servers' = 'logistics-kafka:9092',
    'properties.group.id' = 'flink-logistics-sql',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.ignore-parse-errors' = 'true'
);

-- 2. 创建 Elasticsearch Sink 表（订单明细）
CREATE TABLE es_orders (
    order_id STRING,
    order_number STRING,
    status STRING,
    cost DECIMAL(10, 2),
    pickup_node_id STRING,
    delivery_node_id STRING,
    customer_name STRING,
    vehicle_id STRING,
    created_at TIMESTAMP(3),
    route STRING,
    processed_at TIMESTAMP(3)
) WITH (
    'connector' = 'elasticsearch-7',
    'hosts' = 'http://logistics-elasticsearch:9200',
    'index' = 'logistics-orders-realtime',
    'document-id.key-delimiter' = '$',
    'format' = 'json'
);

-- 3. 创建 Elasticsearch Sink 表（统计结果）
CREATE TABLE es_order_stats (
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    status STRING,
    total_orders BIGINT,
    total_cost DECIMAL(15, 2),
    avg_cost DECIMAL(10, 2),
    stat_id STRING
) WITH (
    'connector' = 'elasticsearch-7',
    'hosts' = 'http://logistics-elasticsearch:9200',
    'index' = 'logistics-order-stats',
    'document-id.key-delimiter' = '$',
    'format' = 'json'
);

-- 4. 创建 Elasticsearch Sink 表（热门路线）
CREATE TABLE es_route_stats (
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    route STRING,
    total_orders BIGINT,
    total_cost DECIMAL(15, 2),
    stat_id STRING
) WITH (
    'connector' = 'elasticsearch-7',
    'hosts' = 'http://logistics-elasticsearch:9200',
    'index' = 'logistics-route-stats',
    'document-id.key-delimiter' = '$',
    'format' = 'json'
);

-- 5. 创建 Elasticsearch Sink 表（告警）
CREATE TABLE es_alerts (
    alert_id STRING,
    alert_type STRING,
    order_id STRING,
    message STRING,
    severity STRING,
    alert_time TIMESTAMP(3)
) WITH (
    'connector' = 'elasticsearch-7',
    'hosts' = 'http://logistics-elasticsearch:9200',
    'index' = 'logistics-alerts',
    'document-id.key-delimiter' = '$',
    'format' = 'json'
);

-- ============================================
-- 实时查询
-- ============================================

-- 5分钟滚动窗口订单统计（按状态分组）
INSERT INTO es_order_stats
SELECT 
    TUMBLE_START(event_time, INTERVAL '5' MINUTE) as window_start,
    TUMBLE_END(event_time, INTERVAL '5' MINUTE) as window_end,
    status,
    COUNT(*) as total_orders,
    SUM(cost) as total_cost,
    AVG(cost) as avg_cost,
    CONCAT(
        DATE_FORMAT(TUMBLE_END(event_time, INTERVAL '5' MINUTE), 'yyyyMMddHHmm'),
        '_', 
        status
    ) as stat_id
FROM kafka_orders
WHERE order_id IS NOT NULL
GROUP BY 
    TUMBLE(event_time, INTERVAL '5' MINUTE),
    status;

-- 热门路线分析（滑动窗口：每1分钟统计最近5分钟）
INSERT INTO es_route_stats
SELECT 
    HOP_START(event_time, INTERVAL '1' MINUTE, INTERVAL '5' MINUTE) as window_start,
    HOP_END(event_time, INTERVAL '1' MINUTE, INTERVAL '5' MINUTE) as window_end,
    CONCAT(pickup_node_id, '->', delivery_node_id) as route,
    COUNT(*) as total_orders,
    SUM(cost) as total_cost,
    CONCAT(
        DATE_FORMAT(HOP_END(event_time, INTERVAL '1' MINUTE, INTERVAL '5' MINUTE), 'yyyyMMddHHmm'),
        '_', 
        pickup_node_id, '_', delivery_node_id
    ) as stat_id
FROM kafka_orders
WHERE order_id IS NOT NULL 
  AND pickup_node_id IS NOT NULL 
  AND delivery_node_id IS NOT NULL
GROUP BY 
    HOP(event_time, INTERVAL '1' MINUTE, INTERVAL '5' MINUTE),
    pickup_node_id, delivery_node_id;

-- 订单明细实时写入 ES（用于搜索）
INSERT INTO es_orders
SELECT 
    order_id,
    order_number,
    status,
    cost,
    pickup_node_id,
    delivery_node_id,
    customer_name,
    vehicle_id,
    created_at,
    CONCAT(pickup_node_id, '->', delivery_node_id) as route,
    CURRENT_TIMESTAMP as processed_at
FROM kafka_orders
WHERE order_id IS NOT NULL;

-- 高价值订单告警（金额 > 10000）
INSERT INTO es_alerts
SELECT 
    CONCAT('high_value_', order_id, '_', DATE_FORMAT(CURRENT_TIMESTAMP, 'yyyyMMddHHmmss')) as alert_id,
    'HIGH_VALUE' as alert_type,
    order_id,
    CONCAT('高价值订单: ¥', CAST(cost AS STRING)) as message,
    'MEDIUM' as severity,
    CURRENT_TIMESTAMP as alert_time
FROM kafka_orders
WHERE order_id IS NOT NULL AND cost > 10000;

-- 打印当前作业状态
SELECT 'Flink SQL 作业已启动！订单实时流处理中...' as status;
