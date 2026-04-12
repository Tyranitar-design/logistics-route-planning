-- 物流实时分析 SQL 作业
-- 使用 Flink SQL 进行实时流处理

-- 创建 Kafka 表：订单流
CREATE TABLE orders_stream (
    order_id STRING,
    order_number STRING,
    status STRING,
    cost DECIMAL(10, 2),
    pickup_node_id INT,
    delivery_node_id INT,
    vehicle_id INT,
    created_at TIMESTAMP(3),
    event_time AS PROCTIME()
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.orders',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-sql-orders',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.ignore-parse-errors' = 'true'
);

-- 创建 Kafka 表：车辆轨迹流
CREATE TABLE tracking_stream (
    vehicle_id INT,
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    speed DECIMAL(6, 2),
    event_time TIMESTAMP(3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.tracking',
    'properties.bootstrap.servers' = 'kafka:9092',
    'properties.group.id' = 'flink-sql-tracking',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.ignore-parse-errors' = 'true'
);

-- 创建 Elasticsearch 表：订单统计
CREATE TABLE order_statistics (
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    status STRING,
    order_count BIGINT,
    total_cost DECIMAL(15, 2),
    avg_cost DECIMAL(10, 2),
    PRIMARY KEY (window_start, window_end, status) NOT ENFORCED
) WITH (
    'connector' = 'elasticsearch-7',
    'hosts' = 'http://elasticsearch:9200',
    'index' = 'logistics-order-stats',
    'document-id.key-delimiter' = '_'
);

-- 创建 Elasticsearch 表：告警
CREATE TABLE alerts (
    alert_id STRING,
    alert_type STRING,
    vehicle_id INT,
    message STRING,
    severity STRING,
    event_time TIMESTAMP(3),
    PRIMARY KEY (alert_id) NOT ENFORCED
) WITH (
    'connector' = 'elasticsearch-7',
    'hosts' = 'http://elasticsearch:9200',
    'index' = 'logistics-alerts',
    'document-id.key-delimiter' => '_'
);

-- 查询1：每5分钟订单统计（按状态分组）
INSERT INTO order_statistics
SELECT
    TUMBLE_START(event_time, INTERVAL '5' MINUTE) as window_start,
    TUMBLE_END(event_time, INTERVAL '5' MINUTE) as window_end,
    status,
    COUNT(*) as order_count,
    SUM(cost) as total_cost,
    AVG(cost) as avg_cost
FROM orders_stream
GROUP BY
    TUMBLE(event_time, INTERVAL '5' MINUTE),
    status;

-- 查询2：高价值订单检测（金额 > 10000）
CREATE VIEW high_value_orders AS
SELECT
    order_id,
    order_number,
    cost,
    vehicle_id,
    event_time
FROM orders_stream
WHERE cost > 10000;

-- 查询3：超速车辆检测
CREATE VIEW overspeed_vehicles AS
SELECT
    vehicle_id,
    latitude,
    longitude,
    speed,
    event_time
FROM tracking_stream
WHERE speed > 120;

-- 查询4：热门路线分析（滚动窗口）
SELECT
    TUMBLE_START(event_time, INTERVAL '10' MINUTE) as window_start,
    TUMBLE_END(event_time, INTERVAL '10' MINUTE) as window_end,
    pickup_node_id,
    delivery_node_id,
    COUNT(*) as route_count
FROM orders_stream
GROUP BY
    TUMBLE(event_time, INTERVAL '10' MINUTE),
    pickup_node_id,
    delivery_node_id
ORDER BY route_count DESC;
