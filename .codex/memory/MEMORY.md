# 物流路径规划项目热启动记忆

Last updated: 2026-07-01
Workspace: `C:\tmp\logistics-route-command-center-layout-dashboard-shell`
Branch observed: `codex/command-center-layout-dashboard-shell`

## 0. 接手第一眼

这是当前物流项目的新主线工作区，不是早期单体演示版。项目已经升级为“物流指挥中枢 / Logistics Command Center”，核心底座是 PostgreSQL/PostGIS + Flask + Vue，另有并行的 Next.js + TypeScript + Tailwind 决策控制台 `frontend-next/`。

进入本项目后先读：

1. `README.md`
2. `frontend-next/README.md`
3. `docs/FRONTEND_NEXT_FOUNDATION_2026-06-20.md`
4. `docs/DISPATCH_LEARNING_DATASET_2026-06-20.md`
5. `docs/AI_PREDICTION_BASELINE_2026-06-20.md`
6. `docs/AI_ANOMALY_DETECTION_2026-06-20.md`
7. `docs/GUROBI_INTEGRATION_2026-06-19.md`
8. `docs/LOCAL_ROUTE_BENCHMARK_2026-06-20.md`
9. `docs/DISPATCH_ROUTE_TRUTH_2026-06-20.md`
10. `AGENTS.md`

## 1. 当前工作区状态

2026-07-01 检查时，工作区是脏的，有大量已修改和未跟踪文件。不要回滚、清理、重置或覆盖不属于当前任务的改动。

已观察到的修改集中在：

- 后端配置和蓝图注册：`backend/app/__init__.py`、`backend/config.py`
- 地图/provider：`backend/app/routes/amap.py`、`backend/app/routes/tianditu_route.py`、`backend/app/services/amap_service.py`、`backend/app/services/tianditu_service.py`、`backend/app/services/traffic_service.py`、`backend/app/services/weather_service.py`
- 调度：`backend/app/routes/dispatch.py`、`backend/app/services/dispatch_orchestration_service.py`
- 订单路线推荐：`backend/app/routes/orders.py`、`backend/app/services/order_route_service.py`
- Gurobi/优化：`backend/app/routes/optimization.py`、`backend/app/services/optimization_engine/solvers/gurobi_solver.py`
- Vue 地图页：`frontend/src/views/MapView.vue`、`frontend/src/api/amap.js`、`frontend/src/components/WeatherCard.vue`
- 新增 `frontend-next/`、AI 预测/异常服务、Gurobi 服务、本地路径 benchmark、节点/路线审计脚本、文档和测试。

先运行：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
git status --short
```

## 2. 稳定项目事实

- 后端入口：`backend/run.py`
- Flask app factory：`backend/app/__init__.py`
- 后端默认端口：`5000`
- 旧生产前端：`frontend/`，Vue 3 + Element Plus + Vite，默认端口 `5173`
- 新并行前端：`frontend-next/`，Next.js App Router + TypeScript + Tailwind，默认端口 `5174`
- 小程序：`miniprogram/`
- PostgreSQL/PostGIS 是主线数据库；SQLite 只作为历史/兼容兜底。
- 真实物流明细主源是 `shipment_facts`，用户反复强调是 5 万条真实 PostgreSQL 数据。
- 大数据目录仍保留，但腾讯云核心演示部署默认不启动大数据容器。

## 3. 核心边界

不要读取、打印、提交或写入以下敏感内容：

- 腾讯云 SSH 密码/密钥文件
- 高德/天地图 key 文件
- 本机 Gurobi license 文件
- `.env.production`
- 真实 JWT、cookie、token、数据库密码

AI/RL 边界：

- DQL/DQN 当前必须保持 shadow mode。
- DQL/DQN 只做评分、重排、动态重调度建议和离线训练准备。
- 容量、订单唯一分配、车辆可用性、时间窗、路径可行性等硬约束必须由 Gurobi/OR-Tools/ALNS/调度 solver 层保底。
- 不要让 shadow policy 直接修改 `shipment_facts`、`orders`、`vehicles`、`dispatch_scenarios` 或 `dispatch_assignments`。

## 4. 已落地能力快照

### 智能调度

- `dispatch_orchestration_service.py` 已从旧 `orders` 单源升级为 `shipment_facts` / `orders` 双源适配。
- `/api/dispatch/health` 返回真实数据源、车辆源、可调度数量、不可调度原因、truth metadata。
- `/api/dispatch/waves` 支持按筛选创建调度波次，避免 5 万单一次性求解。
- `/api/dispatch/preview` 支持 `persist: false`，Next SSR 预览不会反复写入场景。
- `/api/dispatch/apply`、`/api/dispatch/scenarios`、`/api/dispatch/scenarios/:id` 保留场景应用和历史回放。
- `dispatch_scenarios` / `dispatch_assignments` 是调度结果和后续 AI shadow 数据集的落点，不污染原始物流事实。

### 调度 AI shadow

- `/api/dispatch/learning-dataset` 把已落库场景/分配转为 `rl_shadow_dataset_v1`。
- `/api/dispatch/policy-scorer` 比较 historical、balanced、utilization-first、reliability-first、risk-averse、cost-guarded 等 shadow policies。
- `/api/dispatch/reward-model` 训练轻量 `linear_reward_ranker_v1` 离线 reward baseline。
- `/api/dispatch/redispatch-simulator` 提供延误、车辆不可用、成本放大、provider 降级等只读动态重调度模拟。
- `/api/dispatch/redispatch-profiles` 从真实异常信号生成模拟 profile。
- `/api/dispatch/rl-shadow-runner`、`/api/dispatch/fitted-q-shadow-model`、`/api/dispatch/shadow-benchmark` 是 DQL/DQN 前置 shadow 验证链路。

### AI 预测

- 新增 `backend/app/services/shipment_prediction_service.py`
- 新增 `backend/app/routes/ai_prediction.py`
- 真实 `shipment_facts` baseline 已覆盖 demand、ETA、delay、cost。
- 已新增时间序列 benchmark、运力缺口预测、成本波动预测、AI readiness scorecard。
- 主要接口：
  - `/api/ai-prediction/health`
  - `/api/ai-prediction/baseline/evaluate`
  - `/api/ai-prediction/demand/forecast`
  - `/api/ai-prediction/time-series/benchmark`
  - `/api/ai-prediction/capacity-gap/forecast`
  - `/api/ai-prediction/cost-volatility/forecast`
  - `/api/ai-prediction/scorecard`
  - `/api/ai-prediction/features/dataset`
  - `/api/ai-prediction/model/status`

### AI 异常检测

- 新增 `backend/app/services/shipment_anomaly_service.py`
- 新增 `backend/app/routes/ai_anomaly.py`
- 真实 `shipment_facts` 异常检测覆盖 status、geo、cost、ETA、delay、OD volume、node congestion 和可选 ML。
- IsolationForest 是可选增强，没有 scikit-learn 时接口必须解释降级原因。
- 主要接口：
  - `/api/ai-anomaly/health`
  - `/api/ai-anomaly/detect`
  - `/api/ai-anomaly/scorecard`
  - `/api/ai-anomaly/explain`

### 运营/成本分析

- `backend/app/services/shipment_cost_analytics_service.py` 支持真实 `shipment_facts` 运营/成本总览。
- `/api/analytics/operations-summary` 和 `/api/analytics/operations-scorecard` 已作为 Next 首页控制塔组件输入。

### Gurobi 和高级优化

- 用户提供过本机 Gurobi 安装位置和 license 位置，但严禁读取或输出 license 内容。
- 新增 `gurobi_capability_service.py`，能力探测比单纯 import 更严格。
- 已有接口：
  - `/api/optimization/gurobi/health`
  - `/api/optimization/gurobi/smoke`
  - `/api/optimization/gurobi/vehicle-assignment`
  - `/api/optimization/gurobi/vrp`
  - `/api/optimization/gurobi/network-design`
  - `/api/optimization/solver-benchmark`
  - `/api/optimization/route-sequence-benchmark`
- Gurobi 不可用时必须返回明确 `fallback_reason`，不能伪装成精确求解成功。

### 地图、provider 和本地路径算法

- 高德/天地图 provider 现在统一返回 `provider_status`、`fallback_reason`、`distance_source`、`path_source`、`authenticity_level`。
- `/api/amap/provider-health?probe=1` 汇总路线、天气、路况 provider 状态。
- `/api/amap/distance/cache/stats` 和 `/api/amap/distance/validate` 用于距离缓存健康和 OD 验证。
- `/api/amap/route/local-benchmark` 已成为后端统一本地路径算法对比入口，支持 Dijkstra/A* 多策略和 `provider_sources=["amap","tianditu"]`。
- 本地路径是节点/Route 图序列，provider polyline 是真实道路几何；二者只能对比，不能混成同一真实性等级。
- `/api/tianditu/keys` 只返回 key 状态，不暴露 key。
- `/api/tianditu/compare/amap` 用于天地图/高德路线对比。

### 订单路线推荐和节点路线审计

- `/api/orders/<id>/recommend-route` 已做 ShipmentFact 兼容，legacy `orders` 为空时仍可按真实运单推荐路线。
- `/api/orders/recommend-route` 支持按节点显式推荐。
- 节点/路线坐标审计接口：
  - `/api/nodes/coordinate-audit`
  - `/api/nodes/route-coordinate-audit`
  - `/api/nodes/<id>/resolve-coordinates`
- 辅助脚本：
  - `scripts/audit_node_route_coordinates.py`
  - `scripts/backfill_route_distances.py`

### Next.js 决策控制台

`frontend-next/` 是现代化迁移入口，不替换 Vue 生产入口。现有页面包括：

- `/`
- `/ai-prediction`
- `/anomaly-detection`
- `/dispatch`
- `/dispatch/scenarios/[id]`
- `/network-design`
- `/map-view`
- `/route-compare`
- `/login`

Next 通过 `safeApiFetch` 做 SSR 数据读取，支持服务端 Bearer token、httpOnly cookie 和 refresh-and-retry。不要把真实 token 输出到页面、日志或文档。

## 5. 推荐验证命令

后端聚焦测试：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
python -m pytest backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q
python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q
python -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_order_route_shipment_fact_compat.py -q
python -m pytest backend\tests\test_gurobi_capability_service.py backend\tests\test_gurobi_assignment_service.py backend\tests\test_gurobi_vrp_service.py backend\tests\test_gurobi_network_design_service.py -q
```

Next 验证：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend-next
npm run typecheck
npm run build
```

Vue 验证：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run build
```

## 6. 当前接手风险

- 工作区存在大量未提交/未跟踪内容，提交前必须精确 staged，不要 `git add .`。
- `frontend-next/node_modules/`、`.next/`、tsbuildinfo 等本地产物不能提交。
- `.env.production`、真实 key、JWT/cookie、Gurobi license 内容不能提交。
- 大量 provider 接口需要登录态或服务端 token；未登录时 Next 页面会显示 degraded/401，不等同于功能不存在。
- 网络设计当前是 bounded CFLP 小规模真实 OD 入口，不是全量 5 万单真实道路精确网络优化。
- Gurobi 小规模 VRP 当前有客户数上限，避免误把 5 万单送入精确 MILP。

## 7. 推荐下一步

1. 先把当前新增文档、测试、服务分组提交，避免工作区继续膨胀。
2. 跑一轮核心后端测试和 `frontend-next` typecheck/build，记录新的验证证据。
3. 对生产服务器执行 `/api/dispatch/health`、`/api/dispatch/preview`、`/api/amap/provider-health?probe=1`、`/api/amap/route/local-benchmark` 冒烟。
4. 继续完善地图真实 provider 冒烟：高德不应长期无解释降级，天地图应只暴露状态不暴露 key。
5. 把 Next 首页 SSR 聚合迁移或复制为后端 `/api/control-tower/scorecard`，便于审计和移动端复用。
6. 继续推进 network design scorecard、route truth scorecard 和 dispatch readiness scorecard。
