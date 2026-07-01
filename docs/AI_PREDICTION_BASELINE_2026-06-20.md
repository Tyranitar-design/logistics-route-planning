# AI 预测真实数据 baseline（2026-06-20）

## 背景

项目 Phase 3 的目标是把 AI 预测从演示型时序曲线升级到真实 `shipment_facts` 驱动。当前先落地可解释 baseline，确保每个预测目标都有真实数据集、回测指标和真实性元数据，再逐步接入 LightGBM / LSTM / TFT / DQL。

## 新增后端能力

- 新增服务：
  - `backend/app/services/shipment_prediction_service.py`
- 新增路由：
  - `GET /api/ai-prediction/health`
  - `GET /api/ai-prediction/dataset-health`
  - `POST /api/ai-prediction/baseline/evaluate`
  - `GET /api/ai-prediction/demand/forecast`
  - `GET|POST /api/ai-prediction/time-series/benchmark`
  - `GET|POST /api/ai-prediction/time-series-benchmark`
  - `GET|POST /api/ai-prediction/capacity-gap/forecast`
  - `GET|POST /api/ai-prediction/capacity-gap-forecast`
  - `GET|POST /api/ai-prediction/cost-volatility/forecast`
  - `GET|POST /api/ai-prediction/cost-volatility-forecast`
  - `GET|POST /api/ai-prediction/scorecard`
  - `GET|POST /api/ai-prediction/readiness-scorecard`
  - `GET /api/ai-prediction/dataset/preview`
  - `GET|POST /api/ai-prediction/features/dataset`
  - `GET|POST /api/ai-prediction/training-dataset`
  - `GET /api/ai-prediction/model/status`
  - `POST /api/ai-prediction/model/train`
  - `POST /api/ai-prediction/model/evaluate`
  - `POST /api/ai-prediction/model/predict`
- 新增测试：
  - `backend/tests/test_shipment_prediction_service.py`

该路由不依赖 PyTorch、Prophet、scikit-learn 等重依赖，因此即使 `DISABLE_ML_ROUTES=1`，`/api/ai-prediction/*` 仍会注册，用于轻量健康检查和真实数据 baseline 验证。

## 支持的预测目标

### 1. Demand

目标：按日订单量预测。

数据来源：

- `shipment_facts.shipped_at`
- 可选城市筛选：`origin_city_std` / `destination_city_std`

baseline：

- `weekday_mean_baseline`
- 使用历史同星期均值预测未来日订单量。

输出：

- `metrics.mae`
- `metrics.rmse`
- `metrics.mape`
- `forecast[]`
- `backtest[]`

### 2. ETA

目标：实际运输时长，单位小时。

数据来源：

- `shipment_facts.shipped_at`
- `shipment_facts.delivered_at` 或 `shipment_facts.signed_at`

baseline：

- `od_mode_median_eta_baseline`
- 优先使用 OD + transport mode + cargo type 分组中位数。
- 不足时退回 mode + cargo type，再退回全局中位数。

### 3. Delay

目标：相对 ETA 的延误分钟数。

数据来源：

- `shipment_facts.eta_at`
- `shipment_facts.delivered_at` 或 `shipment_facts.signed_at`

baseline：

- `od_mode_median_delay_baseline`

附加输出：

- `classification_summary.delay_threshold_minutes = 15`
- `actual_delay_rate`
- `predicted_delay_rate`

### 4. Cost

目标：运费金额。

数据来源：

- `shipment_facts.freight`
- `shipment_facts.weight_kg`
- OD / transport mode / cargo type

baseline：

- `od_mode_weight_unit_cost_baseline`
- 优先用同 OD/mode/cargo 的单位重量运费中位数估算。
- 不足时退回 mode/cargo 或全局单位重量运费。

## 请求示例

```http
POST /api/ai-prediction/baseline/evaluate
```

```json
{
  "tasks": ["demand", "eta", "delay", "cost"],
  "horizon_days": 7,
  "limit": 50000,
  "city": "上海"
}
```

```http
GET /api/ai-prediction/demand/forecast?days=7&city=上海
```

## 时间序列 Benchmark 与深度学习 readiness

接口：

```http
POST /api/ai-prediction/time-series/benchmark
```

兼容别名：

```http
POST /api/ai-prediction/time-series-benchmark
```

示例 payload：

```json
{
  "task": "demand",
  "horizon_days": 14,
  "test_days": 14,
  "sequence_length": 14,
  "limit": 50000,
  "city": "上海"
}
```

当前支持 `demand` / `eta` / `delay` / `cost` 的日粒度序列：

- `demand`: 每日订单量，缺失日期补 0。
- `eta`: 每日平均实际运输小时。
- `delay`: 每日平均到达延误分钟。
- `cost`: 每日平均运费金额。

Benchmark 比较的经典模型：

- `historical_mean`
- `weekday_mean`
- `moving_average_7`
- `seasonal_naive_7`
- `exponential_smoothing_alpha_0_35`

响应重点字段：

- `series_summary`: 日序列点数、日期范围、目标均值/最小/最大。
- `backtest.models[]`: 各模型 MAE/RMSE/MAPE 与样本回测行。
- `backtest.best_model`: 当前 holdout 下 MAE 最低的模型。
- `forecast[]`: 使用 best model 生成的未来序列预测。
- `deep_learning_readiness`: LSTM/GRU/TFT 的训练窗口数、最低窗口要求和 shadow-only 部署边界。
- `truth_contract.business_mutation = none`

该接口不训练 LSTM/TFT，也不引入 PyTorch 等重依赖。它先建立真实时序数据和模型对比口径；后续深度学习模型必须在 shadow backtest 中超过这些经典 baseline 后，才能进入半自动建议阶段。

## 运力缺口预测

接口：

```http
POST /api/ai-prediction/capacity-gap/forecast
```

兼容别名：

```http
POST /api/ai-prediction/capacity-gap-forecast
```

示例 payload：

```json
{
  "horizon_days": 14,
  "test_days": 14,
  "sequence_length": 14,
  "limit": 50000,
  "city": "上海",
  "include_all_vehicles": false
}
```

该接口把真实 `shipment_facts` 的每日发运重量、体积和单量序列，与 `vehicles` 表中可用车辆容量做对比：

- 需求来源：`shipment_facts.shipped_at`、`weight_kg`、`volume_m3`。
- 运力来源：默认只读取 `vehicles.status in ("available", "idle", "空闲")`。
- 载重容量：优先 `vehicles.load_capacity`，兼容旧字段 `vehicles.capacity`，单位按吨换算为 kg。
- 容积容量：优先 `vehicles.volume_capacity`，缺失时用载重吨数的保守估算兜底。
- 时序模型：分别对重量、体积、单量选择 MAE 最低的经典 baseline。

响应重点字段：

- `fleet_capacity`: 可用车辆数、总载重、总体积、车辆样本和容量来源。
- `models.weight/volume/shipments`: 各自最佳时序模型与回测指标。
- `forecast[]`: 每日预测重量/体积/单量、容量、缺口、利用率和 `covered` / `shortage` 状态。
- `summary.shortage_days`: 预测期内存在缺口的天数。
- `summary.max_weight_gap_kg` / `summary.max_volume_gap_m3`: 最大预测缺口。
- `recommendations[]`: 调车、外协、拆分波次等运营建议。
- `deep_learning_readiness`: LSTM/GRU/TFT 运力预测训练窗口 readiness。

边界：

- `truth_contract.business_mutation = none`
- `truth_contract.deployment_boundary = shadow_capacity_planning_only_solver_must_enforce_hard_constraints`
- 该接口只用于运力规划和调度前预警，不会写入 `shipment_facts`、`vehicles`、`dispatch_scenarios` 或 `dispatch_assignments`。
- 最终派车、容量、时间窗和订单唯一分配仍由 Gurobi / OR-Tools / ALNS / dispatch solver 层校验。

## 成本波动预测

接口：

```http
POST /api/ai-prediction/cost-volatility/forecast
```

兼容别名：

```http
POST /api/ai-prediction/cost-volatility-forecast
```

示例 payload：

```json
{
  "horizon_days": 14,
  "test_days": 14,
  "sequence_length": 14,
  "volatility_window": 7,
  "limit": 50000,
  "city": "上海"
}
```

该接口把真实 `shipment_facts` 运费数据整理为日粒度成本序列，并输出经营风险预警：

- 成本来源：`shipment_facts.freight`。
- 需求归一化：`weight_kg`、`volume_m3`。
- 日粒度指标：`total_freight`、`avg_freight`、`unit_cost_per_kg`、`unit_cost_per_m3`。
- 时序模型：分别对平均运费、单位重量成本、总运费选择 MAE 最低的经典 baseline。
- 波动率：基于单位重量成本的滚动 coefficient of variation。

响应重点字段：

- `summary.risk_days` / `summary.high_risk_days`: 预测期内中高风险和高风险天数。
- `summary.recent_volatility_cv`: 近期单位重量成本波动率。
- `summary.unit_cost_threshold`: 当前 unit-cost 风险阈值。
- `models.unit_cost_per_kg`: 单位重量成本最佳时序模型与回测指标。
- `forecast[]`: 每日预测平均运费、单位重量成本、总运费、压力倍数、风险分和风险等级。
- `recommendations[]`: 锁价、承运商报价复核、备选线路、调度成本权重建议。
- `deep_learning_readiness`: LSTM/GRU/TFT 成本预测训练窗口 readiness。

边界：

- `truth_contract.business_mutation = none`
- `truth_contract.deployment_boundary = shadow_cost_planning_only_not_financial_settlement_or_dispatch_controller`
- 该接口只用于成本预警和方案评分，不会写入 `shipment_facts`、财务结算表、调度方案或车辆状态。
- 后续 LightGBM / LSTM / TFT 成本模型应复用该 unit-cost 与 volatility 评估口径，避免不同模型指标不可比。

## AI 预测 Readiness Scorecard

接口：

```http
POST /api/ai-prediction/scorecard
```

兼容别名：

```http
POST /api/ai-prediction/readiness-scorecard
```

示例 payload：

```json
{
  "horizon_days": 14,
  "test_days": 14,
  "sequence_length": 14,
  "limit": 50000,
  "city": "上海"
}
```

该接口把 Phase 3 的分散预测能力汇总为一个验收入口：

- `dataset_health`: 真实数据样本与任务 readiness。
- `baseline_evaluate`: demand / ETA / delay / cost 的 MAE/RMSE/MAPE 覆盖。
- `time_series_benchmark`: demand 时序 benchmark 和 LSTM/TFT readiness。
- `capacity_gap_forecast`: 运力缺口和车辆容量风险。
- `cost_volatility_forecast`: 成本波动和单位成本风险。

响应重点字段：

- `summary.readiness_score`: 0-100 综合分。
- `summary.status`: `ready` / `watch` / `needs_work`。
- `components[]`: 数据 readiness、baseline 覆盖、时序 readiness、运力规划、成本波动五个组件分。
- `gates[]`: 真实数据、baseline 指标、shadow 边界、深度学习训练窗口等验收门。
- `recommendations[]`: 面向下一步工程推进的建议。
- `evidence`: scorecard 使用的关键证据快照，避免只有分数没有来源。

边界：

- `truth_contract.business_mutation = none`
- `truth_contract.deployment_boundary = scorecard_readiness_only_models_remain_shadow_until_validated`
- Scorecard 是验收和决策入口，不训练新模型、不写业务表、不替代 Gurobi / OR-Tools / ALNS 硬约束求解。

## 训练数据集接口

接口：

```http
POST /api/ai-prediction/features/dataset
```

兼容别名：

```http
POST /api/ai-prediction/training-dataset
```

示例 payload：

```json
{
  "task": "eta",
  "limit": 50000,
  "row_limit": 100
}
```

参数：

- `task`: `demand` / `eta` / `delay` / `cost`
- `limit`: 最多扫描多少条源 `shipment_facts`
- `row_limit`: 本次 API 最多返回多少行，当前服务端上限 `1000`
- `city`: 仅用于 demand，可筛选 origin/destination city

响应包含：

- `dataset_name`
- `target_definition`
- `feature_schema`
- `row_count`
- `returned_rows`
- `truncated`
- `rows`
- `summary`
- `truth_contract`

### Feature Schema 口径

`demand` 是日粒度数据集，主要字段：

- `date`
- `city_scope`
- `weekday`
- `is_weekend`
- `month`
- `day_of_month`
- `trailing_7d_avg_orders`
- `trailing_28d_avg_orders`
- `target = daily_order_count`

`eta` / `delay` / `cost` 是 shipment 粒度数据集，主要字段：

- `origin_city`
- `destination_city`
- `transport_mode`
- `cargo_type`
- `weight_kg`
- `volume_m3`
- `freight`
- `distance_km`
- `shipped_weekday`
- `shipped_hour`
- `feature_key`
- `fallback_key`
- `target`

这些字段是后续 LightGBM / LSTM / TFT / DQL 训练脚本的建议入口。新模型应优先复用该 target 和 feature contract，避免不同模型之间指标不可比。

## 轻量模型训练 API

当前已新增一个不依赖 scikit-learn / LightGBM / PyTorch 的训练层，用 `numpy` 实现 `ridge_feature_hashing_regressor_v1`：

- 数值特征做训练集标准化。
- 类别特征使用稳定哈希桶，避免 5 万真实运单的 OD/城市组合造成过高维度。
- 模型保存在当前后端进程内存中，不写业务库，不修改 `shipment_facts`。
- 目标是先稳定训练、评估、预测 API 合同，后续 LightGBM/XGBoost/LSTM/TFT 可以复用同一特征和指标口径。

### 训练

```http
POST /api/ai-prediction/model/train
```

```json
{
  "task": "eta",
  "limit": 50000,
  "test_ratio": 0.25,
  "hash_buckets": 24,
  "alpha": 1.0
}
```

响应重点字段：

- `model.model_id`
- `model.model_type = ridge_feature_hashing_regressor_v1`
- `model.metrics.mae/rmse/mape`
- `model.feature_importance`
- `model.training_summary`
- `training_contract.business_mutation = none`

### 状态

```http
GET /api/ai-prediction/model/status
```

返回当前进程内模型缓存、按任务聚合的最新模型、数据集 readiness 和训练合同。

### 评估

```http
POST /api/ai-prediction/model/evaluate
```

```json
{
  "task": "eta",
  "model_id": "optional",
  "limit": 50000,
  "row_limit": 20
}
```

评估当前真实特征行，返回整体指标与样本预测误差。

### 预测

```http
POST /api/ai-prediction/model/predict
```

```json
{
  "task": "eta",
  "model_id": "optional",
  "limit": 50000,
  "row_limit": 20
}
```

返回模型预测样本，并显式标记 `prediction.mutation = none`。

## 响应真实性字段

所有响应包含或继承：

- `data_source = shipment_fact`
- `provider_status`
- `fallback_reason`
- `authenticity_level`
- `truth_contract`

预测特征中的距离只用于模型特征，不作为真实道路路径：

- `distance_source = shipment_fact_coordinates_haversine_when_needed`
- `path_source = not_route_geometry_prediction_features`

## 当前边界

- 这是 Phase 3 baseline，不是最终深度学习模型。
- 当前轻量训练模型只保存在后端进程内存中；重启后需要重新训练。
- 时间序列 benchmark 是 classical baseline + LSTM/TFT readiness，不是已经上线的深度学习控制器。
- 运力缺口预测是 shadow capacity planning，不直接应用调度结果。
- 成本波动预测是 shadow cost planning，不替代财务结算或调度控制器。
- Readiness scorecard 是 shadow readiness 汇总入口，不代表 AI 模型已自动接管业务。
- 目前不训练持久化模型文件，不写回业务表。
- 训练数据集接口默认只返回部分 rows；用 `row_count` 和 `truncated` 判断是否需要离线脚本批量读取。
- MAPE 对 0 值分母做 1.0 裁剪，避免除零。
- 路径/距离只作为特征，不代表真实导航 polyline。
- 后续接入 LightGBM/LSTM/TFT 时应复用当前 dataset 和 metrics contract，而不是另起一套不可比较口径。

## 验证

```powershell
python -m py_compile backend/app/services/shipment_prediction_service.py backend/app/routes/ai_prediction.py backend/app/__init__.py backend/tests/test_shipment_prediction_service.py
python -m pytest backend/tests/test_shipment_prediction_service.py -q
cd frontend-next
npm run typecheck
npm run build
```

结果：

- `9 passed`
- Next typecheck: passed
- Next production build: passed
