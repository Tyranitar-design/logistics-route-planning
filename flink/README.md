# Flink 实时流处理模块

## 概述

本模块使用 Apache Flink 对物流订单进行实时流处理，实现以下功能：

1. **实时订单统计** - 每5分钟按状态统计订单量和金额
2. **异常订单检测** - 金额突增、高价值订单告警
3. **热门路线分析** - 滑动窗口分析热门路线
4. **写入 Elasticsearch** - 支持实时搜索

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Flink Stream Processing                  │
│                                                              │
│   Kafka (logistics.orders)                                  │
│         │                                                    │
│         ▼                                                    │
│   ┌─────────────┐                                            │
│   │ OrderParser │  解析 JSON                                 │
│   └─────────────┘                                            │
│         │                                                    │
│         ├──────────────────┬──────────────────┐             │
│         ▼                  ▼                  ▼             │
│   ┌────────────┐     ┌────────────┐     ┌────────────┐      │
│   │ 窗口统计   │     │ 异常检测   │     │ 路线分析   │      │
│   │ (5分钟)    │     │ (状态机)   │     │ (滑动窗口) │      │
│   └────────────┘     └────────────┘     └────────────┘      │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                 │
│                            ▼                                 │
│                    Elasticsearch                            │
│                            │                                 │
│                            ▼                                 │
│                    Grafana / 前端大屏                        │
└─────────────────────────────────────────────────────────────┘
```

## 部署步骤

### 1. 确保 Flink 集群运行

```bash
# 检查 Flink 状态
docker ps | grep flink

# Flink Web UI
http://localhost:8083
```

### 2. 安装 PyFlink

```bash
py -3 -m pip install apache-flink==1.18.1
```

### 3. 提交作业到 Flink 集群

方式一：通过 Web UI 提交
1. 访问 http://localhost:8083
2. 点击 "Submit New Job"
3. 上传 Python 文件或 JAR

方式二：通过命令行提交
```bash
flink run -py logistics_order_stream.py
```

方式三：本地运行（测试）
```bash
py -3 logistics_order_stream.py
```

## 配置说明

### Kafka 配置
- Bootstrap Servers: `logistics-kafka:9092`
- Topic: `logistics.orders`
- Consumer Group: `flink-logistics-processor`

### Checkpoint 配置
- 间隔: 60秒
- 模式: Exactly-Once
- 超时: 10分钟

### 窗口配置
- 订单统计: 5分钟滚动窗口
- 路线分析: 5分钟滑动窗口（步长1分钟）

## 监控

### Flink Web UI
- 地址: http://localhost:8083
- 功能: 作业状态、Checkpoints、背压监控

### Elasticsearch 索引
- 索引名: `logistics-orders-realtime`
- 查询示例:
```bash
curl "localhost:9200/logistics-orders-realtime/_search?pretty"
```

## 常见问题

### Q: 作业提交失败 "NoResourceAvailableException"
A: TaskManager slots 不足，增加 TaskManager 数量或 slots 数量

### Q: Kafka 连接失败
A: 检查网络连通性：
```bash
docker exec logistics-flink-jobmanager ping logistics-kafka
```

### Q: Checkpoint 失败
A: 检查状态后端配置，确保存储路径可写

## 相关文档

- [Flink 官方文档](https://nightlies.apache.org/flink/flink-docs-stable/)
- [PyFlink 文档](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/python/)
- [Flink Kafka Connector](https://nightlies.apache.org/flink/flink-docs-stable/docs/connectors/datastream/kafka/)

---

*小彩的物流项目 | 2026-04-11*
