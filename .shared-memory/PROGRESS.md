# 📈 PROGRESS.md - 项目进度

> 记录项目演进的关键里程碑与当前状态。
> **最后更新**：2026-06-19

---

## 🏁 当前状态（2026-06-19）

✅ **指挥中心 + 大屏 Dashboard 已上线**（https://logistics-demo-yu.top）
✅ **数据库已切换 PostgreSQL/PostGIS**（生产核心 4 服务：postgres / redis / backend / frontend）
✅ **多求解器引擎就绪**（9 种 solver + operators + Pareto metrics + solver_factory）
✅ **统一调度编排（dispatch orchestration）打通**（preview / apply / 健康检查链路）
✅ **文档与记忆系统对齐 PostgreSQL/工程现状**（2026-06-19 C哥完成）

---

## 🛠️ 已知待办

1. ~~`.env.example` / `docs/数据库设计.md` 对齐 PostgreSQL~~ ✅ 2026-06-19 C哥完成
2. ~~`.shared-memory` 补齐 PROGRESS.md / CONTEXT.md / DECISIONS.md~~ ✅ 2026-06-19 C哥完成
3. **`CODE_REVIEW_REPORT.md`（3 月）3 个低优尾巴**：信息素持久化、自适应冷却、配置化成本
4. **`scripts/_tmp_dispatch_smoke.py`** 为 untracked 临时脚本，待清理或纳入正式测试
5. `backend/config.py` 第 33/81 行重复 `.replace('\\','/')`（无害冗余，可顺手清理）
6. 线上 dispatch 链路烟雾测试（需联网 + admin 凭据，待小宇确认）

---

## 🛣️ 里程碑（基于 git 历史，倒序）

| 时间 | Commit | 内容 |
|------|--------|------|
| 最近 | `72472c4` | feat: 统一运单调度编排（dispatch orchestration） |
| - | `2c36ad0` | feat: 升级物流指挥中心部署 |
| - | `ef9f42a` | fix: 优化引擎 6 大问题修复（统一链路 + PyVRP 兼容 + 真实 Pareto + duration_matrix） |
| - | `29cf580` | feat: 轻量级大数据服务（替代 Kafka/Spark/Flink 重型栈） |
| - | `671b9e9` | feat: 优化引擎 + 智能调度 V2 + 天地图服务 |
| 早期 | - | Flask + Vue + OR-Tools 基础框架 / SQLite → PostgreSQL 切换 |

---

## 📊 生产数据规模（已验证）

| 表 | 记录数 |
|----|--------|
| `shipment_facts` | 50,000 |
| `raw_logistics_shipment_records` | 50,000 |
| `nodes` | 21 |
| `routes` | 306 |
| `vehicles` | 2 |

> 来源：`docs/COMMAND_CENTER_DEPLOYMENT.md`

---

## 🧠 记忆系统演进

- **4 月**：学习调研阶段（VeRyPy / PyVRP / Metaheuristic / MCP 等开源仓库学习）—— `TASKS.md` / `daily/` 记录停留于此
- **5-6 月**：工程化阶段（指挥中心、多求解器引擎、PostgreSQL、统一调度）—— 代码大幅演进，记忆系统本次（2026-06-19）补齐对齐

---

_最后更新：2026-06-19（C哥建立）_
