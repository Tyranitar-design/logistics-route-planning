# Next.js 前端迁移基座（2026-06-20）

## 背景

目标前端是 Next.js App Router + TypeScript + Tailwind CSS，但不能一次性推倒现有 Vue 生产界面。因此本阶段新增并行目录：

```text
frontend-next/
```

它是现代化决策控制台的迁移入口，不替换现有 `frontend/`。

## 新增能力

- 新增 Next.js App Router 工程壳：
  - `frontend-next/app/layout.tsx`
  - `frontend-next/app/page.tsx`
  - `frontend-next/app/globals.css`
- 新增 TypeScript API 合同：
  - `frontend-next/lib/types.ts`
  - `frontend-next/lib/api.ts`
- 新增基础组件：
  - `RefreshButton`
  - `StatusPill`
  - `TruthStrip`
  - `MetricCard`
  - `Panel`
  - `DataState`
- 新增配置：
  - `package.json`
  - `tsconfig.json`
  - `next.config.ts`
  - `postcss.config.mjs`
  - `.env.example`

## 首屏控制台

当前根页面是可用的决策控制台，不是营销落地页。它展示：

- 决策控制塔总评分
- 真实运单数量
- 异常信号数量
- 可调度订单
- 训练模型数量
- 运营评分
- Decision Control Tower
- AI Forecast
- Anomaly Watch
- Operations Scorecard
- Operations & Cost
- Dispatch Health
- Solver Benchmarks
- Provider Truth

`Decision Control Tower` 是 Next SSR 层的只读聚合，不是新的业务写入接口。它复用 AI prediction scorecard、anomaly scorecard、operations scorecard、dispatch health/shadow benchmark、Gurobi health 和 solver benchmark，生成统一的 0-100 控制塔评分、组件分、gate 和建议。该评分用于首页验收和运营 triage，不持久化、不调度、不结算。

## 独立模块页面

本轮已把根页面中的控制台壳抽成共享布局，并新增三个独立页面：

- `/`：分析总览，聚合 AI 预测、异常检测、调度健康、Gurobi 与求解器 benchmark。
- `/ai-prediction`：AI 预测页，展示 dataset readiness、需求预测、ETA 特征样本、baseline MAE/RMSE/MAPE、模型注册状态。
- `/anomaly-detection`：异常检测页，展示异常分布、Top 异常解释、规则/ML 检测器状态和真实性元数据。
- `/dispatch`：智能调度页首版迁移，展示调度健康、算法目录、波次候选、只读预览、未分配原因、诊断、AI Shadow、求解器对比、历史场景。
- `/network-design`：网络设计页首版迁移，展示真实 `shipment_facts` OD 聚合、候选仓网、CFLP 选址结果、需求分配、成本覆盖率、Gurobi 能力和 truth metadata。
- `/map-view`：地图视图首版迁移，展示高德路线/天气/路况 provider health、天地图 key/status、距离缓存健康、当前 OD 距离验证、地图运行台、provider polyline 预览、真实节点样本、订单路线推荐契约和混合地图来源边界。页面现已支持 `origin_id`、`destination_id`、`order_id`、`prefer_source`、`strategy`、`node_query`、`order_query`，并通过 `Map Selection Console` 提供 Node/Order ID 表单、SSR 搜索和客户端自动补全。
- `/route-compare`：高级路径对比页首版迁移，展示高德 provider health、天地图 key/status、高德/本地图算法对比、天地图/高德对比、订单路线推荐契约和混合路径来源边界。
- `/map-view` 与 `/route-compare` 已共用 `Local Algorithm Benchmark`：展示本地图算法相对当前真实路网候选的距离差、时长差、偏差率、路径节点数、provider geometry 点数和 truth metadata。该面板明确区分本地图节点序列与高德/天地图道路 polyline，避免把本地估算包装成真实道路结果。
- `/route-compare` 现在支持 query/form 驱动的起点、终点、订单 ID、推荐偏好和天地图策略切换；只填 `order_id` 时会优先从订单路线推荐结果里派生 OD，再跑 provider 对比。页面还新增 provider polyline 几何预览，会解析高德、天地图、推荐结果和可绘制本地路径坐标，并用图例和 truth metadata 标注来源。配置 `NEXT_PUBLIC_ROUTE_TILE_URL` 后会额外启用 Leaflet 瓦片底图；未配置时保留 SVG 坐标预览。
- `/route-compare` 已新增 `Selection Assist`：用 SSR 调 Flask `/api/nodes` 和 `/api/orders` 搜索真实节点/订单候选。订单搜索沿用后端 `shipment_facts` fallback，legacy `orders` 为空时仍能查真实运单。候选操作会更新 URL 的 `origin_id`、`destination_id` 或 `order_id`，不把 token 暴露给浏览器脚本。
- `/route-compare` 已新增客户端自动补全：浏览器只请求同源 Next BFF `/api/route-compare/suggestions`，BFF 在服务端读取 httpOnly cookie、转发 Flask `/api/nodes` / `/api/orders`、必要时 refresh-and-retry，并只返回清洗后的节点/订单字段。
- `/route-compare` 已新增 `Cache & Tile Diagnostics`：用 SSR 调 Flask `/api/amap/distance/cache/stats` 和 `/api/amap/distance/validate`，展示距离缓存条目、`amap` 精确距离数、`haversine_corrected` 数、过期数、当前 OD 的缓存命中前后状态、距离来源和瓦片层配置状态。页面不会展示后端缓存数据库路径。
- `/login`：Next 登录入口，代理 Flask `/api/auth/login`，将 access/refresh token 写入 httpOnly cookie，浏览器脚本不直接接触 token。

共享布局与工具：

- `frontend-next/components/console-shell.tsx`
- `frontend-next/lib/format.ts`
- `frontend-next/lib/truth.ts`

新增页面都使用同一套深色侧栏、白色工作面板、紧凑业务指标卡和 `TruthStrip`，保持与现有 command-center 风格一致。

## 接入的真实 API

- `/api/ai-prediction/health`
- `/api/ai-prediction/baseline/evaluate`
- `/api/ai-prediction/scorecard`
- `/api/ai-prediction/model/status`
- `/api/ai-prediction/demand/forecast`
- `/api/ai-prediction/features/dataset`
- `/api/ai-anomaly/health`
- `/api/ai-anomaly/detect`
- `/api/ai-anomaly/scorecard`
- `/api/analytics/operations-summary`
- `/api/analytics/operations-scorecard`
- `/api/dispatch/health`
- `/api/dispatch/shadow-benchmark`
- `/api/dispatch/algorithms`
- `/api/dispatch/waves`
- `/api/dispatch/preview`
- `/api/dispatch/scenarios`
- `/api/dispatch/compare-solvers`
- `/api/optimization/gurobi/health`
- `/api/optimization/gurobi/network-design-demo`
- `/api/optimization/gurobi/network-design`
- `/api/optimization/solver-benchmark-demo`
- `/api/amap/provider-health?probe=1`
- `/api/amap/distance/cache/stats`
- `/api/amap/distance/validate`
- `/api/amap/route/compare`
- `/api/amap/route/local-benchmark`
- `/api/tianditu/keys`
- `/api/tianditu/compare/amap`
- `/api/orders/recommend-route`
- `/api/orders/35692/recommend-route`
- `/api/nodes`
- `/api/orders`
- Next auth bridge：
  - `/api/auth/login`
  - `/api/auth/logout`
  - `/api/auth/refresh`
  - `/api/auth/session`
- Route compare BFF：
  - `/api/route-compare/suggestions`

所有请求通过 `safeApiFetch` 包装。后端未启动时页面会显示 degraded 状态，不会白屏。

`safeApiFetch` 已支持受保护 API 的服务器端鉴权转发，优先级为：

- 调用方显式传入的 `Authorization`
- 服务端环境变量 `NEXT_API_BEARER_TOKEN` / `NEXT_API_AUTH_TOKEN`
- 反向代理或浏览器请求传入的 `Authorization`
- cookie 中的 `access_token` / `jwt` / `token`

以上机制只转发 Bearer token，不在页面、日志或文档中展示真实值。真实 token 不能提交到仓库。

当 `safeApiFetch` 收到 `HTTP_401`，且认证来源不是调用方显式 `Authorization` 或服务端 `NEXT_API_BEARER_TOKEN` / `NEXT_API_AUTH_TOKEN` 时，会使用 httpOnly `refresh_token` cookie 调用 Flask `/api/auth/refresh`，并用新的 access token 重试原请求一次。浏览器脚本仍不会直接获得 token。普通 Server Component 渲染中 cookie 写入受 Next 运行上下文限制，因此刷新后的 cookie 持久化是 best-effort；但本次 SSR 请求仍可用刷新后的 token 完成重试。Next route handler 场景会通过响应 cookie 明确持久化。

`/login` 已提供第一版登录入口。登录成功后，Next route handler 会将 Flask 返回的 `access_token` / `refresh_token` 写入 httpOnly cookie；`/api/auth/refresh` 使用 refresh cookie 向 Flask 刷新 access cookie；`/api/auth/session` 会在 access token 缺失或过期时尝试 refresh-and-retry 一次；`/api/auth/logout` 清理 cookie。当前仍未实现完整角色权限、刷新失败后的自动跳转和注册/改密等管理流。

`/api/route-compare/suggestions` 是路径对比页和地图视图页共用的客户端自动补全 BFF。它接受 `kind=node|order` 和 `q`，空关键词返回空结果；非空关键词通过服务端 Bearer 转发到 Flask，并对 401 做一次 refresh-and-retry。返回内容会清洗字段，避免把 token、内部缓存路径或非必要上游字段暴露给浏览器脚本。未登录、上游 401 或上游不可用等业务降级返回 HTTP 200 + `success:false`，以便页面内展示友好提示并避免浏览器 console 出现资源加载红字；无效参数仍返回 400。

`/api/dispatch/preview` 现在支持请求体 `persist: false`。Next 调度页的服务器端预览使用该只读模式，避免页面刷新不断写入 `dispatch_scenarios` / `dispatch_assignments`。旧 Vue 页面未传该字段时仍保持原先默认预览落库行为，方便确认执行。

## 真实性展示

页面保留并展示：

- `data_source`
- `distance_source`
- `path_source`
- `provider_status`
- `fallback_reason`
- `authenticity_level`

这延续后端 Phase 1-3 的 truth metadata 合同。

## 当前边界

- 未替换现有 Vue 生产前端。
- 未引入 shadcn/ui 或 TanStack Query；当前先稳定工程目录、类型合同和 SSR 数据读取。已引入 Leaflet 作为高级路径对比页的可选瓦片底图层。
- 已完成本地 `npm install`、`npm run typecheck`、`npm run build` 和 Playwright 桌面/移动 smoke。
- 本阶段仅完成基础视觉 smoke，不等同于完整页面级设计验收。
- `frontend-next/node_modules/`、`.next/` 和 tsbuildinfo 为本地验证产物，不应提交。
- 调度相关接口当前受 JWT 保护；未登录、未配置服务端 token、refresh cookie 失效、或本地端口 5000 是旧后端时，Next 页面会显示 `HTTP_401` / `HTTP_404` 降级状态。后续正式切换前仍需要补角色权限、刷新失败跳转登录和更完整的 BFF 鉴权策略。
- 路径对比页当前同样调用受 JWT 保护的高德/天地图/订单推荐接口。未登录时页面会显示可解释降级状态；正式替换 Vue 地图页前，需要接入节点/订单选择控件、provider polyline 地图预览和交互式策略切换。
- 路径对比页已具备 SSR query/form 级别的节点/订单选择、客户端自动补全、真实节点/订单候选辅助面板、provider 策略切换、polyline 坐标几何预览、可选 Leaflet 瓦片底图和 provider/cache/tile 诊断，但仍未完成登录态真实 provider polyline smoke。
- 地图视图页已完成 provider-readiness 首版迁移：SSR 聚合 `/api/amap/provider-health?probe=1`、`/api/tianditu/keys`、`/api/amap/distance/cache/stats`、`/api/amap/distance/validate`、路线对比、节点库存和订单路线推荐。它已支持 query/form 选择和客户端自动补全，但仍是运行诊断和入口控制台，不是旧 Vue 地图所有交互的一次性替换；后续仍需补登录态真实 polyline 冒烟、浏览器安全瓦片配置和更深的本地路径算法对比指标。
- 本地路径算法对比现在优先使用后端 `/api/amap/route/local-benchmark`：该接口运行 Dijkstra/A* 多策略，Next 请求 `provider_sources=["amap","tianditu"]`，可同时拉取高德和天地图 provider 候选，计算 local-vs-provider 偏差，并返回 `provider_routes`、`provider_errors`、`route_segments`、`route_truth`、`data_source`、`distance_source`、`path_source`、`provider_status`、`fallback_reason`、`authenticity_level`。前端仍保留原有候选自算逻辑作为 endpoint 不可用时的降级解释层。
- 网络设计页当前是 bounded CFLP 决策面：`use_database=true` 从 `shipment_facts` 聚合少量目的地需求和起点候选，距离仍为 `haversine_corrected`。它是真实 OD 网络设计入口，不等同于全量 5 万单 + 真实道路距离的最终网络优化。

## 本轮验证

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend-next
npm run typecheck
npm run build
```

结果：

- `npm run typecheck`：通过。
- `npm run build`：通过，Next.js 16.2.9 生成动态路由 `/`、`/ai-prediction`、`/anomaly-detection`、`/dispatch`、`/network-design`、`/route-compare`、`/login` 和 `/api/auth/*`。

后端聚焦测试：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
python -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_dispatch_smart_contract.py -q
```

结果：

- `7 passed`
- 新增覆盖：`/api/dispatch/preview` 传 `persist: false` 时不会返回 `scenario_id` / `scenario_code`，即不会创建预览场景。

Playwright smoke：

- 桌面 1440x1000 打开 `/`、`/ai-prediction`、`/anomaly-detection`、`/dispatch`，页面标题为 `物流决策控制台`，主内容正常渲染。
- 移动 390x900 打开 `/dispatch`，侧栏收起，内容单列渲染。
- 后续追加 smoke：桌面 1440x1000 和移动 390x900 打开 `/network-design`，页面标题为 `物流决策控制台`，网络设计主内容正常渲染。
- 后续追加 smoke：桌面 1440x1000 和移动 390x900 打开 `/route-compare`，页面标题为 `物流决策控制台`，路径对比主内容正常渲染；本地后端不可达或未登录时受保护 provider API 显示 `fetch failed` / `HTTP_401` 降级状态。
- 后续追加 smoke：生产模式 `next start` 下 `/login`、`/api/auth/session`、`/dispatch` 返回 200；空请求 `POST /api/auth/login` 返回 400；`POST /api/auth/logout` 返回 200；桌面 1440x1000 和移动 390x900 打开 `/login`，页面标题为 `物流决策控制台`，登录表单正常渲染。
- 后续追加 smoke：实现 SSR `HTTP_401` refresh-and-retry 后，`npm run typecheck`、`npm run build` 通过；生产模式 `next start -- --hostname 127.0.0.1` 下 `/api/auth/session`、`/dispatch`、`/route-compare`、`POST /api/auth/logout` 均返回 200。
- 后续追加 smoke：`/route-compare?origin_id=1&destination_id=2&prefer_source=auto&strategy=0` 返回 200；`/route-compare?order_id=35692&prefer_source=auto` 返回 200，页面包含订单 ID 查询表单和值 `35692`。
- 后续追加 smoke：新增 `RoutePolylinePreview` 后，`npm run typecheck`、`npm run build` 通过；生产模式 `/route-compare?origin_id=1&destination_id=2&prefer_source=auto&strategy=0` 返回 200，页面包含 `Provider Polyline Preview` 和 `route-map-legend`。Playwright 全页截图检查通过，未登录/provider 不可达时显示空 polyline 降级态且布局无明显重叠；QA 截图已删除。
- 后续追加 smoke：新增 `Selection Assist` 后，`npm run typecheck`、`npm run build` 通过；生产模式 `/route-compare?node_query=广州&order_query=35692&prefer_source=auto&strategy=0` 返回 200，页面包含 `Selection Assist`、`节点候选`、`订单候选` 和 `Provider Polyline Preview`。未登录时候选列表显示 fetch-failed 降级空态；Playwright 全页截图检查通过，QA 截图已删除。
- 后续追加 smoke：新增 Leaflet 可选瓦片层后，`npm run typecheck`、`npm run build` 通过；生产模式 `/route-compare?node_query=广州&order_query=35692&prefer_source=auto&strategy=0` 返回 200，页面包含 Leaflet 预览区域、`NEXT_PUBLIC_ROUTE_TILE_URL` 未配置提示和 `Provider Polyline Preview`。Playwright 全页截图检查通过，QA 截图已删除。
- 后续追加 smoke：新增 `Cache & Tile Diagnostics` 后，`npm run typecheck`、`npm run build` 通过；Browser/IAB 生产模式打开 `/route-compare?node_query=广州&order_query=35692&prefer_source=auto&strategy=0`，页面标题为 `物流决策控制台`，DOM 包含 `Cache & Tile Diagnostics`、`cache hit`、`tile layer`，console error/warn 为 0；填写 `origin_id=1`、`destination_id=2` 并提交后 URL 更新为 `/route-compare?origin_id=1&destination_id=2...`，诊断面板仍正常渲染；移动 390x844 视口下诊断面板单列堆叠，无明显文字重叠或横向溢出。
- 后续追加 smoke：新增路径对比客户端自动补全和 `/api/route-compare/suggestions` BFF 后，`npm run typecheck`、`npm run build` 通过，生产 build 中出现动态路由 `/api/route-compare/suggestions`。Browser/IAB 生产模式打开 `/route-compare?node_query=广州&order_query=35692&prefer_source=auto&strategy=0`，页面标题为 `物流决策控制台`，DOM 包含 `节点自动补全`、`订单自动补全` 和 BFF 说明文案；输入 `广州` / `35692` 后未登录态显示 `登录后可搜索真实节点和订单`，页面 console error/warn 为 0。桌面和移动 390x844 均检查通过；曾发现右侧窄栏标题被挤压，已通过自适应网格和标题上下排列修复。
- 后续追加 smoke：新增 `/map-view` 后，`npm run typecheck`、`npm run build` 通过，生产 build 中出现动态路由 `/map-view`。HTTP/DOM 烟测 `http://127.0.0.1:5174/map-view` 返回 200，页面包含 `Map Provider Matrix`、`Distance Cache Readiness`、`Provider Polyline Preview` 和 `Truth Boundary`。Playwright 桌面 1440x1000 与移动 390x844 打开 `/map-view`，页面标题为 `物流决策控制台`，快照和全页截图生成成功，console warning/error 记录文件生成；未登录/provider 不可达时页面显示可解释 degraded 状态。
- 后续追加 smoke：`/map-view` 升级为 query/form 驱动后，`npm run typecheck`、`npm run build` 通过。HTTP/DOM 烟测 `/map-view?node_query=广州&order_query=35692&prefer_source=auto&strategy=0` 返回 200，页面包含 `Map Selection Console`、`节点自动补全`、`订单自动补全`、`查节点`、`查订单` 和 `送去高级路径对比`。HTTP/DOM 烟测 `/map-view?origin_id=1&destination_id=2&order_id=35692&prefer_source=auto&strategy=0` 返回 200，页面包含 `当前 OD 距离` 和 OD 状态。BFF 直接请求 `/api/route-compare/suggestions?kind=node&q=广州`、`/api/route-compare/suggestions?kind=order&q=35692` 在未登录态返回 200 和友好 auth-required payload。Playwright 桌面 1440x1000 与移动 390x844 打开带查询 `/map-view`，页面标题为 `物流决策控制台`，console error/warn 为 0。
- 后续追加 smoke：新增 `RouteAlgorithmBenchmark` 后，`npm run typecheck`、`npm run build` 通过。HTTP/DOM 烟测 `/map-view?node_query=广州&order_query=35692&prefer_source=auto&strategy=0` 返回 200，页面包含 `Local Algorithm Benchmark`、`distance delta`、`duration delta`、`本地算法` 和 `几何可视化`。HTTP/DOM 烟测 `/route-compare?origin_id=1&destination_id=2&prefer_source=auto&strategy=0` 返回 200，页面包含 `Local Algorithm Benchmark`、`distance delta`、`duration delta`、`候选状态` 和 `local_graph_sequence_vs_provider_polyline`。Playwright 桌面打开 `/map-view` 与 `/route-compare`，页面标题为 `物流决策控制台`，console error/warn 均为 0。
- 后续追加 smoke：新增后端 `/api/amap/route/local-benchmark` 后，`python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q` 通过（14 passed），`npm run typecheck` 和 `npm run build` 通过。`/map-view` 与 `/route-compare` 的 `Local Algorithm Benchmark` 面板现在优先显示后端 Dijkstra/A* 多策略结果、provider delta、closest-to-provider strategy 和 truth metadata。
- 后续追加 smoke：扩展 `/api/amap/route/local-benchmark` 支持 `provider_sources=["amap","tianditu"]` 后，`python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q` 通过（16 passed），`npm run typecheck` 和 `npm run build` 通过。Next `/map-view` 与 `/route-compare` 现在请求双 provider benchmark，面板显示 road-provider 表、每个本地策略相对高德/天地图的偏差，以及部分 provider 降级原因。
- 后续追加 smoke：扩展 `/api/amap/route/local-benchmark` 本地 Route 来源审计后，`python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q` 通过（17 passed），`npm run typecheck` 和 `npm run build` 通过。每个本地策略现在带 `route_segments` 和 `route_truth`，Next `Local Algorithm Benchmark` 面板显示本地路径段数、缺失段、`distance_source_counts`、`provider_status_counts` 和 Route ID 样本。

## 验证建议

```powershell
cd frontend-next
npm install
npm run typecheck
npm run build
npm run dev
```

默认访问：

```text
http://localhost:5174
```
