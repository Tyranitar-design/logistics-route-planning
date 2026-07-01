# 本地路径算法 Benchmark 接口（2026-06-20）

## 背景

此前 Next `/map-view` 和 `/route-compare` 的 `Local Algorithm Benchmark` 只是在前端读取已有 local/provider route candidates 后计算偏差。它能解释结果，但不是后端统一能力，也不能稳定复用于 Vue、小程序或后续调度/网络设计模块。

本次新增后端统一接口：

```text
POST /api/amap/route/local-benchmark
```

该接口仍挂在 AMap 蓝图下，是因为它当前以高德 provider 路线作为第一道路对照源；本地算法结果来自 `nodes/routes` 图结构。

## 请求

```json
{
  "origin_id": 1,
  "destination_id": 2,
  "include_provider": true,
  "strategy": "0",
  "provider_sources": ["amap", "tianditu"]
}
```

字段说明：

- `origin_id` / `destination_id`：必填，运营节点 ID。
- `include_provider`：是否拉取高德 provider 候选，默认 `true`。
- `provider_sources`：可选，支持 `amap`、`tianditu`。未传时默认只跑 `amap`，以保持旧调用兼容。
- `strategy`：provider 策略标记，目前用于响应元数据；现有 `multi_route` 仍使用高德多策略接口。

## 响应重点

响应包含：

- `origin` / `destination`：节点信息。
- `provider_route`：主 provider 候选；按 `provider_sources` 顺序选择第一个可用 provider，保持旧前端兼容。
- `provider_routes`：所有可用道路 provider 候选，目前可包含高德和天地图。
- `provider_errors`：不可用 provider 的降级原因，例如 `TIANDITU_KEY_MISSING`。
- `local_strategies`：本地多策略候选：
  - `dijkstra_distance`
  - `dijkstra_time`
  - `dijkstra_cost`
  - `dijkstra_comprehensive`
  - `astar_distance`
  - `astar_time`
  - `astar_cost`
- `comparison_to_provider`：每个本地候选相对主 provider 的距离/时长偏差。
- `comparison_to_providers`：每个本地候选分别相对高德/天地图的距离/时长偏差。
- `route_segments`：每个本地候选的实际 Route 边序列，包含 `route_id`、`distance_source`、`duration_source`、`provider_status` 和 `fallback_reason`。
- `route_truth`：每个本地候选的本地图距离来源汇总：
  - `segment_count`
  - `missing_segment_count`
  - `distance_source_counts`
  - `duration_source_counts`
  - `provider_status_counts`
  - `authenticity_level`
- `summary`：成功策略数、最佳距离/时长/成本策略、最接近 provider 的策略。
- `diagnostics`：节点数、活跃线路数、provider 错误、本地成功/失败计数。
- truth metadata：
  - `data_source`
  - `distance_source`
  - `path_source`
  - `provider_status`
  - `fallback_reason`
  - `authenticity_level`

## 真实性边界

- `local_strategies` 的 `distance_source=local_graph`，只代表本地图结构估算。
- `route_truth.distance_source_counts` 才表示本地图中每条 Route 边的底层距离来源，例如 `haversine_corrected`、`amap_driving_route` 或 `route_table_legacy_unknown`。
- `provider_route` 的 `distance_source=amap` 时才代表道路 provider 口径。
- provider 不可用时，接口仍返回本地策略和降级原因，不伪造真实道路距离。
- 当部分 provider 可用、部分 provider 失败时，顶层 `provider_status=degraded`，`fallback_reason` 以 `PARTIAL_PROVIDER_DEGRADATION` 开头，并在 `provider_errors` 中给出具体 provider 原因。
- 本地路径 `path` 是节点序列；provider `polyline` 是道路几何，两者只能对比，不能混成同一真实性等级。

## Next 接入

`frontend-next/lib/api.ts` 已在以下页面数据加载中请求该接口：

- `/map-view`
- `/route-compare`

`frontend-next/components/route-algorithm-benchmark.tsx` 现在优先展示后端 benchmark 的多策略结果、道路 provider 表和本地 `route_truth` 摘要；当接口不可用时，仍使用页面已有的 local/provider candidates 做前端降级对比。

## 验证

后端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_local_route_benchmark_service.py -q
```

结果：

```text
17 passed
```

前端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell\frontend-next
npm run typecheck
npm run build
```

结果：

```text
typecheck passed
build passed
```

## 下一步

- 增加 OR-Tools / ALNS / Gurobi 的小规模路径或 TSP/VRP 对照。
- 做登录态真实 provider polyline smoke，验证 `provider_route.polyline` 在 Leaflet/SVG 双模式下都能渲染。
- 增加 OR-Tools / ALNS / Gurobi 的小规模路径或 TSP/VRP 对照，并复用 `route_truth` 作为输入真实性解释。
