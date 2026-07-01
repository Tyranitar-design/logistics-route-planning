# 物流路径规划项目工作日志

Workspace: `C:\tmp\logistics-route-command-center-layout-dashboard-shell`
Last updated: 2026-07-01

## 2026-07-01 - 接手记忆与协作文件补齐

- 检查目标项目工作区：当前分支为 `codex/command-center-layout-dashboard-shell`。
- 确认 `.codex/` 与根目录 `AGENTS.md` 原本不存在。
- 新增 `.codex/memory/MEMORY.md`，记录当前项目热启动事实、AI/调度/Gurobi/地图/Next 边界、验证命令和接手风险。
- 新增 `.codex/memory/WORKLOG.md`，作为后续阶段日志入口。
- 新增根目录 `AGENTS.md`，给后续 agent 明确读取顺序、敏感文件纪律、修改策略和验证流程。
- 本次为文档/记忆整理，没有运行完整测试套件；记忆内容基于当前源码、README、`frontend-next/README.md`、近期 docs 和 `git status` 观察。

## 2026-06-20 - Next 决策控制台与 AI scorecard 阶段

已从项目文档与当前文件确认：

- `frontend-next/` 已成为并行 Next.js + TypeScript + Tailwind 决策控制台，不替换 Vue 生产 UI。
- Next 页面已覆盖 `/`、`/ai-prediction`、`/anomaly-detection`、`/dispatch`、`/dispatch/scenarios/[id]`、`/network-design`、`/map-view`、`/route-compare`、`/login`。
- `frontend-next/lib/api.ts` 和 `safeApiFetch` 已支持 SSR 数据读取、服务端 Bearer token、httpOnly cookie、refresh-and-retry。
- 首页已聚合 AI prediction scorecard、AI anomaly scorecard、operations scorecard、dispatch shadow benchmark、Gurobi health 和 solver benchmark，形成只读 Decision Control Tower。
- AI 预测服务新增真实 `shipment_facts` baseline、time-series benchmark、capacity gap forecast、cost volatility forecast 和 readiness scorecard。
- AI 异常检测服务新增真实 `shipment_facts` 异常检测、readiness scorecard 和 explain 接口。
- 运营/成本分析新增 `operations-summary` 和 `operations-scorecard`。
- 调度学习数据集新增 `learning-dataset`、`policy-scorer`、`reward-model`、`redispatch-simulator`、`redispatch-profiles`、`rl-shadow-runner`、`fitted-q-shadow-model`、`shadow-benchmark`、`shadow-benchmark/snapshot`。
- DQL/DQN 仍为 shadow mode，不直接应用业务状态。

项目文档记录的验证：

- AI 预测测试：`backend/tests/test_shipment_prediction_service.py` 曾记录通过。
- AI 异常测试：`backend/tests/test_shipment_anomaly_service.py` 曾记录通过。
- 成本分析测试：`backend/tests/test_shipment_cost_analytics_service.py` 曾记录通过。
- `frontend-next` 曾记录 `npm run typecheck` 和 `npm run build` 通过。

## 2026-06-20 - 地图视图、路径对比与本地算法 benchmark 阶段

已从项目文档与当前文件确认：

- `/map-view` 与 `/route-compare` 已迁移出 provider readiness、地图选择台、订单/节点选择、自动补全 BFF、缓存诊断、provider polyline preview。
- 新增 `/api/route-compare/suggestions` Next BFF，浏览器只请求同源接口，服务端转发 Flask，避免前端暴露 token。
- 新增后端 `/api/amap/route/local-benchmark`，统一本地路径算法对比能力。
- 本地算法支持 Dijkstra/A* 多策略：distance、time、cost、comprehensive 等。
- benchmark 可同时对比高德和天地图 provider，输出 `provider_routes`、`provider_errors`、`route_segments`、`route_truth`。
- 本地 Route 路径是节点序列，provider polyline 是道路几何；文档已明确真实性边界。

项目文档记录的验证：

- `python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q` 曾记录 `17 passed`。
- `frontend-next` 曾记录 `npm run typecheck` 和 `npm run build` 通过。
- Playwright 桌面和移动 smoke 曾记录通过，包含 `/map-view` 与 `/route-compare`。

## 2026-06-19 - Gurobi 高级优化接入阶段

已从项目文档与当前文件确认：

- 新增 `backend/app/services/gurobi_capability_service.py`，提供安全能力探测。
- 新增 Gurobi health/smoke、小规模车辆分配、小规模 CVRP、CFLP 网络设计和 solver benchmark 接口。
- `GurobiSolver.is_available()` 与 `GurobiVRPTWSolver.is_available()` 统一走能力探测。
- Gurobi 不可用时返回 `fallback_reason`，并降级到 greedy/nearest-neighbor 等可解释 fallback。
- 小规模 VRP 有规模上限，避免全量真实数据误入精确 MILP。
- 用户提供过本机 Gurobi 安装位置和 license 位置，但后续 agent 不得读取或输出 license 内容。

## 2026-06-19 - 调度与真实数据适配阶段

已从当前 README、服务和测试文件确认：

- 智能调度从旧 `orders` 单源转向 `shipment_facts` / `orders` 双源适配。
- `/api/dispatch/health`、`/api/dispatch/waves`、`/api/dispatch/preview`、`/api/dispatch/apply`、`/api/dispatch/scenarios` 构成统一调度控制台 API。
- `dispatch_scenarios` / `dispatch_assignments` 是预览和执行结果的记录表；Next SSR 预览使用 `persist:false`，避免刷新污染场景历史。
- 调度响应统一强调 `data_source`、`distance_source`、`provider_status`、`fallback_reason`、`authenticity_level`。
- 真实距离优先 provider/cache/route truth；失败时允许 Haversine 降级，但必须解释。

项目文档记录的验证：

- `backend/tests/test_dispatch_orchestration_layered.py` 已作为调度分层核心测试。
- `backend/tests/test_order_route_shipment_fact_compat.py` 覆盖订单路线推荐的 ShipmentFact 兼容。

## 历史基线

- README 显示当前主线版本为 `v2.2 Command Center`。
- 生产部署目标是 PostgreSQL/PostGIS + Redis + Flask Backend + Vue/Nginx Frontend。
- 大数据相关目录保留，但核心演示部署默认不启动大数据容器。
- 仓库包含 Flask 后端、Vue 前端、Next 决策控制台、微信小程序、大数据目录、Docker Compose、多份 docs 和 OpenSpec 变更。
