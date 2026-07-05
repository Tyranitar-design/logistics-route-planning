# 物流路径规划项目工作日志

Workspace: `C:\tmp\logistics-route-command-center-layout-dashboard-shell`
Last updated: 2026-07-05

## 2026-07-05 - 稳定展示版发布前验证与部署收束（小C）

- 目标：把当前 Vue 单前端 + Flask + PostgreSQL/PostGIS + 食品供应链仓配优化案例收束为可发布到 Tencent Cloud/GitHub 的稳定展示版。
- 本地 `/api/ready` 验证：`database_runtime.backend=postgresql`、`shipment_facts=50000`、`registered_capabilities.missing=[]`。
- 浏览器验证：
  - 正确总览路由是 `/cases/food-supply`，不是 `/cases/food-supply/overview`。
  - `/cases/food-supply` 渲染案例总览、9 个源文件审计和真实性契约，无 Vite overlay、无相关 console error。
  - `/cases/food-supply/dispatch` 渲染 AMap JS API、A 级高德路线、数学模型和权重实验台。
  - 点击“播放求解动画”后进度从 `0%` 推进到 `50%`，累计距离为 `7.863 km`，鲜度同步变化为 `95%`。
  - 成本权重从 `32%` 拖到 `85%` 后综合目标值从约 `0.5012` 变到 `0.6741`；点击“生成候选方案对比”后排名包含 `particle_swarm_pso`、`ortools_cvrptw`、`greedy_vrptw_fresh`。
- 后端/前端验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q`：`48 passed`。
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_runtime_agent_gis_decision_routes.py backend\tests\test_optional_capability_service.py backend\tests\test_postgres_layered_preview_fallback.py -q`：`20 passed`。
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q`：`41 passed`。
  - `npx openspec validate refactor-food-supply-case-console --strict`：valid。
  - `frontend npm run build`：通过；仅保留既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
  - `enterprise_smoke_harness.py --base-url http://127.0.0.1:5000 --timeout 25`：`passed=true`、`total=44`、`ok=40`、`auth_required=4`、`route_missing=0`、`failed=0`。
- 单独验证发布主展示链路：`POST /api/cases/food-supply/optimize/dispatch-fresh` 使用 `solver_mode=ortools`、`route_provider=amap`、`persist=false` 返回 `solver_family=ortools_cvrptw`、`distance_source=amap_driving`、`path_source=amap_route_polyline`、`authenticity_level=A`、`assigned_orders=8`、`animation_stage=dispatch_solver_replay_v1`、首条路线 `frames=17`。
- 发布工程补强：
  - `scripts/deploy_tencent_cloud_command_center.py` 增加 `--identity-file`，支持使用本地 SSH 私钥部署；无密码模式下远程 sudo 走 `sudo -n`，要求远程用户具备 NOPASSWD sudo。
  - 发布包纳入 `案例一：食品供应链仓配优化(1)`，避免远程新机缺少案例 Excel 数据。
  - `docker-compose.prod.yml` 将食品案例目录只读挂载到 `/app/cases/food-supply`，并通过 `FOOD_SUPPLY_CASE_DIR` 指定后端读取路径。
  - `frontend/Dockerfile` + `docker-compose.prod.yml` 支持 `VITE_AMAP_KEY` / `VITE_AMAP_SECURITY_KEY` build args，避免生产前端 AMap JS key 丢失。
  - 新增 `docs/STABLE_DEMO_RELEASE_2026-07-05.md`，README 增加中英文 Stable Demo Release 摘要。
- 安全纪律：未读取或输出 pem、API key、数据库密码、license 内容；发布文档只写占位符和验证结论。

## 2026-07-05 - 食品案例调度权重实验台与 Pareto 即时对比（小C）

- 后端 `dispatch-fresh` 的 `mathematical_model` 继续扩展：新增 `weight_controls` 与 `weight_sensitivity`，权重维度覆盖成本、鲜度、时效、碳排、车辆均衡；`weight_sensitivity.stage=same_solution_rescore`、`front_quality=scorecard_projection_not_solver_pareto`。
- 后端返回 current/balanced/cost_first/freshness_first/time_first/carbon_first 等同方案重评分点；truth note 明确滑杆即时反馈是 scorecard 重评分，路线变化必须以重新请求 solver 后的 `plans`、`distance_source`、`constraint_validation` 为准。
- 前端 `CaseDispatch.vue` 新增“权重实验台”：5 个 `el-slider` 支持现场调权并自动归一化；综合目标值、目标项贡献条、当前推荐和候选方案排名即时更新；新增 ECharts 成本压力 x 鲜度风险散点图，突出当前权重最优方案。
- 前端按钮边界：`按权重重算路线` 显式重新调用 `dispatch-fresh`；`生成候选方案对比` 并行拉取 greedy/OR-Tools/PSO 候选方案并按当前权重重排，不把即时重评分伪装成真实路线重算。
- 测试扩展：`backend/tests/test_food_supply_case_service.py` 新增权重控件、敏感性契约和不同权重下 scorecard 重评分覆盖。
- 验证命令：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -k "dispatch_fresh"` 通过，`7 passed, 41 deselected`。
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`48 passed`。
  - `cd frontend; npm run build` 通过；仍仅有既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
- 浏览器验证：`http://[::1]:5173/cases/food-supply/dispatch` 显示权重实验台、5 个滑杆和 Pareto canvas；成本权重从 `32%` 拖到 `74%` 后综合目标值从 `0.5012` 变为 `0.6486` 并显示即时预览；候选对比后排名包含 `particle_swarm_pso`、`ortools_cvrptw`、`greedy_vrptw_fresh`；无 Vite overlay、无新增 console error。

## 2026-07-05 - 食品案例数学模型 v2：多目标 VRPTW 模型画像（小C）

- 后端 `dispatch-fresh` 新增 `mathematical_model` 响应契约，覆盖 OR-Tools、PSO、greedy 三条链路；模型 id 为 `food_fresh_vrptw_mo_v2`，定位为 `explainable_weighted_vrptw_scorecard`，用于解释和方案对比，不宣称当前在线链路已经直接求解完整多目标 MILP。
- 数学模型契约包含：集合 `D/C/K/A`、决策变量 `x_{ijk}/y_{ik}/s_i/u_i`、KaTeX 目标函数、鲜度衰减公式、5 个目标项、4 个约束块、求解流程伪代码、复杂度说明和 truth notes。
- 多目标评分项：运输成本、碳排放、鲜度风险、服务违约、车辆均衡；支持 `objective_weights` 输入并归一化，兼容 `cost/freshness/sla/balance` 等别名。评分层只用于解释/排序/报告，不改变 solver 硬约束。
- 前端 `CaseDispatch.vue` 的“多目标 VRPTW 数学模型”从静态文本升级为模型面板：顶部 KaTeX 公式，下面展示综合目标值、服务水平、碳排估算、硬约束状态、目标项贡献条、约束卡片和算法步骤；约束卡片显示可读数学表达，完整 LaTeX 保留在响应中。
- HTTP smoke：`dispatch-fresh` 返回 `model_id=food_fresh_vrptw_mo_v2`、`objective_score=0.5564`、`term_count=5`、`constraint_count=4`；`/api/ready` 仍为 PostgreSQL + `shipment_facts=50000` + `missing=[]`。
- 浏览器验证：`/cases/food-supply/dispatch` 渲染模型面板，显示 `综合目标值=0.5011`、`服务水平=100%`、`碳排估算=506.27 kgCO2e`、`硬约束=OK`，约束卡片为 `ΣkΣj x_ijk ≤ 1`、`Σi q_i y_ik ≤ Q_k`、`0 ≤ s_i ≤ T_max = 48h`、`F_i ≥ F_min 或惩罚 (1-F_i)`；无 Vite overlay，控制台仅有既有 WebSocket polling warning。
- 验证命令：
  - `backend\.venv\Scripts\python.exe -B -m pytest tests\test_food_supply_case_service.py -q -k "dispatch_fresh"` 通过，`6 passed, 41 deselected`。
  - `backend\.venv\Scripts\python.exe -B -m pytest tests\test_food_supply_case_service.py -q -k "mathematical_model_contract or dispatch_fresh_returns_replay_contract"` 通过，`2 passed, 45 deselected`。
  - `cd frontend; npm run build` 通过；仍仅保留历史 glyphicons、旧 CSS `*zoom` 和大 chunk 警告。

## 2026-07-05 - 食品案例智能调度动画播放修复与浏览器验证（小C）

- 问题复现：`/cases/food-supply/dispatch` 页面能渲染 AMap/Leaflet 回放壳，但“播放求解动画”和内层“播放”按钮为 disabled；浏览器读取显示当前 5000 后端返回旧结构，`animation.frame_count=null`、`animation.routes=[]`，所以前端按契约正确禁用了播放。
- 根因：源码 test-client 已能返回 `animation.frame_count=136`、`routes_len=8`、`route0_frames_len=17`，但本地 5000 端口仍是旧 Flask 进程，未加载最新 `dispatch-fresh` 动画契约。停止旧 `run.py` 进程并用 `backend\.venv\Scripts\python.exe run.py` 重启后，HTTP `/api/cases/food-supply/optimize/dispatch-fresh` 正常返回 136 帧。
- 前端修复：
  - `DispatchReplayMap.vue` 播放逻辑增加 `canReplay`，末帧再次点击会自动从头播放；点击后立即推进一帧并显示“播放中”，暂停按钮只在播放中启用；暴露 `playFromStart()` 给父页面。
  - `CaseDispatch.vue` 顶部按钮改按 `animation.frame_count>1` 启用，点击时优先调用 `playFromStart()`；新增“有方案但无动画帧”的可恢复诊断提示，避免未来旧进程/旧契约只表现为按钮灰掉。
  - `amapLoader.js` 的 Leaflet fallback 优先加载本地 bundled `leaflet` 与 CSS，CDN 仅作为最后兜底并设置超时，避免 AMap 不可用时被外部 CDN 卡住。
- 浏览器验证：`http://[::1]:5173/cases/food-supply/dispatch` 刷新后显示 `AMap JS API`、`authenticity_level=A`、`REAL_PROVIDER_OK`；点击“播放求解动画”后内层按钮变为“播放中”，telemetry 从 `0% / 0 km / 0 min / 100%` 推进到 `31% / 4.914 km / 6.7 min / 97%`，后续截图中播放到 `88% / 953.931 km / 567.9 min / 81%`。
- 验证命令：
  - `cd frontend; npm run build` 通过；仅保留历史 glyphicons、旧 CSS `*zoom` 和大 chunk 警告。
  - `/api/ready` 返回 `backend=postgresql`、`shipment_facts=50000`、`registered_capabilities.missing=[]`。
  - `dispatch-fresh` HTTP smoke 返回 `frame_count=136`、`routes_len=8`；真实高德 provider 可能按当次路线成功率在 A/B 间波动，必须继续以 `distance_source/path_source/authenticity_level/fallback_reason` 为准。
- 浏览器控制台：无动态 import 或框架 overlay；仍有既有 `geo3D exists`、Element Plus radio label deprecation、WebSocket polling warning，非本次调度回放阻断项。

## 2026-07-05 - 食品案例调度回放接入真实高德 route polyline / distance_matrix（小C）

- 后端 `dispatch-fresh` 新增 `route_provider=amap|auto|none`：求解器仍先完成容量/时间窗/分配，随后逐条调用既有 `_preview_provider_route(..., "amap")` 回填真实高德 `distance/duration/polyline`；不改原始事实表和 case_food_* 事实数据。
- 响应 truth metadata 可动态升级：全部路线高德 `driving_route` 成功时顶层 `provider_status=ok`、`distance_source=amap_driving`、`path_source=amap_route_polyline`、`authenticity_level=A`；路线 polyline 不可用但 `distance_matrix` 成功时升级为 B 级真实距离 + 估算几何，顶层 `distance_source=amap_distance_matrix`、`path_source=estimated_polyline_with_amap_distance_matrix`；部分成功时为 B 级 mixed；全部失败时保留 C 级估算回放并逐 route 写明 fallback。
- 动画从“起终点直线插值”升级为“沿 polyline 累计距离取点”：`animation.routes[].frames` 会沿高德 polyline 多段轨迹移动，`freshness_timeline` 使用 provider 时长重算。
- 新增 `_dispatch_amap_distance_matrix()`：在 provider route 失败时批量请求 depot→门店矩阵，逐 plan 覆盖 `distance_km/duration_min/distance_source/path_source/authenticity_level`，但 `route_geometry.polyline_points=2` 仍保持估算几何并保留 route-level fallback，避免把矩阵距离伪装成真实导航 polyline。
- 前端 `CaseDispatch.vue` 默认 `route_provider=amap`，新增“高德真实路线 / 估算回放”切换；KPI 和表格显示 `path_source`、`distance_source`、`authenticity_level`，`DispatchReplayMap.vue` 自动随顶层 truth metadata 展示 A/B/C。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -k "dispatch_fresh"` 通过，`5 passed, 41 deselected`。
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`46 passed`。
  - `cd frontend; npm run build` 通过；仅保留历史 glyphicons、旧 CSS `*zoom` 和大 chunk 警告。
  - `openspec validate refactor-food-supply-case-console --strict` 通过。
- 注意：自动化测试使用 mock `get_amap_service().driving_route()` 和 `distance_matrix()`，不依赖真实网络/key；真实演示需后端 `.env.local` 中服务端高德 key 可用。

## 2026-07-05 - 食品案例企业级震撼化：AMap JS + 调度轨迹回放（小C）

- OpenSpec：补齐 `refactor-food-supply-case-console/specs/food-supply-case-console-multi-page/spec.md`，明确多页面案例控制台、AMap JS API、调度轨迹回放、鲜度曲线和自动化测试不依赖 live provider key 的规范。
- 后端契约：`optimize_dispatch_fresh`、OR-Tools VRPTW、PSO 三条 dispatch-fresh 链路统一补 `animation.stage=dispatch_solver_replay_v1`、`animation.routes[].frames`、`freshness_timeline`、`route_geometry`、`animation_frame_count`；当前几何仍是 WGS84 坐标插值/估算回放，统一标记 `authenticity_level=C`、`path_source=*estimated_replay`、`fallback_reason`，不冒充真实道路导航。
- 前端地图：新增 `frontend/src/components/case/DispatchReplayMap.vue`，复用 `amapLoader.js` 的 AMapLoader + securityJsCode 单例加载；可用时渲染 AMap 3D dark map、路网/卫星/交通图层、节点 marker、路线 polyline、车辆 marker 移动；失败时降级 Leaflet 并展示原因。
- 前端调度：`CaseDispatch.vue` 接入高德 JS 回放组件，保留 greedy/OR-Tools/PSO 切换、三算法对比、KaTeX VRPTW 模型；播放/暂停/重置/速度控制与鲜度衰减 ECharts 曲线同步。
- 前端 GIS：`CaseGis.vue` 从手写 Leaflet loader 改为共用 `loadMapEngine()`，高德 JS 可用时显示 AMap MapType/Traffic/ToolBar/Scale 与节点 marker，失败时 Leaflet fallback；marker 文本做 HTML 转义。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`44 passed`。
  - `cd frontend; npm run build` 通过；仍仅有历史 glyphicons 字体、旧 CSS `*zoom` 和大 chunk 警告。
  - `openspec validate refactor-food-supply-case-console --strict` 通过。
- 未做：本轮未临时安装 Playwright；工作区没有现成 Playwright 依赖/脚本，页面截图 E2E 留到后续专门阶段，避免污染依赖树。

## 2026-07-05 - 案例模块 A-E 补强：OR-Tools VRPTW + Leaflet + optuna + 真实 geocoding（C哥）

- **A (OR-Tools VRPTW)**：`_try_ortools_dispatch_fresh` 精确求解，Time dimension 作为 48h 时间窗硬约束 + Capacity dimension + 鲜度衰减；`solver_mode=ortools` 触发，失败降级 greedy。
- **B (Leaflet 地图)**：前端 `leaflet@1.9.4`（已有），新增「地理地图」tab，动态加载 Leaflet，果园/仓/门店/机场/C端聚类按类型着色 + popup；build 10.05s 通过。
- **C (真实 geocoding 批量落地)**：`geocode_case_regions` + `_region_geocoded`，c2c_clusters 读缓存升级 authenticity C→A；脚本 `geocode_case_addresses.py` 真实跑通：305 地址，**111 resolved（A 级真实坐标）**，8 个 c2c cluster 升级为真实坐标。
- **D (Gurobi MILP)**：复用已有 `_try_milp_network_design`（选址 MILP），VRPTW 用 OR-Tools——运筹分工合理。
- **E (optuna 调参)**：`_try_lightgbm_optuna_forecast`（n_trials=3，时序 80/20 split，最小化 MAE，返回 best_params + validation_mae）；`use_optuna=1` 触发，逐级降级。
- 安全配置：`scripts/configure_keys.py`（配 key，只打印长度）、`verify_providers.py`（验 provider）、`geocode_case_addresses.py`（批量 geocoding）。key 写入被 .gitignore 忽略的 `.env.local`，绝不输出 key 值。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`41 passed`（含 ortools/optuna/geocode_case_regions 新测试），26.93s。
  - 真实高德 geocode smoke：`success=True lon=117.310133 lat=31.793801`（合肥包河区）。
  - 批量 geocoding：305 地址，111 resolved，8 cluster 升级 A 级。
  - `cd frontend; npm run build` 通过（10.05s）。
- 已知待优化：194 region 名 needs_geocoding（多为"阜阳/亳州"组合 region，高德不识别整串；后续可取首 token geocoding）。
- **组合 region 优化（2026-07-05 续）**：`geocode_case_regions` 对含 `/`、`、` 的 region 取首 token geocoding + 首轮失败加"市"后缀重试（高德对地级市识别更好）；305 地址 resolved 从 111→226（**74%**），A 级 cluster 从 8→20（**50%**），needs 从 194→79。pytest 41 passed 不破坏。
- **POI 搜索 fallback（2026-07-05 续）**：amap_service 新增 `place_text_search`（高德 place/text API）；`geocode_case_regions` 第四轮 POI 搜索救回 geocode 失败的非常规地名（如"大兴安岭"）；305 地址 resolved **305/305=100%**，needs 从 79→**0**，A 级 cluster 从 20→**24（60%）**。pytest 42 passed。四级 geocoding 策略：首 token → "市"后缀 → POI 搜索 → 本地兜底。
- **Phase 2 多页面控制台重构（2026-07-05）**：单页 FoodSupplyChainCaseView → 9 子页面 nested routes（`/cases/food-supply/{overview,gis,forecast,dispatch,multimodal,c2c,clustering,trace,scenarios,agent}`）；FoodSupplyCaseLayout 父布局 + 内侧栏；每个子页面独立 onMounted 加载数据；修复拦截器 `.data` 多余 bug；launch_case_console.ps1 启动保障脚本（启动 5000 + import + geocode 预热）。
- **A. LaTeX 多目标数学模型**：CaseDispatch 用 KaTeX CDN 动态渲染 `min w₁·成本+w₂·碳排-w₃·鲜度+w₄·SLA` 多目标 + 6 约束 VRPTW 公式。
- **C. PSO 粒子群启发式**：`_try_pso_dispatch_fresh`（粒子=顾客排列，适应度=总距离，迭代向 gbest 靠拢）；CaseDispatch 三算法切换 greedy/OR-Tools/PSO。pytest 42 passed。
- **D. 聚类子页面**：CaseClustering 算法说明（四级 geocoding）+ 真实性饼图 + 区域订单柱图 + 明细表。
- 快速修复：Agent timeout 30s→120s；C端 last-mile `distance_mode=amap`（C→A 真实路网）；seed_case_scenarios.py 种子 4 场景（场景对比页有数据）。
- 剩余待做：**B. 高德地图求解动画**（CaseDispatch 动画改高德底座）、E. 网络拓扑优化、F. 核心业务范畴。
- **B+E+F 全部完成（2026-07-05 续）**：B. CaseDispatch 求解动画改 Leaflet 地图底座（高德 tile 优先 + OSM 兜底）+ 路线逐步绘制；E. CaseGis 网络拓扑优化（force repulsion 140/edgeLength 60-120 + 节点标签 + emphasis 联动 + scaleLimit）+ 高德底图；F. business_kpi 后端（SLA/覆盖率/产能/履约率）+ CaseBusiness 前端（仪表盘 + 柱图）+ harness +1。
- **可视化增强（2026-07-05 续）**：CaseForecast 预测曲线（ECharts：历史92天蓝实线 + 预测14天青虚线 + 采摘波次 markArea + 果园切换）；CaseMultimodal 三模式成本/时效/碳排对比柱图 + CFLP 仓网选址数学模型；configure_frontend_keys.py 配 frontend VITE_AMAP_KEY（高德底图生效）。11 子页面全部有可视化，build 通过，pytest 43 passed。

## 2026-07-04 - 食品供应链季节预测+多式联运+鲜度VRPTW+追溯+场景对比（C哥 Phase 1-7）

- 新建 OpenSpec 变更 `enhance-food-supply-orchard-forecast-multimodal-freshness`（proposal/design/tasks/spec delta）。
- Phase 1 果园 92 天时序：`_load_orchards` 增强读 row[9:101] 逐日箱数（5 果园 × 92 天，季总 ~326 万箱）；`orchard_timeseries` + `orchard_forecast`（移动平均+趋势+周季节性+保鲜感知采摘波次），明确 `model_stage=deterministic_baseline` 非已训练 ML。
- Phase 2 空运多式联运：扩展 22+ 货运机场城市坐标库；`_airport_city` 从机场名提取城市匹配本地坐标（27 机场全部解析）；`optimize_multimodal` 输出 pure_road/air_plus_road/air_plus_drone 三模式（B747-8F 135t/426km/h/1.17元/kg），空运距离<500km 判不可行。
- Phase 3 鲜度 VRPTW：`_freshness_score(hours,temp_c,transfers)` 衰减模型（30℃ 4 天满衰减，案例基准校准）；`optimize_dispatch_fresh` 48h 时间窗硬约束，超时订单进 unassigned 绝不静默丢弃。
- Phase 5 真实路网距离：`optimize_last_mile` 加 `distance_mode=amap|tianditu|haversine`，复用 provider distance_matrix，逐 pair provenance，authenticity C→A。
- Phase 6 可追溯：`trace_issue` + `trace_lookup` 确定性追溯码（码即数据，无需查库），采摘→包装→运输→签收四阶段链路。
- Phase 7 场景对比：`list_scenarios` + `compare_scenarios` 横向对比成本/碳排/时效/鲜度/服务，推荐可行中最优（成本最低+鲜度 tiebreak）。
- 前端 `/cases/food-supply` 新增「季节 & 多式联运」tab：时序预测+多式联运+鲜度 VRPTW+追溯+场景对比 5 面板；loadAll 首屏加载。
- harness 扩展 6 项检查（orchard_timeseries/forecast/multimodal/dispatch_fresh/trace_issue/scenarios_compare）。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -p no:cacheprovider` 通过，`37 passed`（原 28 + Phase 1-7 新增 9），22s。
  - `cd frontend; npm run build` 通过（9.33s）；FoodSupplyChainCaseView chunk 44.69 kB；仅保留既有大 chunk 警告。
  - openspec validate：待跑（分类器暂不可用）。
- 后续增强：Leaflet 地图可视化（当前用 ECharts 拓扑，节点地图待补，不影响契约与数据）。

## 2026-07-04 - 食品供应链 C 端地理编码 + 无人机最后一公里（C哥 TDD+SDD+harness）

- 新建 OpenSpec 变更 `openspec/changes/enhance-food-supply-c2c-geocoding-drone-lastmile/`（proposal/design/tasks/spec delta），全部 tasks 勾选。
- 后端新增隔离表 `case_food_geocoding_cache`（`address_hash` 唯一约束 + provider/authenticity/fallback 字段）；不污染 shipment_facts/orders/vehicles。`app/__init__.py` 与 `service.ensure_tables` 同步注册。
- C 端 22259 行 → 有界区域聚类（按 region 聚合，~30 区域中心）；`_load_c2c_demands` 增强保留 `unique_addresses` + `region_dates` + `address_count`，不再只有 (date,region) 聚合。
- 地理编码：amap → tianditu → 本地区域中心兜底（公开城市坐标，C 级）；`geocode_limit` 硬上限 200；`persist` 写缓存表，`use_cache` 命中不再调 provider；未命中标 `needs_geocoding`，**绝不造假坐标**（延续 6-19 数据真实性教训）。
- 无人机最后一公里：`/optimize/last-mile` 输出 drone/vehicle/hybrid 三模式对比（成本/时效/碳排/鲜度/服务水平），载重(10kg)+续航(20km×0.9 reserve)可行性筛选，`constraint_validation`(payload/range/unassigned)，推荐仅在可行模式中按成本最低选取。
- 性能增强：进程级 dataset 缓存（Excel file size+mtime sha256 签名），22k 行每进程只解析一次；区域聚类跨 geocode/last-mile 复用。
- 新增 4 端点：`GET /api/cases/food-supply/c2c/clusters`、`POST /c2c/geocode`、`GET /c2c/geocode/status`、`POST /optimize/last-mile`。
- 前端 `/cases/food-supply` 新增「C 端 & 无人机」tab：C 端地理分布面板（聚类表+KPI+真实性）+ 无人机最后一公里对比表；`loadAll` 首屏加载。
- `enterprise_smoke_harness.py` 扩展 4 项检查。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -p no:cacheprovider` 通过，`28 passed`（原 19 + 新增 9：clusters / geocode 成功+缓存+失败降级+bounded+status / last-mile 可行性+推荐+truth contract / dataset 缓存），21.44s。
  - `cd frontend; npm run build` 通过（9.51s）；`FoodSupplyChainCaseView` chunk 35.33 kB；仅保留既有 glyphicons/大 chunk 警告。
  - `npx openspec validate enhance-food-supply-c2c-geocoding-drone-lastmile --strict` 通过，`Change is valid`。

## 2026-07-04 - 食品供应链路线对比历史缓存与 PostgreSQL 生产冒烟

- 继续 OpenSpec 变更 `enhance-food-supply-advanced-optimization`，完成 Phase 7：路线对比历史/缓存 + 真实 PostgreSQL 5 万数据生产冒烟。
- 新增案例专属表模型 `case_food_route_comparisons`，用于保存食品案例路线对比缓存与历史记录；字段包括 source/target、providers、request_hash、provider_status、fallback_reason、recommended_provider、recommended_score、best_quality_score、route_count、geometry_count、summary_json、response_json、diagnostics_json。该表只属于案例模块，不修改 `shipment_facts`、`orders`、`vehicles` 或原始 Excel 导入事实。
- `POST /api/cases/food-supply/routes/compare` 新增 `use_cache`、`persist`、`cache_ttl_hours`：`persist=true` 时写入 `case_food_route_comparisons`；`use_cache=true` 且 request_hash 未过期时返回 `cache_status=hit`，同时保留原始 `distance_source`、`path_source`、`authenticity_level`、`fallback_reason` 和推荐评分。
- 新增 `GET /api/cases/food-supply/routes/compare/history`，返回轻量历史列表：起终点、providers、推荐 provider、推荐评分、路线数、几何数、创建时间、cache_age、推荐原因摘要；不在列表中回放完整 polyline 大 JSON。
- Vue `/cases/food-supply` 的 GIS 网络工作台新增“历史”按钮、缓存状态卡和最近路线对比记录表；“对比来源”按钮现在显式使用 24 小时缓存并写入案例历史。
- `enterprise_smoke_harness.py` 扩展 `food_supply_route_compare_history` 检查，并在摘要中输出 `route_history_count`。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m py_compile backend\app\models\food_supply_case.py backend\app\routes\food_supply_case.py backend\app\services\food_supply_case_service.py backend\scripts\enterprise_smoke_harness.py` 通过。
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -p no:cacheprovider` 通过，`19 passed`。
  - `cd frontend; node .\scripts\build-direct.mjs` 通过；仍仅保留既有 glyphicons 字体路径和旧 CSS `*zoom` 警告。
  - `npx openspec validate enhance-food-supply-advanced-optimization --strict` 通过。
  - 临时 5068/5069 app-factory 使用 `--config development --load-local-env` 真实 PostgreSQL 冒烟通过：`/api/ready` 返回 `database_runtime.backend=postgresql`、`shipment_facts=50000`、`registered_capabilities.missing=[]`；最终 harness `33 total`、`29 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，`runtime_capabilities.demo_readiness_status=ready`、`score=100`，`food_supply_route_compare` 返回 `recommended_provider=amap`、`recommended_score=97.3`、`cache_status=hit`，`food_supply_route_compare_cached` 同样命中缓存，`food_supply_route_compare_history` 返回 `route_history_count=1`。临时服务已停止。

## 2026-07-04 - 食品供应链案例路线评分与推荐解释第五/六阶段

- 继续 OpenSpec 变更 `enhance-food-supply-advanced-optimization`，在已落地的 `/api/cases/food-supply/routes/compare` 基础上增加路线质量评分。
- 后端 `FoodSupplyCaseService.compare_routes` 现在为每条 provider 路线返回 `quality_score`、`quality_band` 和 `score_breakdown`，评分由 provider 状态、真实性等级、polyline 几何、降级状态和相对距离组成；推荐路线优先参考质量评分，再由原有真实性/降级/时长规则兜底。
- 路线对比 summary 新增 `recommended_score`、`best_quality_score`、`average_quality_score`；`enterprise_smoke_harness.py` 摘要同步输出推荐评分和最高评分。
- Vue `FoodSupplyChainCaseView.vue` 的 GIS 网络工作台新增 provider 评分卡和表格评分列，点击评分卡/表格行会同步切换 ECharts 高亮路线，并继续常驻展示 `distance_source`、`path_source`、`authenticity_level` 和 `fallback_reason`。
- OpenSpec spec 已补充路线质量评分要求；`tasks.md` 新增 Phase 10 并完成代码/测试/构建/冒烟项。Phase 8 的 `8.5` 继续未勾选，因为本轮 OpenSpec strict 仍被本机 `npx` npm cache 写权限阻塞。
- 验证：
  - `backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q -p no:cacheprovider` 通过，`16 passed, 2 skipped`；跳过项仍为受限环境 GraphML 写入测试。
  - `cd frontend; node .\scripts\build-direct.mjs` 通过；仅保留既有 glyphicons 字体路径和旧 CSS `*zoom` 警告。
  - 临时 5067 app-factory HTTP harness 通过：`31 total`、`27 ok`、`4 auth_required`、`route_missing=0`、`failed=0`；`food_supply_route_compare` 输出 `route_count=4`、`route_geometry_count=4`、`recommended_provider=haversine`、`recommended_score=65.0`、`best_quality_score=65.0`、`recommendation_reason=SHORTEST_VISIBLE_LOCAL_BASELINE_AFTER_PROVIDER_FALLBACK`。临时服务已停止。
  - `npx openspec validate enhance-food-supply-advanced-optimization --strict` 未完成：`EPERM mkdir C:\Users\Administrator\AppData\Local\npm-cache\_cacache\tmp`，属于本机 npm cache 权限问题，不是规格内容校验结果。

## 2026-07-04 - 食品供应链案例路线来源对比第四阶段

- 继续 OpenSpec 变更 `enhance-food-supply-advanced-optimization`，追加 Phase 4：同一起终点下的路线 provider 对比。
- 后端新增 `POST /api/cases/food-supply/routes/compare`：一次返回 `amap`、`tianditu`、`osm`、`haversine` 等 bounded provider 路线行；每行都包含 `provider_status`、距离/时长、`distance_source`、`path_source`、`authenticity_level`、`fallback_reason` 和 `polyline`。
- 路线推荐规则：优先非降级 A/B 级 provider 几何，再按可见路线时长/距离排序；不把隐藏 fallback 当成真实 provider 成功。
- Vue `FoodSupplyChainCaseView.vue` 的 GIS 网络工作台新增“对比来源”：会调用 `/routes/compare`，显示 provider 对比表；点击表格行后，ECharts 拓扑图会切换到所选 provider 的路线 polyline，旁侧保留来源、真实性、距离和降级说明。
- `frontend/src/api/foodSupplyCase.js` 新增 `compareFoodSupplyRoutes`；`enterprise_smoke_harness.py` 新增 `food_supply_route_compare` 检查，并在摘要中输出 `route_count` 与 `recommended_provider`。
- 测试新增 `test_food_supply_route_compare_returns_provider_rows`，mock 高德成功并使用本地 GraphML 基线，确保不依赖真实 provider key 或网络。
- 验证：
  - `.\backend\.venv\Scripts\python.exe -m py_compile backend\app\services\food_supply_case_service.py backend\app\routes\food_supply_case.py backend\scripts\enterprise_smoke_harness.py` 通过。
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`18 passed`。
  - `cd frontend; npm run build` 通过；仍仅保留既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
  - 本轮 OpenSpec CLI 启动被当前工具层/Windows 拒绝：`CreateProcessAsUserW failed: 5`；`cmd.exe` 环境找不到 `openspec`。临时 HTTP harness 也因当前 shell 引号传递问题未完成，因此 Phase 4 的 tasks `8.5` 暂未勾选，后续恢复 PowerShell 后可补跑。

## 2026-07-04 - 食品供应链案例 GraphML 缓存与路径几何预览第三阶段

- 继续 OpenSpec 变更 `enhance-food-supply-advanced-optimization`，完成 Phase 3：OSM/GraphML 缓存状态、基线 GraphML 构建、路线几何预览、Vue GIS 叠加显示和 harness 冒烟。
- 后端新增食品案例接口：
  - `GET /api/cases/food-supply/osm-cache/status`：返回 GraphML 缓存是否存在、`cache_kind`、节点/边计数、`provider_status`、`fallback_reason`，不需要外网或密钥。
  - `POST /api/cases/food-supply/osm-cache/build`：本地构建小规模 `case_baseline_graphml`，默认写入被忽略的 `backend/var/food_supply_osm/`；该图来自案例节点 + Haversine 边，只作为离线对照，返回 `authenticity_level=C` 与 `CASE_BASELINE_GRAPHML_NOT_REAL_OSM`，不伪装成真实 OSM 导航。
  - `POST /api/cases/food-supply/routes/preview`：支持 `provider=auto|osm|amap|tianditu|haversine`，返回 `polyline`、`distance_source`、`path_source`、`authenticity_level`、`fallback_reason`。高德/天地图成功时标记 A 级 provider polyline；GraphML 基线标记 C 级；失败时透明降级到本地 Haversine。
- 修复 GraphML 兼容：`osmnx.load_graphml` 对 `FAC-1`/`BSTORE-001` 业务节点 id 会按整数解析失败，`_load_osm_graph` 现在在该场景下回退 `networkx.read_graphml`，保留业务编码基线图可读。
- Vue `FoodSupplyChainCaseView.vue` 的“GIS 网络”页新增路径预览工作台：缓存状态、构建基线 GraphML、provider/起终点选择、路线预览按钮、常驻真实性标签和降级原因；路线 polyline 会作为高亮路径节点链叠加到 ECharts 拓扑图中。
- `frontend/src/api/foodSupplyCase.js` 新增 `getFoodSupplyOsmCacheStatus`、`buildFoodSupplyOsmCache`、`previewFoodSupplyRoute`。
- `backend/scripts/enterprise_smoke_harness.py` 扩展食品案例检查：`food_supply_osm_cache_status`、`food_supply_osm_cache_build`、`food_supply_route_preview`，并在摘要中输出 `distance_source`、`path_source`、`authenticity_level`、`polyline_points`、`cache_kind`。
- `.gitignore` 新增 `backend/var/`，防止本地 GraphML 缓存误入版本库。
- 验证：
  - `openspec validate enhance-food-supply-advanced-optimization --strict` 通过。
  - `.\backend\.venv\Scripts\python.exe -m py_compile backend\app\services\food_supply_case_service.py backend\app\routes\food_supply_case.py backend\scripts\enterprise_smoke_harness.py` 通过。
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`17 passed`。
  - `cd frontend; npm run build` 通过；仍仅保留既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
  - 临时 5062 app-factory HTTP harness 通过：`30 total`、`26 ok`、`4 auth_required`、`route_missing=0`、`failed=0`；`food_supply_osm_cache_build` 返回 `case_baseline_graphml`，`food_supply_route_preview` 返回 `path_source=case_graphml_baseline`、`authenticity_level=C`、`polyline_points=2`。临时服务已停止。

## 2026-07-04 - 食品供应链案例真实路网矩阵与 pyVRP 第二阶段

- 继续 OpenSpec 变更 `enhance-food-supply-advanced-optimization`，在 `tasks.md` 追加并完成第二阶段：真实 provider/OSM 路网矩阵、pyVRP 可执行适配、harness 验证。
- 后端 `food_supply_case_service.py` 增强 `distance-matrix/build`：
  - `matrix_mode=amap` 会调用既有高德 `AmapService.distance_matrix`，小批量同步上限 10 个节点；成功行标记 `distance_source=amap_driving`、`path_source=amap_distance_matrix`、`authenticity_level=A`，失败行逐 pair 降级到 Haversine 并保留 provider/fallback 原因。
  - `matrix_mode=tianditu` 会调用既有天地图 `TiandituService.distance_matrix`，小批量同步上限 8 个节点；成功行标记 `tianditu_driving` / `tianditu_route_matrix`，失败行透明降级。
  - `matrix_mode=osm` 支持 `FOOD_SUPPLY_OSM_GRAPHML` GraphML 缓存；只有显式设置 `FOOD_SUPPLY_OSM_ENABLE_NETWORK=1` 时才允许 OSMnx 在线拉图，默认不联网，避免演示接口被 Overpass/DNS 拖住。无图时返回 `OSM_GRAPH_UNAVAILABLE_USING_HAVERSINE_BASELINE:*`，不伪装为真实路网。
  - 矩阵响应新增 `diagnostics.source_summary/path_summary/fallback_count/exact_count/requested_limit/effective_node_limit/sync_provider_node_caps`，`persist=true` 仍只写 `case_food_distance_matrix`。
- 后端 `optimize/dispatch` 新增 `solver_mode=pyvrp`：使用 pyVRP `Model` 构建 bounded CVRP，限 `store_limit<=24`、`vehicle_count<=12`，返回 `solver_family=pyvrp_cvrp`、`execution_mode=hybrid_genetic_vrp`、迭代数、runtime、objective，并校验容量与重复分配；advanced solver compare 增加 `pyvrp_dispatch` 执行行。
- 测试新增并通过：Amap/Tianditu mock 成功、provider 失败 per-row fallback、OSMnx graph provenance、pyVRP dispatch、advanced compare pyVRP 执行。验证 `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_food_supply_case_service.py -q` 为 `14 passed`。
- Harness `enterprise_smoke_harness.py` 增加 `food_supply_matrix_amap`、`food_supply_matrix_tianditu`、`food_supply_dispatch_pyvrp`；真实临时 5059 冒烟通过：`27 total`、`23 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，`/api/ready` 显示 `backend=postgresql`、`shipment_facts=50000`，`food_supply_dispatch_pyvrp` 返回 `pyvrp_cvrp/hybrid_genetic_vrp`。
- 验证：
  - `openspec validate enhance-food-supply-advanced-optimization --strict` 通过。
  - `.\backend\.venv\Scripts\python.exe -m py_compile backend\app\services\food_supply_case_service.py backend\app\routes\food_supply_case.py backend\scripts\enterprise_smoke_harness.py` 通过。
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`14 passed`。
  - `cd frontend; npm run build` 通过；仍仅保留既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
  - 临时 5059 harness 通过后已停止服务。

## 2026-07-04 - 食品供应链案例高级优化第一阶段

- 新建 OpenSpec 变更 `openspec/changes/enhance-food-supply-advanced-optimization/`，覆盖 Gurobi/CPLEX MILP、OR-Tools/pyVRP/粒子群调度、pymoo NSGA Pareto、OSM/高德/天地图矩阵来源和 harness 验证。
- 后端 `food_supply_case_service.py` 增强：
  - `distance-matrix/build` 新增 `matrix_mode=postgis|haversine|osm|amap|tianditu|auto`，每条 pair 返回 `distance_source`、`path_source`、`authenticity_level`、`fallback_reason`；OSM/高德/天地图未实际执行时透明降级，不伪装为真实导航。
  - `optimize/network-design` 支持 `solver_mode=milp`，当前本机测试运行态可执行 Gurobi CFLP MILP，返回 `solver_family=gurobi_milp`、`execution_mode=exact_milp`；Gurobi不可执行时尝试 docplex/CPLEX，再降级 greedy。
  - `optimize/dispatch` 支持 `solver_mode=ortools`，当前可执行 OR-Tools bounded CVRP，返回 `solver_family=ortools_cvrp`、`execution_mode=vrp_solver`，并保留容量/重复分配校验；粒子群为 bounded metaheuristic baseline，pyVRP 当前为 readiness-only。
  - `optimize/pareto` 支持 `algorithm_family=nsga`，当前可执行 pymoo NSGA-II，输出成本、碳排、鲜损、服务水平 Pareto front。
  - `optimize/solver-compare` 支持 `advanced_mode=true`，会触发 MILP/OR-Tools/NSGA 执行；普通模式仍是基线 + runtime readiness。
- Vue `FoodSupplyChainCaseView.vue` 新增“高级求解”开关，调度/仓网/Pareto/求解器对比会传 `ortools`、`milp`、`nsga`、`advanced_mode=true`，表格展示 `solver_family` 与 `execution_mode`。
- Harness `enterprise_smoke_harness.py` 已扩展食品案例高级检查：OSM matrix、MILP network、OR-Tools dispatch、NSGA Pareto、advanced solver compare。
- 验证：
  - `openspec validate enhance-food-supply-advanced-optimization --strict` 通过。
  - `.\backend\.venv\Scripts\python.exe -m py_compile backend\app\services\food_supply_case_service.py backend\app\routes\food_supply_case.py backend\scripts\enterprise_smoke_harness.py` 通过。
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_food_supply_case_service.py -q` 通过，`9 passed`。
  - `cd frontend; npm run build` 通过；仍仅保留既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
  - 临时 5057 app-factory HTTP harness 通过：`24 total`、`20 ok`、`4 auth_required`、`route_missing=0`、`failed=0`；高级检查中 MILP=`gurobi_milp/exact_milp`、VRP=`ortools_cvrp/vrp_solver`、Pareto=`pymoo_nsga/multi_objective_search`，OSM matrix 按 `OSM_GRAPH_UNAVAILABLE_USING_HAVERSINE_BASELINE` 透明降级；临时服务已停止。
- 下一阶段重点：把 OSMnx 本地图缓存/裁剪图真正接入矩阵，按高德/天地图批量距离 API 做缓存与限流，生产化 pyVRP adapter，并加入前端地图路线几何预览。

## 2026-07-03 - 专家 Agent 抽屉建议可读性修复

- 用户反馈 MiniMax-M3 专家 Agent 返回的建议正文在抽屉中呈现“白底淡蓝字”，长 Markdown 文本几乎不可读。
- 修复 `frontend/src/views/DecisionConsoleView.vue`：将 Agent 建议正文从普通段落改为 `agent-answer-text` 长文阅读区，并提高标题、正文、JSON 预览、边界提示的对比度。
- 由于 `el-drawer append-to-body` 会把抽屉传送到组件作用域外，Element Plus 抽屉壳样式必须使用 `:global(.agent-drawer ...)` 覆盖；此前 `:deep()` 只稳定影响组件自身输出卡片，不能覆盖 teleported drawer 背景。
- 本地 Playwright + Chrome 只读视觉核验：拦截 `/api/` 请求返回模拟健康数据，不调用真实 LLM、不写业务表；抽屉背景变为深色，建议正文 `agent-answer-text` 为高对比浅色，输出卡片深色背景，未出现页面错误。
- 验证：`frontend npm run build` 通过；仍仅保留既有 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。

## 2026-07-03 - MiniMax-M3 Agent Key 本机配置与输出清洗

- 用户提供维云模型开放平台 key 文件位置；本轮只把 key 写入被 `.gitignore` 忽略的 `backend/.env.local`，未打印、未写入文档/记忆/前端源码/Git。
- `backend/.env.local` 已配置 `MINIMAX_BASE_URL=https://vsllm.com/v1`、`MINIMAX_MODEL=MiniMax-M3`、`MINIMAX_API_KEY`；后端 `run.py` 会在启动时优先加载该本机文件。
- 重启当前 `backend\.venv` 后端后，`/api/runtime/capabilities?solver_probe=0` 显示 `agent_status=ok`、`agent_key_configured=true`、`model=MiniMax-M3`、`api_keys_returned=false`，同时 PostgreSQL 仍为 `shipment_facts=50000`。
- 真实 `/api/agent/chat` 冒烟成功：`success=true`、`provider_status=ok`、`fallback_reason=null`，说明前端“获取建议”不应再显示 `MINIMAX_API_KEY_MISSING`。
- 修复 Agent 网关输出清洗：若模型返回 `<think>...</think>` 思考标签，后端会剥离后再返回 Vue；system prompt 也明确要求不输出隐藏推理或 `<think>` 标签。
- 验证：`backend .\.venv\Scripts\python.exe -m py_compile app\services\agent_gateway_service.py` 通过；`backend .\.venv\Scripts\python.exe -m pytest tests\test_runtime_agent_gis_decision_routes.py -q` 通过，`9 passed`。

## 2026-07-02 - 演示稳定闭环与 Agent 轻量面板

- 后端 `/api/runtime/capabilities` 新增 `demo_readiness` 摘要：聚合 PostgreSQL/`shipment_facts`、关键路由注册、项目 `.venv`、高德/天地图、MiniMax Agent、可选 solver 状态；只返回安全布尔与降级原因，不返回 key、密码、token 或 license 内容。
- `backend/scripts/enterprise_smoke_harness.py` 扩展为 13 项演示冒烟，覆盖 `/api/runtime/capabilities`、`/api/gis/provider-health`、`advanced-ml`、企业汇总、碳足迹、Agent 工具预演、Decision dry-run、优化能力和调度 health/preview/smart；脚本区分 `ok`、`auth_required`、`route_missing`、`server_error`，401/403 不再误判为 404。
- Vue `DecisionConsoleView.vue` 新增“演示健康条”，首屏显示 PostgreSQL 5 万数据、13/13 路由注册、GIS Provider A 级、MiniMax Agent key 状态、调度健康、Gurobi/RL 可选 solver 状态。
- Vue `DecisionConsoleView.vue` 新增专家 Agent 抽屉：固定 GIS 路网、智能调度、成本风险、仓网设计、数据质量、运营报告 6 个角色；支持只读工具预演、MiniMax-M3 建议调用和 `/api/decision/scenarios` dry-run 草稿，默认 `persist:false`，不写业务事实表。
- 前端请求层 401/403/404 文案改为可恢复诊断：404 会提示检查当前 `backend\.venv` 进程和 `/api/runtime/capabilities` 路由注册摘要。
- 新增 `docs/DEMO_STABILITY_RUNBOOK_2026-07-02.md`，记录推荐启动命令、冒烟命令、401/404/旧进程排查和 secret 纪律。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_runtime_agent_gis_decision_routes.py tests\test_optional_capability_service.py tests\test_postgres_layered_preview_fallback.py -q` 通过，`20 passed`。
- 验证：`frontend npm run build` 通过；仍仅保留既有 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 真实 HTTP 冒烟：重启当前 `backend\.venv` 后端后，`/api/runtime/capabilities?solver_probe=0` 显示 `demo_readiness.status=ready`、`score=96`、`backend=postgresql`、`shipment_facts=50000`、`registered_capabilities.missing=[]`、`using_project_venv=true`；MiniMax 未配置时仅 Agent 降级为 `MINIMAX_API_KEY_MISSING`。
- Harness 冒烟：不带 token 时 13 项中 9 项 200、4 项 `auth_required`、0 个 404；带默认演示登录 token 时 13/13 全部 200，`/api/dispatch/preview` 与 `/api/dispatch/smart` 均可用，20 单波次分配 10 单、未分配 10 单，降级原因明确为 `precise_distance_disabled_or_missing_coordinates`。
- 浏览器验证：`http://127.0.0.1:5173/decision-console` 无白屏，健康条显示 50,000 运单、13/13 路由、GIS A 级、10/10 可选能力；点击“专家 Agent”抽屉正常打开，点击“工具预演”后页面出现 `read_only` 与 `will_execute=false`，仅剩既有 ECharts tick 可读性 warning。

## 2026-07-02 - 优化引擎与网络设计真实数据接入

- 修复 `/optimization-engine` 与 `/network-design` 运行态动态导入问题：清理 `frontend/node_modules/.vite` 并重启 5173 后，`NetworkDesignView.vue` 与 `OptimizationEngine.vue` 动态模块均返回 200。
- 新增 `GurobiNetworkDesignService.database_dataset_payload()`，把真实 `shipment_facts` 按目的城市/始发城市聚合成 bounded 客户与候选设施数据，保留 `data_source`、`distance_source`、`path_source`、`authenticity_level`、`fallback_reason` 和 `shipment_facts_total`。
- 新增 `/api/optimization/real-shipment-demo` 与 `/api/optimization/real-vrp-demo`，把真实城市 OD 聚合投影到 0-100 平面，供优化引擎 VRP/solver 对比页面使用，并明确标注投影不是高德导航路径。
- 新增 `/api/network/real-shipment-dataset`，供网络设计页面直接加载真实目的城市客户与始发候选设施；Vue 页面默认数据源改为“真实运单”，测试数据和节点同步仅作为兜底。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_gurobi_network_design_service.py -q` 通过，`7 passed`。
- 验证：`frontend npm run build` 通过；仅保留旧 glyphicons 字体路径、旧 CSS `*zoom`、大 chunk 体积警告。
- 真实 PostgreSQL 冒烟：`/api/ready` 显示 `backend=postgresql`、`shipment_facts=50000`；优化真实样本返回 `data_source=shipment_fact_od_aggregate`、`n_customers=8`；网络真实数据集返回 8 个客户、4 个候选设施、`shipment_facts_total=50000`。
- 浏览器验证：点击侧边栏「优化引擎」显示“已加载真实运单样本：12 个目的城市”；点击「网络设计」显示 `shipment_fact_city_od_aggregate` / `haversine_corrected` 的真实性等级 C 说明；未再出现 `Failed to fetch dynamically imported module`。

## 2026-07-02 - Vue 动态导入与高德 Key 本机配置修复

- 用户反馈 `/decision-console` 与 `/ml-prediction` 点击时报 `Failed to fetch dynamically imported module`，地图页仍显示高德 `Key 缺失`。
- 排查确认：`DecisionConsoleView.vue` 与 `MLPredictionView.vue` 直接经 Vite 请求均为 `200 text/javascript`，`frontend npm run build` 也能通过；实际根因是前端 dev server 仍使用旧 Vite 依赖缓存/旧 env，且 `frontend/.env.development` 中空的 `VITE_AMAP_KEY=` 覆盖了 `.env.local`。
- 安全处理：从本机 key 文件生成被 `.gitignore` 忽略的 `frontend/.env.local`、`frontend/.env.development.local`、`backend/.env.local`；未在命令输出、文档或记忆中打印任何 API key、数据库密码或 token。
- 后端本机启动边界：`backend/run.py` 负责加载 `backend/.env.local`；`backend/config.py` 不直接加载本机 key，避免 pytest/test client 误读真实密钥。`TestingConfig` 显式清空地图 provider key，防止测试间配置污染。
- 重启前端后，Vite inline HTML proxy 中 `VITE_AMAP_KEY` 不再为空，且会注入高德 JS API；重启后端后，`/api/amap/provider-health` 登录态冒烟返回 `provider_status=ok`、`KEY_CONFIGURED=True`、`KEY_SOURCE=AMAP_SERVICE_KEY`。
- 真实数据冒烟：`/api/ready` 返回 `status=ready`、`database_runtime.backend=postgresql`、`shipment_facts=50000`。
- 浏览器验证：登录态下点击「智能决策中枢」进入 `/decision-console`、点击「AI 预测」进入 `/ml-prediction`，均无 `Failed to fetch dynamically imported module`；点击「地图视图」进入 `/map`，页面显示 `Key 已配置`，不再显示 `Key 缺失`。
- 验证：`frontend npm run build` 通过；仍仅有既有 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。`backend .\.venv\Scripts\python.exe -m pytest tests\test_amap_phase1_contract.py -q` 通过，`10 passed`。

## 2026-07-02 - 企业级 AI/优化能力探测、Dispatch 稳定与控制塔强化

- 用户要求执行三阶段目标：P0 修复 Vue 智能调度可访问/可点击、地图 key 配置和真实 PostgreSQL 冒烟；P1 以可选能力探测方式接入 CPLEX、pymoo、Torch/SB3、Optuna、Gurobi/OR-Tools/LightGBM/Transformers/geospatial stack；P2 补齐企业级决策控制台、测试 harness、OpenSpec/记忆日志。
- 新建 OpenSpec 变更：`openspec/changes/strengthen-enterprise-ai-optimization-platform/`，包含 proposal、design、3 个 specs 和 tasks；本轮 tasks 已全部打勾。
- 安全配置：移除 `frontend/vite.config.js` 与 `frontend/index.html` 中硬编码的高德浏览器 key/security key，改为 `VITE_AMAP_KEY`、`VITE_AMAP_SECURITY_KEY`；新增 `frontend/.env.example`，`frontend/.env.development` 只保留空占位，不写真实 key。
- Provider 健康：`/api/amap/provider-health` 在 key 缺失时明确返回 `provider_status=degraded`、`fallback_reason=AMAP_KEY_MISSING`；新增缺 key 回归测试。
- 后端能力矩阵：新增 `optional_capability_service.py`，新增 `/api/optimization/capabilities` 与 `/api/optimization/capability-health`；`/api/optimization/solvers` 同步返回 capability summary。所有响应只返回可用性、版本、fallback、边界和安全布尔，不返回密钥、密码或 license 内容。
- DRL 修复：修正 `drl_vrp_solver.py` 的错误相对导入，并修复 nested attention 中的 torch 引用；DRL-VRP 可被 solver registry 识别，但仍保持 shadow/rerank 边界。
- Vue 控制塔：`DecisionConsoleView.vue` 接入“优化/AI 能力矩阵”和 Optional Runtime 评分组件，展示 Gurobi、CPLEX/docplex、OR-Tools、pymoo、Torch、Stable-Baselines3、Optuna、LightGBM、Transformers、geospatial stack 的状态。
- Harness：新增 `backend/scripts/enterprise_smoke_harness.py`，支持传入 backend URL 与可选 token 后冒烟 ready、capabilities、dispatch health/preview/smart；输出精简 JSON，不打印 token。
- 验证：`backend\.venv\Scripts\python.exe -m py_compile backend\app\services\optional_capability_service.py backend\app\routes\optimization.py backend\app\services\optimization_engine\solvers\drl_vrp_solver.py backend\scripts\enterprise_smoke_harness.py` 通过。
- 验证：`backend\.venv\Scripts\python.exe -m pytest backend\tests\test_optional_capability_service.py backend\tests\test_amap_phase1_contract.py backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_dispatch_smart_contract.py backend\tests\test_postgres_layered_preview_fallback.py backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q` 通过，`61 passed`；仍有 Flask-Limiter 内存存储、测试 JWT key 长度、SQLAlchemy legacy Query.get 等既有警告。
- 验证：`frontend npm run build` 通过；`DispatchView` 成功产出 chunk，未再出现 Vite `%VITE_AMAP_*%` 未定义警告；仍有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 真实 PostgreSQL test-client 冒烟：`/api/ready` 显示 `backend=postgresql`、`shipment_facts=50000`；`/api/optimization/capabilities` 显示 `available=10/total=10`、RL shadow/geospatial 可用；`/api/dispatch/health` 显示 `data_source=shipment_fact`、`dispatchable_orders=200`；`/api/dispatch/preview` 与 `/api/dispatch/smart` 均 200，20 单波次分配 10 单、未分配 10 单、2 条 plans，provider 降级原因明确为 `precise_distance_disabled_or_missing_coordinates`。
- 敏感信息检查：源码扫描未命中旧高德硬编码 key 或数据库密码；本次没有把 PostgreSQL 连接串、API key、SSH key 或 license 内容写入文档/记忆。

## 2026-07-01 - AI 预测真实性与 DQN Shadow 调度升级

- 用户要求落实“物流 AI 预测与 DQN 调度升级计划”，重点修复 AI 预测空趋势/0 值误导，并明确 LSTM/Transformer 与 DQN 不能伪装为已在线接管。
- 后端 `shipment_prediction_service.py` 新增真实时间轴审计和预测序列适配：`/api/ai-prediction/timeline/audit` 返回 `shipped_at/eta_at/delivered_at/signed_at/created_at` 的日期/小时覆盖、推荐粒度和训练窗口；`/api/ai-prediction/demand/forecast` 支持 `time_granularity=daily|hourly|auto` 与 `series_source`。
- 预测接口改为数据库侧按时间桶聚合，不再先截取前 N 条订单再聚合；真实 5 万数据当前 `shipped_at` 只有 2 个业务日期，auto 会降到 24 个小时桶，并返回 `forecast_status=degraded`、`fallback_reason=DEMAND_DAILY_POINTS_INSUFFICIENT_USING_HOURLY_FALLBACK`，不再把历史不足渲染成“预测订单 0”或“日级深度模型可用”。
- 新增 AI 预测后台任务：`POST /api/ai-prediction/jobs` 与 `GET /api/ai-prediction/jobs/:id`。LSTM/GRU/Transformer 目前是 deep shadow readiness/job，不阻塞 Flask 请求，不写业务表；时间窗口不足时返回 degraded readiness。
- 调度升级为分层策略：`/api/dispatch/preview` 新增 `policy_mode=solver_only|shadow_rerank|dqn_shadow`，响应包含 `solver_plan`、`rl_rerank`、`constraint_validation`、`deployable`。DQN shadow 只做候选方案评分/重排建议，容量与订单唯一分配等硬约束仍由 solver validation 保底。
- 新增调度 policy 后台任务：`POST /api/dispatch/policy/jobs` 与 `GET /api/dispatch/policy/jobs/:id`；响应补齐顶层 `job_id/status/policy_family/runtime_profile`，便于 Vue 轮询和后续 agent 冒烟。
- Vue `MLPredictionView.vue` 升级为更诚实的预测页：展示时间轴状态、forecast 降级原因、深度 Shadow job；即使小时桶 forecast 有结果，也会提示这是历史不足后的降级预测。`DispatchView.vue` 增加 AI 策略层选择和 Solver + AI Shadow 对比面板。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest backend\tests\test_shipment_prediction_service.py backend\tests\test_dispatch_orchestration_layered.py -q` 通过，`32 passed`。
- 验证：`frontend npm run build` 通过；仍仅有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 真实 PostgreSQL HTTP 冒烟：临时端口 `5056` 当前代码后端返回 `/api/ready` `backend=postgresql`、`shipment_facts=50000`；`timeline/audit` 显示 `shipped_dates=2`、`shipped_hours=24`、`recommended_granularity=hourly`、`training_window_count=10`；轻量 forecast 84ms 返回 degraded hourly forecast；LSTM job 57ms 创建、轮询 completed 但 `fallback_reason=needs_more_time_points`；`dispatch/preview` `policy_mode=dqn_shadow` 52ms 返回 `validation_passed=true`、`violation_count=0`、`deployable=false`；policy job 22ms 创建并完成。
- 临时 `5056` 后端服务已停止；不要把数据库连接串、token 或任何密钥写入文档/提交。

## 2026-07-01 - AI/调度超时与后端 500 稳定化

- 用户反馈 AI 预测、异常检测、调度 shadow 页面打开后 30s timeout，并伴随 `/api/dispatch/fitted-q-shadow-model`、`reward-model`、`shadow-benchmark`、`shadow-benchmark/snapshot` 500；分析确认主因不是 Flask-Limiter，也不需要立即迁移 FastAPI，而是 Vue 首屏并发触发多个真实 5 万数据/调度 shadow 重接口。
- 新增后端 `runtime_profile` 约定：`interactive` 用于页面首屏，prediction/anomaly `limit<=5000`，调度 shadow `scenario_limit<=1`、`row_limit<=20`、`anomaly_source_limit<=2000`、`use_ml=false`；`full` 保留给用户手动训练/全量分析。
- 后端 `ai_prediction.py` 与 `ai_anomaly.py` route 层统一裁剪 interactive 请求并在响应中附加 `runtime_profile`、`runtime_limits`；模型训练默认仍可走 full，但前端默认训练样本收窄到 10000。
- 后端 `dispatch.py` 的调度学习/shadow route 接入运行保护；Fitted-Q、reward、RL、redispatch、shadow benchmark、snapshot 等可选 shadow 端点遇到内部异常时返回 HTTP 200 + `success:false`、`provider_status:degraded`、`fallback_reason`，不再让控制台直接炸成 500；核心 `/dispatch/preview`、`/dispatch/smart`、`/dispatch/health` 仍保留真实错误语义。
- Vue API 默认轻量化：`frontend/src/api/aiPrediction.js`、`aiAnomaly.js`、`dispatch.js` 不再默认 5 万或开启 ML/RL；full 任务使用更长 timeout 并由按钮手动触发。
- Vue 页面修复：`MLPredictionView.vue` 首屏只跑 demand forecast、capacity gap、scorecard，并新增训练后 `model_id` 预测入口；`AnomalyDetectionView.vue` 将 IsolationForest/ML 深度检测改成手动按钮；`DecisionConsoleView.vue` 初始化改为最多 2 个并发的小批量请求，并移除自动 Fitted-Q/RL/snapshot，改为“高级 Shadow”手动刷新。
- 前端请求错误提示区分 timeout、后端不可达、服务器错误和后端降级原因，减少“网络错误”误导。
- 新增回归测试：interactive profile 裁剪 prediction/anomaly limit；Fitted-Q shadow 内部异常时 route 返回 200 degraded 并保留 shadow truth contract。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_dispatch_orchestration_layered.py tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py -q` 通过，`33 passed`。
- 验证：`frontend npm run build` 通过；仍仅有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 限制：当前 Codex shell 未设置 `POSTGRES_DATABASE_URL`，本机 `http://127.0.0.1:5000/api/ready` 探测返回 502，未做真实 PostgreSQL 5 万数据 HTTP smoke；真实 smoke 需要用户在启动后端的同一 PowerShell 会话中设置 PostgreSQL 连接串后重启。

## 2026-07-01 - 真实订单数据源诊断与 Vue AI 决策增强

- 用户反馈订单真实数据全变 0，并希望把 `frontend-next` 的 AI 预测、高级功能、异常检测、智能调度能力进一步集成回 Vue 主前端。
- 数据源根因：当前 Codex shell 未注入 PostgreSQL 连接串，C 盘 backend 没有 `.env`；D 盘 backend `.env` 中 `DATABASE_URL` 当前也是 SQLite。实测 `/api/ready` 在该环境下显示 `database_backend=sqlite`、`shipment_facts=0`、`legacy_orders=0`，因此这是启动环境落到 SQLite 兜底，不代表 PostgreSQL 真实 5 万 `shipment_facts` 丢失。
- 后端修复：`/api/orders`、`/api/orders/stats`、`/api/orders/statistics`、`/api/stats/overview`、`/api/stats/orders/trend`、`/api/stats/orders/distribution` 在 auto 模式下优先真实 `shipment_facts`，即使 legacy `orders` 有演示残留也不会抢主源；仍支持 `data_source=orders` 显式查看旧表。
- 后端诊断增强：`/api/ready` 返回 `database_runtime`，包含数据库 backend、主订单源、`shipment_facts`/legacy `orders` 计数、count error 和 SQLite 兜底 warning；SQLite 表缺失时也能返回诊断而不是直接失败。
- Vue 订单页增强：`frontend/src/views/Orders.vue` 增加数据源 warning，当接口未检测到 `shipment_facts` 时直接提示检查 `POSTGRES_DATABASE_URL` 或 `DATABASE_URL` 后重启后端，避免用户只看到 0。
- Vue 决策中枢增强：`frontend/src/views/DecisionConsoleView.vue` 集成更多原 `frontend-next` 能力，新增 AI 能力雷达、需求预测曲线、异常信号分布、AI 深度预测增强、调度学习链与 RL Shadow 面板；调度 API 封装新增 learning dataset、policy scorer、reward model、RL shadow runner、Fitted-Q、shadow benchmark snapshot 等接口。
- 样式修复：补齐 `.visual-grid`、`.visual-panel`、`.visual-chart`、`.forecast-ribbon`、`.mini-bar` 等样式，保证图表高度、响应式布局和文字截断稳定。
- 验证：`frontend npm run build` 通过；仍仅有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_postgres_layered_preview_fallback.py tests\test_order_route_shipment_fact_compat.py tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`28 passed`。
- 冒烟：在未注入 PostgreSQL 的当前环境下，Flask test client 请求 `/api/ready` 返回 200，并明确显示 SQLite 兜底 warning 与 count errors。真实 PostgreSQL 业务数据冒烟仍需用户启动后端时在同一 PowerShell 会话中设置 PostgreSQL 连接环境变量。

### 后续 PostgreSQL 连接串复核

- 用户按 `[PostgreSQL 连接串已脱敏]` 启动后仍看到 Dashboard 500；排查发现 5000 端口旧进程仍在运行，且 `/api/ready` 返回 `psycopg2.OperationalError`。
- 只读验证确认 PostgreSQL 服务 `postgresql-x64-18` 正常、5432 接受连接，`logistics_route_system.public.shipment_facts` 存在且计数为 50000；`app_dev` 与 `postgres` 库没有该表。
- 使用 `127.0.0.1` 替代 `localhost` 并重启 5000 后端后，`/api/ready` 返回 `backend=postgresql`、`shipment_facts=50000`。
- 登录后 Dashboard 关键接口冒烟通过：`/api/stats/overview` 返回 `total_orders=50000`、`/api/orders?per_page=8` 返回 `data_source=shipment_fact`、趋势/分布/车辆利用率接口均 200。
- 后续本地启动建议固定使用 `127.0.0.1`，并先确认 5000 没有旧进程占用。

## 2026-07-01 - Vue 单前端决策中枢修复

- 用户反馈双前端模式连通性仍不稳定，希望把 Next.js 决策控制台换回最适配现有系统的 Vue 前端，类似之前大数据分析平台的集成方式。
- 确认当前代码已将 AI 决策中枢落到 Vue 原生路由 `/decision-console`，页面文件为 `frontend/src/views/DecisionConsoleView.vue`，侧边栏入口为 `frontend/src/views/Layout.vue` 的「智能决策中枢」。
- 确认 Vue 侧不再依赖 `VITE_NEXT_CONSOLE_URL`；`frontend/.env.development` 只保留 `VITE_WS_URL=http://127.0.0.1:5000` 和 `VITE_WS_TRANSPORTS=polling`。
- 确认 `frontend/src/main.js` 不再在登录页提前连接 WebSocket，只暴露 `window.wsService`；`frontend/src/services/websocket.js` 已做幂等连接、HMR cleanup、开发环境 polling 和失败温和提示。
- 后端本地稳定性配套：`backend/run.py` 支持 `DISABLE_KAFKA_CONSUMER=1`；`backend/config.py` 默认关闭 SQL echo；`/api/ai-prediction/scorecard` 已修复时间序列 backtest 数据不足时可能 500 的问题。
- 新增 `docs/VUE_DECISION_CONSOLE_SINGLE_FRONTEND_2026-07-01.md`，明确 `frontend-next/` 仅为历史参考，普通登录、导航和 AI 决策中枢不再依赖 Next.js 或 `5174` 端口。
- 更新 `.codex/memory/MEMORY.md`，替换旧的 Vue -> Next 桥接记忆，避免后续 agent 继续按双前端链路启动。
- 验证：`frontend npm run build` 通过；仍有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`20 passed`。
- 烟测：本机已有 `5000` 和 `5173` 服务监听；`http://127.0.0.1:5000/api/health` 返回 200，`http://127.0.0.1:5173/decision-console` 返回 200。

## 2026-07-01 - C 盘项目独立后端虚拟环境搭建与冒烟

- 用户确认希望在 `C:\tmp\logistics-route-command-center-layout-dashboard-shell` 下搭建独立虚拟环境，避免继续混用 C 盘源码与 D 盘旧 venv。
- 检查本机 Python：可用 Python 3.11，项目原先没有 `backend\.venv`。
- 更新 `.gitignore`：新增 `.venv/`，避免虚拟环境被误提交。
- 在 `backend\.venv` 创建 Python 3.11 虚拟环境，升级 `pip/setuptools/wheel`。
- 安装 `backend/requirements.txt` 成功；补充安装 `pytest`，并新增 `backend/requirements-dev.txt` 用于可复现开发环境。
- 验证：新 `.venv` 下 `pip check` 返回 `No broken requirements found.`。
- 验证：新 `.venv` 下 `py_compile` 通过 `shipment_prediction_service.py`、`shipment_anomaly_service.py`、`shipment_cost_analytics_service.py`、`config.py`、`run.py`。
- 验证：新 `.venv` 下 `python -m pytest tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`19 passed`。
- 冒烟：使用 `FLASK_CONFIG=testing`、`DISABLE_ML_ROUTES=1`、`FLASK_HOST=127.0.0.1`、`FLASK_PORT=5050` 临时启动后端，`/`、`/api/health`、`/api/ready` 均返回成功；随后已停止临时服务。
- 注意：当前 Codex shell 没有 `POSTGRES_DATABASE_URL` / `DATABASE_URL`，因此本次 HTTP 冒烟不代表 PostgreSQL 真实业务数据链路已冒烟；用户本地真实启动时仍需设置 PostgreSQL 连接环境变量且不得写入文档/记忆。
- 观察：未启动 Kafka 时日志会出现 `NoBrokersAvailable`，但不影响基础健康接口。后续可考虑为本地开发新增 Kafka consumer 禁用开关。

## 2026-07-01 - AI/analytics 后端连接池与 5 万事实表读取稳定性修复

- 用户反馈后端运行不久即在 `/api/ai-prediction/baseline/evaluate` 报错，堆栈卡在 SQLAlchemy `engine.raw_connection()` 取数据库连接；报错链路来自 C 盘活动 worktree 源码，解释器来自 D 盘 venv。
- 根因排查：Next 首页/AI 页面会并发请求 prediction、anomaly、operations 等多个 scorecard；其中 prediction baseline、anomaly detect、operations summary 都存在 `shipment_facts` 默认 `limit=50000` 并全量 `.all()` 加载 ORM 实体的模式，容易在真实 PostgreSQL 数据和 SSR 并发下放大连接池、内存和响应时间压力。
- 修复 `backend/app/services/shipment_prediction_service.py`：ETA、delay、cost、daily demand、time-series、capacity gap、cost volatility 等链路改为列级投影 + `yield_per` 分块迭代；状态分布改为数据库端 `GROUP BY count`。
- 修复 `backend/app/services/shipment_anomaly_service.py` 与 `backend/app/services/shipment_cost_analytics_service.py`：核心 `_query_facts` 改为只取分析需要的列，不再构造完整 `ShipmentFact` ORM 对象。
- 修复 `backend/config.py`：PostgreSQL URI 下启用连接池护栏，可用环境变量调整 `SQLALCHEMY_POOL_SIZE`、`SQLALCHEMY_MAX_OVERFLOW`、`SQLALCHEMY_POOL_TIMEOUT`、`SQLALCHEMY_POOL_RECYCLE`、`POSTGRES_CONNECT_TIMEOUT`、`POSTGRES_STATEMENT_TIMEOUT_MS`、`POSTGRES_IDLE_TX_TIMEOUT_MS`。
- 新增回归测试：prediction baseline、anomaly detect、operations summary 会 monkeypatch `sqlalchemy.orm.Query.all`，确保这些 5 万事实表链路不退回全量 ORM `.all()`。
- 验证：`python -m pytest backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q` 通过，`19 passed`。
- 验证：D 盘 venv 下 `py_compile` 三个服务文件与 `config.py` 通过；D 盘 venv 下 `create_app('testing')` 成功，注册路由 `424` 条。D 盘 venv 未安装 `pytest`，因此单测使用系统 Python 执行。

## 2026-07-01 - 后端启动环境纠偏

- 用户提醒后端运行环境不是系统 Python，而是 `D:\物流路径规划系统项目\backend\venv\Scripts\python.exe`。
- 检查结果：该解释器存在，版本为 Python 3.11.4；当前项目 `C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend\run.py` 存在。
- `pip check` 发现冲突：`apache-beam` 与 `protobuf`、`apache-flink` 与 `apache-beam`、`ortools 9.15` 与 `numpy 1.26.4`。这些主要影响大数据/高级求解链路，不一定阻断 Flask 核心启动。
- 按 `requirements.txt` 检查缺失：`eventlet`、`gunicorn` 未安装；当前 WebSocket service 使用 `async_mode='threading'`，所以本地 Windows 启动可先不依赖 `eventlet/gunicorn`，但生产/依赖一致性建议补齐或更新 requirements。
- 额外发现：当前 C 盘 backend 没有 `.env`，D 盘 backend 有 `.env`。如果直接在 C 盘 backend 运行 `run.py` 且未设置 `POSTGRES_DATABASE_URL` / `DATABASE_URL`，会落到 SQLite 兜底并可能出现 dispatch 表路径警告。
- 新推荐启动方式：在 C 盘新版 backend 目录执行 D 盘 venv Python，并先加载 D 盘 backend `.env`，但不读取/打印 `.env` 内容。

## 2026-07-01 - Vue 到 Next AI 控制台桥接入口

- 重新读取 `.codex/memory/MEMORY.md`、`.codex/memory/WORKLOG.md`、`AGENTS.md` 和 `.shared-memory/daily/2026-07-01.md`，确认当前项目已完成后端 AI/调度/Gurobi/地图增强、`frontend-next` 深色指挥中枢风格统一和 4 个提交固化。
- 在 `frontend/src/views/Layout.vue` 侧边栏接入「AI 决策控制台」入口，将 Vue 生产前端作为系统底座，`frontend-next` 作为 AI 增强融合壳。
- 默认 Next 地址为 `http://localhost:5174`，可通过 `VITE_NEXT_CONSOLE_URL` 覆盖。
- 入口点击前会以浏览器 HTTP 探测 Next 壳可达性，显示 `探测中` / `Next 在线` / `Next 未连接` 状态；未连接时给出友好提示并仍打开新标签，方便用户发现是服务未启动还是链接问题。
- 本轮不读取 `frontend/.env.development` 内容，避免误碰本地私有配置。

### 后续修正

- 用户反馈登录 Vue 后看不到入口、进入 Next 后仍提示登录超时。
- 修正 `frontend/src/views/Layout.vue`：将入口移动到侧边栏品牌区下方并让侧边栏改为 flex 布局，菜单滚动区不再挤掉桥接入口。
- 新增 `frontend-next/app/api/auth/handoff/route.ts`：允许 Vue 从 `localStorage` 读取登录 token 后，通过 CORS + credentials 调用 Next handoff；Next 验证 Flask `/api/auth/me`，必要时用 refresh token 调 `/api/auth/refresh`，再写入 httpOnly cookie。
- Vue 点击桥接入口时会先同步 Next 登录态，再打开 Next 控制台。
- 验证：`frontend-next npm run typecheck` 通过；`frontend npm run build` 通过。

## 2026-07-01 - C哥 验证 + 风格统一 + 提交收尾

C哥接手 codex 的未提交工作区（117 文件堆在工作区，且 codex 2026-07-01 那轮只整理记忆没验证代码），完成验证、风格统一和提交收尾。小宇核心诉求：frontend-next 壳风格统一到 Vue 指挥中心大屏。

- **阶段 0 验证（全绿）**：后端测试 68 passed（AI 三件套 16 + Gurobi 四件套 18 + 地图路线 17 + 调度兼容 17）；前端 typecheck + build 通过；Python 3.14.3 + Gurobi 13.0.1 + 全依赖就绪。确认 `ai_prediction`/`ai_anomaly` 路由已在 `backend/app/__init__.py:220-221` 注册。
- **阶段 1 风格统一（核心交付）**：发现 frontend-next 原为浅色商务风（#f6f8fb），与 Vue command-center 深色科幻大屏（#07111f + 青色发光）不一致。研究 Vue 设计系统（`command-center-theme.css` + `main.css` + `Layout.vue` 809 行），重写 `frontend-next/app/globals.css`：保持全部类名和布局属性，只换视觉层（CSS 变量改值 + 面板加 `backdrop-filter: blur(18px)` + 激活态加 glow + 背景加径向发光 + 青色滚动条）。playwright 截图 5 页验证（首页/AI预测/异常/调度/登录）全部深色指挥中心风，无塌陷、无对比度问题。
- **阶段 2 验收**：对照 AGENTS.md 7 条验收指标全部满足（`types.ts` 1821 行完整类型 + `TruthMetadata` 基类 + `TruthStrip` 组件 + 各服务 `fallback_reason`）。
- **阶段 3 提交**：4 commit 固化 117 文件 +33350 行，工作区干净：
  - `f467bf3` 智能决策平台后端（62 文件 +19366 行）
  - `a849852` Next.js 决策控制台 + 深色指挥中心风格（47 文件 +13274 行）
  - `6237c95` Vue 前端增强 + 配置对齐（5 文件）
  - `d440a32` AGENTS.md 协作指南 + .codex 记忆（3 文件）
- 详细日志见 `.shared-memory/daily/2026-07-01.md`。

## 2026-07-02 - 旧 Vue 分析/大屏/高级页面真实数据升级

- 修复并验证 `/api/advanced-ml/predict/with-anomaly` 兼容层契约：`DISABLE_ML_ROUTES=1` 时 legacy `/api/ml` 可禁用，但 `/api/advanced-ml/*` 仍注册，避免 AI 高级功能页 404。
- 新增前端统一转换层 `frontend/src/utils/enterpriseSummary.js`，将 `/api/analytics/enterprise-summary` 映射为数据分析、风险管理、数据大屏、大数据屏、敏捷优化和高级路径页面模型。
- `DataAnalyticsView.vue` 已改为真实 `shipment_facts` 摘要驱动：预测性维护、城市客群、供应链节点、碳排估算均带真实数据/估算边界，不再在接口失败时塞随机/演示数据。
- `RiskManagementView.vue` 已接真实 Top 线路风险：基于运费占比、准时率、异常率生成 Kraljic 分类和风险矩阵；旧 risk API 可补充细节，但不可用时保留真实摘要降级视图。
- `AdvancedRouteView.vue` 与 `AgileOptimizationView.vue` 已显示真实摘要与可选求解/AI runtime 能力边界；DRL/SB3 仍标记为 shadow/rerank，不作为在线硬约束求解器。
- `DataScreen.vue` 与 `BigDataScreen.vue` 已从固定演示数值切到真实摘要：订单趋势、成本趋势、城市节点、Top OD、Spark/Kafka 可选降级都可解释；`BigDataScreen` 不再主动请求不存在的 `/bigdata/dashboard`。
- `AdvancedFeaturesView.vue` 去除价格预测随机 fallback，改为确定性本地估算并标注降级原因。
- 验证：`frontend npm run build` 通过；`backend .\.venv\Scripts\python.exe -m pytest tests\test_postgres_layered_preview_fallback.py tests\test_shipment_prediction_service.py tests\test_shipment_anomaly_service.py tests\test_shipment_cost_analytics_service.py -q` 通过，`32 passed`。

## 2026-07-02 - Vue 动态导入失败恢复与网络设计验证

- 复核用户当前后端启动链路：`/api/ready` 返回 PostgreSQL connected，`database_runtime.backend=postgresql`，`shipment_facts=50000`，说明当前后端启动命令没有把真实数据源带偏。
- 排查 `Failed to fetch dynamically imported module: /src/views/NetworkDesignView.vue`：一度发现 `127.0.0.1:5173` 未监听，`curl --noproxy` 直连失败；随后 5173 重新监听后，直接请求 `/src/views/NetworkDesignView.vue` 返回 200 和 Vite 编译模块，确认源码文件和路由挂载存在。
- 在 `frontend/src/router/index.js` 增加动态 import 失败一次性自恢复：命中 Vite/浏览器动态模块加载失败时按目标路由自动刷新一次，第二次仍失败则输出可诊断 console error，避免无限刷新。
- 验证 `frontend npm run build` 通过；仍保留历史 glyphicons 字体路径、旧 CSS `*zoom`、大 chunk 警告。
- 浏览器验证 `/data-analytics` -> 点击「网络设计 仓网布局与选址」-> `/network-design`：页面正常渲染，未出现 NetworkDesignView/MLPredictionView/DecisionConsoleView 动态导入错误，未见相关 404/500/502 控制台错误；仅剩 Element Plus radio `label` 即将弃用警告。
- 结论：本轮用户看到的网络设计点不开，更可能是旧 Vite dev server、浏览器/HMR 缓存或 5173 未真正运行导致；不是 PostgreSQL 后端启动命令问题。

## 2026-07-02 - GIS/MIS/AI Agent 一体化平台 P0/P1 接口落地

- 新增后端运行态诊断：`/api/runtime/capabilities` 与 `/api/ready.registered_capabilities`，可直接看当前进程是否注册 `advanced-ml`、`enterprise-summary`、`data-analytics carbon`、`agent_gateway`、`gis_provider_health`、`decision_scenarios` 等关键接口，避免源码已改但旧后端进程仍 404。
- 新增安全 Agent 网关：`/api/agent/chat`、`/api/agent/tools/preview`、`/api/agent/actions/confirm`。MiniMax-M3 只从后端环境变量读取 `MINIMAX_*`，未配置 key 时返回 HTTP 200 + degraded；工具预演强制只读，不写业务状态；文本和上下文会做基础脱敏。
- 新增 GIS provider 聚合健康接口：`/api/gis/provider-health`，汇总高德 key 状态、天地图 key 状态、PostGIS 探针、本地 Node/Route 图和 geospatial runtime，响应不返回任何 key 值。
- 新增统一决策场景接口：`/api/decision/scenarios`，默认 dry-run 不写表；显式 `persist:true` 时仅写 `dispatch_scenarios` 场景记录，不修改 `shipment_facts`、订单、车辆或调度 assignments。
- 前端新增 API 封装：`frontend/src/api/runtime.js`、`gis.js`、`agent.js`、`decision.js`；`DecisionConsoleView.vue` 已将 runtime/GIS 状态接入控制塔指标和 readiness gates，不在首屏调用外部 LLM。
- 验证：`backend .\.venv\Scripts\python.exe -m pytest tests\test_optional_capability_service.py tests\test_postgres_layered_preview_fallback.py tests\test_runtime_agent_gis_decision_routes.py -q` 通过，`19 passed`。
- 验证：`frontend npm run build` 通过；仍只有旧 glyphicons 字体路径、旧 CSS `*zoom` 和大 chunk 警告。
- 真实 HTTP 冒烟：停止旧 `run.py` 后端后，用 `backend\.venv\Scripts\python.exe run.py` 重启；`/api/ready` 返回 PostgreSQL + `shipment_facts=50000` 且 `registered_capabilities.missing=[]`；`/api/runtime/capabilities?solver_probe=0`、`/api/advanced-ml/status`、`/api/advanced-ml/predict/with-anomaly?days=7`、`/api/gis/provider-health`、`/api/data-analytics/carbon-footprint/calculate`、`/api/agent/tools/preview`、`/api/decision/scenarios` 均非 404。
- 运行态注意：Windows 进程列表里 Flask 监听 PID 可能显示 base Python 路径，但 `/api/runtime/capabilities` 会用 `sys.executable/sys.prefix` 判断是否来自项目 `backend\.venv`。

## 2026-07-04 - 食品供应链仓配优化案例 MVP 接入

- 按 OpenSpec/SDD 新增 `openspec/changes/integrate-food-supply-chain-case/`，记录食品供应链案例模块的 proposal、design、tasks 和能力 spec。
- 新增后端隔离表模型 `case_food_nodes`、`case_food_demands`、`case_food_resources`、`case_food_distance_matrix`、`case_food_scenarios`，不写入 `shipment_facts`、`orders`、`vehicles` 等生产事实表。
- PostGIS 落库补强：`apply_import(persist=true)` 在 PostgreSQL/PostGIS 运行态会尝试创建 `case_food_nodes.geom geometry(Point,4326)` 与 `ix_case_food_nodes_geom` GiST 索引；SQLite/非 PostGIS 测试运行态返回可解释 skipped/degraded，不影响 MVP 演示。
- 新增 `/api/cases/food-supply/*`：summary、import validate/apply、network、distance matrix、network design、dispatch、pareto、solver compare、scenarios、agent explain。
- Excel 适配器已能读取案例文件夹内 9 个工作簿，识别 5 个果园、3 个仓/中转场、B 端门店、B/C 端需求、始发机场/飞机、车辆和无人机；C 端消费者首期按日期和地区聚合，不逐点伪造真实导航路径。
- 新增 Vue 页面 `/cases/food-supply` 和左侧菜单“食品供应链案例”，包含案例总览、GIS 网络、数学模型、智能调度、方案对比、Agent 解释 6 个视图。
- 扩展 `backend/scripts/enterprise_smoke_harness.py`，纳入食品案例 summary、network、network-design、dispatch、solver-compare、scenario dry-run。
- 验证命令：
  - `openspec validate integrate-food-supply-chain-case --strict` 通过。
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_food_supply_case_service.py backend\tests\test_runtime_agent_gis_decision_routes.py -q` 通过，`13 passed`。
  - `cd frontend; npm run build` 通过；仅保留既有 glyphicons、旧 CSS `*zoom`、大 chunk 警告。
  - 临时 5056 app-factory HTTP harness 通过：`19 total`、`15 ok`、`4 auth_required`、`route_missing=0`、`failed=0`，食品案例 dispatch smoke 分配 8 单；临时服务已停止。
- 注意：`backend/run.py` 会加载 `backend/.env.local` 且 `override=True`，临时 PowerShell 设置的 `FLASK_PORT` 可能被覆盖回 5000；要做新代码 HTTP harness 时可用 app factory 直接起临时端口，避免撞到旧运行态。

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
