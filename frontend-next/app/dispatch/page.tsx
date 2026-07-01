import Link from "next/link";
import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getDispatchPageData } from "@/lib/api";
import { compactText, formatNumber, percent } from "@/lib/format";
import { truthFromResult } from "@/lib/truth";

export const dynamic = "force-dynamic";

function diagnosticValue(diagnostics: Record<string, unknown> | undefined, key: string) {
  const value = diagnostics?.[key];
  return typeof value === "number" ? formatNumber(value, key.includes("weight") ? 1 : 0) : compactText(value as string | undefined);
}

function countSummary(counts: Record<string, number> | undefined, limit = 2) {
  const entries = Object.entries(counts || {})
    .filter(([, value]) => Number(value) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]));

  if (!entries.length) {
    return "-";
  }

  return entries
    .slice(0, limit)
    .map(([key, value]) => `${key}: ${formatNumber(value)}`)
    .join(" / ");
}

function signedNumber(value?: number | null, fractionDigits = 2) {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "-";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${formatNumber(value, fractionDigits)}`;
}

export default async function DispatchPage() {
  const data = await getDispatchPageData();
  const health = data.dispatchHealth.data;
  const algorithms = data.dispatchAlgorithms.data;
  const wave = data.dispatchWave.data?.wave;
  const preview = data.dispatchPreview.data;
  const scenarios = data.dispatchScenarios.data;
  const comparison = data.dispatchSolverComparison.data;
  const learningDataset = data.dispatchLearningDataset.data;
  const policyScorer = data.dispatchPolicyScorer.data;
  const rewardModel = data.dispatchRewardModel.data;
  const shadowBenchmark = data.dispatchShadowBenchmark.data;
  const shadowBenchmarkSnapshot = data.dispatchShadowBenchmarkSnapshot.data;
  const summary = preview?.summary;
  const diagnostics = preview?.diagnostics || wave?.diagnostics || health?.diagnostics;
  const assigned = summary?.total_orders_assigned || summary?.assigned_orders;
  const unassigned = summary?.total_orders_unassigned || summary?.unassigned_orders;

  return (
    <ConsoleShell
      activePath="/dispatch"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="智能调度控制台"
      title="波次、约束、求解器与 AI Shadow"
    >
      <section className="metric-grid" aria-label="智能调度关键指标">
        <MetricCard label="候选订单" value={formatNumber(wave?.candidate_orders || health?.dispatchable_orders)} helper={health?.data_source || "auto data source"} tone="good" />
        <MetricCard label="已分配" value={formatNumber(assigned)} helper={preview?.solver || "balanced preview"} />
        <MetricCard label="未分配" value={formatNumber(unassigned)} helper={data.dispatchPreview.error || "explainable reasons"} tone={unassigned ? "warn" : "good"} />
        <MetricCard label="可用车辆" value={formatNumber(wave?.available_vehicles || health?.vehicle_source?.available_vehicles)} helper={`${formatNumber(health?.vehicle_source?.total_capacity_weight_tons, 1)} t`} />
        <MetricCard label="Shadow Readiness" value={percent(shadowBenchmark?.summary?.readiness_score)} helper={`${formatNumber(shadowBenchmark?.summary?.ready_component_count)} / ${formatNumber(shadowBenchmark?.summary?.component_count)} components`} tone={shadowBenchmark?.summary?.deployable ? "good" : "warn"} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Dispatch Health" action={<DataState result={data.dispatchHealth} />}>
          <p className="panel-note">{health?.message || data.dispatchHealth.error || "等待调度健康接口返回。"}</p>
          <div className="summary-strip">
            <div>
              <span>订单源</span>
              <strong>{health?.data_source || "not_connected"}</strong>
            </div>
            <div>
              <span>可调度</span>
              <strong>{formatNumber(health?.dispatchable_orders)}</strong>
            </div>
            <div>
              <span>运力</span>
              <strong>{formatNumber(health?.vehicle_source?.available_vehicles)} 辆</strong>
            </div>
          </div>
          <TruthStrip truth={truthFromResult(data.dispatchHealth)} />
        </Panel>

        <Panel title="Algorithms" action={<DataState result={data.dispatchAlgorithms} />}>
          <div className="data-list">
            {(algorithms?.algorithms || []).map((item) => (
              <article className="data-row" key={item.id}>
                <span>{item.id || "algorithm"}</span>
                <strong>{item.name || "-"}</strong>
                <p>{item.description || item.best_for || "-"}</p>
              </article>
            ))}
            {!algorithms?.algorithms?.length ? <p className="empty-note">{data.dispatchAlgorithms.error || "调度算法接口暂不可用。"}</p> : null}
          </div>
        </Panel>

        <Panel title="Dispatch Wave" action={<DataState result={data.dispatchWave} />}>
          <div className="summary-strip">
            <div>
              <span>波次</span>
              <strong>{wave?.id || "not_created"}</strong>
            </div>
            <div>
              <span>重量</span>
              <strong>{formatNumber((wave?.total_weight_kg || 0) / 1000, 1)} t</strong>
            </div>
            <div>
              <span>体积</span>
              <strong>{formatNumber(wave?.total_volume_m3, 1)} m3</strong>
            </div>
          </div>
          <div className="data-list">
            {(wave?.orders || []).slice(0, 6).map((order) => (
              <article className="data-row" key={order.id || order.ref}>
                <span>{order.order_number || order.ref || order.id}</span>
                <strong>{compactText(order.origin_name || order.origin_city)} → {compactText(order.destination_name || order.destination_city)}</strong>
                <p>{formatNumber((order.weight_kg || 0) / 1000, 2)} t · {order.data_source || "shipment_fact"}</p>
              </article>
            ))}
            {!wave?.orders?.length ? <p className="empty-note">{data.dispatchWave.error || "当前无法生成波次，可能是未登录或后端保护接口返回 401。"}</p> : null}
          </div>
          <TruthStrip truth={truthFromResult(data.dispatchWave)} />
        </Panel>

        <Panel title="Preview Result" action={<DataState result={data.dispatchPreview} />}>
          <div className="summary-strip">
            <div>
              <span>求解器</span>
              <strong>{preview?.solver || preview?.requested_solver || "not_ready"}</strong>
            </div>
            <div>
              <span>总里程</span>
              <strong>{formatNumber(summary?.total_distance_km || summary?.total_distance, 1)} km</strong>
            </div>
            <div>
              <span>总成本</span>
              <strong>{formatNumber(summary?.total_cost, 1)} 元</strong>
            </div>
          </div>
          {summary?.route_truth ? (
            <div className="summary-strip route-truth-strip">
              <div>
                <span>Assignment Legs</span>
                <strong>{formatNumber(summary.route_truth.leg_count)}</strong>
              </div>
              <div>
                <span>Estimated Legs</span>
                <strong>{formatNumber(summary.route_truth.estimated_leg_count)}</strong>
              </div>
              <div>
                <span>Distance Source</span>
                <strong>{countSummary(summary.route_truth.distance_source_counts)}</strong>
              </div>
              <div>
                <span>Provider Status</span>
                <strong>{countSummary(summary.route_truth.provider_status_counts)}</strong>
              </div>
            </div>
          ) : null}
          <div className="plan-list-next">
            {(preview?.plans || []).slice(0, 5).map((plan) => {
              const routeTruth = plan.route_truth;
              return (
                <article className="plan-card-next" key={plan.vehicle_id}>
                  <div>
                    <span>{plan.vehicle_info?.plate_number || `vehicle-${plan.vehicle_id}`}</span>
                    <strong>{formatNumber(plan.orders?.length)} 单 · {percent(plan.load_utilization)}</strong>
                  </div>
                  <p>{formatNumber(plan.total_distance, 1)} km / {formatNumber(plan.total_duration, 1)} min / {formatNumber(plan.total_cost, 1)} 元</p>
                  {routeTruth ? (
                    <div className="summary-strip route-truth-strip">
                      <div>
                        <span>Legs</span>
                        <strong>{formatNumber(routeTruth.leg_count)}</strong>
                      </div>
                      <div>
                        <span>Est.</span>
                        <strong>{formatNumber(routeTruth.estimated_leg_count)}</strong>
                      </div>
                      <div>
                        <span>Source</span>
                        <strong>{countSummary(routeTruth.distance_source_counts)}</strong>
                      </div>
                      <div>
                        <span>Status</span>
                        <strong>{countSummary(routeTruth.provider_status_counts)}</strong>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
            {!preview?.plans?.length ? <p className="empty-note">{data.dispatchPreview.error || "暂无预览方案。"}</p> : null}
          </div>
          <TruthStrip truth={truthFromResult(data.dispatchPreview)} />
        </Panel>

        <Panel title="Unassigned Reasons" action={<StatusPill status={unassigned ? "degraded" : "ok"} label={`${formatNumber(unassigned)} orders`} />}>
          <div className="data-list">
            {(preview?.unassigned_orders || []).slice(0, 8).map((order) => (
              <article className="data-row" key={order.id || order.ref || order.order_number}>
                <span>{order.order_number || order.ref || order.id}</span>
                <strong>{order.reason_code || "unassigned"}</strong>
                <p>{order.reason || "未返回具体原因"}</p>
              </article>
            ))}
            {!preview?.unassigned_orders?.length ? <p className="empty-note">当前预览无未分配订单，或调度预览尚不可用。</p> : null}
          </div>
        </Panel>

        <Panel title="Diagnostics" action={<StatusPill status={diagnostics ? "ok" : "unknown"} />}>
          <div className="diagnostic-grid">
            <article>
              <span>订单数量</span>
              <strong>{diagnosticValue(diagnostics, "order_count")}</strong>
            </article>
            <article>
              <span>车辆数量</span>
              <strong>{diagnosticValue(diagnostics, "vehicle_count")}</strong>
            </article>
            <article>
              <span>缺坐标</span>
              <strong>{diagnosticValue(diagnostics, "missing_coordinate_orders")}</strong>
            </article>
            <article>
              <span>零重量</span>
              <strong>{diagnosticValue(diagnostics, "zero_weight_orders")}</strong>
            </article>
            <article>
              <span>重量缺口</span>
              <strong>{diagnosticValue(diagnostics, "capacity_gap_weight_kg")} kg</strong>
            </article>
          </div>
        </Panel>

        <Panel title="AI Shadow" action={<StatusPill status={preview?.ai_shadow?.enabled ? "ok" : "unknown"} label={preview?.ai_shadow?.mode || "shadow"} />}>
          <div className="summary-strip">
            <div>
              <span>风险分</span>
              <strong>{formatNumber(preview?.ai_shadow?.risk_score)}</strong>
            </div>
            <div>
              <span>ETA</span>
              <strong>{preview?.ai_shadow?.models?.eta_prediction || "planned"}</strong>
            </div>
            <div>
              <span>DQL</span>
              <strong>{preview?.ai_shadow?.models?.dql_policy || "shadow_only"}</strong>
            </div>
          </div>
          <div className="data-list">
            {(preview?.ai_shadow?.recommendations || []).map((item) => (
              <article className="data-row" key={item}>
                <span>recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!preview?.ai_shadow?.recommendations?.length ? <p className="empty-note">AI shadow 会在可解释调度预览成功后展示。</p> : null}
          </div>
        </Panel>

        <Panel title="Learning Dataset" action={<DataState result={data.dispatchLearningDataset} />}>
          <div className="summary-strip">
            <div>
              <span>Rows</span>
              <strong>{formatNumber(learningDataset?.summary?.row_count)}</strong>
            </div>
            <div>
              <span>Ready</span>
              <strong>{learningDataset?.readiness?.status || "not_ready"}</strong>
            </div>
            <div>
              <span>Reward</span>
              <strong>{formatNumber(learningDataset?.summary?.avg_reward_proxy, 2)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Truth Coverage</span>
              <strong>{percent(learningDataset?.summary?.route_truth_coverage)}</strong>
            </div>
            <div>
              <span>Scenarios</span>
              <strong>{formatNumber(learningDataset?.summary?.scenario_count)}</strong>
            </div>
            <div>
              <span>Distance Source</span>
              <strong>{countSummary(learningDataset?.summary?.distance_source_counts)}</strong>
            </div>
            <div>
              <span>Provider Status</span>
              <strong>{countSummary(learningDataset?.summary?.provider_status_counts)}</strong>
            </div>
          </div>
          <div className="data-list">
            {(learningDataset?.feature_schema || []).slice(0, 4).map((feature) => (
              <article className="data-row" key={feature.name}>
                <span>{feature.type || "feature"}</span>
                <strong>{feature.name || "-"}</strong>
                <p>{feature.description || "-"}</p>
              </article>
            ))}
            {!learningDataset?.feature_schema?.length ? (
              <p className="empty-note">{data.dispatchLearningDataset.error || learningDataset?.readiness?.reason || "暂无可用于 AI shadow 的调度训练数据。"}</p>
            ) : null}
          </div>
          <p className="panel-note">{learningDataset?.target_definition?.hard_constraints_note || "DQL/DQN 仅用于 shadow scoring，容量和唯一分配等硬约束仍由调度求解器保障。"}</p>
          <TruthStrip truth={truthFromResult(data.dispatchLearningDataset)} />
        </Panel>

        <Panel title="Policy Shadow Score" action={<DataState result={data.dispatchPolicyScorer} />}>
          <div className="summary-strip">
            <div>
              <span>Best Policy</span>
              <strong>{policyScorer?.best_policy?.name || "not_ready"}</strong>
            </div>
            <div>
              <span>Policy Score</span>
              <strong>{formatNumber(policyScorer?.best_policy?.policy_score, 2)}</strong>
            </div>
            <div>
              <span>Delta</span>
              <strong>{signedNumber(policyScorer?.best_policy?.score_delta_vs_baseline, 2)}</strong>
            </div>
          </div>
          <div className="solver-table" role="table" aria-label="调度 shadow 策略对比">
            <div className="solver-head" role="row">
              <span>policy</span>
              <span>top-k reward</span>
              <span>delta</span>
              <span>mode</span>
            </div>
            {(policyScorer?.policies || []).slice(0, 6).map((policy) => (
              <div className="solver-row" role="row" key={policy.policy_id}>
                <span>{policy.name || policy.policy_id || "-"}</span>
                <span>{formatNumber(policy.top_k_reward_proxy, 2)}</span>
                <span>{signedNumber(policy.score_delta_vs_baseline, 2)}</span>
                <StatusPill status={policy.deployable ? "ok" : "degraded"} label={policy.policy_family || "shadow"} />
              </div>
            ))}
            {!policyScorer?.policies?.length ? <p className="empty-note">{data.dispatchPolicyScorer.error || policyScorer?.readiness?.reason || "暂无可评分的 shadow policy 数据。"}</p> : null}
          </div>
          <p className="panel-note">{policyScorer?.target_definition?.scoring_note || "策略评分只做离线影子对比，不会修改调度场景或订单状态。"}</p>
          <TruthStrip truth={truthFromResult(data.dispatchPolicyScorer)} />
        </Panel>

        <Panel title="Reward Model" action={<DataState result={data.dispatchRewardModel} />}>
          <div className="summary-strip">
            <div>
              <span>Model</span>
              <strong>{rewardModel?.model_version || "not_ready"}</strong>
            </div>
            <div>
              <span>Train / Test</span>
              <strong>{formatNumber(rewardModel?.readiness?.train_rows)} / {formatNumber(rewardModel?.readiness?.test_rows)}</strong>
            </div>
            <div>
              <span>Rank Acc.</span>
              <strong>{percent(rewardModel?.metrics?.rank_accuracy?.accuracy)}</strong>
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
                <strong>{feature.feature || "-"}</strong>
                <p>abs {formatNumber(feature.abs_weight, 3)}</p>
              </article>
            ))}
            {!rewardModel?.model?.feature_importance?.length ? (
              <p className="empty-note">{data.dispatchRewardModel.error || rewardModel?.readiness?.reason || "暂无可训练的 shadow reward model 数据。"}</p>
            ) : null}
          </div>
          <p className="panel-note">{rewardModel?.model?.training_note || "Reward model 只预测离线 proxy reward，用于 shadow ranking 与后续 DQL/DQN 基线。"}</p>
          <TruthStrip truth={truthFromResult(data.dispatchRewardModel)} />
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
                {formatNumber(shadowBenchmark?.summary?.ready_component_count)} / {formatNumber(shadowBenchmark?.summary?.component_count)}
              </strong>
            </div>
            <div>
              <span>Gates</span>
              <strong>
                {formatNumber(shadowBenchmark?.summary?.passed_gate_count)} / {formatNumber(shadowBenchmark?.summary?.gate_count)}
              </strong>
            </div>
            <div>
              <span>Deployable</span>
              <strong>{String(shadowBenchmark?.summary?.deployable ?? false)}</strong>
            </div>
          </div>
          <div className="summary-strip route-truth-strip">
            <div>
              <span>Mode</span>
              <strong>{shadowBenchmark?.mode || "offline_shadow"}</strong>
            </div>
            <div>
              <span>Chain</span>
              <strong>{formatNumber(shadowBenchmark?.summary?.shadow_chain?.length)}</strong>
            </div>
            <div>
              <span>Mutation</span>
              <strong>{String(shadowBenchmark?.truth_contract?.mutation || "none")}</strong>
            </div>
            <div>
              <span>Family</span>
              <strong>{shadowBenchmark?.model_family || "dispatch_shadow"}</strong>
            </div>
          </div>
          <div className="data-list">
            {(shadowBenchmark?.components || []).slice(0, 6).map((component) => (
              <article className="data-row" key={component.component_id || component.name}>
                <span>{component.status || "status"} · {component.provider_status || "provider"}</span>
                <strong>{component.name || component.component_id} · {component.ready ? "ready" : "needs work"}</strong>
                <p>{component.reason || component.authenticity_level || "shadow benchmark component"}</p>
              </article>
            ))}
            {(shadowBenchmark?.gates || []).filter((gate) => !gate.passed).slice(0, 4).map((gate) => (
              <article className="data-row" key={gate.gate_id}>
                <span>gate failed</span>
                <strong>{gate.gate_id || "readiness_gate"}</strong>
                <p>{gate.reason || "需要补充 shadow benchmark 证据。"}</p>
              </article>
            ))}
            {(shadowBenchmark?.recommendations || []).slice(0, 4).map((item) => (
              <article className="data-row" key={item}>
                <span>benchmark recommendation</span>
                <strong>{item}</strong>
              </article>
            ))}
            {!shadowBenchmark?.components?.length ? (
              <p className="empty-note">
                {data.dispatchShadowBenchmark.error || shadowBenchmark?.fallback_reason || "暂无全局 shadow benchmark scorecard。"}
              </p>
            ) : null}
          </div>
          <p className="panel-note">
            Shadow benchmark 只评估学习链准备度，不会替代 Gurobi/OR-Tools/ALNS 的硬约束求解，也不会写入订单或调度业务状态。
          </p>
          <TruthStrip truth={truthFromResult(data.dispatchShadowBenchmark)} />
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
              <p>{shadowBenchmarkSnapshot?.snapshot?.replay_request?.method || "POST"} · read-only audit payload</p>
            </article>
            {!shadowBenchmarkSnapshot?.snapshot ? (
              <p className="empty-note">
                {data.dispatchShadowBenchmarkSnapshot.error || shadowBenchmarkSnapshot?.fallback_reason || "暂无 benchmark snapshot。"}
              </p>
            ) : null}
          </div>
          <TruthStrip truth={truthFromResult(data.dispatchShadowBenchmarkSnapshot)} />
        </Panel>

        <Panel title="Solver Compare" action={<DataState result={data.dispatchSolverComparison} />}>
          <div className="solver-table" role="table" aria-label="调度求解器对比">
            <div className="solver-head" role="row">
              <span>solver</span>
              <span>assigned</span>
              <span>cost</span>
              <span>status</span>
            </div>
            {(comparison?.results || []).map((item) => (
              <div className="solver-row" role="row" key={item.solver}>
                <span>{item.solver || "-"}</span>
                <span>{formatNumber(item.assigned_orders)} / {formatNumber(item.unassigned_orders)}</span>
                <span>{formatNumber(item.total_cost, 1)}</span>
                <StatusPill status={item.available ? "ok" : "degraded"} label={item.status || "unknown"} />
              </div>
            ))}
            {!comparison?.results?.length ? <p className="empty-note">{data.dispatchSolverComparison.error || "求解器对比接口暂不可用。"}</p> : null}
          </div>
          <p className="panel-note">{comparison?.note || "Gurobi/OR-Tools/ALNS 后续可继续接入生产波次对比。"}</p>
        </Panel>

        <Panel title="Recent Scenarios" action={<DataState result={data.dispatchScenarios} />}>
          <div className="data-list">
            {(scenarios?.scenarios || []).slice(0, 8).map((scenario) => (
              <article className="data-row" key={scenario.id || scenario.scenario_code}>
                <span>{scenario.scenario_code || `scenario-${scenario.id}`}</span>
                <strong>{scenario.status || "preview"} · {scenario.solver || "solver"}</strong>
                <p>
                  {formatNumber(scenario.summary?.assigned_orders || scenario.summary?.total_orders_assigned)} 已分配 · {scenario.authenticity_level || "truth unknown"}
                  {scenario.id ? <> · <Link href={`/dispatch/scenarios/${scenario.id}`}>查看详情</Link></> : null}
                </p>
              </article>
            ))}
            {!scenarios?.scenarios?.length ? <p className="empty-note">{data.dispatchScenarios.error || "暂无调度场景或当前未登录。"}</p> : null}
          </div>
        </Panel>
      </section>
    </ConsoleShell>
  );
}
