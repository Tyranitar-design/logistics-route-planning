# 真实节点路线序列 Benchmark（2026-06-20）

## 背景

本地路径 benchmark 已经可以比较单个 OD 的 Dijkstra/A* 与高德/天地图 provider 路线。为了继续推进高级路径、Gurobi/OR-Tools/ALNS 对比和后续调度控制台，本次新增一个小规模路线序列 benchmark：

```text
POST /api/optimization/route-sequence-benchmark
GET  /api/optimization/route-sequence-benchmark-demo
```

它使用真实 `nodes/routes` 图构建距离矩阵，再比较多个求解器输出的节点访问顺序。该接口不是 50k 订单大规模调度入口，而是一个 bounded solver governance surface，用于验证真实网络数据、距离来源和求解器降级语义。

## 请求

```json
{
  "depot_id": 1,
  "node_ids": [2, 3, 4],
  "solvers": ["nearest_neighbor", "two_opt", "ortools", "gurobi"],
  "return_to_depot": true,
  "allow_haversine_fallback": true,
  "time_limit": 3
}
```

字段说明：

- `depot_id`：起终点仓/节点 ID。
- `node_ids`：需要访问的节点 ID 列表，自动去重并排除 depot。
- `solvers`：支持 `nearest_neighbor`、`two_opt`、`ortools`、`gurobi`。
- `return_to_depot`：是否闭环回仓，默认 `true`。
- `allow_haversine_fallback`：当本地 Route 图两点不可达时，是否用 Haversine 修正距离降级兜底，默认 `true`。
- `time_limit`：可选求解时间限制，主要用于 OR-Tools/Gurobi。

节点数量上限当前为 9 个，避免把此 benchmark 误用为大规模生产求解入口。

## 响应重点

顶层响应包含：

- `origin` / `waypoints`：真实节点信息。
- `distance_matrix` / `duration_matrix_minutes`：基于本地 Route 图和可选 Haversine 降级构建的矩阵。
- `matrix_truth`：矩阵来源审计：
  - `pair_count`
  - `route_graph_pair_count`
  - `haversine_fallback_pair_count`
  - `failed_pair_count`
  - `distance_source_counts`
  - `duration_source_counts`
  - `provider_status_counts`
  - `authenticity_level`
- `results`：每个求解器一行：
  - `solver`
  - `solver_family`
  - `solver_quality`
  - `node_sequence`
  - `node_labels`
  - `total_distance_km`
  - `total_duration_minutes`
  - `route_legs`
  - `route_truth`
  - `hard_constraint_violations`
- `rankings`：只对成功且可行的行排序。
- truth metadata：
  - `data_source`
  - `distance_source`
  - `path_source`
  - `provider_status`
  - `fallback_reason`
  - `authenticity_level`

## 求解器语义

- `nearest_neighbor`：可解释贪心基线。
- `two_opt`：在 nearest-neighbor 初始序列上做 2-opt 改进。
- `ortools`：可用时使用 OR-Tools RoutingModel；不可用时返回降级行，不使整个响应失败。
- `gurobi`：可用时使用小规模 TSP MILP；不可用时返回 `gurobi_tsp_milp` 降级行，不读取、不打印、不返回 license 内容。

硬约束：

- 起点必须是 depot。
- waypoint 必须各访问一次。
- 请求闭环时必须回 depot。
- 每一条 leg 必须有有限距离。

## 真实性边界

- 首选距离来源是 `routes` 图上的最短路径。
- 每条 leg 的底层 Route 边会聚合为 `route_truth`，保留 `route_ids`、距离来源、时长来源、provider 状态和降级原因。
- 当本地 Route 图不可达且启用 `allow_haversine_fallback` 时，leg 会标记 `distance_source=haversine_corrected`、`provider_status=degraded`，并保留 `HAVERSINE_FALLBACK_AFTER:*`。
- OR-Tools/Gurobi 的可用性是求解器能力，不改变矩阵真实性；求解器不可用只影响该 solver row。
- 该接口适合小规模真实网络求解器治理、前端展示和调度前置验证，不替代生产 dispatch wave 求解。

## Next 接入

`frontend-next` 已在以下页面请求该接口：

- `/map-view`
- `/route-compare`

新增组件：

```text
frontend-next/components/route-sequence-benchmark.tsx
```

页面显示：

- best solver
- route graph pairs / fallback pairs
- solver table
- best sequence
- route truth distance-source summary
- truth metadata

两个页面都支持通过 URL 传入途经点：

```text
/route-compare?origin_id=1&destination_id=3&waypoint_ids=2,5,8
/map-view?origin_id=1&destination_id=3&waypoint_ids=2,5,8
```

前端会把 `waypoint_ids` 和当前 `destination_id` 合并为 `node_ids` 传给 `/api/optimization/route-sequence-benchmark`，并自动去重、排除 depot、限制在小规模 benchmark 上限内。节点搜索、节点自动补全、Node Inventory 中的候选节点现在都提供“设为途经”操作。

## 验证

后端：

```powershell
cd C:\tmp\logistics-route-command-center-layout-dashboard-shell
python -m pytest backend\tests\test_solver_benchmark_service.py backend\tests\test_route_sequence_benchmark_service.py backend\tests\test_local_route_benchmark_service.py -q
```

结果：

```text
15 passed
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

- 继续把 waypoint 操作做成更完整的拖拽/排序体验，目前是 URL 参数和候选节点追加。
- 把 `route_truth` 复用到调度方案预览，显示每辆车路线的真实/估算距离占比。
- 增加 Gurobi/OR-Tools/ALNS 的同输入对比报告，并与 `dispatch_scenarios` 历史方案联动。
