# Node/Route 坐标底座审查报告

日期：2026-06-19

## 结论摘要

本轮只读审查覆盖 `nodes`、`routes`、`shipment_facts` 三类核心数据。审查工具不修改数据库。

- `nodes`: 21 个 active 节点，坐标缺失/越界/经纬度反写/重复坐标均为 0。
- `shipment_facts`: 50000 条真实运单，起终点坐标缺失/越界均为 0。
- `routes`: 306 条 active 路线。首次审查发现 124 条 `distance` 为空；已用 Haversine 修正距离完成本地 PostgreSQL 回填并写入来源标记。
- 城市覆盖：真实运单包含 29 个起点城市和 29 个终点城市；当前 Node 网络仍缺 11 个城市节点覆盖。

## 审查命令

```powershell
python scripts\audit_node_route_coordinates.py --sample-limit 12
```

如需完整 JSON：

```powershell
python scripts\audit_node_route_coordinates.py --sample-limit 20 --json
```

## 关键发现

### 1. Node 坐标质量健康

当前 Node 坐标没有发现阻断级问题：

- `missing_coordinates=0`
- `invalid_coordinates=0`
- `zero_coordinates=0`
- `outside_china_bounds=0`
- `suspected_lng_lat_swapped=0`
- `duplicate_coordinates=0`

这说明“高德总降级”和“本地路径结果不可比”的首要嫌疑不在 Node 经纬度本身。

### 2. Route 距离字段缺口已完成第一轮回填

首次 Route 审查结果：

- `routes_total=306`
- `missing_distance=124`
- `dangling_node_reference=0`
- `endpoint_missing_coordinates=0`
- `nonpositive_distance=0`

样例：

- `1`: 哈尔滨 -> 成县
- `2`: 成县 -> 惠州
- `3`: 成县 -> 澳门特别行政区
- `10`: 齐齐哈尔 -> 成县
- `14`: 大冶 -> 乐清
- `26`: 兰州 -> 秀英区
- `31`: 呼和浩特 -> 澳门特别行政区
- `44`: 澳门特别行政区 -> 南宁

影响：

- 本地路径算法会对缺距离边使用 Haversine 修正距离兜底。
- 多条缺距离 Route 的 `duration=0.92` 小时，长距离线路会产生不可信速度/时长口径。
- 后续高德/天地图/本地算法对比必须显式标记 `distance_source`，否则会把估算边和真实路网边混在一起。

已执行第一轮回填：

```powershell
python scripts\backfill_route_distances.py --provider haversine --apply
```

回填结果：

- `candidate_routes=124`
- `updated=124`
- `skipped=0`
- `distance_source=haversine_corrected`
- `fallback_reason=ROUTE_DISTANCE_BACKFILL_HAVERSINE`

回填后重新审查：

- `missing_distance=0`
- `route_issue_count=0`
- `distance_source_summary.haversine_corrected=124`
- `distance_source_summary.route_table_legacy_non_json=182`

解释：

- 这 124 条已经具备本地算法可计算的距离和时长。
- 它们仍然不是高德/天地图真实路网距离，因此后续产品展示和算法对比必须保留 `haversine_corrected` 标记。
- 182 条历史路线已有距离，但 `route_data` 不是结构化 JSON，来源仍属于 legacy unknown，后续可逐步用高德/天地图重算并结构化标记。

### 3. ShipmentFact 坐标健康，但城市覆盖超过 Node 网络

真实运单审查结果：

- `shipment_fact_total=50000`
- `missing_any_coordinates=0`
- `outside_china_bounds=0`
- `origin_cities=29`
- `destination_cities=29`
- `origin_cities_without_nodes=11`
- `destination_cities_without_nodes=11`

未被当前 Node 网络覆盖的城市：

- 东莞市
- 临沂市
- 义乌市
- 南昌市
- 昆山市
- 昆明市
- 晋江市
- 武汉市
- 苏州市
- 贵阳市
- 长沙市

影响：

- 智能调度和订单路线推荐如果只依赖 Node 网络，会丢掉一部分真实运单城市。
- 订单管理中真实 `shipment_facts` 订单需要做城市/坐标到 Node 或虚拟节点的统一适配。

## 推荐修复顺序

1. 先补 124 条 Route 的距离和来源字段。
   - 已完成 Haversine x 1.3 第一轮回填，并写明 `distance_source=haversine_corrected`。
   - 后续优先用高德/天地图真实道路距离替换其中的估算距离。
   - 已同步修正 `duration`，避免长距离线路固定 0.92 小时。

2. 建立真实运单城市到运营节点的映射。
   - 对缺失的 11 个城市补运营节点或映射表。
   - 明确标记为运营网络补充，不伪装成原始真实节点。

3. 订单路线推荐适配 `shipment_facts`。
   - `/api/orders/:id/recommend-route` 应先查旧 `orders`，查不到再查 `ShipmentFact`。
   - 对 `ShipmentFact` 使用起终点坐标直接规划，或映射到最近/同城 Node 后走本地算法。

4. 本地路径算法增强。
   - 过滤或降权缺真实距离来源的边。
   - 返回 `distance_source`、`path_source`、`fallback_reason`。
   - 和高德/天地图结果在同一个响应里做可解释对比。

## 新增能力

- `GET /api/nodes/route-coordinate-audit`
- `scripts/audit_node_route_coordinates.py`
- `scripts/backfill_route_distances.py`
- `backend/app/services/node_route_audit_service.py`
- `backend/app/services/route_distance_backfill_service.py`

返回统一包含：

- `data_source`
- `distance_source`
- `path_source`
- `authenticity_level`
- `fallback_reason`
- `summary`
- `nodes`
- `routes`
- `shipment_facts`
- `recommendations`
