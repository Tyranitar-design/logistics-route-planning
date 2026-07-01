# 🧠 Claude Code 专属记忆

> 这是 Claude Code 的长期记忆文件，记录经验教训、代码模式、项目知识。
> **最后更新**：2026-06-19

---

## 经验教训

### 2026-07-01 · 接手他人未提交工作时先验证再改
**场景**：codex 做了 117 文件大改动（AI/Gurobi/调度/Next 壳）但没提交、没验证，工作区"非常脏"。
**教训**：不能凭 AGENTS.md/记忆说"曾记录通过"就信。先跑测试 + build 验证当前真实状态，再决定改什么。本次验证发现 codex 工作质量其实过硬（68 测试全过），但记忆/文档和代码提交脱节，需 C哥验证 + 固化。
**How to apply**：接手他人工作区时，第一步 `git status` + 跑核心测试 + build，建立"当前真实状态"基线再动笔。

### 2026-07-01 · 风格统一最小破坏法：保 CSS 变量名只改值
**场景**：frontend-next globals.css 1640 行要换成深色风。
**教训**：原文件大量用 `var(--teal)` 等变量引用。保持变量名不变只改 :root 的值，所有引用自动变色；再手动处理硬编码颜色 + 给面板加 `backdrop-filter`。布局属性（grid/flex/padding）一律不动，绝不会塌陷。
**How to apply**：大 CSS 改皮时，先识别 var() 引用（改 :root 值）vs 硬编码（手动改），布局零改动，改完 playwright 截图每页验证。详见 [[2026-07-01-css-skin-minimal-change]]。

### 2026-07-01 · 提交大改动前必须截图验证视觉
**场景**：改了 1640 行 CSS，typecheck/build 只能证明不报错，不能证明好看。
**教训**：用 playwright 截图 5 个关键页面（首页/AI预测/异常/调度/登录）实际渲染，才能发现潜在对比度/塌陷问题。本次无问题，但流程必须有。
**How to apply**：前端视觉改动后，playwright 截图 5 页（首页/最复杂页/表单页/登录/空状态），人工 review 后再提交。

---

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

### 2026-06-19 · 数据真实性要交叉验证，不凭印象
**场景**：补坐标时发现 37% origin_city_std 是 NULL，raw 是"凤英县/倩县/红梅市"等。
**教训**：不能凭"看起来像地名"就当真实。用 area_format 行政区划名录（29508 条真实行政区划）+ Grep 双重验证，确认这 11 个是**虚构地名**（合成数据"人名+县/市"模板造的）。真实城市（乐清/成县等）全部在名录 YES，虚构全部 NO。
**How to apply**：数据真实性存疑时，用权威名录/数据源交叉验证，不靠模型常识判断；给虚构地名编坐标=造假，必须如实上报让负责人决策。

### 2026-06-19 · 性能问题找根因，别在表象打转
**场景**：dispatch 精确距离 solve_time 188 秒。
**教训**：根因是 `_build_order_distance_lookup` 建 40×40=1600 对全矩阵，但只用 20 对（origin→destination）。1580 对废计算 + 跨 order 废对触发 IMPLAUSIBLE 逐对兜底 → 雪崩。改成逐对查询（1600→20）→ 17.83ms（提升 10000 倍）。
**How to apply**：性能优化先定位"算了多少 vs 用了多少"，砍废计算比优化算法更有效。优化后必须验证不回退（本次 authenticity 曾因 source 字符串误判从 B 掉到 B-，二次修复 source 规范化才稳）。

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

_最后更新: 2026-07-01（C哥）_
