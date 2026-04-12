#!/bin/bash
# 启动 Flink SQL 作业并保持运行
cd /opt/flink

# 创建 SQL 文件（使用 checkpoint 和 restart 策略）
cat > /tmp/persistent_job.sql << 'EOF'
-- 配置 checkpoint
SET execution.checkpointing.interval=60s;
SET execution.checkpointing.mode=EXACTLY_ONCE;
SET restart-strategy=fixed-delay;
SET restart-strategy.fixed-delay.attempts=3;
SET restart-strategy.fixed-delay.delay=10s;

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
    'properties.bootstrap.servers' = '172.18.0.6:9092',
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
    processed_at TIMESTAMP_LTZ(3)
) WITH (
    'connector' = 'kafka',
    'topic' = 'logistics.order.stats',
    'properties.bootstrap.servers' = '172.18.0.6:9092',
    'format' = 'json'
);

-- 启动流处理作业（BEGIN STATEMENT SET 使作业持久运行）
BEGIN STATEMENT SET;
INSERT INTO kafka_order_stats
SELECT 
    order_id,
    event_type,
    cost,
    status,
    CURRENT_TIMESTAMP as processed_at
FROM kafka_orders
WHERE order_id IS NOT NULL;
END;
EOF

# 执行 SQL 作业
./bin/sql-client.sh -f /tmp/persistent_job.sql &

# 保持容器运行
exec tail -f /dev/null
