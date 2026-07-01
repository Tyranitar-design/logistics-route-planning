# 📋 TASKS.md - 学习任务追踪

> ⚠️ 下方「学习任务」为 **4 月调研阶段**记录（已归档）。
> 当前工程主线任务见顶部「🛠️ 当前任务（2026-06）」。

---

## 🛠️ 当前任务（2026-07）

### ✅ 已完成
- [x] **2026-07-01 codex 未提交工作固化 + Next 壳风格统一**（C哥）
  - 接手 codex 117 文件未提交工作区，验证 68 测试 + build 全绿
  - frontend-next 浅色商务风 → **深色科幻指挥中心大屏**（对齐 Vue command-center-theme）
  - 4 commit 固化：`f467bf3` 后端 / `a849852` Next 壳 / `6237c95` Vue+配置 / `d440a32` AGENTS+记忆
  - AGENTS.md 协作指南 + .codex 记忆系统建立
  - 详见 `.shared-memory/daily/2026-07-01.md`
- [x] **2026-06-19 文档对齐 PostgreSQL**（C哥）
  - `backend/.env.example` 补 `POSTGRES_DATABASE_URL` + Redis + `DISABLE_ML_ROUTES`
  - `.env.production.example` 加"分项变量 → compose 拼接 → Flask"双轨机制注释
  - `docs/数据库设计.md` 选型/迁移/规模对齐 PostgreSQL+PostGIS
- [x] **2026-06-19 补齐 .shared-memory 三件套**（C哥）
  - 新建 `PROGRESS.md` / `CONTEXT.md` / `DECISIONS.md`
  - 更新 `TASKS.md` / `MEMORIES.md`，写今日 daily 日志

### ⏳ 进行中 / 待办
- [ ] **部署线上**：4 个新 commit（`f467bf3`/`a849852`/`6237c95`/`d440a32`）推线上，待小宇确认
- [ ] **frontend-next 生产部署评估**：Next 壳目前仅本地 5174，需评估是否纳入 `docker-compose.prod.yml` 或独立部署
- [ ] **CODE_REVIEW 剩余 2 低优**：信息素持久化（ACO）、自适应冷却（SA）
- [ ] **Node/Route 坐标审查**：21 节点 / 306 路线（已有 `node_route_audit_service`，待人工复核真实性）
- [ ] **线上 dispatch 链路烟雾测试**（需联网 + admin 凭据，待小宇确认）

---

## 📚 历史学习任务（2026-04 调研阶段 · 归档）

## 📅 2026-04-24 学习任务（今日）

### 🔴 高优先级

- [ ] **Vehicle-Routing-Optimizer OR-Tools实战**
  - 仓库: https://github.com/A-M-Amine/Vehicle-Routing-Optimizer
  - 目标: 深入理解 OR-Tools API 架构，掌握 VRP 变种建模
  - 预计时间: 2小时
  - 产出: 架构笔记 + GeoJSON 可视化理解

- [ ] **Metaheuristic-Optimization 算法深化**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 深入理解 GA/ACO/PSO 实现细节与适用场景
  - 预计时间: 2小时
  - 产出: 算法实现对比分析

### 🟡 中优先级

- [ ] **Local Streaming Pipeline 实时数据管道**
  - 仓库: https://github.com/MarkPhamm/local_streaming_pipeline
  - 目标: 理解 Kafka → Spark/Flink → ClickHouse 管道架构
  - 预计时间: 1.5小时
  - 产出: 架构图 + 容器化部署理解

- [ ] **MCP Agent 智能体框架探索**
  - 仓库: https://github.com/lastmile-ai/mcp-agent
  - 目标: 理解 MCP 协议与 AI Agent 构建模式
  - 预计时间: 1.5小时
  - 产出: MCP 协议笔记 + Agent 架构理解

### 🟢 拓展优先级

- [ ] **Reinforcement Learning PPO 强化学习**
  - 仓库: https://github.com/lajoiepy/Reinforcement_Learning_PPO
  - 目标: 理解 DQN/PPO 算法基础，为动态调度做储备
  - 预计时间: 1小时
  - 产出: 强化学习入门笔记

---

## 📅 2026-04-23 学习任务

### 🔴 高优先级

- [ ] **Vehicle-Routing-Optimizer OR-Tools实战**
  - 仓库: https://github.com/A-M-Amine/Vehicle-Routing-Optimizer
  - 目标: 深入理解OR-Tools API架构，掌握VRP变种建模
  - 预计时间: 2小时
  - 产出: 架构笔记 + GeoJSON可视化理解

- [ ] **Metaheuristic-Optimization 算法深化**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 深入理解 GA/ACO/PSO 实现细节与适用场景
  - 预计时间: 2小时
  - 产出: 算法实现对比分析

### 🟡 中优先级

- [ ] **Local Streaming Pipeline 实时数据管道**
  - 仓库: https://github.com/MarkPhamm/local_streaming_pipeline
  - 目标: 理解 Kafka → Spark/Flink → ClickHouse 管道架构
  - 预计时间: 1.5小时
  - 产出: 架构图 + 容器化部署理解

- [ ] **Agent-MCP 多智能体框架探索**
  - 仓库: https://github.com/rinadelph/Agent-MCP
  - 目标: 理解 MCP 协议与多智能体协作模式
  - 预计时间: 1.5小时
  - 产出: MCP 协议笔记 + Agent 架构理解

### 🟢 拓展优先级

- [ ] **EVRP-Python 电动车VRP学习**
  - 仓库: https://github.com/NeiH4207/EVRP-Python
  - 目标: 理解电动车续航约束建模，为新能源物流做准备
  - 预计时间: 1小时
  - 产出: 电动车VRP建模笔记

---

## 📅 2026-04-21 学习任务

### 🔴 高优先级

- [ ] **PyVRP 开源VRP求解器学习**
  - 仓库: https://github.com/PyVRP/PyVRP
  - 目标: 理解求解器架构设计，作为物流系统核心引擎
  - 预计时间: 2小时
  - 产出: 架构笔记 + API 使用理解

- [ ] **Local Streaming Pipeline 实时数据管道**
  - 仓库: https://github.com/MarkPhamm/local_streaming_pipeline
  - 目标: 理解 Kafka → Spark/Flink → ClickHouse 管道架构
  - 预计时间: 2小时
  - 产出: 架构图 + 组件理解

### 🟡 中优先级

- [ ] **Metaheuristic-Optimization 算法深化**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 深入理解 GA/ACO/PSO 实现细节
  - 预计时间: 1.5小时
  - 产出: 算法实现对比分析

- [ ] **Agent-MCP 多智能体框架探索**
  - 仓库: https://github.com/rinadelph/Agent-MCP
  - 目标: 理解 MCP 协议与多智能体协作模式
  - 预计时间: 1.5小时
  - 产出: MCP 协议笔记 + Agent 架构理解

### 🟢 拓展优先级

- [ ] **VRP-GA 遗传算法入门**
  - 仓库: https://github.com/wojzam/VRP
  - 目标: 复习遗传算法在VRP中的基础应用
  - 预计时间: 1小时
  - 产出: 入门笔记

---

## 📅 2026-04-20 学习任务

### 🔴 高优先级

- [ ] **Vehicle-Routing-Optimizer 架构学习**
  - 仓库: https://github.com/A-M-Amine/Vehicle-Routing-Optimizer
  - 目标: 理解 OR-Tools API 架构设计，运行并分析
  - 预计时间: 2小时
  - 产出: 架构笔记 + API 设计理解

- [ ] **Metaheuristic-Optimization 算法对比**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 对比 GA/ACO/PSO 实现差异与适用场景
  - 预计时间: 2小时
  - 产出: 算法对比分析文档

### 🟡 中优先级

- [ ] **mcp-agent AI智能体框架**
  - 仓库: https://github.com/lastmile-ai/mcp-agent
  - 目标: 理解 MCP 协议规范与 Agent 构建方式
  - 预计时间: 1.5小时
  - 产出: MCP 协议理解 + Agent 架构笔记

- [ ] **RealTime-Flink-Analytics 架构学习**
  - 仓库: https://github.com/kuldeep27396/RealTime-ECommerce-Analytics-Flink
  - 目标: 理解 Kafka+Flink+ClickHouse 实时数据管道
  - 预计时间: 1.5小时
  - 产出: 架构图 + 组件理解

### 🟢 拓展优先级

- [ ] **MetaGPT 多智能体框架调研**
  - 仓库: https://github.com/FoundationAgents/MetaGPT
  - 目标: 了解多 Agent 协作架构设计
  - 预计时间: 1小时
  - 产出: 多智能体架构笔记

---

## 📅 2026-04-19 学习任务

### 🔴 高优先级

- [ ] **wojzam/VRP 遗传算法VRP实现**
  - 仓库: https://github.com/wojzam/VRP
  - 目标: 遗传算法核心代码分析，理解VRP建模方式
  - 预计时间: 2小时
  - 产出: 核心算法笔记 + 架构理解

- [ ] **VRP-Models-and-Algorithms 精确解法学习**
  - 仓库: https://github.com/RenatoMaynard/VRP-Models-and-Algorithms
  - 目标: 理解Gurobi求解器在VRP中的应用
  - 预计时间: 2小时
  - 产出: 数学建模笔记

### 🟡 中优先级

- [ ] **mcp-agent AI智能体框架**
  - 仓库: https://github.com/lastmile-ai/mcp-agent
  - 目标: 理解MCP协议与Agent构建方式
  - 预计时间: 2小时
  - 产出: MCP协议理解 + Agent架构笔记

### 🟢 拓展优先级

- [ ] **Metaheuristic-Optimization 算法对比**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 对比GA/ACO/PSO实现差异
  - 预计时间: 1.5小时
  - 产出: 算法对比分析

- [ ] **RealTime-Flink-Analytics 架构学习**
  - 仓库: https://github.com/kuldeep27396/RealTime-ECommerce-Analytics-Flink
  - 目标: 理解Kafka+Flink+ClickHouse架构
  - 预计时间: 1.5小时
  - 产出: 架构图 + 组件理解

---

## 📅 2026-04-18 学习任务

### 🔴 高优先级

- [ ] **VRP遗传算法项目深入学习**
  - 仓库: https://github.com/wojzam/VRP
  - 目标: 理解遗传算法核心实现，运行并分析结果
  - 预计时间: 2小时
  - 产出: 核心代码分析笔记 + 运行截图

- [ ] **元启发式算法对比学习**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 对比GA/ACO/PSO在VRP问题上的表现
  - 预计时间: 2小时
  - 产出: 算法性能对比分析文档

### 🟡 中优先级

- [ ] **Flink实时分析管道研究**
  - 仓库: https://github.com/kuldeep27396/RealTime-ECommerce-Analytics-Flink
  - 目标: 理解实时数据流处理架构
  - 预计时间: 1.5小时
  - 产出: 架构图 + 关键组件理解

- [ ] **Kafka/Spark/Flink管道搭建**
  - 仓库: https://github.com/MarkPhamm/local_streaming_pipeline
  - 目标: 本地环境搭建体验
  - 预计时间: 1.5小时
  - 产出: 本地运行环境

### 🟢 拓展优先级

- [ ] **AI Agent框架趋势调研**
  - 链接: https://alphacorp.ai/blog/the-8-best-ai-agent-frameworks-in-2026-a-developers-guide
  - 目标: 了解2026年多智能体框架发展
  - 预计时间: 1小时
  - 产出: 技术趋势笔记

---

## 📅 2026-04-17 学习任务

### 🔴 高优先级

- [ ] **VRP遗传算法项目学习**
  - 仓库: https://github.com/wojzam/VRP
  - 目标: 理解遗传算法在VRP中的应用
  - 预计时间: 4小时
  - 产出: 学习笔记 + 代码运行截图

- [ ] **元启发式算法对比学习**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 掌握GA/ACO/PSO三种算法
  - 预计时间: 4小时
  - 产出: 算法对比分析文档

### 🟡 中优先级

- [ ] **Kafka/Flink实时管道搭建**
  - 仓库: https://github.com/MarkPhamm/local_streaming_pipeline
  - 目标: 搭建本地实时数据管道
  - 预计时间: 3小时
  - 产出: 本地运行环境

- [ ] **MCP多智能体框架调研**
  - 链接: https://github.blog/open-source/maintainers/from-mcp-to-multi-agents-the-top-10-open-source-ai-projects-on-github-right-now-and-why-they-matter/
  - 目标: 理解MCP协议与Agent协作
  - 预计时间: 2小时
  - 产出: 技术调研笔记

### 🟢 基础优先级

- [ ] **Spark实时分析项目学习**
  - 仓库: https://github.com/RichardAfolabi/Realtime-Data-Analytics-Using-Spark
  - 目标: 巩固Spark生态知识
  - 预计时间: 2小时
  - 产出: 复习笔记

---

## 📊 本周学习计划

| 日期 | 主要任务 | 预计时长 |
|------|---------|---------|
| 周一 (04/27) | VeRyPy经典算法 + EVRP + 元启发式 | 6h |
| 周二 (04/28) | 算法深化 + 实验对比 | 4h |
| 周三 (04/29) | Flink实时管道 + 架构理解 | 3h |
| 周四 (04/30) | MCP Agent框架 + 整合思考 | 3h |
| 周五 (05/01) | 本周总结 + 知识整合 | 2h |

---

## 📝 完成记录

_在此记录已完成的任务及心得_

---

---

## 📅 2026-04-27 学习任务（今日）

### 🔴 高优先级

- [ ] **VeRyPy 经典VRP算法库学习**
  - 仓库: https://github.com/yorak/VeRyPy
  - 目标: 理解15+种经典VRP算法实现，掌握算法接口抽象设计
  - 预计时间: 2小时
  - 产出: 算法对比笔记 + 运行截图

- [ ] **EVRP-Python 电动车路径规划**
  - 仓库: https://github.com/NeiH4207/EVRP-Python
  - 目标: 理解电动车续航约束建模，对比传统VRP差异
  - 预计时间: 2小时
  - 产出: EVRP建模笔记 + 新能源物流场景分析

- [ ] **Metaheuristic-Optimization 算法深化**
  - 仓库: https://github.com/AliAmini93/Metaheuristic-Optimization
  - 目标: 深入GA/ACO/PSO中的一种，理解核心实现细节
  - 预计时间: 2小时
  - 产出: 算法源码分析 + 参数调优心得

### 🟡 中优先级

- [ ] **Real-Time Streaming Analytics 实时管道**
  - 仓库: https://github.com/TanishkaMarrott/Real-Time-Streaming-Analytics-with-Kinesis-Flink-and-OpenSearch
  - 目标: 理解 Kinesis → Flink → OpenSearch 完整管道架构
  - 预计时间: 1.5小时
  - 产出: 架构图 + 组件职责理解

- [ ] **MCP-Agent 智能体框架探索**
  - 仓库: https://github.com/lastmile-ai/mcp-agent
  - 目标: 理解MCP协议规范，跑通官方示例
  - 预计时间: 1.5小时
  - 产出: MCP协议笔记 + Agent架构理解

---

*最后更新: 2026-04-27*
