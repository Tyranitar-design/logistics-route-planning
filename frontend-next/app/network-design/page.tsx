import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getNetworkDesignPageData } from "@/lib/api";
import { compactText, formatNumber, percent } from "@/lib/format";
import { truthFromResult } from "@/lib/truth";
import type { NetworkDesignResult, RemoteResult } from "@/lib/types";

export const dynamic = "force-dynamic";

function chooseNetworkResult(
  database: RemoteResult<NetworkDesignResult>,
  demo: RemoteResult<NetworkDesignResult>,
) {
  if (database.ok && database.data?.success) {
    return {
      label: "真实 OD 聚合",
      result: database,
      data: database.data,
      preferredSource: true,
    };
  }
  return {
    label: "Demo baseline",
    result: demo,
    data: demo.data,
    preferredSource: false,
  };
}

export default async function NetworkDesignPage() {
  const data = await getNetworkDesignPageData();
  const active = chooseNetworkResult(data.networkDatabase, data.networkDemo);
  const result = active.data;
  const summary = result?.summary;
  const input = result?.input_summary;
  const selectedFacilities = result?.selected_facilities || [];
  const assignments = result?.assignments || [];
  const unassignedCount = result?.unassigned_customers?.length || summary?.unassigned_customers || 0;

  return (
    <ConsoleShell
      activePath="/network-design"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="物流网络设计"
      title="真实 OD 聚合、仓网选址与容量分配"
    >
      <section className="metric-grid" aria-label="网络设计关键指标">
        <MetricCard label="需求城市" value={formatNumber(input?.customers)} helper={active.label} tone={active.preferredSource ? "good" : "warn"} />
        <MetricCard label="候选节点" value={formatNumber(input?.candidates)} helper={`${formatNumber(input?.total_capacity, 1)} t capacity`} />
        <MetricCard label="开仓数量" value={formatNumber(summary?.selected_facilities)} helper={result?.solver || "solver"} />
        <MetricCard label="覆盖率" value={percent(summary?.demand_coverage_rate)} helper={`${formatNumber(unassignedCount)} unassigned`} tone={unassignedCount ? "warn" : "good"} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Real OD Aggregate" action={<DataState result={data.networkDatabase} />}>
          <p className="panel-note">
            {active.preferredSource
              ? "当前结果来自 shipment_facts 目的地需求与起点候选节点聚合，适合作为企业仓网设计的真实数据入口。"
              : data.networkDatabase.error || data.networkDatabase.data?.fallback_reason || "真实 OD 聚合不可用，当前展示 demo baseline。"}
          </p>
          <div className="summary-strip">
            <div>
              <span>source mode</span>
              <strong>{input?.source_mode || result?.data_source || "unknown"}</strong>
            </div>
            <div>
              <span>transport cost</span>
              <strong>{formatNumber(input?.transport_cost_per_km, 2)} / km</strong>
            </div>
            <div>
              <span>max facilities</span>
              <strong>{formatNumber(input?.max_facilities)}</strong>
            </div>
          </div>
          <TruthStrip truth={truthFromResult(active.result)} />
        </Panel>

        <Panel title="Solver Capability" action={<DataState result={data.gurobiHealth} />}>
          <div className="provider-line">
            <span>Gurobi</span>
            <StatusPill status={data.gurobiHealth.data?.provider_status || (data.gurobiHealth.data?.available ? "ok" : "degraded")} />
            <strong>{data.gurobiHealth.data?.status || data.gurobiHealth.data?.fallback_reason || data.gurobiHealth.error || "not_reported"}</strong>
          </div>
          <div className="summary-strip">
            <div>
              <span>active solver</span>
              <strong>{result?.solver || "not_ready"}</strong>
            </div>
            <div>
              <span>quality</span>
              <strong>{result?.solver_quality || "unknown"}</strong>
            </div>
            <div>
              <span>solve time</span>
              <strong>{formatNumber(result?.solve_time_seconds, 3)} s</strong>
            </div>
          </div>
          <p className="panel-note">
            {result?.fallback_reason || "Gurobi 可用时返回 MILP 精确/近优结果；不可用时显式降级到 greedy facility capacity baseline。"}
          </p>
        </Panel>

        <Panel title="Selected Facilities" action={<DataState result={active.result} />}>
          <div className="facility-grid">
            {selectedFacilities.map((facility) => (
              <article className="facility-card" key={facility.facility_id || facility.id}>
                <div>
                  <span>{compactText(facility.facility_id || facility.id, "facility")}</span>
                  <strong>{facility.facility_name || facility.name || "-"}</strong>
                </div>
                <div className="capacity-bar" aria-label="capacity utilization">
                  <span style={{ width: `${Math.min(100, Math.max(0, Number(facility.utilization || 0) * 100))}%` }} />
                </div>
                <p>{formatNumber(facility.used_capacity, 1)} / {formatNumber(facility.capacity, 1)} t · {percent(facility.utilization)}</p>
              </article>
            ))}
            {!selectedFacilities.length ? <p className="empty-note">{active.result.error || "暂无选址结果。"}</p> : null}
          </div>
        </Panel>

        <Panel title="Assignment Flow" action={<StatusPill status={unassignedCount ? "degraded" : "ok"} label={`${formatNumber(assignments.length)} assigned`} />}>
          <div className="solver-table" role="table" aria-label="仓网分配结果">
            <div className="solver-head network-head" role="row">
              <span>customer</span>
              <span>facility</span>
              <span>demand</span>
              <span>cost</span>
            </div>
            {assignments.slice(0, 10).map((item) => (
              <div className="solver-row network-row" role="row" key={`${item.customer_id}-${item.facility_id}`}>
                <span>{item.customer_name || item.customer_id || "-"}</span>
                <span>{item.facility_name || item.facility_id || "-"}</span>
                <span>{formatNumber(item.demand, 1)} t / {formatNumber(item.distance_km, 1)} km</span>
                <span>{formatNumber(item.transport_cost, 1)}</span>
              </div>
            ))}
            {!assignments.length ? <p className="empty-note">暂无客户分配结果。</p> : null}
          </div>
        </Panel>

        <Panel title="Cost & Coverage" action={<StatusPill status={result?.provider_status || "unknown"} />}>
          <div className="cost-stack">
            <article>
              <span>固定成本</span>
              <strong>{formatNumber(summary?.fixed_cost, 1)}</strong>
            </article>
            <article>
              <span>运输成本</span>
              <strong>{formatNumber(summary?.transport_cost, 1)}</strong>
            </article>
            <article>
              <span>总成本</span>
              <strong>{formatNumber(summary?.total_cost, 1)}</strong>
            </article>
            <article>
              <span>目标值</span>
              <strong>{formatNumber(summary?.objective_value, 1)}</strong>
            </article>
          </div>
          <div className="summary-strip">
            <div>
              <span>需求覆盖</span>
              <strong>{formatNumber(summary?.assigned_demand, 1)} / {formatNumber(summary?.total_demand, 1)} t</strong>
            </div>
            <div>
              <span>model status</span>
              <strong>{compactText(summary?.model_status)}</strong>
            </div>
            <div>
              <span>gap</span>
              <strong>{summary?.optimality_gap === null || summary?.optimality_gap === undefined ? "-" : percent(summary.optimality_gap)}</strong>
            </div>
          </div>
        </Panel>

        <Panel title="Constraints & Truth" action={<StatusPill status={result?.authenticity_level?.startsWith("B") ? "ok" : "degraded"} label={result?.authenticity_level || "unknown"} />}>
          <div className="constraint-list">
            {(result?.constraints || []).map((item) => (
              <article key={item}>
                <span>constraint</span>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
          <p className="panel-note">
            网络设计当前使用小规模 bounded CFLP：真实数据库模式来自 `shipment_facts` OD 聚合，距离为 Haversine 修正估算；后续可接入 provider road distance cache 与更大规模 ALNS/Gurobi 分解。
          </p>
          <TruthStrip truth={truthFromResult(active.result)} />
        </Panel>

        <Panel title="Demo Baseline" action={<DataState result={data.networkDemo} />}>
          <div className="data-list">
            {(data.networkDemo.data?.selected_facilities || []).map((facility) => (
              <article className="data-row" key={facility.facility_id || facility.id}>
                <span>{facility.facility_id || facility.id}</span>
                <strong>{facility.facility_name || facility.name}</strong>
                <p>{formatNumber(facility.used_capacity, 1)} / {formatNumber(facility.capacity, 1)} t · {percent(facility.utilization)}</p>
              </article>
            ))}
            {!data.networkDemo.data?.selected_facilities?.length ? <p className="empty-note">{data.networkDemo.error || "Demo baseline 暂不可用。"}</p> : null}
          </div>
        </Panel>
      </section>
    </ConsoleShell>
  );
}
