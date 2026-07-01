# AI 异常检测真实数据 baseline（2026-06-20）

## 背景

项目已有 `/api/anomaly/*` 实时异常检测接口，但其中部分车辆位置、天气、仪表盘数据仍偏演示/模拟，并主要围绕旧 `orders` 表。

本阶段新增 `/api/ai-anomaly/*`，专门面向真实 PostgreSQL `shipment_facts`，用于 AI 预测、动态调度、网络设计和分析总览的异常数据底座。

## 新增后端能力

- 新增服务：
  - `backend/app/services/shipment_anomaly_service.py`
- 新增路由：
  - `GET /api/ai-anomaly/health`
  - `GET /api/ai-anomaly/dataset-health`
  - `GET|POST /api/ai-anomaly/detect`
  - `GET|POST /api/ai-anomaly/scorecard`
  - `GET|POST /api/ai-anomaly/readiness-scorecard`
  - `GET|POST /api/ai-anomaly/explain`
- 新增测试：
  - `backend/tests/test_shipment_anomaly_service.py`

该路由不依赖 scikit-learn。规则与稳健统计检测始终可用；如果运行环境安装了 scikit-learn，且请求包含 `ml` 任务并满足样本量要求，会额外启用 IsolationForest。否则响应会在 `diagnostics.ml_detector` 中明确说明降级原因。

## 检测任务

默认任务：

- `status`：异常状态或异常原因字段。
- `geo`：坐标缺失、坐标超出常见中国物流网络范围。
- `cost`：运费、单位重量运费异常。
- `eta`：实际运输时长异常、时间顺序异常。
- `delay`：ETA 延误阈值突破、延误分布异常。
- `od_volume`：OD/mode/cargo 组合货量异常。

可选任务：

- `node_congestion`：目的城市货量异常，用于节点拥堵/扩容候选。
- `ml`：可选 IsolationForest 多变量异常检测。

## 请求示例

```http
POST /api/ai-anomaly/detect
```

```json
{
  "tasks": ["status", "geo", "cost", "eta", "delay", "od_volume"],
  "limit": 50000,
  "anomaly_limit": 100,
  "z_threshold": 3.5,
  "min_group_size": 5,
  "delay_threshold_minutes": 120,
  "use_ml": true
}
```

## 响应重点字段

每条 anomaly 包含：

- `anomaly_type`
- `level`
- `score`
- `source`
- `fact_id`
- `shipment_id`
- `order_id`
- `origin_city`
- `destination_city`
- `method`
- `explanation`
- `evidence`
- `actions`
- `data_source`
- `distance_source`
- `path_source`
- `authenticity_level`

汇总字段：

- `summary.records_scanned`
- `summary.anomaly_count`
- `summary.anomaly_rate`
- `summary.by_type`
- `summary.by_level`
- `summary.top_od_lanes`
- `diagnostics.ml_detector`

## 异常检测 Readiness Scorecard

接口：

```http
POST /api/ai-anomaly/scorecard
```

兼容别名：

```http
POST /api/ai-anomaly/readiness-scorecard
```

示例 payload：

```json
{
  "tasks": ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion", "ml"],
  "limit": 50000,
  "anomaly_limit": 100,
  "use_ml": true
}
```

该接口把异常检测能力汇总为一个治理验收入口：

- `health`: 真实样本、费用样本、坐标准备、ETA/延误样本、规则/稳健统计/ML readiness。
- `detect`: 异常类型、异常等级、OD 聚合、ML detector 状态。
- `components[]`: 数据 readiness、信号覆盖、当前风险压力、解释合同、ML shadow readiness。
- `gates[]`: 真实数据、规则/稳健统计、解释字段、只读 shadow 边界。
- `recommendations[]`: 面向人工复核、异常治理任务、ML 离线对比和异常落库的下一步建议。
- `evidence`: scorecard 使用的健康检查和检测摘要快照。

边界：

- `truth_contract.business_mutation = none`
- `truth_contract.deployment_boundary = scorecard_readiness_only_anomaly_events_not_persisted`
- Scorecard 不训练模型、不写异常事件表、不改变订单、车辆或调度结果。
- 高风险分数用于治理优先级，不代表 AI 自动处置异常。

## 单票解释

```http
GET /api/ai-anomaly/explain?order_id=ORD-001
```

可按 `id`、`order_id` 或 `shipment_id` 查询。接口返回该真实运单事实行及匹配到的异常解释。

## 真实性合同

所有响应包含或继承：

- `data_source = shipment_fact`
- `distance_source = shipment_fact_coordinates_haversine_when_needed`
- `path_source = not_route_geometry_anomaly_features`
- `provider_status`
- `fallback_reason`
- `authenticity_level`
- `truth_contract`

异常检测中的距离只作为特征，不代表真实道路导航路径。

## 与旧接口边界

- `/api/anomaly/*`：保留现有实时告警/演示兼容能力。
- `/api/ai-anomaly/*`：面向真实 `shipment_facts` 的生产可信异常检测底座。

后续前端调度控制台、AI 预测面板、网络设计和分析总览应优先使用 `/api/ai-anomaly/*` 作为真实数据异常来源。

## 当前边界

- 规则 + 稳健统计是当前主链路。
- IsolationForest 是可选增强；没有 scikit-learn 时不阻塞接口。
- 暂不写回业务表，不创建持久异常事件表。
- Readiness scorecard 是异常治理验收入口，不代表异常事件已经落库或自动处置。
- 当前 `path_source` 明确为特征/聚合解释，不是导航 polyline。
- 后续可接入 LOF、Autoencoder、LSTM anomaly detection，并将已确认异常落库供 DQL/DQN shadow mode 训练。

## 验证

```powershell
python -m py_compile backend/app/services/shipment_anomaly_service.py backend/app/routes/ai_anomaly.py backend/app/__init__.py backend/tests/test_shipment_anomaly_service.py
python -m pytest backend/tests/test_shipment_anomaly_service.py -q
```

结果：

- `4 passed`
