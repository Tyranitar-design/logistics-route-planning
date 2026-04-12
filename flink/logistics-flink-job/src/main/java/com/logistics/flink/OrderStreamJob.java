package com.logistics.flink;

import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.table.api.bridge.java.StreamTableEnvironment;
import org.apache.flink.table.api.EnvironmentSettings;

/**
 * 物流订单实时流处理作业
 * 
 * 从 Kafka 读取订单数据，处理后输出统计结果
 * 支持持久运行，自动重启
 */
public class OrderStreamJob {
    
    public static void main(String[] args) throws Exception {
        System.out.println("========================================");
        System.out.println("   物流订单实时流处理作业 - Flink");
        System.out.println("========================================");
        
        // 创建流处理环境
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(1);
        
        // 启用 Checkpoint（每 60 秒）
        env.enableCheckpointing(60000);
        
        // 创建 Table 环境
        EnvironmentSettings settings = EnvironmentSettings
            .newInstance()
            .inStreamingMode()
            .build();
        StreamTableEnvironment tEnv = StreamTableEnvironment.create(env, settings);
        
        System.out.println("[1/3] 创建 Kafka 源表...");
        
        // 创建 Kafka 源表
        tEnv.executeSql(
            "CREATE TABLE kafka_orders (" +
            "    order_id STRING," +
            "    event_type STRING," +
            "    cost DOUBLE," +
            "    status STRING," +
            "    `timestamp` STRING" +
            ") WITH (" +
            "    'connector' = 'kafka'," +
            "    'topic' = 'logistics.orders.json.v2'," +
            "    'properties.bootstrap.servers' = '172.18.0.6:9092'," +
            "    'properties.group.id' = 'flink-order-processor-app'," +
            "    'scan.startup.mode' = 'latest-offset'," +
            "    'format' = 'json'" +
            ")"
        );
        
        System.out.println("[2/3] 创建 Kafka 输出表...");
        
        // 创建 Kafka 输出表
        tEnv.executeSql(
            "CREATE TABLE kafka_order_stats (" +
            "    order_id STRING," +
            "    event_type STRING," +
            "    cost DOUBLE," +
            "    status STRING," +
            "    processed_at TIMESTAMP_LTZ(3)" +
            ") WITH (" +
            "    'connector' = 'kafka'," +
            "    'topic' = 'logistics.order.stats'," +
            "    'properties.bootstrap.servers' = '172.18.0.6:9092'," +
            "    'format' = 'json'" +
            ")"
        );
        
        System.out.println("[3/3] 启动流处理...");
        System.out.println("     输入: logistics.orders");
        System.out.println("     输出: logistics.order.stats");
        
        // 执行流处理
        tEnv.executeSql(
            "INSERT INTO kafka_order_stats " +
            "SELECT " +
            "    order_id," +
            "    event_type," +
            "    cost," +
            "    status," +
            "    CURRENT_TIMESTAMP as processed_at " +
            "FROM kafka_orders " +
            "WHERE order_id IS NOT NULL"
        );
        
        System.out.println("[OK] 作业已提交并运行中！");
    }
}
