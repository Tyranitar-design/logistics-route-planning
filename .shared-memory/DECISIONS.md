# 🧭 DECISIONS.md - 技术决策记录（ADR）

> 记录项目关键技术选型与决策的"为什么"。
> **最后更新**：2026-06-19

---

## ADR-001 数据库：SQLite/MySQL → PostgreSQL/PostGIS

- **决策**：生产主库统一为 **PostgreSQL + PostGIS**，SQLite 仅作开发兜底。
- **背景**：早期 SQLite 演示库不支持空间能力，MySQL 曾被列为备选。
- **理由**：物流场景强依赖地理空间计算（地理围栏、空间索引），PostGIS 是成熟方案；与 SQLAlchemy/psycopg2 生态契合。
- **落地**：`backend/config.py` 连接串优先级 `POSTGRES_DATABASE_URL` > `DATABASE_URL` > SQLite；`docker-compose.prod.yml` 用 `postgis/postgis:18-3.6-alpine`，compose 从分项变量拼连接串注入 Flask。
- **影响**：`docs/数据库设计.md` 原以 MySQL 为生产首选，已对齐（2026-06-19）。

---

## ADR-002 优化引擎：多求解器 + 统一工厂

- **决策**：构建 `optimization_engine/`，集成 **9 种求解器**（OR-Tools / PyVRP / Gurobi / PuLP / pymoo / 遗传 / ALNS / 列生成 / 拉格朗日 / DRL-VRP），通过 `solver_factory` + `comparison` 统一调度。
- **理由**：不同 VRP 变种/规模适用不同算法；统一接口便于对比与 A/B，`metrics/pareto_metrics` 支持真实多目标 Pareto。
- **注意**：`requirements.txt` 目前只锁了 PuLP + psycopg2，其余求解器为**软依赖**（try/import 动态加载，缺失时 fallback）。如需启用需补装对应库。

---

## ADR-003 调度：统一 dispatch 编排（preview/apply 分离）

- **决策**：`dispatch_orchestration_service` 统一调度链路，`/dispatch/preview` 只预览不写库，`/dispatch/apply` 才落库（`dispatch_scenarios` / `dispatch_assignments`）。
- **理由**：5 万明细不可一次性求解；preview/apply 分离支持人工确认 + 审计回放 + AI 训练样本采集。
- **AI 边界**：DQL/DQN 处于 **shadow mode**，只产风险/ETA/策略评分元数据；硬约束由调度引擎保底。
- **数据源**：`data_source=auto` 优先读 `shipment_facts`，无可用数据时回退旧 `orders` 表。

---

## ADR-004 大数据：轻量化替代重型栈

- **决策**：用 `lightweight_bigdata.py` 替代 Kafka/Spark/Flink 重型组合。
- **理由**：腾讯云核心部署只起 4 个服务（postgres/redis/backend/frontend），重型大数据栈运维成本过高；轻量服务满足大屏展示与基本流处理需求。
- **保留**：`flink/`、`docker-compose-bigdata*.yml`、`kafka_*_service.py` 仍保留在仓库，供需要时启用。

---

## ADR-005 地图：高德优先 + 降级容错

- **决策**：地图/天气优先调高德真实服务，失败时返回 `provider_status=degraded` 友好降级（前端显示"高德降级估算"）。
- **理由**：避免云主机 DNS/IPv6/服务抖动导致整页中断；`extra_hosts` 固定高德 CDN IP 进一步稳定。
- **天地图**：作为备用底图服务（`tianditu_service.py`）。

---

_最后更新：2026-06-19（C哥建立，基于 git 历史 + 部署文档反推）_
