# 📊 大数据分析平台技术文档

> 物流路径规划系统 - 大数据模块技术说明

---

## 🏗️ 平台架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          数据采集层                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ 订单系统  │  │ 车辆GPS  │  │ 天气服务  │  │ 外部API  │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │              │                     │
│       └──────────────┴──────────────┴──────────────┘                     │
│                              │                                          │
│                     ┌────────▼────────┐                                  │
│                     │  Apache Kafka   │  ← 消息总线/流式处理              │
│                     │  (Port 9092)    │                                  │
│                     └────────┬────────┘                                  │
│                              │                                          │
│              ┌───────────────┼───────────────┐                          │
│              │               │               │                          │
│     ┌────────▼────────┐     │     ┌────────▼────────┐                  │
│     │ Apache Spark    │     │     │  Redis          │                  │
│     │ (Port 4040/8080)│     │     │  (Port 6379)    │                  │
│     │ 批量ETL+流计算   │     │     │  热数据缓存      │                  │
│     └────────┬────────┘     │     └─────────────────┘                  │
│              │              │                                          │
│              └──────┬───────┘                                          │
│                     │                                                  │
│     ┌───────────────┼───────────────┐                                  │
│     │               │               │                                  │
│     ▼               ▼               ▼                                  │
│ ┌──────────┐  ┌───────────┐  ┌────────────┐                           │
│ │ClickHouse│  │Elasticsearch│  │  PostgreSQL │                           │
│ │(Port 8123)│  │(Port 9200)  │  │(Port 5432)  │                           │
│ │ OLAP分析  │  │ 全文搜索    │  │  业务数据    │                           │
│ └────┬─────┘  └─────┬─────┘  └────────────┘                           │
│      │              │                                                 │
│      └──────┬───────┘                                                 │
│             │                                                         │
│    ┌────────▼────────┐                                                 │
│    │  Flask API      │  ← 后端服务 (Port 5000)                         │
│    │  + Vue 3 前端    │  ← 前端应用 (Port 8080)                         │
│    └────────┬────────┘                                                 │
│             │                                                         │
│    ┌────────▼────────┐                                                 │
│    │  Grafana        │  ← 监控大屏 (Port 3000)                         │
│    │  数据可视化       │                                                 │
│    └─────────────────┘                                                 │
│                                                                       │
│    ┌─────────────────┐                                                 │
│    │  Airflow        │  ← 工作流调度 (Port 8081)                       │
│    │  DAG 编排        │                                                 │
│    └─────────────────┘                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈说明

| 组件 | 版本 | 用途 | 端口 |
|------|------|------|------|
| Apache Kafka | 3.x | 消息队列 / 实时流处理 | 9092 |
| Apache Spark | 3.x | 批量数据处理 + 流式计算 | 4040, 7077, 8080 |
| Elasticsearch | 8.x | 全文搜索引擎 | 9200, 9300 |
| ClickHouse | 23.x | 列式OLAP分析数据库 | 8123, 9000 |
| Redis | 7.x | 内存缓存 / 实时数据 | 6379 |
| Grafana | 10.x | 数据可视化 / 监控大屏 | 3000 |
| Apache Airflow | 2.x | 工作流编排 / DAG调度 | 8081 |

---

## 📦 各组件功能介绍

### 🔄 Apache Kafka - 消息总线

- **功能定位**：系统数据流的核心枢纽
- **主要职责**：
  - 接收来自订单系统、车辆GPS、天气服务等多源数据
  - 实现数据的解耦与缓冲
  - 支持实时流处理与批量消费
- **Topic 设计**：
  - `orders` — 订单事件流
  - `vehicle-location` — 车辆实时位置
  - `weather-data` — 天气更新数据
  - `delivery-events` — 配送事件通知
  - `analytics-events` — 分析事件流

### ⚡ Apache Spark - 数据处理引擎

- **功能定位**：大规模数据处理与计算
- **主要职责**：
  - 批量ETL：从Kafka消费数据，清洗转换后写入ClickHouse/ES
  - 流式计算：Structured Streaming 实时聚合
  - 机器学习：MLlib 模型训练（需求预测、路径优化）
- **关键服务**：
  - `spark.py` — Spark 上下文与任务配置
  - `spark_api.py` — Spark 任务REST API
  - `kafka_consumer_service.py` — Kafka消费者服务
  - `data_collection.py` — 数据采集与预处理

### 🔍 Elasticsearch - 全文搜索引擎

- **功能定位**：物流数据智能检索
- **主要职责**：
  - 订单全文搜索（支持模糊匹配、关键词高亮）
  - 路线与节点快速检索
  - 客户信息索引与搜索
  - 日志聚合分析
- **关键服务**：
  - `es_search.py` — ES 搜索路由
  - `bigdata/` 前端搜索视图

### 📊 ClickHouse - OLAP分析数据库

- **功能定位**：海量数据列式分析
- **主要职责**：
  - 物流运营数据存储（订单、配送、成本）
  - 复杂聚合查询（多维度统计、趋势分析）
  - 实时数据看板数据源
- **关键服务**：
  - `clickhouse.py` — ClickHouse 连接与查询路由

### 🧠 Redis - 缓存与实时数据

- **功能定位**：高性能缓存层
- **主要职责**：
  - 热点数据缓存（频繁访问的订单、路线）
  - 实时车辆位置存储
  - 分布式锁与会话管理
  - 排行榜与计数器（配送排名、订单统计）
- **关键服务**：
  - `redis.py` — Redis 连接配置路由
  - `redis_service.py` — Redis 业务逻辑服务

### 📈 Grafana - 数据可视化大屏

- **功能定位**：物流运营实时监控
- **主要职责**：
  - 数据大屏展示（订单量、配送效率、成本趋势）
  - 告警规则配置与通知
  - 多数据源仪表盘
- **前端集成**：
  - `BigDataScreen.vue` — 大屏可视化主页面
  - `bigdata/Analytics.vue` — 数据分析视图
  - `bigdata/Visualization.vue` — 可视化组件

### 🎯 Apache Airflow - 工作流编排

- **功能定位**：自动化数据管道管理
- **主要职责**：
  - DAG定义：数据采集 → 清洗 → 分析 → 报告的完整流水线
  - 定时任务调度（每日统计、周报生成）
  - 任务依赖管理与失败重试
- **前端集成**：
  - `bigdata/Scheduler.vue` — 调度管理视图

---

## 🔌 服务端口列表

| 服务 | 端口 | 说明 |
|------|------|------|
| Flask 后端 | 5000 | 主API服务 |
| Vue 前端 | 8080 | 开发服务器 |
| Kafka | 9092 | 消息代理 |
| Zookeeper | 2181 | Kafka依赖 |
| Elasticsearch | 9200/9300 | HTTP/Transport |
| ClickHouse HTTP | 8123 | HTTP接口 |
| ClickHouse Native | 9000 | 原生协议 |
| Redis | 6379 | 缓存服务 |
| Spark Master | 7077 | 集群管理 |
| Spark Web UI | 4040/8080 | 任务监控 |
| Grafana | 3000 | 监控大屏 |
| Airflow Web | 8081 | DAG管理 |

---

## 🚀 启动命令

### Docker 一键启动（推荐）

```bash
# 启动所有大数据组件
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f kafka spark clickhouse
```

### 手动启动各组件

```bash
# Redis
redis-server redis.conf

# Kafka + Zookeeper
zookeeper-server-start.sh config/zookeeper.properties
kafka-server-start.sh config/server.properties

# 创建 Kafka Topics
kafka-topics.sh --create --topic orders --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
kafka-topics.sh --create --topic vehicle-location --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
kafka-topics.sh --create --topic weather-data --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
kafka-topics.sh --create --topic delivery-events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

# ClickHouse
clickhouse-server --config-file config.xml

# Elasticsearch
elasticsearch

# Spark（standalone模式）
spark-submit --Main local[*] app/spark_jobs.py

# Grafana
grafana-server

# Airflow
airflow standalone

# Flask 后端
cd backend
python run.py

# Vue 前端
cd frontend
npm run dev
```

---

## 📡 API 接口列表

### 大数据模块 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/bigdata/overview` | 大数据平台概览（各组件状态） |
| GET | `/api/bigdata/dashboard` | 大屏实时数据 |
| GET | `/api/bigdata/trends` | 趋势分析数据 |
| GET | `/api/bigdata/analytics` | 综合分析报告 |
| GET | `/api/bigdata/metrics` | 系统指标监控 |
| GET | `/api/bigdata/metrics/realtime` | 实时性能指标 |
| POST | `/api/bigdata/metrics/collect` | 手动采集指标 |
| GET | `/api/bigdata/health` | 组件健康检查 |

### Elasticsearch 搜索 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/es/search` | 全文搜索（支持订单/路线/客户） |
| GET | `/api/es/suggestions` | 搜索建议/自动补全 |
| GET | `/api/es/indexes` | 索引列表与状态 |
| POST | `/api/es/index` | 手动索引数据 |
| GET | `/api/es/stats` | 索引统计信息 |

### ClickHouse 分析 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/clickhouse/query` | 执行查询 |
| GET | `/api/clickhouse/stats` | 数据库统计 |
| GET | `/api/clickhouse/tables` | 表列表 |
| GET | `/api/clickhouse/columns/<table>` | 表字段信息 |

### Spark 任务 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/spark/jobs` | 任务列表 |
| POST | `/api/spark/submit` | 提交Spark任务 |
| GET | `/api/spark/status/<job_id>` | 任务状态 |
| POST | `/api/spark/cancel/<job_id>` | 取消任务 |
| GET | `/api/spark/history` | 历史任务 |

### Kafka 流处理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/kafka/topics` | Topic列表 |
| GET | `/api/kafka/topics/<topic>/messages` | 消费消息 |
| POST | `/api/kafka/topics/<topic>/produce` | 生产消息 |
| GET | `/api/kafka/topics/<topic>/offsets` | 消费偏移量 |
| GET | `/api/kafka/consumer/groups` | 消费者组 |

### Redis 缓存 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/redis/stats` | Redis服务器信息 |
| GET | `/api/redis/keys` | Key列表 |
| GET | `/api/redis/get/<key>` | 获取缓存值 |
| POST | `/api/redis/set` | 设置缓存 |
| DELETE | `/api/redis/delete/<key>` | 删除缓存 |

### 数据采集 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data-collection/sources` | 数据源列表 |
| POST | `/api/data-collection/sources` | 添加数据源 |
| PUT | `/api/data-collection/sources/<id>` | 更新数据源 |
| DELETE | `/api/data-collection/sources/<id>` | 删除数据源 |
| POST | `/api/data-collection/collect` | 触发数据采集 |
| GET | `/api/data-collection/status` | 采集任务状态 |

---

## 🖥️ 前端视图说明

### 大数据模块视图

| 视图文件 | 功能 |
|----------|------|
| `BigDataScreen.vue` | 大数据可视化大屏主页 |
| `DataCollectionView.vue` | 数据采集管理视图 |
| `bigdata/Layout.vue` | 大数据模块布局组件 |
| `bigdata/Analytics.vue` | 数据分析面板 |
| `bigdata/DeepLearning.vue` | 深度学习分析 |
| `bigdata/Monitor.vue` | 系统监控面板 |
| `bigdata/Scheduler.vue` | 任务调度管理 |
| `bigdata/Search.vue` | 全文搜索界面 |
| `bigdata/Spark.vue` | Spark 任务管理 |
| `bigdata/Visualization.vue` | 可视化图表组件 |

### 路由配置

大数据模块使用独立路由文件 `frontend/src/router/bigdata.js`，通过主路由 `frontend/src/router/index.js` 引入。

---

## 📂 后端文件结构

```
backend/app/
├── routes/
│   ├── bigdata.py              # 大数据主路由
│   ├── clickhouse.py           # ClickHouse 查询路由
│   ├── data_collection.py      # 数据采集路由
│   ├── es_search.py            # Elasticsearch 搜索路由
│   ├── metrics.py              # 系统指标路由
│   ├── redis.py                # Redis 缓存路由
│   ├── spark.py                # Spark 任务路由
│   └── spark_api.py            # Spark REST API
│
└── services/
    ├── kafka_service.py        # Kafka 生产者服务
    ├── kafka_consumer_service.py # Kafka 消费者服务
    └── redis_service.py        # Redis 业务服务
```

---

## 🔧 配置说明

### 环境变量（.env）

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Elasticsearch
ES_HOST=http://localhost:9200
ES_INDEX_PREFIX=logistics

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=logistics

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Spark
SPARK_MASTER=local[*]
SPARK_APP_NAME=LogisticsAnalytics

# Grafana
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your_api_key

# Airflow
AIRFLOW_URL=http://localhost:8081
```

---

## 📝 常见问题

### Q: Kafka 连接失败怎么办？
检查 Zookeeper 是否已启动，Kafka broker 是否正常运行。可通过 `kafka-topics.sh --list --bootstrap-server localhost:9092` 验证。

### Q: ClickHouse 查询速度慢？
确保使用了合适的分区键和排序键，大批量插入建议使用 `INSERT ... VALUES` 批量语法。

### Q: Spark 内存不足？
调整 `spark.executor.memory` 和 `spark.driver.memory` 参数，或切换到集群模式部署。

---

**最后更新**: 2026-04-06
