import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getPredictionPageData } from "@/lib/api";
import { compactText, formatNumber, metricLine } from "@/lib/format";
import { truthFromResult } from "@/lib/truth";

export const dynamic = "force-dynamic";

const tasks = [
  { id: "demand", label: "需求量" },
  { id: "eta", label: "ETA" },
  { id: "delay", label: "延误" },
  { id: "cost", label: "成本" },
];

function readinessRows(readiness?: Record<string, { ready?: boolean; records?: number; status?: string }>) {
  return Object.entries(readiness || {}).map(([key, value]) => ({ key, ...value }));
}

export default async function AiPredictionPage() {
  const data = await getPredictionPageData();
  const health = data.predictionHealth.data;
  const baseline = data.predictionBaseline.data;
  const forecast = data.predictionForecast.data;
  const timeSeries = data.predictionTimeSeriesBenchmark.data;
  const capacityGap = data.predictionCapacityGapForecast.data;
  const costVolatility = data.predictionCostVolatilityForecast.data;
  const scorecard = data.predictionScorecard.data;
  const featureDataset = data.predictionFeatureDataset.data;
  const modelStatus = data.predictionModelStatus.data;
  const forecastTotal = (forecast?.forecast || []).reduce(
    (sum, item) => sum + Number(item.predicted_orders || 0),
    0,
  );

  return (
    <ConsoleShell
      activePath="/ai-prediction"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="AI 预测与训练数据"
      title="需求、时效、延误与成本预测"
    >
      <section className="metric-grid" aria-label="AI预测关键指标">
        <MetricCard label="AI Readiness" value={formatNumber(scorecard?.summary?.readiness_score, 1)} helper={scorecard?.summary?.status || "scorecard"} tone={(scorecard?.summary?.readiness_score || 0) >= 85 ? "good" : "warn"} />
        <MetricCard label="真实样本" value={formatNumber(health?.summary?.total_records)} helper="shipment_facts" tone="good" />
        <MetricCard label="可训练任务" value={formatNumber(baseline?.summary?.ready_tasks?.length)} helper={tasks.map((item) => item.id).join(" / ")} />
        <MetricCard label="14日预测订单" value={formatNumber(forecastTotal)} helper="weekday mean baseline" tone="good" />
        <MetricCard label="已训练模型" value={formatNumber(modelStatus?.model_count)} helper={modelStatus?.model_family || "lightweight ML"} />
        <MetricCard label="LSTM/TFT Readiness" value={timeSeries?.deep_learning_readiness?.ready ? "Ready" : "Shadow"} helper={`${formatNumber(timeSeries?.deep_learning_readiness?.training_windows)} windows`} tone={timeSeries?.deep_learning_readiness?.ready ? "good" : "warn"} />
        <MetricCard label="运力缺口天数" value={formatNumber(capacityGap?.summary?.shortage_days)} helper={`${formatNumber(capacityGap?.fleet_capacity?.available_vehicles)} vehicles`} tone={capacityGap?.summary?.shortage_days ? "warn" : "good"} />
        <MetricCard label="成本风险天数" value={formatNumber(costVolatility?.summary?.risk_days)} helper={`${formatNumber(costVolatility?.summary?.recent_volatility_cv, 3)} cv`} tone={costVolatility?.summary?.high_risk_days ? "warn" : "good"} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Prediction Readiness Scorecard" action={<DataState result={data.predictionScorecard} />}>
          <div className="summary-strip">
            <div>
              <span>Score</span>
              <strong>{formatNumber(scorecard?.summary?.readiness_score, 1)}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{scorecard?.summary?.status || "not_ready"}</strong>
            </div>
            <div>
              <span>Capacity Risk</span>
              <strong>{formatNumber(scorecard?.summary?.risk_summary?.capacity_shortage_days)}</strong>
            </div>
            <div>
              <span>Cost Risk</span>
              <strong>{formatNumber(scorecard?.summary?.risk_summary?.cost_risk_days)}</strong>
            </div>
          </div>
          <div className="solver-table" role="table" aria-label="AI预测readiness组件">
            <div className="solver-head metric-head" role="row">
              <span>component</span>
              <span>score</span>
              <span>status</span>
              <span>detail</span>
            </div>
            {(scorecard?.components || []).map((component) => (
              <div className="solver-row metric-row" role="row" key={component.id}>
                <span>{component.label || component.id || "component"}</span>
                <span>{formatNumber(component.score, 1)}</span>
                <StatusPill status={component.status || "unknown"} />
                <span>{compactText(component.details?.best_model as string | undefined, compactText(component.details?.avg_mape as string | number | undefined, "-"))}</span>
              </div>
            ))}
            {!scorecard?.components?.length ? (
              <p className="empty-note">{data.predictionScorecard.error || scorecard?.fallback_reason || "暂无预测评分卡。"}</p>
            ) : null}
          </div>
          <div className="data-list">
            {(scorecard?.gates || []).map((gate) => (
              <article className="data-row" key={gate.id}>
                <span>{gate.id || "gate"}</span>
                <strong>{gate.passed ? "passed" : "watch"}</strong>
                <p>{gate.detail || "readiness gate"}</p>
              </article>
            ))}
            {(scorecard?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>scorecard recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
          <p className="panel-note">
            {compactText(scorecard?.truth_contract?.deployment_boundary as string | undefined, "Scorecard 只用于 readiness 验收，模型保持 shadow，业务硬约束仍由求解器负责。")}
          </p>
          <TruthStrip truth={truthFromResult(data.predictionScorecard)} />
        </Panel>

        <Panel title="Dataset Readiness" action={<DataState result={data.predictionHealth} />}>
          <div className="readiness-grid">
            {readinessRows(health?.readiness).map((item) => (
              <article className="mini-metric" key={item.key}>
                <span>{item.key}</span>
                <strong>{formatNumber(item.records)}</strong>
                <StatusPill status={item.ready ? "ok" : "degraded"} label={item.status || (item.ready ? "ready" : "not ready")} />
              </article>
            ))}
          </div>
          {!health?.readiness ? <p className="empty-note">{data.predictionHealth.error || "等待预测健康接口返回。"}</p> : null}
          <TruthStrip truth={truthFromResult(data.predictionHealth)} />
        </Panel>

        <Panel title="Baseline Evaluation" action={<DataState result={data.predictionBaseline} />}>
          <div className="solver-table" role="table" aria-label="预测基线指标">
            <div className="solver-head metric-head" role="row">
              <span>task</span>
              <span>model</span>
              <span>metrics</span>
              <span>status</span>
            </div>
            {tasks.map((task) => {
              const item = baseline?.results?.[task.id];
              return (
                <div className="solver-row metric-row" role="row" key={task.id}>
                  <span>{task.label}</span>
                  <span>{item?.model || "not_ready"}</span>
                  <span>{metricLine(item?.metrics)}</span>
                  <StatusPill status={item?.provider_status || "unknown"} />
                </div>
              );
            })}
          </div>
          <TruthStrip truth={truthFromResult(data.predictionBaseline)} />
        </Panel>

        <Panel title="Demand Forecast" action={<DataState result={data.predictionForecast} />}>
          <div className="forecast-timeline">
            {(forecast?.forecast || []).slice(0, 14).map((item) => (
              <article className="timeline-row" key={item.date}>
                <span>{item.date || "-"}</span>
                <strong>{formatNumber(item.predicted_orders)} 单</strong>
              </article>
            ))}
            {!forecast?.forecast?.length ? <p className="empty-note">{data.predictionForecast.error || "暂无需求预测结果。"}</p> : null}
          </div>
          <div className="summary-strip">
            <div>
              <span>历史日点</span>
              <strong>{formatNumber(forecast?.feature_summary?.daily_points)}</strong>
            </div>
            <div>
              <span>训练日点</span>
              <strong>{formatNumber(forecast?.feature_summary?.training_points)}</strong>
            </div>
            <div>
              <span>日期范围</span>
              <strong>{compactText(forecast?.feature_summary?.date_range?.start)} / {compactText(forecast?.feature_summary?.date_range?.end)}</strong>
            </div>
          </div>
        </Panel>

        <Panel title="Time-Series Benchmark" action={<DataState result={data.predictionTimeSeriesBenchmark} />}>
          <div className="summary-strip">
            <div>
              <span>Best Model</span>
              <strong>{timeSeries?.backtest?.best_model?.model_id || "not_ready"}</strong>
            </div>
            <div>
              <span>Daily Points</span>
              <strong>{formatNumber(timeSeries?.series_summary?.daily_points)}</strong>
            </div>
            <div>
              <span>Backtest</span>
              <strong>{formatNumber(timeSeries?.backtest?.train_points)} / {formatNumber(timeSeries?.backtest?.test_points)}</strong>
            </div>
            <div>
              <span>DL Windows</span>
              <strong>{formatNumber(timeSeries?.deep_learning_readiness?.training_windows)} / {formatNumber(timeSeries?.deep_learning_readiness?.minimum_training_windows)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Best MAE</span>
              <strong>{formatNumber(timeSeries?.backtest?.best_model?.metrics?.mae, 2)}</strong>
            </div>
            <div>
              <span>Best RMSE</span>
              <strong>{formatNumber(timeSeries?.backtest?.best_model?.metrics?.rmse, 2)}</strong>
            </div>
            <div>
              <span>Best MAPE</span>
              <strong>{formatNumber(timeSeries?.backtest?.best_model?.metrics?.mape, 2)}%</strong>
            </div>
            <div>
              <span>Readiness</span>
              <strong>{timeSeries?.deep_learning_readiness?.status || "not_ready"}</strong>
            </div>
          </div>
          <div className="solver-table" role="table" aria-label="时序模型回测对比">
            <div className="solver-head metric-head" role="row">
              <span>model</span>
              <span>MAE</span>
              <span>RMSE</span>
              <span>MAPE</span>
            </div>
            {(timeSeries?.backtest?.models || []).slice(0, 5).map((model) => (
              <div className="solver-row metric-row" role="row" key={model.model_id}>
                <span>{model.model_id || "model"}</span>
                <span>{formatNumber(model.metrics?.mae, 2)}</span>
                <span>{formatNumber(model.metrics?.rmse, 2)}</span>
                <span>{formatNumber(model.metrics?.mape, 2)}%</span>
              </div>
            ))}
            {!timeSeries?.backtest?.models?.length ? (
              <p className="empty-note">{data.predictionTimeSeriesBenchmark.error || timeSeries?.fallback_reason || "暂无时序模型对比结果。"}</p>
            ) : null}
          </div>
          <div className="data-list">
            <article className="data-row">
              <span>candidate models</span>
              <strong>{(timeSeries?.deep_learning_readiness?.candidate_models || ["LSTM", "TFT"]).join(" / ")}</strong>
              <p>{timeSeries?.deep_learning_readiness?.recommended_next_step || "先用经典时序回测作为深度学习 shadow 训练基线。"}</p>
            </article>
            <article className="data-row">
              <span>boundary</span>
              <strong>{compactText(timeSeries?.truth_contract?.business_mutation as string | undefined, "none")}</strong>
              <p>{timeSeries?.deep_learning_readiness?.deployment_boundary || "深度学习模型必须先在 shadow mode 中超过经典基线。"}</p>
            </article>
          </div>
          <TruthStrip truth={truthFromResult(data.predictionTimeSeriesBenchmark)} />
        </Panel>

        <Panel title="Capacity Gap Forecast" action={<DataState result={data.predictionCapacityGapForecast} />}>
          <div className="summary-strip">
            <div>
              <span>Shortage Days</span>
              <strong>{formatNumber(capacityGap?.summary?.shortage_days)}</strong>
            </div>
            <div>
              <span>Max Weight Gap</span>
              <strong>{formatNumber(capacityGap?.summary?.max_weight_gap_kg, 1)} kg</strong>
            </div>
            <div>
              <span>Fleet Weight</span>
              <strong>{formatNumber(capacityGap?.fleet_capacity?.total_capacity_weight_tons, 2)} t</strong>
            </div>
            <div>
              <span>Avg Util.</span>
              <strong>{capacityGap?.summary?.avg_weight_utilization !== undefined && capacityGap?.summary?.avg_weight_utilization !== null ? `${formatNumber(capacityGap.summary.avg_weight_utilization * 100, 1)}%` : "-"}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Capacity Source</span>
              <strong>{capacityGap?.fleet_capacity?.capacity_source || "vehicles.available"}</strong>
            </div>
            <div>
              <span>Weight Model</span>
              <strong>{capacityGap?.models?.weight?.model_id || "not_ready"}</strong>
            </div>
            <div>
              <span>Weight MAE</span>
              <strong>{formatNumber(capacityGap?.models?.weight?.metrics?.mae, 2)}</strong>
            </div>
            <div>
              <span>DL Windows</span>
              <strong>{formatNumber(capacityGap?.deep_learning_readiness?.training_windows)} / {formatNumber(capacityGap?.deep_learning_readiness?.minimum_training_windows)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(capacityGap?.forecast || []).slice(0, 6).map((row) => (
              <article className="data-row" key={row.date}>
                <span>{row.date || "date"} · {row.status || "covered"}</span>
                <strong>{formatNumber(row.predicted_weight_kg, 1)} kg / {formatNumber(row.capacity_weight_kg, 1)} kg</strong>
                <p>
                  gap {formatNumber(row.weight_gap_kg, 1)} kg · volume gap {formatNumber(row.volume_gap_m3, 2)} m3 · util{" "}
                  {row.weight_utilization !== undefined && row.weight_utilization !== null ? `${formatNumber(row.weight_utilization * 100, 1)}%` : "-"}
                </p>
              </article>
            ))}
            {(capacityGap?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>capacity recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!capacityGap?.forecast?.length ? (
              <p className="empty-note">{data.predictionCapacityGapForecast.error || capacityGap?.fallback_reason || "暂无运力缺口预测。"}</p>
            ) : null}
          </div>
          <p className="panel-note">
            {compactText(capacityGap?.truth_contract?.deployment_boundary as string | undefined, "运力缺口预测只用于 shadow planning，最终派车仍由调度求解器校验硬约束。")}
          </p>
          <TruthStrip truth={truthFromResult(data.predictionCapacityGapForecast)} />
        </Panel>

        <Panel title="Cost Volatility Forecast" action={<DataState result={data.predictionCostVolatilityForecast} />}>
          <div className="summary-strip">
            <div>
              <span>Risk Days</span>
              <strong>{formatNumber(costVolatility?.summary?.risk_days)}</strong>
            </div>
            <div>
              <span>High Risk</span>
              <strong>{formatNumber(costVolatility?.summary?.high_risk_days)}</strong>
            </div>
            <div>
              <span>Unit Cost Threshold</span>
              <strong>{formatNumber(costVolatility?.summary?.unit_cost_threshold, 4)} /kg</strong>
            </div>
            <div>
              <span>Recent CV</span>
              <strong>{formatNumber(costVolatility?.summary?.recent_volatility_cv, 4)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Unit Cost Model</span>
              <strong>{costVolatility?.models?.unit_cost_per_kg?.model_id || "not_ready"}</strong>
            </div>
            <div>
              <span>Unit MAE</span>
              <strong>{formatNumber(costVolatility?.models?.unit_cost_per_kg?.metrics?.mae, 4)}</strong>
            </div>
            <div>
              <span>Total Freight Model</span>
              <strong>{costVolatility?.models?.total_freight?.model_id || "not_ready"}</strong>
            </div>
            <div>
              <span>DL Windows</span>
              <strong>{formatNumber(costVolatility?.deep_learning_readiness?.training_windows)} / {formatNumber(costVolatility?.deep_learning_readiness?.minimum_training_windows)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(costVolatility?.forecast || []).slice(0, 6).map((row) => (
              <article className="data-row" key={row.date}>
                <span>{row.date || "date"} · {row.risk_level || "low"}</span>
                <strong>{formatNumber(row.predicted_unit_cost_per_kg, 4)} /kg · {formatNumber(row.predicted_avg_freight, 2)} avg</strong>
                <p>
                  risk {formatNumber(row.risk_score, 3)} · pressure{" "}
                  {row.unit_cost_pressure !== undefined && row.unit_cost_pressure !== null ? `${formatNumber(row.unit_cost_pressure, 2)}x` : "-"} · volatility{" "}
                  {row.expected_volatility_cv !== undefined && row.expected_volatility_cv !== null ? formatNumber(row.expected_volatility_cv, 4) : "-"}
                </p>
              </article>
            ))}
            {(costVolatility?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>cost recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!costVolatility?.forecast?.length ? (
              <p className="empty-note">{data.predictionCostVolatilityForecast.error || costVolatility?.fallback_reason || "暂无成本波动预测。"}</p>
            ) : null}
          </div>
          <p className="panel-note">
            {compactText(costVolatility?.truth_contract?.deployment_boundary as string | undefined, "成本波动预测只用于 shadow planning，不替代财务结算或调度控制器。")}
          </p>
          <TruthStrip truth={truthFromResult(data.predictionCostVolatilityForecast)} />
        </Panel>

        <Panel title="Feature Contract" action={<DataState result={data.predictionFeatureDataset} />}>
          <div className="summary-strip">
            <div>
              <span>数据集</span>
              <strong>{featureDataset?.dataset_name || "not_ready"}</strong>
            </div>
            <div>
              <span>扫描行</span>
              <strong>{formatNumber(featureDataset?.row_count)}</strong>
            </div>
            <div>
              <span>返回行</span>
              <strong>{formatNumber(featureDataset?.returned_rows)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(featureDataset?.rows || []).slice(0, 5).map((row, index) => (
              <article className="data-row" key={`${featureDataset?.task || "feature"}-${index}`}>
                <span>{compactText(row.order_id as string | number | undefined, `row-${index + 1}`)}</span>
                <strong>{compactText(row.origin_city as string | undefined)} → {compactText(row.destination_city as string | undefined)}</strong>
                <p>{compactText(row.target as string | number | undefined, "target not reported")}</p>
              </article>
            ))}
            {!featureDataset?.rows?.length ? <p className="empty-note">{data.predictionFeatureDataset.error || "暂无特征样本。"}</p> : null}
          </div>
          <TruthStrip truth={truthFromResult(data.predictionFeatureDataset)} />
        </Panel>

        <Panel title="Model Registry" action={<DataState result={data.predictionModelStatus} />}>
          <div className="model-grid">
            {(modelStatus?.models || []).slice(0, 6).map((model) => (
              <article className="model-card" key={model.model_id}>
                <span>{model.task || "task"}</span>
                <strong>{model.model_type || "model"}</strong>
                <p>{metricLine(model.metrics)}</p>
              </article>
            ))}
            {!modelStatus?.models?.length ? (
              <p className="empty-note">{modelStatus?.fallback_reason || data.predictionModelStatus.error || "当前进程暂无已训练模型，可先用基线评估做产品展示。"}</p>
            ) : null}
          </div>
          <TruthStrip truth={truthFromResult(data.predictionModelStatus)} />
        </Panel>
      </section>
    </ConsoleShell>
  );
}
