import Link from "next/link";
import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getDispatchScenarioPageData, type RedispatchSimulatorInput } from "@/lib/api";
import { compactText, formatNumber, percent } from "@/lib/format";
import type { DispatchRouteTruth, DispatchScenarioDetail, RemoteResult, TruthMetadata } from "@/lib/types";

export const dynamic = "force-dynamic";

type PageSearchParams = Record<string, string | string[] | undefined>;

function firstParam(params: PageSearchParams, key: string): string | undefined {
  const value = params[key];
  return Array.isArray(value) ? value[0] : value;
}

function numericParam(
  params: PageSearchParams,
  key: string,
  fallback: number,
  min: number,
  max: number,
): number {
  const parsed = Number(firstParam(params, key));
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function boolParam(params: PageSearchParams, key: string, fallback: boolean): boolean {
  const value = firstParam(params, key)?.trim().toLowerCase();
  if (!value) return fallback;
  return ["1", "true", "yes", "on"].includes(value);
}

function compactListParam(params: PageSearchParams, key: string): string | null {
  const value = firstParam(params, key)?.trim();
  if (!value) return null;
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 20)
    .join(",");
}

function parseRedispatchParams(params: PageSearchParams): RedispatchSimulatorInput {
  return {
    delayMinutes: numericParam(params, "delay_minutes", 45, 0, 1440),
    delayVehicleIds: compactListParam(params, "delay_vehicle_ids"),
    unavailableVehicleIds: compactListParam(params, "unavailable_vehicle_ids"),
    costMultiplier: numericParam(params, "cost_multiplier", 1.12, 0.1, 10),
    providerDegradation: boolParam(params, "provider_degradation", true),
    reliabilityDrop: numericParam(params, "reliability_drop", 0.25, 0, 0.9),
    priorityOrderRefs: compactListParam(params, "priority_order_refs"),
    topK: numericParam(params, "top_k", 10, 1, 50),
  };
}

function profileHref(scenarioId: string, params?: Record<string, unknown>) {
  const search = new URLSearchParams();
  const priorityRefs = Array.isArray(params?.priority_order_refs)
    ? params?.priority_order_refs.filter(Boolean).join(",")
    : params?.priority_order_refs;
  const delayVehicles = Array.isArray(params?.delay_vehicle_ids)
    ? params?.delay_vehicle_ids.filter(Boolean).join(",")
    : params?.delay_vehicle_ids;
  const unavailableVehicles = Array.isArray(params?.unavailable_vehicle_ids)
    ? params?.unavailable_vehicle_ids.filter(Boolean).join(",")
    : params?.unavailable_vehicle_ids;
  const entries: Array<[string, unknown]> = [
    ["delay_minutes", params?.delay_minutes],
    ["delay_vehicle_ids", delayVehicles],
    ["unavailable_vehicle_ids", unavailableVehicles],
    ["cost_multiplier", params?.cost_multiplier],
    ["provider_degradation", params?.provider_degradation],
    ["reliability_drop", params?.reliability_drop],
    ["priority_order_refs", priorityRefs],
    ["top_k", params?.top_k],
  ];
  for (const [key, value] of entries) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return `/dispatch/scenarios/${scenarioId}${query ? `?${query}` : ""}`;
}

function countSummary(counts: Record<string, number> | undefined, limit = 3) {
  const entries = Object.entries(counts || {})
    .filter(([, value]) => Number(value) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]));

  if (!entries.length) return "-";

  return entries
    .slice(0, limit)
    .map(([key, value]) => `${key}: ${formatNumber(value)}`)
    .join(" / ");
}

function signedNumber(value?: number | null, fractionDigits = 2) {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return `${value > 0 ? "+" : ""}${formatNumber(value, fractionDigits)}`;
}

function scenarioTruth(result: RemoteResult<DispatchScenarioDetail>): TruthMetadata {
  const scenario = result.data?.scenario;
  return {
    data_source: scenario?.data_source || "not_connected",
    distance_source: scenario?.distance_source,
    path_source: scenario?.summary?.route_truth?.path_source || "dispatch_assignment_sequence",
    provider_status: scenario?.provider_status || (result.ok ? "ok" : "degraded"),
    fallback_reason: scenario?.fallback_reason || result.error,
    authenticity_level: scenario?.authenticity_level,
  };
}

function routeTruthSummary(routeTruth?: DispatchRouteTruth) {
  return (
    <div className="summary-strip route-truth-strip">
      <div>
        <span>Legs</span>
        <strong>{formatNumber(routeTruth?.leg_count)}</strong>
      </div>
      <div>
        <span>Estimated</span>
        <strong>{formatNumber(routeTruth?.estimated_leg_count)}</strong>
      </div>
      <div>
        <span>Distance Source</span>
        <strong>{countSummary(routeTruth?.distance_source_counts)}</strong>
      </div>
      <div>
        <span>Provider Status</span>
        <strong>{countSummary(routeTruth?.provider_status_counts)}</strong>
      </div>
    </div>
  );
}

export default async function DispatchScenarioPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<PageSearchParams>;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;
  const scenarioId = Number(resolvedParams.id);
  const redispatchInput = parseRedispatchParams(resolvedSearchParams);
  const data = await getDispatchScenarioPageData(
    Number.isFinite(scenarioId) ? scenarioId : 0,
    redispatchInput,
  );
  const detail = data.scenarioDetail.data;
  const scenario = detail?.scenario;
  const summary = scenario?.summary;
  const routeTruth = summary?.route_truth;
  const assignments = scenario?.assignments || [];
  const learningDataset = data.dispatchLearningDataset.data;
  const policyScorer = data.dispatchPolicyScorer.data;
  const rewardModel = data.dispatchRewardModel.data;
  const redispatchSimulator = data.dispatchRedispatchSimulator.data;
  const redispatchProfiles = data.dispatchRedispatchProfiles.data;
  const redispatchScenarioGenerator = data.dispatchRedispatchScenarioGenerator.data;
  const rlShadowRunner = data.dispatchRlShadowRunner.data;
  const fittedQShadowModel = data.dispatchFittedQShadowModel.data;
  const shadowBenchmark = data.dispatchShadowBenchmark.data;
  const shadowBenchmarkSnapshot = data.dispatchShadowBenchmarkSnapshot.data;

  return (
    <ConsoleShell
      activePath="/dispatch"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="调度历史方案"
      title={scenario?.scenario_code || `Scenario ${resolvedParams.id}`}
    >
      <section className="metric-grid" aria-label="调度场景关键指标">
        <MetricCard label="已分配" value={formatNumber(summary?.assigned_orders || summary?.total_orders_assigned)} helper={scenario?.status || "scenario"} tone="good" />
        <MetricCard label="未分配" value={formatNumber(summary?.unassigned_orders || summary?.total_orders_unassigned)} helper={scenario?.solver || "solver"} tone={summary?.unassigned_orders ? "warn" : "good"} />
        <MetricCard label="Assignment" value={formatNumber(assignments.length)} helper={scenario?.data_source || "data source"} />
        <MetricCard label="总成本" value={formatNumber(summary?.total_cost, 1)} helper={`${formatNumber(summary?.total_distance_km || summary?.total_distance, 1)} km`} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Scenario Summary" action={<DataState result={data.scenarioDetail} />}>
          <div className="summary-strip">
            <div>
              <span>场景</span>
              <strong>{scenario?.name || scenario?.scenario_code || "-"}</strong>
            </div>
            <div>
              <span>状态</span>
              <strong>{scenario?.status || "-"}</strong>
            </div>
            <div>
              <span>创建时间</span>
              <strong>{scenario?.created_at ? new Date(scenario.created_at).toLocaleString("zh-CN") : "-"}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>求解器</span>
              <strong>{scenario?.solver || "-"}</strong>
            </div>
            <div>
              <span>总时长</span>
              <strong>{formatNumber(summary?.total_duration_min || summary?.total_duration, 1)} min</strong>
            </div>
            <div>
              <span>利用率</span>
              <strong>{percent(summary?.average_load_utilization)}</strong>
            </div>
            <div>
              <span>真实性</span>
              <strong>{scenario?.authenticity_level || "-"}</strong>
            </div>
          </div>
          <TruthStrip truth={scenarioTruth(data.scenarioDetail)} />
          <p className="panel-note">
            <Link href="/dispatch">返回智能调度</Link>
          </p>
        </Panel>

        <Panel title="Route Truth" action={<StatusPill status={scenario?.provider_status || "unknown"} />}>
          {routeTruthSummary(routeTruth)}
          <div className="data-list">
            <article className="data-row">
              <span>distance source</span>
              <strong>{countSummary(routeTruth?.distance_source_counts, 5)}</strong>
              <p>{routeTruth?.note || "场景详情保留 assignment sequence 层面的路径真实性摘要。"}</p>
            </article>
            <article className="data-row">
              <span>fallback reason</span>
              <strong>{countSummary(routeTruth?.fallback_reason_counts, 5)}</strong>
              <p>{scenario?.fallback_reason || "未报告场景级降级原因"}</p>
            </article>
          </div>
        </Panel>

        <Panel title="Assignments" action={<StatusPill status={assignments.length ? "ok" : "unknown"} label={`${formatNumber(assignments.length)} rows`} />}>
          <div className="data-list expanded-list">
            {assignments.slice(0, 20).map((assignment) => {
              const assignmentTruth = assignment.diagnostics?.route_truth;
              return (
                <article className="data-row" key={assignment.id || `${assignment.vehicle_id}-${assignment.sequence_index}`}>
                  <span>{assignment.order_number || assignment.order_ref || assignment.id}</span>
                  <strong>
                    {assignment.vehicle_plate || `vehicle-${assignment.vehicle_id}`} · seq {formatNumber(assignment.sequence_index)}
                  </strong>
                  <p>
                    {formatNumber((assignment.weight_kg || 0) / 1000, 2)} t · {formatNumber(assignment.distance_km, 1)} km · {assignment.order_source || "source unknown"}
                  </p>
                  {assignmentTruth ? routeTruthSummary(assignmentTruth) : null}
                </article>
              );
            })}
            {!assignments.length ? <p className="empty-note">{data.scenarioDetail.error || detail?.error || "暂无 assignment 明细。"}</p> : null}
          </div>
        </Panel>

        <Panel title="AI Shadow Context" action={<StatusPill status={scenario?.ai_shadow?.enabled ? "ok" : "unknown"} label={scenario?.ai_shadow?.mode || "shadow"} />}>
          <div className="summary-strip">
            <div>
              <span>Scope</span>
              <strong>{learningDataset?.filters?.scenario_ids?.join(",") || resolvedParams.id}</strong>
            </div>
            <div>
              <span>Risk</span>
              <strong>{formatNumber(scenario?.ai_shadow?.risk_score, 1)}</strong>
            </div>
            <div>
              <span>Dataset Rows</span>
              <strong>{formatNumber(learningDataset?.summary?.row_count)}</strong>
            </div>
            <div>
              <span>Reward</span>
              <strong>{formatNumber(learningDataset?.summary?.avg_reward_proxy, 2)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(scenario?.ai_shadow?.recommendations || []).slice(0, 4).map((item) => (
              <article className="data-row" key={item}>
                <span>recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!scenario?.ai_shadow?.recommendations?.length ? <p className="empty-note">当前场景未记录 AI shadow 建议。</p> : null}
          </div>
        </Panel>

        <Panel title="Policy & Reward Model" action={<DataState result={data.dispatchRewardModel} />}>
          <div className="summary-strip">
            <div>
              <span>Best Policy</span>
              <strong>{policyScorer?.best_policy?.name || "not_ready"}</strong>
            </div>
            <div>
              <span>Policy Delta</span>
              <strong>{signedNumber(policyScorer?.best_policy?.score_delta_vs_baseline, 2)}</strong>
            </div>
            <div>
              <span>Rank Acc.</span>
              <strong>{percent(rewardModel?.metrics?.rank_accuracy?.accuracy)}</strong>
            </div>
            <div>
              <span>Model Scope</span>
              <strong>{rewardModel?.filters?.scenario_ids?.join(",") || resolvedParams.id}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Test MAE</span>
              <strong>{formatNumber(rewardModel?.metrics?.test?.mae, 2)}</strong>
            </div>
            <div>
              <span>Test RMSE</span>
              <strong>{formatNumber(rewardModel?.metrics?.test?.rmse, 2)}</strong>
            </div>
            <div>
              <span>All R²</span>
              <strong>{formatNumber(rewardModel?.metrics?.all?.r2, 2)}</strong>
            </div>
            <div>
              <span>Features</span>
              <strong>{formatNumber(rewardModel?.readiness?.feature_count)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(rewardModel?.model?.feature_importance || []).slice(0, 4).map((feature) => (
              <article className="data-row" key={feature.feature}>
                <span>weight {signedNumber(feature.weight, 3)}</span>
                <strong>{compactText(feature.feature)}</strong>
                <p>abs {formatNumber(feature.abs_weight, 3)}</p>
              </article>
            ))}
            {!rewardModel?.model?.feature_importance?.length ? (
              <p className="empty-note">{data.dispatchRewardModel.error || rewardModel?.readiness?.reason || "暂无 reward model 结果。"}</p>
            ) : null}
          </div>
        </Panel>

        <Panel title="Shadow Benchmark Scorecard" action={<DataState result={data.dispatchShadowBenchmark} />}>
          <div className="summary-strip">
            <div>
              <span>Readiness</span>
              <strong>{percent(shadowBenchmark?.summary?.readiness_score)}</strong>
            </div>
            <div>
              <span>Components</span>
              <strong>
                {formatNumber(shadowBenchmark?.summary?.ready_component_count)} /{" "}
                {formatNumber(shadowBenchmark?.summary?.component_count)}
              </strong>
            </div>
            <div>
              <span>Gates</span>
              <strong>
                {formatNumber(shadowBenchmark?.summary?.passed_gate_count)} /{" "}
                {formatNumber(shadowBenchmark?.summary?.gate_count)}
              </strong>
            </div>
            <div>
              <span>Deployable</span>
              <strong>{String(shadowBenchmark?.summary?.deployable ?? false)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(shadowBenchmark?.components || []).slice(0, 6).map((component) => (
              <article className="data-row" key={component.component_id || component.name}>
                <span>{component.status || "status"} · {component.provider_status || "provider"}</span>
                <strong>
                  {component.name || component.component_id} · {component.ready ? "ready" : "needs work"}
                </strong>
                <p>{component.reason || countSummary(component.metrics as Record<string, number>, 3)}</p>
              </article>
            ))}
            {(shadowBenchmark?.gates || []).filter((gate) => !gate.passed).slice(0, 3).map((gate) => (
              <article className="data-row" key={gate.gate_id}>
                <span>gate failed</span>
                <strong>{gate.gate_id}</strong>
                <p>{gate.reason || "需要补充 shadow benchmark 证据。"}</p>
              </article>
            ))}
            {(shadowBenchmark?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>benchmark recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!shadowBenchmark?.components?.length ? (
              <p className="empty-note">
                {data.dispatchShadowBenchmark.error ||
                  shadowBenchmark?.fallback_reason ||
                  "暂无 shadow benchmark scorecard。"}
              </p>
            ) : null}
          </div>
          <TruthStrip
            truth={{
              data_source: shadowBenchmark?.data_source,
              distance_source: shadowBenchmark?.distance_source,
              path_source: shadowBenchmark?.path_source,
              provider_status: shadowBenchmark?.provider_status,
              fallback_reason: shadowBenchmark?.fallback_reason || "offline readiness scorecard; not deployable",
              authenticity_level: shadowBenchmark?.authenticity_level,
            }}
          />
        </Panel>

        <Panel title="Benchmark Snapshot" action={<DataState result={data.dispatchShadowBenchmarkSnapshot} />}>
          <div className="summary-strip">
            <div>
              <span>Snapshot</span>
              <strong>{shadowBenchmarkSnapshot?.snapshot?.snapshot_id || "not_ready"}</strong>
            </div>
            <div>
              <span>Storage</span>
              <strong>{shadowBenchmarkSnapshot?.snapshot?.storage || "not_persisted"}</strong>
            </div>
            <div>
              <span>Components</span>
              <strong>{formatNumber(shadowBenchmarkSnapshot?.snapshot?.component_count)}</strong>
            </div>
            <div>
              <span>Gates</span>
              <strong>{formatNumber(shadowBenchmarkSnapshot?.snapshot?.gate_count)}</strong>
            </div>
          </div>
          <div className="data-list">
            <article className="data-row">
              <span>content hash</span>
              <strong>{shadowBenchmarkSnapshot?.snapshot?.content_hash?.slice(0, 28) || "-"}</strong>
              <p>{shadowBenchmarkSnapshot?.snapshot?.hash_algorithm || "sha256"} · mutation {shadowBenchmarkSnapshot?.snapshot?.mutation || "none"}</p>
            </article>
            <article className="data-row">
              <span>replay request</span>
              <strong>{shadowBenchmarkSnapshot?.snapshot?.replay_request?.endpoint || "/api/dispatch/shadow-benchmark"}</strong>
              <p>
                method {shadowBenchmarkSnapshot?.snapshot?.replay_request?.method || "POST"} · created{" "}
                {shadowBenchmarkSnapshot?.snapshot?.created_at
                  ? new Date(shadowBenchmarkSnapshot.snapshot.created_at).toLocaleString("zh-CN")
                  : "-"}
              </p>
            </article>
            {!shadowBenchmarkSnapshot?.snapshot ? (
              <p className="empty-note">
                {data.dispatchShadowBenchmarkSnapshot.error ||
                  shadowBenchmarkSnapshot?.fallback_reason ||
                  "暂无 benchmark snapshot。"}
              </p>
            ) : null}
          </div>
          <TruthStrip
            truth={{
              data_source: shadowBenchmarkSnapshot?.data_source,
              distance_source: shadowBenchmarkSnapshot?.distance_source,
              path_source: shadowBenchmarkSnapshot?.path_source,
              provider_status: shadowBenchmarkSnapshot?.provider_status,
              fallback_reason: shadowBenchmarkSnapshot?.fallback_reason || "snapshot export only; not persisted",
              authenticity_level: shadowBenchmarkSnapshot?.authenticity_level,
            }}
          />
        </Panel>

        <Panel title="Historical Disruption Episodes" action={<DataState result={data.dispatchRedispatchScenarioGenerator} />}>
          <div className="summary-strip">
            <div>
              <span>Episodes</span>
              <strong>{formatNumber(redispatchScenarioGenerator?.summary?.generated_scenario_count)}</strong>
            </div>
            <div>
              <span>Anomalies</span>
              <strong>{formatNumber(redispatchScenarioGenerator?.summary?.anomaly_count)}</strong>
            </div>
            <div>
              <span>Avg Impacted</span>
              <strong>{formatNumber(redispatchScenarioGenerator?.summary?.avg_impacted_assignments, 1)}</strong>
            </div>
            <div>
              <span>Best Episode</span>
              <strong>{redispatchScenarioGenerator?.summary?.best_scenario_id || "not_ready"}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>By Type</span>
              <strong>{countSummary(redispatchScenarioGenerator?.summary?.anomaly_by_type, 4)}</strong>
            </div>
            <div>
              <span>Readiness</span>
              <strong>{redispatchScenarioGenerator?.readiness?.status || "unknown"}</strong>
            </div>
          </div>
          <div className="data-list">
            {(redispatchScenarioGenerator?.generated_scenarios || []).slice(0, 4).map((episode) => (
              <article className="data-row" key={episode.scenario_id || episode.name}>
                <span>
                  {episode.source || "historical disruption"} · {episode.confidence || "confidence"}
                </span>
                <strong>{episode.name || episode.scenario_id}</strong>
                <p>
                  impacted {formatNumber(episode.simulation_summary?.impacted_assignments)} · held{" "}
                  {formatNumber(episode.simulation_summary?.held_for_reassignment)} · best{" "}
                  {episode.best_policy?.name || "not_ready"} ·{" "}
                  <Link href={profileHref(resolvedParams.id, episode.params as Record<string, unknown>)}>Apply</Link>
                </p>
                <p>{episode.description || episode.training_use || "DQL/DQN shadow episode preset."}</p>
              </article>
            ))}
            {!redispatchScenarioGenerator?.generated_scenarios?.length ? (
              <p className="empty-note">
                {data.dispatchRedispatchScenarioGenerator.error ||
                  redispatchScenarioGenerator?.readiness?.reason ||
                  "暂无历史扰动 episode。"}
              </p>
            ) : null}
          </div>
        </Panel>

        <Panel title="RL Shadow Runner" action={<DataState result={data.dispatchRlShadowRunner} />}>
          <div className="summary-strip">
            <div>
              <span>Episodes</span>
              <strong>{formatNumber(rlShadowRunner?.summary?.episode_count)}</strong>
            </div>
            <div>
              <span>Actions</span>
              <strong>{formatNumber(rlShadowRunner?.summary?.action_count)}</strong>
            </div>
            <div>
              <span>Q States</span>
              <strong>{formatNumber(rlShadowRunner?.summary?.state_bucket_count)}</strong>
            </div>
            <div>
              <span>Deployable</span>
              <strong>{String(rlShadowRunner?.summary?.deployable ?? false)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Baseline</span>
              <strong>{formatNumber(rlShadowRunner?.summary?.avg_baseline_score, 2)}</strong>
            </div>
            <div>
              <span>Selected</span>
              <strong>{formatNumber(rlShadowRunner?.summary?.avg_selected_score, 2)}</strong>
            </div>
            <div>
              <span>Score Δ</span>
              <strong>{signedNumber(rlShadowRunner?.summary?.avg_score_delta_vs_baseline, 2)}</strong>
            </div>
            <div>
              <span>Actions</span>
              <strong>{countSummary(rlShadowRunner?.summary?.selected_action_counts, 4)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(rlShadowRunner?.q_table || []).slice(0, 4).map((row) => (
              <article className="data-row" key={row.state_bucket || row.best_action}>
                <span>state bucket</span>
                <strong>{row.state_bucket || "unknown"}</strong>
                <p>
                  best {row.best_action || "not_ready"} · Q {formatNumber(row.best_q_value, 2)}
                </p>
              </article>
            ))}
            {(rlShadowRunner?.episode_results || []).slice(0, 3).map((episode) => (
              <article className="data-row" key={episode.episode_id || episode.state_bucket}>
                <span>{episode.source || "episode"} · {episode.confidence || "confidence"}</span>
                <strong>{episode.episode_id || "episode"} · {episode.selected_policy_name || episode.selected_action}</strong>
                <p>
                  baseline {formatNumber(episode.baseline_score, 2)} · selected{" "}
                  {formatNumber(episode.selected_score, 2)} · Δ{" "}
                  {signedNumber(episode.score_delta_vs_baseline, 2)}
                </p>
              </article>
            ))}
            {!rlShadowRunner?.episode_results?.length ? (
              <p className="empty-note">
                {data.dispatchRlShadowRunner.error ||
                  rlShadowRunner?.readiness?.reason ||
                  "暂无 RL shadow 评估结果。"}
              </p>
            ) : null}
          </div>
          <TruthStrip
            truth={{
              data_source: rlShadowRunner?.data_source,
              distance_source: rlShadowRunner?.distance_source,
              path_source: rlShadowRunner?.path_source,
              provider_status: rlShadowRunner?.provider_status,
              fallback_reason: rlShadowRunner?.fallback_reason || "offline shadow only; not deployable",
              authenticity_level: rlShadowRunner?.authenticity_level,
            }}
          />
        </Panel>

        <Panel title="Fitted-Q Shadow Model" action={<DataState result={data.dispatchFittedQShadowModel} />}>
          <div className="summary-strip">
            <div>
              <span>Samples</span>
              <strong>{formatNumber(fittedQShadowModel?.summary?.sample_count)}</strong>
            </div>
            <div>
              <span>Episodes</span>
              <strong>{formatNumber(fittedQShadowModel?.summary?.episode_count)}</strong>
            </div>
            <div>
              <span>Actions</span>
              <strong>{formatNumber(fittedQShadowModel?.summary?.action_count)}</strong>
            </div>
            <div>
              <span>Deployable</span>
              <strong>{String(fittedQShadowModel?.summary?.deployable ?? false)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>All MAE</span>
              <strong>{formatNumber(fittedQShadowModel?.metrics?.all?.mae, 2)}</strong>
            </div>
            <div>
              <span>All RMSE</span>
              <strong>{formatNumber(fittedQShadowModel?.metrics?.all?.rmse, 2)}</strong>
            </div>
            <div>
              <span>All R²</span>
              <strong>{formatNumber(fittedQShadowModel?.metrics?.all?.r2, 2)}</strong>
            </div>
            <div>
              <span>Rank Acc.</span>
              <strong>{percent(fittedQShadowModel?.metrics?.rank_accuracy?.accuracy)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Predicted Q</span>
              <strong>{formatNumber(fittedQShadowModel?.summary?.avg_predicted_q, 2)}</strong>
            </div>
            <div>
              <span>Actual Q</span>
              <strong>{formatNumber(fittedQShadowModel?.summary?.avg_actual_q, 2)}</strong>
            </div>
            <div>
              <span>Predicted Actions</span>
              <strong>{countSummary(fittedQShadowModel?.summary?.best_predicted_action_counts, 4)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(fittedQShadowModel?.recommendations || []).slice(0, 4).map((item) => (
              <article className="data-row" key={item.episode_id || item.state_bucket}>
                <span>{item.state_bucket || "state"}</span>
                <strong>
                  {item.predicted_best_policy_name || item.predicted_best_action || "not_ready"} · Q{" "}
                  {formatNumber(item.predicted_best_q, 2)}
                </strong>
                <p>
                  actual {item.actual_best_action || "unknown"} · match{" "}
                  {String(item.matches_actual_best ?? false)}
                </p>
              </article>
            ))}
            {(fittedQShadowModel?.model?.feature_importance || []).slice(0, 4).map((feature) => (
              <article className="data-row" key={feature.feature}>
                <span>feature weight {signedNumber(feature.weight, 3)}</span>
                <strong>{compactText(feature.feature)}</strong>
                <p>abs {formatNumber(feature.abs_weight, 3)}</p>
              </article>
            ))}
            {!fittedQShadowModel?.recommendations?.length ? (
              <p className="empty-note">
                {data.dispatchFittedQShadowModel.error ||
                  fittedQShadowModel?.readiness?.reason ||
                  "暂无 fitted-Q shadow 模型结果。"}
              </p>
            ) : null}
          </div>
          <TruthStrip
            truth={{
              data_source: fittedQShadowModel?.data_source,
              distance_source: fittedQShadowModel?.distance_source,
              path_source: fittedQShadowModel?.path_source,
              provider_status: fittedQShadowModel?.provider_status,
              fallback_reason: fittedQShadowModel?.fallback_reason || "offline fitted-Q shadow only; not deployable",
              authenticity_level: fittedQShadowModel?.authenticity_level,
            }}
          />
        </Panel>

        <Panel title="Dynamic Re-dispatch Shadow" action={<DataState result={data.dispatchRedispatchSimulator} />}>
          <div className="data-list">
            {(redispatchProfiles?.profiles || []).slice(0, 3).map((profile) => (
              <article className="data-row" key={profile.profile_id || profile.name}>
                <span>{profile.source || "anomaly profile"} · {profile.confidence || "confidence"}</span>
                <strong>{profile.name || profile.profile_id}</strong>
                <p>
                  {profile.description || "由真实 anomaly signals 生成的 shadow 扰动参数。"}{" "}
                  <Link href={profileHref(resolvedParams.id, profile.params as Record<string, unknown>)}>Apply</Link>
                </p>
              </article>
            ))}
            {!redispatchProfiles?.profiles?.length ? (
              <p className="empty-note">{data.dispatchRedispatchProfiles.error || redispatchProfiles?.readiness?.reason || "暂无 anomaly-driven profiles。"}</p>
            ) : null}
          </div>
          <form className="route-filter-form" action={`/dispatch/scenarios/${resolvedParams.id}`}>
            <label>
              <span>Delay Min</span>
              <input
                inputMode="decimal"
                name="delay_minutes"
                type="text"
                defaultValue={String(redispatchInput.delayMinutes ?? 45)}
              />
            </label>
            <label>
              <span>Delay Vehicles</span>
              <input
                name="delay_vehicle_ids"
                type="text"
                defaultValue={redispatchInput.delayVehicleIds || ""}
              />
            </label>
            <label>
              <span>Unavailable Vehicles</span>
              <input
                name="unavailable_vehicle_ids"
                type="text"
                defaultValue={redispatchInput.unavailableVehicleIds || ""}
              />
            </label>
            <label>
              <span>Cost Multiplier</span>
              <input
                inputMode="decimal"
                name="cost_multiplier"
                type="text"
                defaultValue={String(redispatchInput.costMultiplier ?? 1.12)}
              />
            </label>
            <label>
              <span>Provider Degrade</span>
              <select name="provider_degradation" defaultValue={String(redispatchInput.providerDegradation ?? true)}>
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            </label>
            <label>
              <span>Priority Orders</span>
              <input
                name="priority_order_refs"
                type="text"
                defaultValue={redispatchInput.priorityOrderRefs || ""}
              />
            </label>
            <label>
              <span>Reliability Drop</span>
              <input
                inputMode="decimal"
                name="reliability_drop"
                type="text"
                defaultValue={String(redispatchInput.reliabilityDrop ?? 0.25)}
              />
            </label>
            <label>
              <span>Top K</span>
              <input
                inputMode="numeric"
                name="top_k"
                type="text"
                defaultValue={String(redispatchInput.topK ?? 10)}
              />
            </label>
            <button type="submit">Run Shadow</button>
          </form>
          <div className="summary-strip">
            <div>
              <span>Disruption</span>
              <strong>{redispatchSimulator?.disruption?.profile || "shadow"}</strong>
            </div>
            <div>
              <span>Impacted</span>
              <strong>{formatNumber(redispatchSimulator?.summary?.impacted_assignments)}</strong>
            </div>
            <div>
              <span>Held</span>
              <strong>{formatNumber(redispatchSimulator?.summary?.held_for_reassignment)}</strong>
            </div>
            <div>
              <span>Reward Δ</span>
              <strong>{signedNumber(redispatchSimulator?.summary?.avg_reward_delta, 2)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Best Shadow</span>
              <strong>{redispatchSimulator?.best_policy?.name || "not_ready"}</strong>
            </div>
            <div>
              <span>Score</span>
              <strong>{formatNumber(redispatchSimulator?.summary?.best_policy_score, 2)}</strong>
            </div>
            <div>
              <span>Delay</span>
              <strong>{formatNumber(redispatchSimulator?.disruption?.delay_minutes, 0)} min</strong>
            </div>
            <div>
              <span>Cost x</span>
              <strong>{formatNumber(redispatchSimulator?.disruption?.cost_multiplier, 2)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(redispatchSimulator?.impacts || []).slice(0, 5).map((impact) => (
              <article className="data-row" key={impact.assignment_id || `${impact.vehicle_id}-${impact.order_ref}`}>
                <span>{impact.recommended_action || "rerank_candidate"}</span>
                <strong>
                  {impact.order_ref || "order"} · {signedNumber(impact.reward_delta, 2)}
                </strong>
                <p>
                  vehicle {impact.vehicle_plate || impact.vehicle_id || "-"} · {(impact.impact_flags || []).join(", ") || "no flags"}
                </p>
              </article>
            ))}
            {(redispatchSimulator?.recommendations || []).slice(0, 3).map((item) => (
              <article className="data-row" key={item}>
                <span>shadow recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!redispatchSimulator?.impacts?.length ? (
              <p className="empty-note">{data.dispatchRedispatchSimulator.error || redispatchSimulator?.readiness?.reason || "暂无动态重调度模拟结果。"}</p>
            ) : null}
          </div>
        </Panel>

        <Panel title="Diagnostics" action={<StatusPill status={scenario?.diagnostics ? "ok" : "unknown"} />}>
          <div className="diagnostic-grid">
            <article>
              <span>订单数量</span>
              <strong>{formatNumber(Number(scenario?.diagnostics?.order_count))}</strong>
            </article>
            <article>
              <span>车辆数量</span>
              <strong>{formatNumber(Number(scenario?.diagnostics?.vehicle_count))}</strong>
            </article>
            <article>
              <span>缺坐标</span>
              <strong>{formatNumber(Number(scenario?.diagnostics?.missing_coordinate_orders))}</strong>
            </article>
            <article>
              <span>重量缺口</span>
              <strong>{formatNumber(Number(scenario?.diagnostics?.capacity_gap_weight_kg), 1)} kg</strong>
            </article>
          </div>
          <TruthStrip truth={scenarioTruth(data.scenarioDetail)} />
        </Panel>
      </section>
    </ConsoleShell>
  );
}
