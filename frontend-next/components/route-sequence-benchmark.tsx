import { StatusPill, TruthStrip } from "@/components/status-pill";
import { compactText, formatNumber } from "@/lib/format";
import type { ProviderStatus, RouteSequenceBenchmark, RouteSequenceResult } from "@/lib/types";

function countSummary(counts?: Record<string, number> | null, limit = 3): string {
  const entries = Object.entries(counts || {})
    .filter(([, value]) => Number.isFinite(value))
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
  if (!entries.length) return "not reported";
  return entries.map(([key, value]) => `${key} ${formatNumber(value)}`).join(" / ");
}

function statusForRow(row: RouteSequenceResult): ProviderStatus {
  if (row.provider_status) return row.provider_status;
  if (row.success && row.feasible) return "ok";
  if (row.success) return "degraded";
  return "failed";
}

function bestResult(benchmark?: RouteSequenceBenchmark | null): RouteSequenceResult | null {
  const best = benchmark?.summary?.best_solver;
  const rows = benchmark?.results || [];
  return rows.find((row) => row.solver === best) || rows.find((row) => row.success && row.feasible) || null;
}

function sequenceLabel(row?: RouteSequenceResult | null): string {
  const labels = row?.node_labels?.length ? row.node_labels : row?.node_sequence?.map(String);
  return labels?.length ? labels.join(" -> ") : "-";
}

export function RouteSequenceBenchmarkPanel({
  benchmark,
}: {
  benchmark?: RouteSequenceBenchmark | null;
}) {
  const rows = benchmark?.results || [];
  const best = bestResult(benchmark);
  const matrixTruth = benchmark?.matrix_truth;

  if (!benchmark) {
    return <p className="empty-note">暂无路线序列 benchmark 数据。</p>;
  }

  return (
    <div className="route-benchmark">
      <div className="summary-strip">
        <div>
          <span>best solver</span>
          <strong>{compactText(benchmark.summary?.best_solver, "not feasible")}</strong>
        </div>
        <div>
          <span>nodes</span>
          <strong>
            {formatNumber(benchmark.summary?.node_count)} / {formatNumber(benchmark.summary?.waypoint_count)}
          </strong>
        </div>
        <div>
          <span>route graph pairs</span>
          <strong>
            {formatNumber(matrixTruth?.route_graph_pair_count)} / {formatNumber(matrixTruth?.pair_count)}
          </strong>
        </div>
        <div>
          <span>fallback pairs</span>
          <strong>{formatNumber(matrixTruth?.haversine_fallback_pair_count)}</strong>
        </div>
      </div>

      <div className="diagnostic-grid">
        <article>
          <span>depot</span>
          <strong>{compactText(benchmark.origin?.node_name || benchmark.origin?.name || benchmark.origin?.id)}</strong>
          <p>{compactText(benchmark.origin?.city || benchmark.origin?.address || benchmark.origin?.type)}</p>
        </article>
        <article>
          <span>waypoints</span>
          <strong>{formatNumber(benchmark.waypoints?.length)}</strong>
          <p>{(benchmark.waypoints || []).map((node) => node.node_name || node.name || node.id).join(" / ") || "-"}</p>
        </article>
        <article>
          <span>matrix truth</span>
          <strong>{compactText(matrixTruth?.authenticity_level, "C-route-matrix")}</strong>
          <p>{countSummary(matrixTruth?.distance_source_counts, 2)}</p>
        </article>
        <article>
          <span>provider status</span>
          <strong>
            <StatusPill status={benchmark.provider_status} label={benchmark.provider_status || "unknown"} />
          </strong>
          <p>{countSummary(matrixTruth?.provider_status_counts, 2)}</p>
        </article>
      </div>

      <div className="solver-table" role="table" aria-label="路线序列求解器 benchmark">
        <div className="solver-head route-head" role="row">
          <span>solver</span>
          <span>distance</span>
          <span>duration</span>
          <span>status</span>
        </div>
        {rows.map((row) => (
          <div className="solver-row route-row" role="row" key={row.solver || row.solver_quality}>
            <span>{row.solver || "solver"} · {row.solver_quality || "quality"}</span>
            <span>{formatNumber(row.total_distance_km, 2)} km</span>
            <span>{formatNumber(row.total_duration_minutes, 1)} min</span>
            <StatusPill status={statusForRow(row)} label={row.fallback_reason || (row.feasible ? "feasible" : "degraded")} />
          </div>
        ))}
      </div>

      {best ? (
        <div className="diagnostic-grid">
          <article>
            <span>best sequence</span>
            <strong>{best.solver || "solver"}</strong>
            <p>{sequenceLabel(best)}</p>
          </article>
          <article>
            <span>route truth</span>
            <strong>{compactText(best.route_truth?.authenticity_level, "C-route-sequence")}</strong>
            <p>
              {formatNumber(best.route_truth?.leg_count)} legs · {formatNumber(best.route_truth?.segment_count)} segments
            </p>
          </article>
          <article>
            <span>distance sources</span>
            <strong>{countSummary(best.route_truth?.distance_source_counts, 2)}</strong>
            <p>{formatNumber(best.route_truth?.missing_segment_count)} missing segments</p>
          </article>
          <article>
            <span>route ids</span>
            <strong>{(best.route_truth?.route_ids || []).slice(0, 4).join(", ") || "-"}</strong>
            <p>{best.fallback_reason || "route sequence is fully traceable through local graph legs"}</p>
          </article>
        </div>
      ) : null}

      <TruthStrip
        truth={{
          data_source: benchmark.data_source,
          distance_source: benchmark.distance_source,
          path_source: benchmark.path_source,
          provider_status: benchmark.provider_status,
          fallback_reason: benchmark.fallback_reason || benchmark.error,
          authenticity_level: benchmark.authenticity_level,
        }}
      />
    </div>
  );
}
