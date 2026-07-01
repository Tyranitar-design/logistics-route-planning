# AGENTS.md - 物流路径规划项目协作指南

本文件用于帮助后续 agent 直接接手 `C:\tmp\logistics-route-command-center-layout-dashboard-shell`。进入项目后先把它当作“物流业务 + 真实 PostgreSQL 数据 + 调度优化 + 地图 provider + AI shadow + 多前端”的综合系统，而不是单一 Flask/Vue demo。

## 1. 读取顺序

开始任何修改前，按顺序阅读：

1. `.codex/memory/MEMORY.md`
2. `.codex/memory/WORKLOG.md`
3. `README.md`
4. `frontend-next/README.md`
5. 与当前任务相关的 `docs/*.md`
6. 目标源码和测试

如果任务涉及大改动，再看 `openspec/changes/` 中是否已有相关提案。

## 2. 当前项目事实

- 工作区：`C:\tmp\logistics-route-command-center-layout-dashboard-shell`
- 后端入口：`backend/run.py`
- Flask app factory：`backend/app/__init__.py`
- Vue 生产前端：`frontend/`，默认端口 `5173`
- Next 决策控制台：`frontend-next/`，默认端口 `5174`
- 小程序：`miniprogram/`
- 主数据库：PostgreSQL/PostGIS
- 真实物流事实表：`shipment_facts`
- 调度结果表：`dispatch_scenarios`、`dispatch_assignments`
- 当前核心部署默认不启动大数据容器，但大数据目录仍保留。

2026-07-01 观察时工作区非常脏，存在大量已修改和未跟踪文件。不要执行 `git reset --hard`、`git checkout --`、粗暴清理、或回滚别人改动。提交前精确 staged，不要默认 `git add .`。

## 3. 敏感信息纪律

严禁读取、打印、复制、提交：

- 腾讯云 SSH 密码/密钥文件
- 高德地图 key 文件
- 天地图 key 文件
- 本机 Gurobi license 文件
- `.env.production`
- 真实 JWT、cookie、token、数据库密码

如果需要配置状态，只读取 `.env.example`、文档或接口返回的安全状态字段。`/api/tianditu/keys` 只能用于 key 状态，不应暴露 key 值。

## 4. 技术栈

后端：

- Python 3.10+
- Flask 3
- SQLAlchemy / Flask-SQLAlchemy
- Flask-JWT-Extended
- Flask-SocketIO
- PostgreSQL/PostGIS
- Redis / Kafka 兼容
- PuLP、Gurobi 可选、小规模 solver benchmark

前端：

- `frontend/`: Vue 3、Vite、Element Plus、Pinia、ECharts、Leaflet、Three.js
- `frontend-next/`: Next.js App Router、React、TypeScript、Tailwind、Leaflet 可选瓦片

移动端：

- 微信小程序原生框架，司机端作业流。

## 5. 关键业务边界

真实数据：

- 用户明确要求使用 PostgreSQL 的 5 万条真实 `shipment_facts` 数据。
- 旧 `orders` 表只能作为兼容来源，不能让核心调度、预测、异常检测只读旧表。

调度：

- `/api/dispatch/health`、`/api/dispatch/waves`、`/api/dispatch/preview`、`/api/dispatch/apply`、`/api/dispatch/scenarios` 是当前统一调度 API。
- Next SSR 调 `/api/dispatch/preview` 时应传 `persist:false`，避免页面刷新写入场景。
- 确认执行才写入 `dispatch_scenarios` / `dispatch_assignments`。

AI/RL：

- DQL/DQN 仍为 shadow mode。
- 影子策略只做评分、重排、建议、离线数据准备。
- 容量、时间窗、订单唯一分配、车辆可用性、路径可行性等硬约束必须由 solver 层保证。

地图和路线真实性：

- 高德/天地图/缓存/PostGIS/本地图都必须返回或展示真实性元数据。
- `provider_status`、`fallback_reason`、`distance_source`、`path_source`、`authenticity_level` 不能丢。
- 本地路径算法输出的是节点/Route 图序列，不是道路 provider polyline。
- provider 失败可降级，但必须解释原因，不能把 Haversine 包装成真实道路导航。

Gurobi：

- 能力判断走 `gurobi_capability_service.py`。
- Gurobi 不可用要降级并说明 `fallback_reason`。
- 小规模 VRP/CFLP/车辆分配可以用 Gurobi；全量 5 万单不能直接送入精确 MILP。

## 6. 修改原则

- 先读现状，再改代码，再验证。
- 后端 route 层只做参数、鉴权、响应组装；复杂逻辑放 `backend/app/services/`。
- 前端复杂业务转换优先放 `frontend-next/lib/`、`frontend/src/api/` 或工具层，不堆进页面组件。
- 保持 truth metadata 合同；任何降级都要能被前端解释。
- 不做无关大重构，不格式化无关文件。
- 当前文件可能包含用户或上一轮 agent 的未提交改动，改前先看相关文件内容。

## 7. 推荐启动和验证

后端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\backend
python run.py
```

Vue 前端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run dev
```

Next 前端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend-next
npm run dev
```

常用验证：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
python -m pytest backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q
python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q
python -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_order_route_shipment_fact_compat.py -q
```

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend-next
npm run typecheck
npm run build
```

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend
npm run build
```

## 8. 重点文件地图

后端调度：

- `backend/app/routes/dispatch.py`
- `backend/app/services/dispatch_orchestration_service.py`
- `backend/app/services/dispatch_learning_dataset_service.py`

AI 预测/异常/分析：

- `backend/app/routes/ai_prediction.py`
- `backend/app/services/shipment_prediction_service.py`
- `backend/app/routes/ai_anomaly.py`
- `backend/app/services/shipment_anomaly_service.py`
- `backend/app/routes/analytics.py`
- `backend/app/services/shipment_cost_analytics_service.py`

地图和路径：

- `backend/app/routes/amap.py`
- `backend/app/services/amap_service.py`
- `backend/app/routes/tianditu_route.py`
- `backend/app/services/tianditu_service.py`
- `backend/app/services/local_route_benchmark_service.py`
- `backend/app/services/order_route_service.py`
- `backend/app/services/node_route_audit_service.py`
- `backend/app/services/route_distance_backfill_service.py`

Gurobi/求解器：

- `backend/app/routes/optimization.py`
- `backend/app/services/gurobi_capability_service.py`
- `backend/app/services/gurobi_assignment_service.py`
- `backend/app/services/gurobi_vrp_service.py`
- `backend/app/services/gurobi_network_design_service.py`
- `backend/app/services/solver_benchmark_service.py`
- `backend/app/services/route_sequence_benchmark_service.py`

Next 控制台：

- `frontend-next/app/page.tsx`
- `frontend-next/app/ai-prediction/page.tsx`
- `frontend-next/app/anomaly-detection/page.tsx`
- `frontend-next/app/dispatch/page.tsx`
- `frontend-next/app/dispatch/scenarios/[id]/page.tsx`
- `frontend-next/app/network-design/page.tsx`
- `frontend-next/app/map-view/page.tsx`
- `frontend-next/app/route-compare/page.tsx`
- `frontend-next/lib/api.ts`
- `frontend-next/lib/types.ts`

Vue 生产界面：

- `frontend/src/views/MapView.vue`
- `frontend/src/views/DispatchView.vue`
- `frontend/src/views/Orders.vue`
- `frontend/src/views/NetworkDesignView.vue`
- `frontend/src/views/OptimizationEngine.vue`

## 9. 已知接手风险

- provider 接口常因未登录、未配置服务端 token、DNS、第三方 key 或网络失败显示 degraded。
- 高德/天地图降级时先看 provider health、key resolver、DNS、网络和 fallback reason。
- 订单路线推荐历史 bug 是 `/api/orders/<id>/recommend-route` 在旧 `orders` 不存在但 `shipment_facts` 存在时返回 400；已有 ShipmentFact 兼容测试，不要退化。
- `routes` 的距离来源可能混有 legacy、haversine_corrected、provider 距离，必须保留来源标记。
- Next 是迁移入口，不是已经完全替代 Vue 生产 UI。
- 大数据功能不是当前生产核心依赖，除非用户明确要求，不要把核心部署绑死在 Spark/Flink/ClickHouse 上。

## 10. 写回记忆

完成重要修复、验证、部署或架构决策后，至少更新：

- `.codex/memory/MEMORY.md`：稳定事实和接手提示
- `.codex/memory/WORKLOG.md`：时间线与验证结果

不要把密码、token、key、cookie 或 license 内容写入记忆。
