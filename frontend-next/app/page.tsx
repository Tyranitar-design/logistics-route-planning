import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getDecisionConsoleData } from "@/lib/api";
import { formatNumber, metricLine, percent } from "@/lib/format";
import { truthFromResult } from "@/lib/truth";
import type { DecisionConsoleData } from "@/lib/types";

export const dynamic = "force-dynamic";

interface ControlTowerComponent {
  id: string;
  label: string;
  score: number;
  status: string;
  detail: string;
}

interface ControlTowerGate {
  id: string;
  passed: boolean;
  detail: string;
}

function boundedScore(value: unknown, fallback = 0): number {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return fallback;
  return Math.max(0, Math.min(100, numberValue));
}

function averageScore(values: number[]): number {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function yesNo(value: boolean | undefined): string {
  return value ? "yes" : "no";
}

function buildDecisionControlTower(data: DecisionConsoleData) {
  const predictionScore = boundedScore(
    data.predictionScorecard.data?.summary?.readiness_score,
    ((data.predictionBaseline.data?.summary?.ready_tasks?.length || 0) / 4) * 100,
  );
  const anomalyScore = boundedScore(
    data.anomalyScorecard.data?.summary?.readiness_score,
    data.anomalyDetect.data?.summary ? 60 : 0,
  );
  const operationsScore = boundedScore(data.operationsScorecard.data?.summary?.readiness_score, 0);
  const dispatchScore = boundedScore(
    data.dispatchShadowBenchmark.data?.summary?.readiness_score,
    data.dispatchHealth.data?.dispatchable_orders ? 65 : data.dispatchHealth.ok ? 40 : 0,
  );
  const solverCount = Number(data.solverBenchmark.data?.summary?.solver_count || 0);
  const feasibleSolverCount = Number(data.solverBenchmark.data?.summary?.feasible_solver_count || 0);
  const solverRatioScore = solverCount ? (feasibleSolverCount / solverCount) * 100 : data.solverBenchmark.ok ? 45 : 0;
  const gurobiScore = data.gurobiHealth.data?.available ? 100 : data.gurobiHealth.ok ? 55 : 0;
  const solverScore = boundedScore(averageScore([solverRatioScore, gurobiScore]));

  const components: ControlTowerComponent[] = [
    {
      id: "ai_prediction",
      label: "AI Prediction",
      score: predictionScore,
      status: data.predictionScorecard.data?.summary?.status || (predictionScore >= 75 ? "ready" : "watch"),
      detail: `${data.predictionBaseline.data?.summary?.ready_tasks?.length || 0}/4 tasks · ${data.predictionScorecard.data?.model_family || "baseline"}`,
    },
    {
      id: "anomaly_governance",
      label: "Anomaly Governance",
      score: anomalyScore,
      status: data.anomalyScorecard.data?.summary?.status || (anomalyScore >= 75 ? "ready" : "watch"),
      detail: `${formatNumber(data.anomalyScorecard.data?.summary?.high_risk_count || 0)} high risk · ${formatNumber(data.anomalyDetect.data?.summary?.anomaly_count || 0)} signals`,
    },
    {
      id: "operations_cost",
      label: "Operations & Cost",
      score: operationsScore,
      status: data.operationsScorecard.data?.summary?.status || (operationsScore >= 75 ? "ready" : "watch"),
      detail: `${formatNumber(data.operationsSummary.data?.kpis?.total_freight, 0)} freight · ${percent(data.operationsSummary.data?.kpis?.on_time_rate)} on-time`,
    },
    {
      id: "dispatch_shadow",
      label: "Dispatch Shadow",
      score: dispatchScore,
      status: data.dispatchShadowBenchmark.data?.summary?.deployable ? "unsafe" : data.dispatchShadowBenchmark.data?.provider_status || "shadow",
      detail: `${formatNumber(data.dispatchHealth.data?.dispatchable_orders)} orders · deployable ${yesNo(data.dispatchShadowBenchmark.data?.summary?.deployable)}`,
    },
    {
      id: "solver_provider",
      label: "Solver & Provider",
      score: solverScore,
      status: data.gurobiHealth.data?.available ? "ok" : data.gurobiHealth.data?.provider_status || "degraded",
      detail: `${formatNumber(feasibleSolverCount)}/${formatNumber(solverCount)} feasible · Gurobi ${yesNo(data.gurobiHealth.data?.available)}`,
    },
  ];

  const score = boundedScore(averageScore(components.map((component) => component.score)));
  const gates: ControlTowerGate[] = [
    {
      id: "real_data_visible",
      passed: Boolean(data.predictionHealth.data?.summary?.total_records || data.operationsSummary.data?.summary?.records_scanned),
      detail: "shipment_facts evidence is visible to the console.",
    },
    {
      id: "scorecards_loaded",
      passed: Boolean(data.predictionScorecard.ok || data.anomalyScorecard.ok || data.operationsScorecard.ok),
      detail: "at least one module-level readiness scorecard is available.",
    },
    {
      id: "dispatch_readable",
      passed: Boolean(data.dispatchHealth.ok),
      detail: "dispatch health endpoint is readable through the current auth context.",
    },
    {
      id: "solver_benchmark_visible",
      passed: Boolean(data.solverBenchmark.ok || data.gurobiHealth.ok),
      detail: "solver benchmark or Gurobi provider health is visible.",
    },
    {
      id: "shadow_boundary_preserved",
      passed: data.dispatchShadowBenchmark.data?.summary?.deployable !== true,
      detail: "AI/RL dispatch output remains shadow/non-deployable on the console.",
    },
  ];

  const recommendations = [
    ...(components.some((component) => component.score < 70) ? ["优先处理低于 70 分的控制塔组件，避免只看单点绿色指标。"] : []),
    ...(!gates.every((gate) => gate.passed) ? ["存在未通过控制塔 gate，建议先补齐认证、后端服务或真实数据可见性。"] : []),
    "控制塔分数是只读 SSR 聚合，不写业务数据，也不替代调度求解器或财务结算。",
  ];

  return {
    score,
    status: score >= 85 ? "ready" : score >= 65 ? "watch" : "needs_work",
    components,
    gates,
    recommendations,
  };
}

export default async function Page() {
  const data = await getDecisionConsoleData();
  const controlTower = buildDecisionControlTower(data);
  const predictionHealth = data.predictionHealth.data;
  const predictionBaseline = data.predictionBaseline.data;
  const anomalyHealth = data.anomalyHealth.data;
  const anomalyDetect = data.anomalyDetect.data;
  const operationsSummary = data.operationsSummary.data;
  const operationsScorecard = data.operationsScorecard.data;
  const dispatchHealth = data.dispatchHealth.data;
  const gurobiHealth = data.gurobiHealth.data;
  const solverBenchmark = data.solverBenchmark.data;
  const totalRecords = predictionHealth?.summary?.total_records || anomalyHealth?.summary?.total_records;
  const anomalyCount = anomalyDetect?.summary?.anomaly_count;
  const dispatchableOrders = dispatchHealth?.dispatchable_orders;
  const modelCount = data.predictionModelStatus.data?.model_count;
  const totalFreight = operationsSummary?.kpis?.total_freight;

  return (
    <ConsoleShell
      activePath="/"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="真实数据驱动决策层"
      title="AI、异常、调度与求解器状态"
    >
      <section className="metric-grid" aria-label="关键指标">
        <MetricCard label="控制塔评分" value={formatNumber(controlTower.score, 1)} helper={controlTower.status} tone={controlTower.score >= 85 ? "good" : "warn"} />
        <MetricCard label="真实运单" value={formatNumber(totalRecords)} helper="shipment_facts" tone="good" />
        <MetricCard label="异常信号" value={formatNumber(anomalyCount)} helper={percent(anomalyDetect?.summary?.anomaly_rate)} tone={anomalyCount ? "warn" : "good"} />
        <MetricCard label="可调度订单" value={formatNumber(dispatchableOrders)} helper="dispatch health" />
        <MetricCard label="训练模型" value={formatNumber(modelCount)} helper="in-memory models" />
        <MetricCard label="真实运费" value={formatNumber(totalFreight, 0)} helper={`${formatNumber(operationsSummary?.kpis?.freight_per_kg, 2)} / kg`} tone="good" />
        <MetricCard label="运营评分" value={formatNumber(operationsScorecard?.summary?.readiness_score, 1)} helper={operationsScorecard?.summary?.status || "scorecard"} tone={(operationsScorecard?.summary?.readiness_score || 0) >= 85 ? "good" : "warn"} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Decision Control Tower" action={<StatusPill status={controlTower.status === "ready" ? "ok" : "degraded"} label={controlTower.status} />}>
          <div className="summary-strip">
            <div>
              <span>总评分</span>
              <strong>{formatNumber(controlTower.score, 1)}</strong>
            </div>
            <div>
              <span>AI</span>
              <strong>{formatNumber(controlTower.components.find((item) => item.id === "ai_prediction")?.score, 1)}</strong>
            </div>
            <div>
              <span>调度</span>
              <strong>{formatNumber(controlTower.components.find((item) => item.id === "dispatch_shadow")?.score, 1)}</strong>
            </div>
            <div>
              <span>求解器</span>
              <strong>{formatNumber(controlTower.components.find((item) => item.id === "solver_provider")?.score, 1)}</strong>
            </div>
          </div>
          <div className="solver-table" role="table" aria-label="决策控制塔组件">
            <div className="solver-head metric-head" role="row">
              <span>component</span>
              <span>score</span>
              <span>status</span>
              <span>detail</span>
            </div>
            {controlTower.components.map((component) => (
              <div className="solver-row metric-row" role="row" key={component.id}>
                <span>{component.label}</span>
                <span>{formatNumber(component.score, 1)}</span>
                <StatusPill status={component.status} />
                <span>{component.detail}</span>
              </div>
            ))}
          </div>
          <div className="data-list">
            {controlTower.gates.map((gate) => (
              <article className="data-row" key={gate.id}>
                <span>{gate.id}</span>
                <strong>{gate.passed ? "passed" : "watch"}</strong>
                <p>{gate.detail}</p>
              </article>
            ))}
            {controlTower.recommendations.map((item) => (
              <article className="data-row" key={item}>
                <span>control recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
          <p className="panel-note">该控制塔只聚合已验证接口的只读 readiness，不持久化、不调度、不结算。</p>
        </Panel>

        <Panel title="AI Forecast" action={<DataState result={data.predictionBaseline} />}>
          <div className="forecast-list">
            {["demand", "eta", "delay", "cost"].map((task) => {
              const item = predictionBaseline?.results?.[task];
              return (
                <article className="signal-row" key={task}>
                  <div>
                    <span>{task}</span>
                    <strong>{item?.model || "not_ready"}</strong>
                  </div>
                  <p>{metricLine(item?.metrics)}</p>
                  <StatusPill status={item?.provider_status || "unknown"} />
                </article>
              );
            })}
          </div>
          <TruthStrip truth={truthFromResult(data.predictionBaseline)} />
        </Panel>

        <Panel title="Anomaly Watch" action={<DataState result={data.anomalyDetect} />}>
          <div className="anomaly-summary">
            <strong>{formatNumber(anomalyDetect?.summary?.records_scanned)}</strong>
            <span>records scanned</span>
            <strong>{formatNumber(anomalyCount)}</strong>
            <span>signals</span>
          </div>
          <div className="anomaly-list">
            {(anomalyDetect?.anomalies || []).slice(0, 5).map((item) => (
              <article className="anomaly-row" key={item.anomaly_id}>
                <div>
                  <span>{item.anomaly_type || "unknown"}</span>
                  <strong>{item.origin_city || "-"} → {item.destination_city || "-"}</strong>
                  <p>{item.explanation || "No explanation reported."}</p>
                </div>
                <StatusPill status={item.level || "unknown"} label={item.level || "unknown"} />
              </article>
            ))}
            {!anomalyDetect?.anomalies?.length ? <p className="empty-note">暂无异常明细或后端未连接。</p> : null}
          </div>
        </Panel>

        <Panel title="Operations Scorecard" action={<DataState result={data.operationsScorecard} />}>
          <div className="summary-strip">
            <div>
              <span>评分</span>
              <strong>{formatNumber(operationsScorecard?.summary?.readiness_score, 1)}</strong>
            </div>
            <div>
              <span>状态</span>
              <strong>{operationsScorecard?.summary?.status || "not_ready"}</strong>
            </div>
            <div>
              <span>准时率</span>
              <strong>{percent(operationsScorecard?.summary?.on_time_rate)}</strong>
            </div>
            <div>
              <span>异常率</span>
              <strong>{percent(operationsScorecard?.summary?.exception_rate)}</strong>
            </div>
          </div>
          <div className="solver-table" role="table" aria-label="运营成本评分组件">
            <div className="solver-head metric-head" role="row">
              <span>component</span>
              <span>score</span>
              <span>status</span>
              <span>detail</span>
            </div>
            {(operationsScorecard?.components || []).map((component) => (
              <div className="solver-row metric-row" role="row" key={component.id}>
                <span>{component.label || component.id || "component"}</span>
                <span>{formatNumber(component.score, 1)}</span>
                <StatusPill status={component.status || "unknown"} />
                <span>{formatNumber(component.details?.freight_coverage as number | undefined, 3) || "-"}</span>
              </div>
            ))}
            {!operationsScorecard?.components?.length ? (
              <p className="empty-note">{data.operationsScorecard.error || operationsScorecard?.fallback_reason || "暂无运营评分卡。"}</p>
            ) : null}
          </div>
          <div className="data-list">
            {(operationsScorecard?.gates || []).slice(0, 4).map((gate) => (
              <article className="data-row" key={gate.id}>
                <span>{gate.id || "gate"}</span>
                <strong>{gate.passed ? "passed" : "watch"}</strong>
                <p>{gate.detail || "operations gate"}</p>
              </article>
            ))}
            {(operationsScorecard?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>operations recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
          <TruthStrip truth={truthFromResult(data.operationsScorecard)} />
        </Panel>

        <Panel title="Operations & Cost" action={<DataState result={data.operationsSummary} />}>
          <div className="summary-strip">
            <div>
              <span>运费总额</span>
              <strong>{formatNumber(operationsSummary?.kpis?.total_freight, 0)}</strong>
            </div>
            <div>
              <span>单均运费</span>
              <strong>{formatNumber(operationsSummary?.kpis?.avg_freight_per_paid_shipment, 2)}</strong>
            </div>
            <div>
              <span>准时率</span>
              <strong>{percent(operationsSummary?.kpis?.on_time_rate)}</strong>
            </div>
            <div>
              <span>完成率</span>
              <strong>{percent(operationsSummary?.kpis?.delivery_completion_rate)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>覆盖率</span>
              <strong>{percent(operationsSummary?.kpis?.freight_coverage)}</strong>
            </div>
            <div>
              <span>单位重量成本</span>
              <strong>{formatNumber(operationsSummary?.kpis?.freight_per_kg, 4)}</strong>
            </div>
            <div>
              <span>平均时效</span>
              <strong>{formatNumber(operationsSummary?.kpis?.avg_transit_hours, 2)} h</strong>
            </div>
            <div>
              <span>异常率</span>
              <strong>{percent(operationsSummary?.kpis?.exception_rate)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(operationsSummary?.top_lanes || []).slice(0, 4).map((lane) => (
              <article className="data-row" key={lane.lane}>
                <span>{lane.lane || "lane"}</span>
                <strong>{formatNumber(lane.total_freight, 0)} · {percent(lane.freight_share)}</strong>
                <p>
                  {formatNumber(lane.shipment_count)} 单 · {formatNumber(lane.freight_per_kg, 3)} / kg · 准时 {percent(lane.on_time_rate)}
                </p>
              </article>
            ))}
            {(operationsSummary?.recommendations || []).slice(0, 2).map((item) => (
              <article className="data-row" key={item}>
                <span>cost recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!operationsSummary?.top_lanes?.length ? (
              <p className="empty-note">{data.operationsSummary.error || operationsSummary?.fallback_reason || "暂无真实成本运营总览。"}</p>
            ) : null}
          </div>
          <TruthStrip truth={truthFromResult(data.operationsSummary)} />
        </Panel>

        <Panel title="Dispatch Health" action={<DataState result={data.dispatchHealth} />}>
          <div className="dispatch-layout">
            <div>
              <span>可用车辆</span>
              <strong>{formatNumber(dispatchHealth?.vehicle_source?.available_vehicles)}</strong>
            </div>
            <div>
              <span>总载重能力</span>
              <strong>{formatNumber(dispatchHealth?.vehicle_source?.total_capacity_weight_tons, 1)} t</strong>
            </div>
            <div>
              <span>数据源</span>
              <strong>{dispatchHealth?.data_source || "not_connected"}</strong>
            </div>
          </div>
          <p className="panel-note">{dispatchHealth?.message || data.dispatchHealth.error || "等待调度健康接口返回。"}</p>
          <TruthStrip truth={truthFromResult(data.dispatchHealth)} />
        </Panel>

        <Panel title="Solver Benchmarks" action={<DataState result={data.solverBenchmark} />}>
          <div className="solver-table" role="table" aria-label="求解器对比">
            <div className="solver-head" role="row">
              <span>solver</span>
              <span>distance</span>
              <span>objective</span>
              <span>status</span>
            </div>
            {(solverBenchmark?.rankings || []).slice(0, 5).map((row) => (
              <div className="solver-row" role="row" key={row.solver}>
                <span>{row.solver || "-"}</span>
                <span>{formatNumber(row.total_distance_km, 1)} km</span>
                <span>{formatNumber(row.objective, 1)}</span>
                <StatusPill status={row.provider_status || (row.success ? "ok" : "degraded")} />
              </div>
            ))}
            {!solverBenchmark?.rankings?.length ? <p className="empty-note">暂无 benchmark 行或后端未连接。</p> : null}
          </div>
        </Panel>

        <Panel title="Provider Truth" action={<DataState result={data.gurobiHealth} />}>
          <div className="truth-board">
            <TruthStrip truth={truthFromResult(data.predictionHealth)} />
            <TruthStrip truth={truthFromResult(data.anomalyHealth)} />
            <TruthStrip truth={truthFromResult(data.gurobiHealth)} />
          </div>
          <div className="provider-line">
            <span>Gurobi</span>
            <StatusPill status={gurobiHealth?.provider_status || (gurobiHealth?.available ? "ok" : "degraded")} />
            <strong>{gurobiHealth?.status || gurobiHealth?.fallback_reason || data.gurobiHealth.error || "not_reported"}</strong>
          </div>
        </Panel>
      </section>
    </ConsoleShell>
  );
}
