# 物流路径规划项目热启动记忆

Last updated: 2026-07-05
Workspace: `C:\tmp\logistics-route-command-center-layout-dashboard-shell`
Branch observed: `codex/command-center-layout-dashboard-shell`

## 0. 接手第一眼

这是当前物流项目的新主线工作区，不是早期单体演示版。项目已经升级为“物流指挥中枢 / Logistics Command Center”，核心底座是 PostgreSQL/PostGIS + Flask + Vue 单前端。AI 决策中枢已回归 Vue 原生路由 `/decision-console`；`frontend-next/` 仅保留为历史参考和迁移素材，普通登录、导航和运行不再依赖 Next.js 或 `5174` 端口。

进入本项目后先读：

1. `README.md`
2. `docs/VUE_DECISION_CONSOLE_SINGLE_FRONTEND_2026-07-01.md`
3. `docs/DISPATCH_LEARNING_DATASET_2026-06-20.md`
4. `docs/AI_PREDICTION_BASELINE_2026-06-20.md`
5. `docs/AI_ANOMALY_DETECTION_2026-06-20.md`
6. `docs/GUROBI_INTEGRATION_2026-06-19.md`
7. `docs/LOCAL_ROUTE_BENCHMARK_2026-06-20.md`
8. `docs/DISPATCH_ROUTE_TRUTH_2026-06-20.md`
9. `AGENTS.md`

`docs/FRONTEND_NEXT_FOUNDATION_2026-06-20.md` 和 `frontend-next/README.md` 是历史迁移资料，除非任务明确要求 Next，否则不要按它们启动双前端链路。

## 1. 当前工作区状态

2026-07-01 检查时，工作区是脏的，有大量已修改和未跟踪文件。不要回滚、清理、重置或覆盖不属于当前任务的改动。

已观察到的修改集中在：

- 后端配置和蓝图注册：`backend/app/__init__.py`、`backend/config.py`
- 地图/provider：`backend/app/routes/amap.py`、`backend/app/routes/tianditu_route.py`、`backend/app/services/amap_service.py`、`backend/app/services/tianditu_service.py`、`backend/app/services/traffic_service.py`、`backend/app/services/weather_service.py`
- 调度：`backend/app/routes/dispatch.py`、`backend/app/services/dispatch_orchestration_service.py`
- 订单路线推荐：`backend/app/routes/orders.py`、`backend/app/services/order_route_service.py`
- Gurobi/优化：`backend/app/routes/optimization.py`、`backend/app/services/optimization_engine/solvers/gurobi_solver.py`
- Vue 地图页：`frontend/src/views/MapView.vue`、`frontend/src/api/amap.js`、`frontend/src/components/WeatherCard.vue`
- `frontend-next/` 历史参考目录、AI 预测/异常服务、Gurobi 服务、本地路径 benchmark、节点/路线审计脚本、文档和测试。

先运行：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
git status --short
```

## 2. 稳定项目事实

- 后端入口：`backend/run.py`
- Flask app factory：`backend/app/__init__.py`
- 后端默认端口：`5000`
- 主前端：`frontend/`，Vue 3 + Element Plus + Vite，默认端口 `5173`
- AI 决策中枢：Vue 原生路由 `/decision-console`，页面文件 `frontend/src/views/DecisionConsoleView.vue`
- 历史参考前端：`frontend-next/`，不作为普通运行依赖
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

### 2026-07-05 稳定展示版发布前验证

- 发布前本地完整验证已完成：`/api/ready` 显示 PostgreSQL + `shipment_facts=50000` + `registered_capabilities.missing=[]`；食品案例测试 `48 passed`；运行态/Agent/GIS/可选能力测试 `20 passed`；AI/调度/成本核心测试 `41 passed`；OpenSpec `refactor-food-supply-case-console` strict 通过；`frontend npm run build` 通过；HTTP harness `44 total / 40 ok / 4 auth_required / 0 route_missing / 0 failed`。
- 浏览器验证：正确总览路由为 `/cases/food-supply`；调度页 `/cases/food-supply/dispatch` 可显示 AMap JS API、A 级高德路线、数学模型和权重实验台；播放动画后进度推进到 `50%`，成本权重从 `32%` 拖到 `85%` 后评分变化，候选对比包含 `particle_swarm_pso`、`ortools_cvrptw`、`greedy_vrptw_fresh`。
- 发布补丁：`scripts/deploy_tencent_cloud_command_center.py` 支持 `--identity-file`；发布包纳入 `案例一：食品供应链仓配优化(1)`；生产 compose 将该目录只读挂载为 `FOOD_SUPPLY_CASE_DIR=/app/cases/food-supply`；前端 Docker build 支持 `VITE_AMAP_KEY` / `VITE_AMAP_SECURITY_KEY`。
- 新增发布记录：`docs/STABLE_DEMO_RELEASE_2026-07-05.md`，README 已增加中英文 Stable Demo Release 摘要。继续保持不提交 `.env.production`、pem、API key、数据库密码或 license 内容。

### 2026-07-05 食品案例 AMap JS + 调度轨迹回放

- 案例模块 `/cases/food-supply/dispatch` 已从 Leaflet 逐线绘制升级为 `DispatchReplayMap.vue`：优先通过 `frontend/src/utils/amapLoader.js` 加载 AMap JS API 2.0（含 securityJsCode、ToolBar、ControlBar、MapType、Traffic/Satellite 图层），支持车辆 marker 移动、播放/暂停/重置/速度控制、鲜度衰减 ECharts 曲线同步；AMap 不可用时明确降级 Leaflet。
- 后端 `backend/app/services/food_supply_case_service.py` 的 `dispatch-fresh` 返回统一动画契约：`animation.stage=dispatch_solver_replay_v1`、`animation.routes[].frames`、`freshness_timeline`、`route_geometry`、`animation_frame_count`。OR-Tools VRPTW、PSO、greedy 三条链路都补齐该契约。
- 2026-07-05 续：`dispatch-fresh` 新增 `route_provider=amap|auto|none`，前端 `CaseDispatch.vue` 默认请求 `route_provider=amap`。高德 `driving_route` 全部成功时顶层升级为 `distance_source=amap_driving`、`path_source=amap_route_polyline`、`authenticity_level=A`，车辆 frames 沿高德 polyline 累计距离移动；路线 polyline 不可用但 `distance_matrix` 成功时升级为 B 级真实路网距离 + 估算几何，顶层 `distance_source=amap_distance_matrix`、`path_source=estimated_polyline_with_amap_distance_matrix`；部分成功时为 B 级 mixed；全部失败时透明退回 C 级估算回放。
- 真实性边界：只有 `route_provider=amap` 且后端服务端高德 key 可用、`driving_route` 返回非降级真实 polyline 时，才能说成 A 级高德路线；`distance_matrix` 只能把距离/时长升到 B 级，几何仍是估算 polyline；任何 fallback 都必须展示 route-level `fallback_reason`，不能把估算 polyline 说成真实导航。
- `CaseGis.vue` 也改用 `loadMapEngine()`：高德 JS 可用时渲染 AMap 3D dark map + MapType/Traffic/ToolBar/Scale + 节点 marker，失败时 Leaflet fallback；marker 文本已经做 HTML 转义。
- OpenSpec `refactor-food-supply-case-console` 补齐 `food-supply-case-console-multi-page` spec delta；`openspec validate refactor-food-supply-case-console --strict` 通过。
- 最新验证：`backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -k "dispatch_fresh"` 为 `5 passed, 41 deselected`；完整食品案例测试 `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q` 为 `46 passed`；`frontend npm run build` 通过；`openspec validate refactor-food-supply-case-console --strict` 通过。未临时安装 Playwright，E2E 截图留到后续专门阶段。
- 2026-07-05 续：智能调度动画“不能播放”的直接原因是 5000 端口旧 Flask 进程返回无 `animation.routes[].frames` 的旧响应；源码 test-client 已返回 `frame_count=136`。重启后端后浏览器验证 `/cases/food-supply/dispatch` 正常：顶部播放按钮启用，点击后内层显示“播放中”，进度从 `0%` 推进到 `31%`，随后可继续到 `88%`；页面显示 `AMap JS API`、`REAL_PROVIDER_OK`、A 级。前端已补 `canReplay`、末帧从头播放、即时推进一帧、`playFromStart()`、本地 Leaflet fallback，以及“有方案但无动画帧”的诊断提示。最新 `frontend npm run build` 通过，`/api/ready` 仍显示 PostgreSQL + `shipment_facts=50000`。
- 2026-07-05 续：食品案例调度数学模型升级到 `food_fresh_vrptw_mo_v2`。`dispatch-fresh` 现在返回 `mathematical_model`：集合、决策变量、KaTeX 多目标 VRPTW 公式、目标项贡献、硬/软约束、伪代码、复杂度和 truth notes。前端模型面板展示综合目标值、服务水平、碳排估算、硬约束、5 个目标贡献条和 4 张约束卡片；这是解释性 scorecard，不宣称当前在线链路已直接求解完整多目标 MILP。验证：dispatch-fresh 聚焦测试 `6 passed`，模型契约/回放契约 `2 passed`，`frontend npm run build` 通过，浏览器 `/cases/food-supply/dispatch` 无 overlay。
- 2026-07-05 续：食品案例调度数学模型面板新增“权重实验台”。后端 `mathematical_model` 新增 `weight_controls`、`weight_sensitivity.stage=same_solution_rescore`、`front_quality=scorecard_projection_not_solver_pareto` 和多套权重预设；truth note 明确滑杆即时反馈是同方案重评分，只有重新调用 `dispatch-fresh` 后，`plans/distance_source/constraint_validation` 才代表真实路线重算。前端 `/cases/food-supply/dispatch` 可拖动成本、鲜度、时效、碳排、均衡 5 个权重，立即更新综合目标值、贡献条、候选方案排名和 ECharts Pareto 散点，并可一键按当前权重重算或生成 greedy/OR-Tools/PSO 候选对比。验证：`backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -k "dispatch_fresh"` 为 `7 passed, 41 deselected`；完整食品案例测试 `48 passed`；`frontend npm run build` 通过；浏览器 `http://[::1]:5173/cases/food-supply/dispatch` 验证滑杆从 32% 拖到 74% 后目标值即时变化，候选对比后排名包含 `particle_swarm_pso`、`ortools_cvrptw`、`greedy_vrptw_fresh`，无 Vite overlay、无新增 console error。

### 2026-07-04 食品供应链仓配优化案例 MVP

- 新增独立案例模块 `/cases/food-supply`，前端页面为 `frontend/src/views/FoodSupplyChainCaseView.vue`，菜单入口位于“优化决策 / 食品供应链案例”。
- 新增后端 API 前缀 `/api/cases/food-supply`，覆盖 summary、import validate/apply、network、distance-matrix、network-design、dispatch、pareto、scenarios、agent explain。
- 案例数据使用专属 `case_food_*` 表隔离，不混入 `shipment_facts`、`orders`、`vehicles`；C 端 2 万多条消费者需求首期按日期/地区聚合，不伪装为逐点真实导航。
- `apply_import(persist=true)` 在 PostgreSQL/PostGIS 运行时会尝试物化 `case_food_nodes.geom geometry(Point,4326)` 和 `ix_case_food_nodes_geom` GiST 索引；SQLite/无 PostGIS 运行态返回透明 skipped/degraded，不阻断导入。
- 食品案例 service 已能读取 `案例一：食品供应链仓配优化(1)` 下 9 个 Excel 工作簿，识别果园、仓/中转场、B 端门店、B/C 端需求、机场/飞机、车辆、无人机。
- 验证：`openspec validate integrate-food-supply-chain-case --strict` 通过；`backend\tests\test_food_supply_case_service.py` + `test_runtime_agent_gis_decision_routes.py` 共 `13 passed`；`frontend npm run build` 通过；临时 5056 harness 通过，`19 total`、`route_missing=0`、`failed=0`，食品案例 dispatch smoke 分配 8 单。
- 新增增强变更 `openspec/changes/enhance-food-supply-advanced-optimization/`：`solver_mode=milp` 可在小规模案例上真跑 Gurobi CFLP MILP，`solver_mode=ortools` 可真跑 OR-Tools CVRP，`solver_mode=pyvrp` 可真跑 bounded pyVRP CVRP，`algorithm_family=nsga` 可真跑 pymoo NSGA-II。
- 食品案例 `distance-matrix/build` 已支持 `matrix_mode=amap|tianditu|osm|postgis|haversine|auto` 的可执行/降级适配：高德/天地图使用既有 provider service 的小批量同步矩阵并逐 pair 标注来源；OSM 使用 `FOOD_SUPPLY_OSM_GRAPHML` GraphML 缓存或显式 `FOOD_SUPPLY_OSM_ENABLE_NETWORK=1` OSMnx 拉图，默认不联网以免演示接口被 Overpass 拖住；缺图/失败时明确降级到 Haversine，不能说成真实导航。
- 2026-07-04 验证：增强 OpenSpec strict 通过；食品案例测试 `9 passed`；Vue build 通过；临时 5057 harness 扩展到 `24 total`、`20 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，其中 `food_supply_network_milp` 返回 `gurobi_milp/exact_milp`，`food_supply_dispatch_ortools` 返回 `ortools_cvrp/vrp_solver`，`food_supply_pareto_nsga` 返回 `pymoo_nsga/multi_objective_search`。
- 2026-07-04 第二阶段验证：增强 OpenSpec strict 通过；食品案例测试扩展到 `14 passed`，覆盖 Amap/Tianditu mock 成功、provider 失败降级、OSMnx graph provenance、pyVRP dispatch 和 advanced solver compare；Vue build 通过；临时 5059 harness `27 total`、`23 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，`/api/ready` 显示 PostgreSQL + `shipment_facts=50000`，食品案例 `pyvrp_cvrp/hybrid_genetic_vrp`、`gurobi_milp/exact_milp`、`ortools_cvrp/vrp_solver`、`pymoo_nsga/multi_objective_search` 均可用。
- 2026-07-04 第三阶段新增食品案例 GraphML 缓存和路径几何预览：`GET /api/cases/food-supply/osm-cache/status`、`POST /osm-cache/build`、`POST /routes/preview` 已落地；默认 GraphML 缓存写入被忽略的 `backend/var/food_supply_osm/`。`case_baseline_graphml` 只由案例节点 + Haversine 边构成，必须标记 `authenticity_level=C`、`path_source=case_graphml_baseline`、`fallback_reason=CASE_BASELINE_GRAPHML_NOT_REAL_OSM`，不能说成真实 OSM 导航。
- Vue `/cases/food-supply` 的“GIS 网络”页新增路径预览工作台：可检查/构建 GraphML 缓存，选择 `auto|osm|amap|tianditu|haversine`、起点和终点，并把返回 `polyline` 作为高亮路线叠加到 ECharts 拓扑图；旁侧常驻显示 `distance_source/path_source/authenticity_level/fallback_reason`，不依赖 hover 才能知道真实性。
- 2026-07-04 第三阶段验证：增强 OpenSpec strict 通过；`food_supply_case_service.py`、`food_supply_case.py`、`enterprise_smoke_harness.py` py_compile 通过；食品案例测试 `17 passed`；Vue build 通过；临时 5062 harness `30 total`、`26 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，其中 `food_supply_osm_cache_build` 返回 `case_baseline_graphml`，`food_supply_route_preview` 返回 `path_source=case_graphml_baseline`、`authenticity_level=C`、`polyline_points=2`。
- 2026-07-04 第四阶段新增食品案例路线来源对比：`POST /api/cases/food-supply/routes/compare` 已落地，可在同一 source/target 下返回 `amap`、`tianditu`、`osm`、`haversine` 多行路线结果；每行保留 `distance_source/path_source/authenticity_level/fallback_reason/polyline`，推荐规则优先非降级 A/B 级 provider 几何，不把 fallback 包装成真实 provider 成功。
- Vue `/cases/food-supply` 的 GIS 网络页新增“对比来源”按钮和 provider 对比表；点击任一 provider 行会切换图上的高亮路线。`enterprise_smoke_harness.py` 已加入 `food_supply_route_compare` 检查，摘要输出 `route_count` 与 `recommended_provider`。
- 2026-07-04 第四阶段验证：`food_supply_case_service.py`、`food_supply_case.py`、`enterprise_smoke_harness.py` py_compile 通过；食品案例测试 `18 passed`；Vue build 通过。OpenSpec CLI/临时 HTTP harness 在本轮受工具层 Windows 进程启动限制影响未补跑，Phase 4 `8.5` 暂留未勾。
- 2026-07-04 第五/六阶段补强路线对比解释性与评分：`/routes/compare` 每条路线新增 `quality_score`、`quality_band`、`score_breakdown`，summary 新增 `recommended_score`、`best_quality_score`、`average_quality_score`；评分由 provider 状态、真实性等级、polyline 几何、降级状态和相对距离组成。Vue GIS 网络页新增 provider 评分卡与表格评分列，harness 摘要同步输出推荐评分。
- 2026-07-04 第五/六阶段验证：食品案例测试 `16 passed, 2 skipped`；`frontend/scripts/build-direct.mjs` 受限环境构建通过；临时 5067 app-factory harness `31 total`、`27 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，`food_supply_route_compare` 返回 `recommended_score=65.0`、`best_quality_score=65.0`。`npx openspec validate enhance-food-supply-advanced-optimization --strict` 被本机 npm cache `EPERM` 阻塞，不能标记为 strict 通过。
- 2026-07-04 第七阶段新增路线对比历史/缓存：新增案例专属 `case_food_route_comparisons` 表；`POST /api/cases/food-supply/routes/compare` 支持 `use_cache`、`persist`、`cache_ttl_hours`，缓存命中返回 `cache_status=hit`；新增 `GET /api/cases/food-supply/routes/compare/history` 返回轻量可复盘记录。Vue GIS 网络页新增缓存状态和最近路线对比记录表。
- 2026-07-04 第七阶段验证：食品案例测试 `19 passed`；`frontend/scripts/build-direct.mjs` 通过；`npx openspec validate enhance-food-supply-advanced-optimization --strict` 通过；临时 5068/5069 使用真实 PostgreSQL 配置冒烟，`/api/ready` 返回 `backend=postgresql`、`shipment_facts=50000`、`registered_capabilities.missing=[]`，最终 harness `33 total`、`29 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，`food_supply_route_compare.cache_status=hit`、`food_supply_route_compare_cached.cache_status=hit`、`food_supply_route_compare_history.route_history_count=1`。
- 注意：`backend/run.py` 会用 `backend/.env.local override=True` 覆盖临时环境变量；做临时端口 HTTP harness 时优先用 app factory 直启，避免误打到 5000 上旧进程。

### 2026-07-02 企业级 AI/优化能力强化

- 2026-07-02 GIS/MIS/AI Agent 一体化平台 P0/P1 接口已落地：新增 `/api/runtime/capabilities`、`/api/gis/provider-health`、`/api/agent/chat`、`/api/agent/tools/preview`、`/api/agent/actions/confirm`、`/api/decision/scenarios`；`/api/ready` 现在包含 `registered_capabilities`，能直接判断当前运行进程是否注册 advanced-ml、enterprise-summary、data-analytics carbon、Agent、GIS 和 Decision 场景接口。
- MiniMax-M3 Agent 网关只通过后端环境变量读取 `MINIMAX_BASE_URL`、`MINIMAX_API_KEY`、`MINIMAX_MODEL`；无 key 时返回 200 + `provider_status=degraded`，不能把 key 写进前端、文档、记忆或 Git。Agent 当前边界是“建议 + 人工确认”，工具预演只读，业务写入需显式确认。
- `/api/gis/provider-health` 汇总高德、天地图、PostGIS、本地图算法和 geospatial runtime，响应只返回 key 是否配置和来源变量名，不返回 key 值；`/api/decision/scenarios` 默认 dry-run，不写表，`persist:true` 也只写 `dispatch_scenarios` 场景记录。
- 前端 `DecisionConsoleView.vue` 已把 runtime/GIS health 接入控制塔指标和 readiness gates；新增 API 封装 `frontend/src/api/runtime.js`、`gis.js`、`agent.js`、`decision.js`。
- 2026-07-02 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_optional_capability_service.py tests\test_postgres_layered_preview_fallback.py tests\test_runtime_agent_gis_decision_routes.py -q` 通过，`19 passed`；`frontend npm run build` 通过。
- 2026-07-02 真实 HTTP 冒烟：旧 5000 后端曾由非当前源码进程占用，导致新接口 404；停止旧 `run.py` 后用 `backend\.venv\Scripts\python.exe run.py` 重启，`/api/ready` 显示 PostgreSQL + `shipment_facts=50000` + `registered_capabilities.missing=[]`，`/api/runtime/capabilities?solver_probe=0`、`/api/advanced-ml/status`、`/api/advanced-ml/predict/with-anomaly?days=7`、`/api/gis/provider-health`、`/api/data-analytics/carbon-footprint/calculate`、`/api/agent/tools/preview`、`/api/decision/scenarios` 均非 404。
- 2026-07-02 演示稳定闭环追加：`/api/runtime/capabilities` 新增 `demo_readiness`，当前真实运行态显示 `demo_readiness.status=ready`、`score=96`、`backend=postgresql`、`shipment_facts=50000`、`registered_capabilities.missing=[]`、`interpreter.using_project_venv=true`；未配置 MiniMax key 时 Agent 只降级为 `MINIMAX_API_KEY_MISSING`，不阻断演示。
- `backend/scripts/enterprise_smoke_harness.py` 已扩展为 13 项 P0/P1 冒烟并区分 `auth_required` 与 `route_missing`；不带 token 时 0 个 404，带默认演示登录 token 时 13/13 全部 200，`/api/dispatch/preview` 与 `/api/dispatch/smart` 均可用。
- Vue `DecisionConsoleView.vue` 新增“演示健康条”和专家 Agent 抽屉；浏览器验证 `/decision-console` 可显示 50,000 运单、13/13 路由、GIS A 级、10/10 可选能力，Agent 工具预演返回 `read_only` / `will_execute=false`。Agent 抽屉默认不调用 LLM，dry-run 场景固定 `persist:false`。
- 新增 `docs/DEMO_STABILITY_RUNBOOK_2026-07-02.md`，记录推荐启动、冒烟、401/404/旧进程排查和 secret 纪律。最新验证：后端聚焦测试 `20 passed`，`frontend npm run build` 通过。
- 2026-07-03 MiniMax-M3 Agent 本机 key 已通过被忽略的 `backend/.env.local` 配置，`MINIMAX_BASE_URL` 使用 OpenAI-style `/v1` endpoint；重启后 `/api/runtime/capabilities?solver_probe=0` 显示 `agent_status=ok`、`agent_key_configured=true`、`model=MiniMax-M3`、`api_keys_returned=false`，真实 `/api/agent/chat` 返回 `success=true`。后端已清洗模型 `<think>` 标签，避免前端展示隐藏推理文本。
- 2026-07-03 Vue 专家 Agent 抽屉已修复建议正文可读性：`el-drawer append-to-body` 会脱离 scoped 祖先，抽屉外壳样式需用 `:global(.agent-drawer ...)` 覆盖；建议正文使用 `agent-answer-text` 高对比长文阅读区，避免白底淡蓝字。
- 2026-07-02 继续升级旧 Vue 页面真实数据链路：新增 `frontend/src/utils/enterpriseSummary.js`，把 `/api/analytics/enterprise-summary` 统一转换为数据分析、风险、大屏、大数据、敏捷优化和高级路径页面模型；`DataAnalyticsView.vue`、`RiskManagementView.vue`、`AdvancedRouteView.vue`、`AgileOptimizationView.vue`、`DataScreen.vue`、`BigDataScreen.vue` 已接真实 `shipment_facts` 摘要和可解释降级条，不再依赖随机 mock 作为首屏核心数据。
- 2026-07-02 `/api/advanced-ml/predict/with-anomaly` 404 回归已补测试：`DISABLE_ML_ROUTES=1` 时 legacy `/api/ml` 仍可禁用，但 `advanced-ml` 兼容层必须注册；`backend/tests/test_postgres_layered_preview_fallback.py` 新增 advanced-ml 与 enterprise-summary 契约测试。
- 2026-07-02 前端验证：`frontend npm run build` 通过；后端聚焦测试 `backend .\.venv\Scripts\python.exe -m pytest tests\test_postgres_layered_preview_fallback.py tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`32 passed`。构建仍仅保留旧 glyphicons 路径、旧 CSS `*zoom` 和大 chunk 警告。
- 2026-07-02 进一步修复 Vue dev 动态导入与地图 key 本机配置：`frontend/.env.development` 的空 `VITE_AMAP_KEY=` 会覆盖 `.env.local`，真实本机前端 key 应放在被忽略的 `frontend/.env.development.local`；后端本机 key/数据库连接放在被忽略的 `backend/.env.local`，由 `backend/run.py` 启动入口加载。
- 注意：`backend/config.py` 不直接加载 `.env.local`，避免 pytest/test client 误读真实 provider key；`TestingConfig` 会显式清空地图 provider key。若地图页再次显示 `Key 缺失`，优先检查是否重启了 Vite/Flask、是否存在空 env 覆盖、以及 `/api/amap/provider-health` 登录态是否返回 `KEY_CONFIGURED=True`。
- 2026-07-02 浏览器验证：`/decision-console`、`/ml-prediction` 点击可进入且无 `Failed to fetch dynamically imported module`；`/map` 显示 `Key 已配置`。同时 `/api/ready` 保持 `backend=postgresql`、`shipment_facts=50000`。
- 2026-07-02 修复 `/optimization-engine` 与 `/network-design` 点击/动态导入运行态：清理 `frontend/node_modules/.vite` 并重启 Vite 后，两个源码动态模块均 200；浏览器实际点击验证无 `Failed to fetch dynamically imported module`。
- 2026-07-02 追加路由层动态导入恢复：`frontend/src/router/index.js` 已在 `router.onError` 中识别 Vite/浏览器动态模块加载失败并按目标路由自动刷新一次，避免旧 HMR 缓存或 5173 未干净重启时页面一直白屏。再次复核 `/api/ready` 为 PostgreSQL + `shipment_facts=50000`，`/src/views/NetworkDesignView.vue` 直连 200，浏览器从 `/data-analytics` 点击「网络设计」进入 `/network-design` 正常。
- 2026-07-02 优化引擎和网络设计已接真实 `shipment_facts` 聚合样本：新增 `/api/optimization/real-shipment-demo`/`real-vrp-demo` 与 `/api/network/real-shipment-dataset`；前者把真实城市 OD 聚合投影到 0-100 平面供 VRP 求解器对比，后者返回真实目的城市客户与始发候选设施。真实性等级为 C，明确标注 `shipment_fact_city_od_aggregate`/`haversine_corrected` 或投影语义，不伪装为高德导航路径。
- 2026-07-02 真实 PostgreSQL 冒烟：`/api/ready` 返回 `backend=postgresql`、`shipment_facts=50000`；`/api/optimization/real-shipment-demo?customer_limit=8&candidate_limit=4` 返回 `data_source=shipment_fact_od_aggregate`、`n_customers=8`；登录态 `/api/network/real-shipment-dataset?customer_limit=8&candidate_limit=4` 返回 8 个客户、4 个候选设施、`shipment_facts_total=50000`。
- 新增 OpenSpec 变更 `openspec/changes/strengthen-enterprise-ai-optimization-platform/`，覆盖 P0 调度/Provider 稳定、P1 可选 AI/优化能力探测、P2 控制台/harness/记忆日志。
- 前端高德浏览器 key 已从 `frontend/vite.config.js` 和 `frontend/index.html` 的硬编码移除，改为 `VITE_AMAP_KEY` / `VITE_AMAP_SECURITY_KEY` env 注入；无 key 时浏览器端只输出可解释提示，不再把真实 key 写在源码里。
- `/api/amap/provider-health` 现在即使不跑外部 probe，也会在 key 缺失时返回 `provider_status=degraded`、`fallback_reason=AMAP_KEY_MISSING`，避免“无解释降级”。
- 新增 `backend/app/services/optional_capability_service.py` 和 `/api/optimization/capabilities` / `/api/optimization/capability-health`，安全探测 Gurobi、CPLEX/docplex、OR-Tools、pymoo、Torch、Stable-Baselines3/Gymnasium、Optuna、LightGBM、Transformers、GeoPandas/Shapely/PyProj/Geopy。响应只返回可用性、版本、边界和 fallback，不返回 key、密码或 license 内容。
- 修复 `backend/app/services/optimization_engine/solvers/drl_vrp_solver.py` 的错误相对导入，避免 DRL-VRP 被 solver registry 静默隐藏；DRL/Torch/SB3 仍只作为 shadow/rerank 能力，硬约束仍归 dispatch solver 层。
- Vue `DecisionConsoleView.vue` 已接入“优化/AI 能力矩阵”，控制塔评分新增 Optional Runtime 组件，显示 CPLEX/Gurobi/pymoo/Torch/SB3/Optuna 等 runtime 的可用/降级和 shadow 边界。
- 新增 `backend/scripts/enterprise_smoke_harness.py`，可对后端 URL 执行 `/api/ready`、`/api/optimization/capabilities`、`/api/dispatch/health`、`/api/dispatch/preview`、`/api/dispatch/smart` 精简冒烟；脚本不打印 token 或 secret。
- 2026-07-02 当前 `.venv` 只读探测：10/10 optional capabilities 可用；包含 Gurobi、CPLEX/docplex、OR-Tools、pymoo、Torch、SB3/Gymnasium、Optuna、LightGBM、Transformers、geospatial stack。
- 2026-07-02 PostgreSQL test-client 冒烟：`/api/ready` 返回 `backend=postgresql`、`shipment_facts=50000`；`/api/optimization/capabilities` 返回 `available=10/total=10`；`/api/dispatch/health` 返回 `data_source=shipment_fact`、`dispatchable_orders=200`；`/api/dispatch/preview` 和 `/api/dispatch/smart` 均 200，20 单波次中分配 10 单、未分配 10 单、2 条 plans，fallback 原因为 `precise_distance_disabled_or_missing_coordinates`。

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
- `/api/dispatch/preview` 已支持 `policy_mode=solver_only|shadow_rerank|dqn_shadow`，响应包含 `solver_plan`、`rl_rerank`、`constraint_validation`、`deployable`；DQN shadow 永远是建议层，`deployable=false`，硬约束必须由 solver validation 通过。
- `/api/dispatch/policy/jobs` 与 `/api/dispatch/policy/jobs/:id` 是 DQN/Fitted-Q/PPO shadow 后台任务入口，适合手动高级分析，不应在页面首屏自动触发。

### AI 预测

- 新增 `backend/app/services/shipment_prediction_service.py`
- 新增 `backend/app/routes/ai_prediction.py`
- 真实 `shipment_facts` baseline 已覆盖 demand、ETA、delay、cost。
- 已新增时间序列 benchmark、运力缺口预测、成本波动预测、AI readiness scorecard。
- 2026-07-01 真实 PostgreSQL 冒烟确认：`shipment_facts=50000`，但 `shipped_at` 日级只有 2 个业务日期、小时桶 24 个；这不是数据丢失，而是时间轴不足。日级 LSTM/Transformer 不能标记为可用。
- `/api/ai-prediction/timeline/audit` 是预测前置审计入口，返回各时间字段覆盖、推荐粒度、训练窗口；当前真实数据推荐 `hourly`，`training_window_count=10`，未达到深度模型训练窗口。
- `/api/ai-prediction/demand/forecast` 支持 `time_granularity=daily|hourly|auto` 与 `series_source`；当 auto 从日级降到小时桶时必须返回 `forecast_status=degraded` 和 `fallback_reason=DEMAND_DAILY_POINTS_INSUFFICIENT_USING_HOURLY_FALLBACK`，前端不能把它显示成无解释的 0 或完全 ok 的日级预测。
- `/api/ai-prediction/jobs` 与 `/api/ai-prediction/jobs/:id` 是 LSTM/GRU/Transformer 等 deep shadow 后台任务入口；当前时间窗口不足时 job 可完成但 readiness degraded，不阻塞 Flask 请求，不写业务表。
- 主要接口：
  - `/api/ai-prediction/health`
  - `/api/ai-prediction/timeline/audit`
  - `/api/ai-prediction/baseline/evaluate`
  - `/api/ai-prediction/demand/forecast`
  - `/api/ai-prediction/jobs`
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
- `/api/analytics/operations-summary` 和 `/api/analytics/operations-scorecard` 已作为 Vue 决策中枢控制塔组件输入。

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

### Vue 单前端决策中枢

2026-07-01 已取消普通运行中的 Vue -> Next 桥接链路，避免双前端带来的登录态超时、端口占用和跨运行时故障。

- 决策中枢入口：`/decision-console`
- 页面文件：`frontend/src/views/DecisionConsoleView.vue`
- 路由挂载：`frontend/src/router/index.js`
- 侧边栏入口：`frontend/src/views/Layout.vue`，菜单项「智能决策中枢」
- 开发配置：`frontend/.env.development` 只保留 Vue 单前端所需 `VITE_WS_URL` / `VITE_WS_TRANSPORTS`
- 普通本地运行只需后端 `5000` + Vue 前端 `5173`
- `frontend-next/` 仍可保留为历史参考，但不要再把它作为登录、导航或 AI 控制台的必需运行时

Vue 决策中枢复用现有 Flask API 聚合：

- `/api/ai-prediction/health`
- `/api/ai-prediction/baseline/evaluate`
- `/api/ai-prediction/scorecard`
- `/api/ai-anomaly/*`
- `/api/analytics/operations-*`
- `/api/dispatch/health`
- `/api/dispatch/shadow-benchmark`
- `/api/optimization/gurobi/health`
- `/api/optimization/solver-benchmark-demo`

前端 WebSocket 也已收敛：

- `frontend/src/main.js` 不再在登录页自动连接，只暴露 `window.wsService`
- `frontend/src/services/websocket.js` 幂等连接，支持 `VITE_WS_DISABLED`、`VITE_WS_URL`、`VITE_WS_TRANSPORTS`
- 开发环境默认 polling，减少本地 WebSocket 握手噪音
- HMR dispose 会断开旧连接，避免热更新后重复 socket

后端 AI/analytics 稳定性提醒：

- 2026-07-01 已修复决策中枢/AI 页面并发请求容易拖垮后端的问题：`shipment_prediction_service.py`、`shipment_anomaly_service.py`、`shipment_cost_analytics_service.py` 的 5 万 `shipment_facts` 读取改为列级投影 + `yield_per` 分块迭代。
- 不要把这些链路退回 `ShipmentFact.query...limit(50000).all()` 加载完整 ORM 实体；真实 5 万数据可以读，但必须按任务只取必要列。
- 2026-07-01 已进一步加入 `runtime_profile` 稳定化约定：页面首屏必须默认 `interactive`，prediction/anomaly `limit<=5000` 且 anomaly 默认 `use_ml=false`；调度 shadow 默认 `scenario_limit<=1`、`row_limit<=20`、`anomaly_source_limit<=2000`，Fitted-Q/RL/snapshot 不得在页面初始化自动运行。
- `full` profile 只给用户手动训练、深度检测或高级 Shadow 使用；DQL/DQN/Fitted-Q 仍是 shadow mode，不写业务状态。
- 2026-07-01 AI 预测真实性补丁：forecast 必须区分 `ok`、`degraded`、`insufficient_history`；真实日级点不足时允许小时桶 baseline，但要在响应和 Vue 页面明确降级原因。
- 可选调度 shadow 端点在内部异常时应返回 HTTP 200 + `success:false`、`provider_status:degraded`、`fallback_reason`，避免 Vue 控制台因缺少 assignments 或临时训练失败变成 500；核心 `/dispatch/preview`、`/dispatch/smart`、`/dispatch/health` 仍应保留真实错误语义。
- `backend/config.py` 已为 PostgreSQL 增加连接池护栏：`SQLALCHEMY_POOL_SIZE`、`SQLALCHEMY_MAX_OVERFLOW`、`SQLALCHEMY_POOL_TIMEOUT`、`SQLALCHEMY_POOL_RECYCLE`、`POSTGRES_CONNECT_TIMEOUT`、`POSTGRES_STATEMENT_TIMEOUT_MS`、`POSTGRES_IDLE_TX_TIMEOUT_MS`。
- 相关回归测试会 monkeypatch `sqlalchemy.orm.Query.all`，覆盖 prediction baseline、anomaly detect、operations summary 的列级读取约束。

## 5. 推荐验证命令

历史后端启动方式曾使用 D 盘虚拟环境：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
& "D:\物流路径规划系统项目\backend\venv\Scripts\python.exe" -c "from dotenv import load_dotenv; load_dotenv(r'D:\物流路径规划系统项目\backend\.env'); import runpy; runpy.run_path('run.py', run_name='__main__')"
```

说明：

- 代码目录使用 `C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend`。
- Python 解释器使用 `D:\物流路径规划系统项目\backend\venv\Scripts\python.exe`。
- 2026-07-01 实测：当前 C 盘 backend 没有 `.env`；D 盘 backend `.env` 的 `DATABASE_URL` 指向 SQLite，不是 PostgreSQL。真实 5 万 `shipment_facts` 冒烟必须在启动后端的同一个 PowerShell 会话中显式设置 PostgreSQL `POSTGRES_DATABASE_URL` 或 `DATABASE_URL`，不要只依赖 D 盘 `.env`。
- 不要把 `.env` 内容写入日志、记忆或提交。

当前更推荐的新本地后端环境：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

事实记录：

- 2026-07-01 已创建 `backend\.venv`，Python 3.11。
- `.gitignore` 已忽略 `.venv/`。
- `backend/requirements-dev.txt` 已新增，包含 `requirements.txt` + `pytest==9.1.1`。
- 新 `.venv` 下 `pip check` 通过；核心 AI/analytics 测试最新为 `20 passed`；临时 `FLASK_CONFIG=testing`、端口 `5050` HTTP 冒烟 `/`、`/api/health`、`/api/ready` 通过。
- 本次没有注入真实 PostgreSQL 连接串，因此 5050 冒烟是运行环境/Flask/基础 DB ready 冒烟，不是 PostgreSQL 业务数据冒烟。
- 本地未启动 Kafka 时可设置 `DISABLE_KAFKA_CONSUMER=1`，避免刷 `NoBrokersAvailable`。

后端聚焦测试：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
python -m pytest backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q
python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q
python -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_order_route_shipment_fact_compat.py -q
python -m pytest backend\tests\test_gurobi_capability_service.py backend\tests\test_gurobi_assignment_service.py backend\tests\test_gurobi_vrp_service.py backend\tests\test_gurobi_network_design_service.py -q
```

Vue 验证：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run build
```

Vue 单前端本地启动：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

后端本地启动：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
$env:DISABLE_ML_ROUTES='1'
$env:DISABLE_KAFKA_CONSUMER='1'
$env:FLASK_HOST='127.0.0.1'
$env:FLASK_PORT='5000'
$env:FLASK_DEBUG='False'
$env:SQLALCHEMY_ECHO='0'
.\.venv\Scripts\python.exe run.py
```

决策中枢访问：

```text
http://127.0.0.1:5173/decision-console
```

最近验证：

- 2026-07-01 `backend .\.venv\Scripts\python.exe -m pytest backend\tests\test_shipment_prediction_service.py backend\tests\test_dispatch_orchestration_layered.py -q` 通过，`32 passed`；覆盖 timeline audit、forecast hourly degraded fallback、AI prediction job、DQN shadow preview、dispatch policy job。
- 2026-07-01 `frontend npm run build` 通过；AI 预测页会显示 forecast 降级原因，调度页会展示 Solver + AI Shadow 对比。
- 2026-07-01 临时端口 `5056` 当前代码 + 真实 PostgreSQL HTTP 冒烟通过：`/api/ready` 显示 `shipment_facts=50000`；`/api/ai-prediction/timeline/audit` 显示 `shipped_dates=2`、`shipped_hours=24`；`/api/ai-prediction/demand/forecast` 84ms 返回 degraded hourly forecast；LSTM shadow job 后台完成但 readiness degraded；`/api/dispatch/preview policy_mode=dqn_shadow` 约束校验通过且 `deployable=false`；临时服务已停止。
- 2026-07-01 `backend .\.venv\Scripts\python.exe -m pytest tests\test_dispatch_orchestration_layered.py tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py -q` 通过，`33 passed`；覆盖 AI runtime_profile 裁剪和 Fitted-Q shadow 200 degraded。
- 2026-07-01 `frontend npm run build` 通过；AI 预测、异常检测、决策中枢已改为首屏 interactive，Fitted-Q/RL/snapshot 改为手动高级 Shadow。
- 2026-07-01 `frontend npm run build` 通过；仅有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 2026-07-01 `frontend npm run build` 再次通过；Vue `/decision-console` 已加入 AI 能力雷达、需求预测曲线、异常信号分布、AI 深度预测增强和调度学习链/RL Shadow 面板。
- 2026-07-01 `backend .\.venv\Scripts\python.exe -m pytest tests\test_postgres_layered_preview_fallback.py tests\test_order_route_shipment_fact_compat.py tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`28 passed`。
- 2026-07-01 在未注入 PostgreSQL 的当前环境下，`/api/ready` test client 冒烟返回 200，`database_runtime.backend=sqlite`、`shipment_facts=0`、`warning_present=True`。这证明“订单全 0”是 SQLite 兜底环境问题，不代表 PostgreSQL 真实数据丢失。
- 2026-07-01 进一步复核：真实 5 万数据位于 `logistics_route_system.public.shipment_facts`，计数 50000；`app_dev` 与 `postgres` 没有该表。固定用 `127.0.0.1:5432` 重启后，`/api/ready` 显示 `backend=postgresql`、`shipment_facts=50000`，Dashboard 核心接口 `/api/stats/overview`、`/api/orders?per_page=8`、订单趋势、订单分布、车辆利用率均 200。
- 2026-07-01 `backend .\.venv\Scripts\python.exe -m pytest tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`20 passed`。
- 2026-07-01 本机 HTTP 烟测 `/api/health` 返回 200，`/decision-console` 返回 200。

## 6. 当前接手风险

- 工作区存在大量未提交/未跟踪内容，提交前必须精确 staged，不要 `git add .`。
- `frontend-next/node_modules/`、`.next/`、tsbuildinfo 等本地产物不能提交；`frontend-next/` 目前只是历史参考，不是普通运行入口。
- `.env.production`、真实 key、JWT/cookie、Gurobi license 内容不能提交。
- 大量 provider 接口需要登录态；未登录时 Vue 决策中枢/地图/调度页面出现 degraded/401，不等同于功能不存在。
- 网络设计当前是 bounded CFLP 小规模真实 OD 入口，不是全量 5 万单真实道路精确网络优化。
- Gurobi 小规模 VRP 当前有客户数上限，避免误把 5 万单送入精确 MILP。

## 7. 推荐下一步

1. 先把当前新增文档、测试、服务分组提交，避免工作区继续膨胀。
2. 跑一轮核心后端测试和 `frontend` build，记录新的验证证据。
3. 对生产服务器执行 `/api/dispatch/health`、`/api/dispatch/preview`、`/api/amap/provider-health?probe=1`、`/api/amap/route/local-benchmark` 冒烟。
4. 继续完善地图真实 provider 冒烟：高德不应长期无解释降级，天地图应只暴露状态不暴露 key。
5. 把 Vue 决策中枢当前的前端聚合进一步收敛为后端 `/api/control-tower/scorecard`，便于审计和移动端复用。
6. 继续推进 network design scorecard、route truth scorecard 和 dispatch readiness scorecard。
