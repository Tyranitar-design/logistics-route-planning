# 地图 Provider 健康诊断说明（2026-06-19）

## 背景

地图视图曾经把“高德路线降级”“高德路况降级”“天气降级”混在同一个状态面板里展示，导致用户看到类似“不管怎么选都是高德地图降级服务”的体验。

本次修复后，路线、天气、路况、天地图会分别报告 provider 状态，不再用路况权限失败污染路线规划结果。

## 后端变化

- 新增 `backend/app/services/provider_key_resolver.py`，统一解析地图 key 变量名，不返回真实 key 值。
- 高德 key 兼容：
  - `AMAP_SERVICE_KEY`
  - `AMAP_KEY`
  - `GAODE_SERVICE_KEY`
  - `GAODE_MAP_KEY`
  - `GAODE_REST_KEY`
  - `GAODE_BACKEND_KEY`
  - `AMAP_WEB_KEY`
  - `GAODE_WEB_KEY`
- 天地图 key 兼容：
  - `TIANDITU_SERVER_KEY`
  - `TIANDITU_KEY`
  - `TIANDITU_API_KEY`
  - `TDT_SERVER_KEY`
  - `TDT_KEY`
  - `TIANDITU_BROWSER_KEY`
- 新增 `GET /api/amap/provider-health`：
  - 默认只返回 key 是否配置和来源变量名。
  - 加 `?probe=1` 时真实探测高德路线、天气、路况。
  - 不返回、不记录真实 key。
- `traffic_service.py` 改为复用统一高德请求链路，继承 IPv4 优先、重试、provider metadata。
- 天地图路线响应补充 `provider_status`、`degraded`、`fallback_reason`。

## 前端变化

- `MapView.vue` 增加高德链路诊断条。
- 路线结果只显示路线 provider 状态。
- 实时路况卡只显示路况 provider 状态。
- 天气卡显示天气 provider 状态。
- 天地图卡显示配置状态和 fallback reason。

## 真实冒烟结果

使用本机安全读取的 API key 文件做真实 provider 冒烟，未打印 key：

```json
{
  "amap_route": {
    "success": true,
    "provider_status": "ok",
    "degraded": false
  },
  "amap_weather": {
    "success": true,
    "provider_status": "ok",
    "degraded": false
  },
  "amap_traffic": {
    "success": false,
    "provider_status": "degraded",
    "degraded": true,
    "fallback_reason": "SERVICE_NOT_AVAILABLE"
  },
  "tianditu_route": {
    "success": true,
    "provider_status": "ok",
    "degraded": false
  }
}
```

结论：当前 key 对高德路线和天气有效，天地图路线有效；高德路况服务返回 `SERVICE_NOT_AVAILABLE`，更像是账号/应用未开通对应路况能力或该服务权限不可用，而不是路线规划失败。

## 验证

- `python -m py_compile backend\app\services\provider_key_resolver.py backend\app\services\amap_service.py backend\app\services\weather_service.py backend\app\services\traffic_service.py backend\app\services\tianditu_service.py backend\app\routes\amap.py backend\app\routes\tianditu_route.py`
- `python -m pytest backend\tests\test_amap_phase1_contract.py backend\tests\test_order_route_shipment_fact_compat.py backend\tests\test_route_distance_backfill_service.py backend\tests\test_node_route_coordinate_audit.py -q`
  - result: `13 passed`
- `npm run build`
  - result: passed with existing Vite font/chunk warnings.
