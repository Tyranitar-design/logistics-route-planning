# 🧠 Claude Code 专属记忆

> 这是 Claude Code 的长期记忆文件，记录经验教训、代码模式、项目知识。
> **最后更新**：2026-06-19

---

## 经验教训

### 2026-06-19 · 改配置/文档前先顺链路核实
**场景**：要把 `.env.example` / `数据库设计.md` 对齐 PostgreSQL。
**教训**：不能凭"项目已切 PostgreSQL"一句话就改。先顺链路查清：
- `config.py` 真实读哪个环境变量（`POSTGRES_DATABASE_URL`）
- 生产是谁拼连接串（`docker-compose.prod.yml` 第 50-51 行从分项变量拼）
- 结果发现 `.env.production.example` 的分项写法**本身是对的**（compose 负责拼），只是缺注释解释；而 `backend/.env.example`（本地）才该直接给连接串。两份文件职责不同，改法不同。
**How to apply**：改配置/文档前，先把"生产链路 / 本地链路 / 默认兜底"三条路径的实际代码读一遍再动笔。

### 2026-06-19 · 记忆系统要随代码演进
**场景**：`.shared-memory` 停在 4 月学习阶段，但代码已到 6 月指挥中心 + 多求解器。
**教训**：TASKS.md / daily 日志若只记"学习调研"，工程演进会无人记录，新会话进来抓瞎。
**How to apply**：完成工程性改动后，及时更新 PROGRESS.md / DECISIONS.md / 当日 daily，保持记忆与代码同步。

---

## 代码模式库

### 模式 1: OR-Tools 通用求解器
```python
# 标准流程：Manager → Routing → Callback → Dimension → Solve → Extract
# 关键：约束添加顺序为 距离→容量→时间→配对→时间窗
```

### 模式 2: Flask API 路由
```python
# 标准格式：Blueprint → 路由函数 → 数据验证 → 业务逻辑 → 返回JSON
```

### 模式 3: Vue 3 组件
```vue
<!-- 标准格式：<script setup> → ref/reactive → onMounted → methods → template -->
```

### 模式 4: 数据库连接双轨（PostgreSQL 优先）
```python
# backend/config.py：POSTGRES_DATABASE_URL > DATABASE_URL > SQLite 兜底
# 生产：docker-compose.prod.yml 从 POSTGRES_USER/PASSWORD/DB 拼连接串注入
# 本地：直接设 POSTGRES_DATABASE_URL 整串
```

---

## 项目知识

### 物流系统架构（2026-06）
- 后端：Flask 3.0 + SQLAlchemy 2.0 + JWT + SocketIO + **多求解器引擎**
- 前端：Vue 3 + Element Plus + ECharts + Leaflet + Three.js
- 数据库：**PostgreSQL + PostGIS**（生产）/ SQLite（开发兜底）
- 缓存：Redis 7
- 部署：`docker-compose.prod.yml`（腾讯云，核心 4 服务）+ `scripts/deploy_tencent_cloud_command_center.py`

### 当前主线：统一调度（dispatch orchestration）
- `data_source=auto` → 优先读 `shipment_facts`（5 万），回退 `orders`
- `/dispatch/preview` 只预览不写库；`/dispatch/apply` 写 `dispatch_scenarios`/`dispatch_assignments`
- AI（DQL/DQN）shadow mode，硬约束由调度引擎保底

### 关键文件位置
- 调度编排（最新）：`backend/app/services/dispatch_orchestration_service.py`
- 调度服务：`backend/app/services/dispatch_service.py`
- 智能调度 V2：`backend/app/services/smart_dispatch_service_v2.py`
- 多求解器引擎：`backend/app/services/optimization_engine/`
- 路径算法：`backend/app/services/path_algorithm.py`
- ML 预测：`backend/app/services/prediction_service.py`
- 数据模型：`backend/app/models/`
- 配置：`backend/config.py`
- 权威部署文档：`docs/COMMAND_CENTER_DEPLOYMENT.md`

### 开发规范
- 中文注释、中文 Git commit message
- TDD: RED → GREEN → REFACTOR
- 不删 C 盘文件

---

## 待同步给小彩

_（暂无 —— 本次成果已在对话中同步小彩）_

---

_最后更新: 2026-06-19（C哥）_
