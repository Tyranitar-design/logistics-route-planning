# 📖 CONTEXT.md - 项目上下文与技术栈

> 一份随时可查的"项目说明书"，给小彩 / C哥 / 小宇对齐认知用。
> **最后更新**：2026-06-19

---

## 🎯 项目定位

**智慧物流路径规划系统** → 已升级为 **物流指挥中心（Logistics Command Center）+ 大屏 Dashboard**。

- **在线 Demo**：https://logistics-demo-yu.top
- **GitHub**：https://github.com/Tyranitar-design/logistics-route-planning
- **当前工作副本**：`C:\tmp\logistics-route-command-center-layout-dashboard-shell`（独立 .git / .claude / .shared-memory / openspec）
- **当前分支**：`codex/command-center-layout-dashboard-shell`

---

## 🧑‍🤝‍🧑 协作模式

| 角色 | 身份 | 职责 |
|------|------|------|
| **小彩** | OpenClaw AI | 项目管家：规划、部署、记忆、系统操作 |
| **C哥** | Claude Code | 代码专家：代码生成、审查、优化、Bug 修复 |
| **小宇** | 项目负责人 | 需求、决策、验收 |

---

## 🧱 技术栈

### 后端
- **语言**：Python 3.10
- **框架**：Flask 3.0 + Flask-SQLAlchemy 3.1 + Flask-JWT-Extended 4.6 + Flask-SocketIO 5.3
- **ORM**：SQLAlchemy 2.0
- **优化求解**：OR-Tools（核心）+ PyVRP / Gurobi / PuLP / pymoo / 遗传 / ALNS / 列生成 / 拉格朗日 / DRL-VRP（9 种求解器，渐进式可用）
- **其他**：redis 4.5、kafka-python、pandas 2.2、numpy 1.26、openpyxl、reportlab
- **依赖清单**：`backend/requirements.txt`

### 前端
- **框架**：Vue 3 + Vite
- **UI**：Element Plus
- **可视化**：ECharts / Leaflet / Three.js
- **页面**：45+ views（含 bigdata/ 大屏子模块 13 页、Earth3DPage、Pareto、多目标、网络设计）

### 数据与基础设施
- **数据库**：PostgreSQL + PostGIS（生产主库，镜像 `postgis/postgis:18-3.6-alpine`）
- **缓存**：Redis 7
- **生产编排**：`docker-compose.prod.yml`（核心 4 服务：postgres / redis / backend / frontend）
- **数据库连接优先级**：`POSTGRES_DATABASE_URL` > `DATABASE_URL` > 本地 SQLite 兜底

### 额外模块
- `miniprogram/` 微信小程序
- `flink/` 流处理
- `openspec/` 变更提案（3 个）

---

## 🗂️ 核心目录结构

```
backend/
├── config.py                    # Flask 配置（4 套：dev/prod/docker/testing）
├── requirements.txt
├── app/
│   ├── models/                  # 数据模型（user/node/route/vehicle/order/dispatch/task/audit/oil_price/supplier/layered_data/network）
│   ├── routes/                  # API 路由（49 个 Blueprint）
│   └── services/                # 业务服务
│       ├── optimization_engine/ # 🧠 多求解器引擎（9 种 solver + operators + metrics + solver_factory）
│       ├── dispatch_orchestration_service.py  # 🚚 统一调度编排（最新主线）
│       ├── dispatch_service.py / smart_dispatch_service_v2.py
│       ├── path_algorithm.py / vrp_problem_builder.py
│       ├── multi_objective.py
│       ├── lightweight_bigdata.py / kafka_*.py
│       ├── tianditu_service.py / amap_service.py
│       └── ...
docs/                            # 文档（COMMAND_CENTER_DEPLOYMENT / 数据库设计 / ...）
docker-compose.prod.yml          # 生产编排
scripts/                         # 部署 / 烟雾测试脚本
.shared-memory/                  # 小彩记忆系统
openspec/                        # 变更提案
```

---

## 🚚 核心运行链路（统一调度 dispatch）

最新主线（commit `72472c4 unified shipment dispatch orchestration`）：

1. **数据源**：`data_source=auto` → 优先读 PostgreSQL `shipment_facts`（5 万真实物流明细），无可用数据时回退旧 `orders` 表
2. **预览**：`POST /api/dispatch/preview` → 生成调度方案预览（不写库），返回 plans / unassigned / diagnostics / solver / authenticity_level
3. **执行**：`POST /api/dispatch/apply` → 写入 `dispatch_scenarios` / `dispatch_assignments`（审计/回放/训练样本）
4. **AI 辅助**：DQL/DQN 处于 shadow mode，只提供风险/ETA/策略评分元数据；硬约束（容量、车辆、唯一分配）由调度引擎保底
5. **波次控制**：5 万明细不一次性求解，前端/API 通过 dispatch wave 控制波次

烟雾测试脚本：`scripts/_tmp_dispatch_smoke.py`（打线上 /auth/login → /dispatch/health → /dispatch/preview）

---

## 🗺️ 地图与外部服务

- **高德地图**：优先真实服务；DNS/IPv6/服务不可用时返回 `provider_status=degraded` 降级（前端显示"高德降级估算"）
- **天地图**：TIANDITU_BROWSER_KEY / TIANDITU_SERVER_KEY
- **AMAP_RESTAPI_IPV4**：固定高德 CDN IP，规避 Docker DNS 抖动

---

## 📐 开发规范

- **中文注释** + **中文 Git commit message**
- **TDD**：RED → GREEN → REFACTOR
- **SDD**：先规划后开发
- **安全铁律**：不删 C 盘文件，不执行危险操作
- 不提交真实密钥 / `.env.production` / API Key 到 Git

---

## 📚 关键文档索引

| 文档 | 用途 |
|------|------|
| `docs/COMMAND_CENTER_DEPLOYMENT.md` | 生产部署 + 数据库口径（**最权威**） |
| `docs/数据库设计.md` | 数据库设计（已对齐 PostgreSQL） |
| `.shared-memory/MEMORY_ARCHITECTURE.md` | 记忆系统说明 |
| `CODE_REVIEW_REPORT.md` | 代码审查报告（3 月，3 个低优待办） |
| `skills/or-tools-logistics-expert-2.0.0/SKILL.md` | OR-Tools 技能知识库 |

---

_最后更新：2026-06-19（C哥建立）_
