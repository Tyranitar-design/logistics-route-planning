# 🚚 物流路径规划与管理信息系统

> Intelligent Logistics Route Planning & Management System

[![Vue](https://img.shields.io/badge/Vue-3.4-brightgreen)](https://vuejs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com/)
[![ECharts](https://img.shields.io/badge/ECharts-5.4-orange)](https://echarts.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)

---

## 📋 项目简介

本项目是一个完整的**管理信息系统（MIS）**与**大数据分析平台**，由小宇与小彩共同开发，帮助物流企业优化运输路线、降低成本、提高效率，并通过大数据技术实现实时数据采集、流式处理与智能分析。

### 🌟 核心亮点

- **55+项核心功能**：覆盖物流全流程 + 大数据分析
- **智能调度算法**：遗传算法、蚁群、粒子群、深度强化学习
- **机器学习预测**：LSTM + Prophet 需求预测
- **实时监控**：WebSocket + 3D地球可视化
- **移动端支持**：微信小程序司机端
- **大数据分析平台**：Kafka + Spark + ES + ClickHouse + Redis 全栈实时数据处理
- **Grafana 大屏可视化**：物流运营数据实时展示

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 克隆项目
git clone https://github.com/[your-username]/logistics-route-planning.git
cd logistics-route-planning

# 一键启动
docker-compose up -d

# 访问应用
# 前端: http://localhost:8080
# 后端: http://localhost:5000
# 默认账号: admin / admin123
```

### 方式二：本地开发

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py

# 前端
cd frontend
npm install
npm run dev
```

---

## ✨ 功能清单（55+项）

### 基础功能模块（9项）
- ✅ 节点管理 - 仓库、配送站、中转站
- ✅ 路线管理 - 路径定义、成本估算
- ✅ 订单管理 - 创建、追踪、批量操作
- ✅ 车辆管理 - 档案、状态监控
- ✅ 用户权限 - JWT认证、多角色
- ✅ 数据统计 - 仪表盘、趋势分析
- ✅ 地图可视化 - 高德地图集成
- ✅ 3D地球 - Three.js 车辆动画
- ✅ 供应商管理 - 档案、绩效、合同

### 智能调度模块（5项）
- ✅ 遗传算法调度 - 自动订单分配
- ✅ 高级路径优化 - ACO、PSO、DRL
- ✅ 敏捷优化 - 模拟退火、禁忌搜索
- ✅ 多目标优化 - Pareto前沿
- ✅ 订单路线推荐 - 路径规划

### 数据分析模块（6项）
- ✅ 仪表盘中心 - 关键指标
- ✅ ML需求预测 - LSTM+Prophet
- ✅ 客户画像 - RFM价值分级
- ✅ 成本分析 - 全维度统计
- ✅ 供应链可视化 - 端到端追踪
- ✅ 碳足迹计算 - 绿色路线

### 预警监控模块（5项）
- ✅ 智能预警中心 - 多维度告警
- ✅ 实时异常检测 - 订单/成本/路线
- ✅ 预测性维护 - 路线拥堵预测
- ✅ 天气服务 - 影响评估
- ✅ 车辆故障预测 - 风险评分

### 移动端模块（8项）
- ✅ 微信小程序 - 司机端完整功能
- ✅ 派单通知 - 接收/接受/拒绝
- ✅ 电子签收 - Canvas签名板
- ✅ 轨迹上报 - GPS定位发送
- ✅ 语音交互 - 命令+TTS播报
- ✅ 收入明细 - 配送统计
- ✅ 荣誉中心 - 徽章系统
- ✅ 评价管理 - 客户反馈

### 大数据分析模块（12项）
- ✅ Kafka 实时流处理 - 订单/车辆/天气多源数据接入
- ✅ Elasticsearch 全文搜索 - 订单、路线、客户智能检索
- ✅ ClickHouse 列式分析 - 海量物流数据OLAP查询
- ✅ Spark 数据处理 - 批量ETL与流式计算
- ✅ Redis 缓存加速 - 热点数据毫秒级响应
- ✅ Grafana 数据大屏 - 物流运营实时监控面板
- ✅ 数据采集中心 - 多源数据统一接入与管理
- ✅ 大数据分析视图 - 多维度数据可视化分析
- ✅ 深度学习分析 - 神经网络驱动的智能分析
- ✅ 调度监控 - 大数据任务调度与状态追踪
- ✅ 系统指标监控 - 服务健康度与性能指标
- ✅ Airflow 工作流调度 - 自动化数据管道编排

### 高级功能模块（10项）
- ✅ 高级预测 - LSTM时序
- ✅ 动态定价 - 供需定价引擎
- ✅ 库存优化 - EOQ模型
- ✅ 多式联运 - 四种运输方式
- ✅ 3D可视化 - Three.js
- ✅ 数据大屏 - 演示级界面
- ✅ 审计日志 - 操作追踪
- ✅ 测试数据生成 - 一键填充
- ✅ 用户权限系统 - 管理员/普通用户
- ✅ 国际化 - 中/英文切换

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite |
| UI组件 | Element Plus |
| 图表 | ECharts 5.4 |
| 3D | Three.js |
| 地图 | Leaflet + 高德API |
| 后端框架 | Flask 3.0 |
| ORM | SQLAlchemy 2.0 |
| 认证 | JWT |
| 实时通信 | WebSocket (Flask-SocketIO) |
| 数据库 | SQLite / PostgreSQL |
| 消息队列 | Apache Kafka |
| 搜索引擎 | Elasticsearch |
| 列式分析 | ClickHouse |
| 数据处理 | Apache Spark |
| 缓存 | Redis |
| 监控大屏 | Grafana |
| 工作流 | Apache Airflow |
| 移动端 | 微信小程序原生 |

---

## 🤖 AI协同开发

本项目由**小宇 + 小彩(AI)**共同开发：

| 角色 | 贡献 |
|------|------|
| 小宇 | 需求分析、产品设计、功能测试 |
| 小彩(AI) | 架构设计、代码编写、文档生成 |

**AI协同占比**: 约 85%

---

## 📁 项目结构

```
logistics-route-planning/
├── frontend/           # 前端项目
│   ├── src/
│   │   ├── views/     # 页面组件
│   │   ├── components/
│   │   ├── api/       # API接口
│   │   └── utils/     # 工具函数
│   ├── Dockerfile
│   └── nginx.conf
│
├── backend/            # 后端项目
│   ├── app/
│   │   ├── routes/    # API路由
│   │   ├── services/  # 业务逻辑
│   │   └── models/    # 数据模型
│   ├── Dockerfile
│   └── requirements.txt
│
├── miniprogram/        # 微信小程序
├── docs/               # 文档
├── docker-compose.yml
└── README.md
```

---

## 📊 数据演示

系统已内置测试数据生成器，一键填充：
- 100+ 订单
- 20+ 车辆
- 50+ 路线
- 30+ 节点

---

## 🔧 环境配置

### 必需配置

创建 `.env` 文件：
```env
# 高德地图 API Key
AMAP_KEY=your_amap_key

# 安全密钥
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret
```

### 获取 API Key

- 高德地图: https://lbs.amap.com/
- 天行数据: https://www.tianapi.com/

---

## 📖 文档

- [演示文档](docs/演示文档.md)
- [部署指南](docs/DOCKER_DEPLOY.md)
- [API文档](docs/API.md)
- [大数据平台文档](docs/BIGDATA.md)

---

## 🎨 界面预览

### 数据大屏
科技感设计，深色主题，适合演示汇报

### 3D地球
Three.js 实现多车并发轨迹动画

### 移动端
微信小程序司机端完整功能

---

## 👥 团队

| 成员 | 角色 |
|------|------|
| 小宇 | 项目负责人、产品设计 |
| 小彩 (AI) | 开发工程师、架构师 |

---

## 📄 License

MIT License

---

**开发周期**: 2026-03-18 ~ 2026-04-06（持续迭代中）

**项目口号**: 让每一公里都有意义 🚚
