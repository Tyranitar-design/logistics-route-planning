import { StatusPill, TruthStrip } from "@/components/status-pill";
import { compactText, formatNumber } from "@/lib/format";
import {
  coordinatesFromCandidate,
  normalizeCandidateStatus,
  routeDistanceKm,
  routeDurationMinutes,
} from "@/lib/route-geometry";
import type { LocalRouteBenchmark, LocalRouteStrategy, ProviderStatus, RouteCandidate, TruthMetadata } from "@/lib/types";

interface RouteAlgorithmBenchmarkProps {
  localCandidate?: RouteCandidate | null;
  roadCandidate?: RouteCandidate | null;
  benchmark?: LocalRouteBenchmark | null;
  roadLabel?: string;
}

interface DeltaMetric {
  local: number | null;
  road: number | null;
  delta: number | null;
  deltaRatio: number | null;
}

function finite(value?: number | null): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function deltaMetric(local?: number | null, road?: number | null): DeltaMetric {
  const localValue = finite(local);
  const roadValue = finite(road);
  const delta = localValue !== null && roadValue !== null ? localValue - roadValue : null;
  const deltaRatio = delta !== null && roadValue && roadValue > 0 ? delta / roadValue : null;
  return {
    local: localValue,
    road: roadValue,
    delta,
    deltaRatio,
  };
}

function signedNumber(value?: number | null, fractionDigits = 1, suffix = ""): string {
  const numeric = finite(value);
  if (numeric === null) return "-";
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${formatNumber(numeric, fractionDigits)}${suffix}`;
}

function signedPercent(value?: number | null): string {
  const numeric = finite(value);
  if (numeric === null) return "-";
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${formatNumber(numeric * 100, 1)}%`;
}

function pathCount(candidate?: RouteCandidate | null): number | null {
  return Array.isArray(candidate?.path) ? candidate.path.length : null;
}

function sourceLabel(candidate?: RouteCandidate | null, fallback = "not_reported"): string {
  return compactText(
    candidate?.distance_source ||
      candidate?.path_source ||
      candidate?.provider ||
      candidate?.source ||
      candidate?.algorithm ||
      fallback,
  );
}

function selectBenchmarkLocal(benchmark?: LocalRouteBenchmark | null): LocalRouteStrategy | null {
  const strategies = benchmark?.local_strategies || [];
  const preferred = benchmark?.summary?.best_local_strategy;
  return (
    strategies.find((candidate) => candidate.strategy_id === preferred && candidate.success) ||
    strategies.find((candidate) => candidate.success) ||
    null
  );
}

function providerCandidates(
  benchmark?: LocalRouteBenchmark | null,
  fallback?: RouteCandidate | null,
): RouteCandidate[] {
  const candidates = benchmark?.provider_routes?.filter(Boolean) || [];
  if (candidates.length) return candidates;
  return fallback ? [fallback] : [];
}

function benchmarkStatus(local?: RouteCandidate | null, road?: RouteCandidate | null): ProviderStatus {
  if (local && road) return "ok";
  if (local || road) return "degraded";
  return "failed";
}

function providerDeltaSummary(strategy: LocalRouteStrategy): string {
  const comparisons = strategy.comparison_to_providers;
  if (!comparisons || !Object.keys(comparisons).length) {
    if (strategy.comparison_to_provider?.comparable) {
      return `${compactText(strategy.comparison_to_provider.provider, "provider")} ${signedNumber(
        strategy.comparison_to_provider.distance_delta_km,
        1,
        " km",
      )}`;
    }
    return compactText(strategy.fallback_reason || strategy.error || "not comparable");
  }

  return Object.entries(comparisons)
    .map(([provider, comparison]) =>
      comparison.comparable
        ? `${provider} ${signedNumber(comparison.distance_delta_km, 1, " km")}`
        : `${provider} -`,
    )
    .join(" / ");
}

function countSummary(counts?: Record<string, number> | null, limit = 3): string {
  const entries = Object.entries(counts || {})
    .filter(([, value]) => Number.isFinite(value))
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
  if (!entries.length) return "not reported";
  return entries.map(([key, value]) => `${key} ${formatNumber(value)}`).join(" / ");
}

function verdict(distanceDelta: DeltaMetric, durationDelta: DeltaMetric): string {
  if (distanceDelta.delta === null && durationDelta.delta === null) {
    return "缺少同口径候选，暂不能计算偏差。";
  }

  const distanceText =
    distanceDelta.delta === null
      ? "距离缺少对照"
      : distanceDelta.delta <= 0
        ? `本地距离短 ${formatNumber(Math.abs(distanceDelta.delta), 1)} km`
        : `本地距离长 ${formatNumber(distanceDelta.delta, 1)} km`;
  const durationText =
    durationDelta.delta === null
      ? "时长缺少对照"
      : durationDelta.delta <= 0
        ? `本地时长少 ${formatNumber(Math.abs(durationDelta.delta), 1)} min`
        : `本地时长多 ${formatNumber(durationDelta.delta, 1)} min`;

  return `${distanceText}；${durationText}。偏差用于算法对比，不代表真实道路优劣结论。`;
}

function truthForBenchmark(
  local?: RouteCandidate | null,
  road?: RouteCandidate | null,
  roadLabel = "road_provider",
  benchmark?: LocalRouteBenchmark | null,
): TruthMetadata {
  if (benchmark) {
    return {
      data_source: benchmark.data_source || "nodes/routes",
      distance_source: benchmark.distance_source || `${sourceLabel(local, "local_graph")} vs ${sourceLabel(road, roadLabel)}`,
      path_source: benchmark.path_source || "local_route_graph_vs_provider_polyline",
      provider_status: benchmark.provider_status || benchmarkStatus(local, road),
      fallback_reason: benchmark.fallback_reason || undefined,
      authenticity_level: benchmark.authenticity_level || (road ? "B/C-comparative-benchmark" : "C-local-only-benchmark"),
    };
  }

  return {
    data_source: "route_candidates",
    distance_source: `${sourceLabel(local, "local_graph")} vs ${sourceLabel(road, roadLabel)}`,
    path_source: "local_graph_sequence_vs_provider_polyline",
    provider_status: benchmarkStatus(local, road),
    fallback_reason: !local
      ? "LOCAL_ROUTE_MISSING"
      : !road
        ? "ROAD_PROVIDER_ROUTE_MISSING"
        : undefined,
    authenticity_level: road ? "B/C-comparative-benchmark" : "C-local-only-benchmark",
  };
}

export function RouteAlgorithmBenchmark({
  localCandidate: localCandidateProp,
  roadCandidate: roadCandidateProp,
  benchmark,
  roadLabel = "road provider",
}: RouteAlgorithmBenchmarkProps) {
  const benchmarkLocalCandidate = selectBenchmarkLocal(benchmark);
  const localCandidate = benchmarkLocalCandidate || localCandidateProp;
  const roadCandidate = benchmark?.provider_route || roadCandidateProp;
  const roadProviders = providerCandidates(benchmark, roadCandidate);
  const backendStrategies = benchmark?.local_strategies || [];
  const distanceDelta = deltaMetric(routeDistanceKm(localCandidate), routeDistanceKm(roadCandidate));
  const durationDelta = deltaMetric(routeDurationMinutes(localCandidate), routeDurationMinutes(roadCandidate));
  const localGeometryPoints = coordinatesFromCandidate(localCandidate).length;
  const roadGeometryPoints = coordinatesFromCandidate(roadCandidate).length;
  const status = benchmarkStatus(localCandidate, roadCandidate);

  return (
    <div className="route-benchmark">
      <div className="summary-strip">
        <div>
          <span>benchmark</span>
          <strong>{status === "ok" ? "可比较" : "降级对比"}</strong>
        </div>
        <div>
          <span>distance delta</span>
          <strong>
            {signedNumber(distanceDelta.delta, 1, " km")} / {signedPercent(distanceDelta.deltaRatio)}
          </strong>
        </div>
        <div>
          <span>duration delta</span>
          <strong>
            {signedNumber(durationDelta.delta, 1, " min")} / {signedPercent(durationDelta.deltaRatio)}
          </strong>
        </div>
      </div>

      <div className="diagnostic-grid">
        <article>
          <span>本地算法</span>
          <strong>
            {benchmarkLocalCandidate?.strategy_id ||
              localCandidate?.algorithm ||
              sourceLabel(localCandidate, "local graph")}
          </strong>
          <p>
            {formatNumber(distanceDelta.local, 1)} km · {formatNumber(durationDelta.local, 1)} min ·{" "}
            {formatNumber(pathCount(localCandidate))} path nodes
          </p>
        </article>
        <article>
          <span>{roadProviders.length > 1 ? "道路 provider" : roadLabel}</span>
          <strong>{sourceLabel(roadCandidate, "road provider")}</strong>
          <p>
            {formatNumber(distanceDelta.road, 1)} km · {formatNumber(durationDelta.road, 1)} min ·{" "}
            {formatNumber(roadGeometryPoints)} geometry points
          </p>
        </article>
        <article>
          <span>几何可视化</span>
          <strong>{formatNumber(localGeometryPoints)} / {formatNumber(roadGeometryPoints)}</strong>
          <p>本地图路径常是节点序列，provider 路径常是道路 polyline；两者不可混成同一真实性等级。</p>
        </article>
        <article>
          <span>候选状态</span>
          <strong>
            <StatusPill status={status} label={`${normalizeCandidateStatus(localCandidate)} / ${normalizeCandidateStatus(roadCandidate)}`} />
          </strong>
          <p>{verdict(distanceDelta, durationDelta)}</p>
        </article>
      </div>

      {benchmarkLocalCandidate?.route_truth ? (
        <div className="diagnostic-grid">
          <article>
            <span>local route truth</span>
            <strong>{compactText(benchmarkLocalCandidate.route_truth.authenticity_level, "C-local-graph")}</strong>
            <p>
              {formatNumber(benchmarkLocalCandidate.route_truth.segment_count)} segments ·{" "}
              {formatNumber(benchmarkLocalCandidate.route_truth.missing_segment_count)} missing
            </p>
          </article>
          <article>
            <span>distance sources</span>
            <strong>{countSummary(benchmarkLocalCandidate.route_truth.distance_source_counts, 2)}</strong>
            <p>来自 `routes.route_data`，用于说明本地图边距离是回填、缓存还是真实 provider。</p>
          </article>
          <article>
            <span>provider status</span>
            <strong>{countSummary(benchmarkLocalCandidate.route_truth.provider_status_counts, 2)}</strong>
            <p>本地路径边可以混合 ok/degraded，不能只看最终最短路径数值。</p>
          </article>
          <article>
            <span>route ids</span>
            <strong>{(benchmarkLocalCandidate.route_truth.route_ids || []).slice(0, 4).join(", ") || "-"}</strong>
            <p>用于回查 Route 表和后续距离重算/供应商 provider 审计。</p>
          </article>
        </div>
      ) : null}

      {roadProviders.length ? (
        <div className="solver-table" role="table" aria-label="道路 provider benchmark">
          <div className="solver-head route-head" role="row">
            <span>provider</span>
            <span>distance</span>
            <span>duration</span>
            <span>status</span>
          </div>
          {roadProviders.map((provider, index) => (
            <div className="solver-row route-row" role="row" key={`${provider.provider || provider.source || "provider"}-${index}`}>
              <span>{provider.provider || provider.source || "road provider"}</span>
              <span>{formatNumber(routeDistanceKm(provider), 1)} km</span>
              <span>{formatNumber(routeDurationMinutes(provider), 1)} min</span>
              <StatusPill
                status={provider.provider_status || normalizeCandidateStatus(provider)}
                label={provider.fallback_reason || provider.provider_status || normalizeCandidateStatus(provider)}
              />
            </div>
          ))}
        </div>
      ) : null}

      {backendStrategies.length ? (
        <div className="solver-table" role="table" aria-label="本地算法多策略 benchmark">
          <div className="solver-head route-head" role="row">
            <span>strategy</span>
            <span>distance</span>
            <span>duration</span>
            <span>delta</span>
          </div>
          {backendStrategies.map((strategy) => (
            <div className="solver-row route-row" role="row" key={strategy.strategy_id || strategy.algorithm}>
              <span>
                {strategy.strategy_id || strategy.algorithm} · {strategy.optimize_by || "target"}
              </span>
              <span>{formatNumber(routeDistanceKm(strategy), 1)} km</span>
              <span>{formatNumber(routeDurationMinutes(strategy), 1)} min</span>
              <span>{providerDeltaSummary(strategy)}</span>
            </div>
          ))}
        </div>
      ) : null}

      {benchmark?.summary ? (
        <div className="summary-strip">
          <div>
            <span>backend strategies</span>
            <strong>
              {formatNumber(benchmark.summary.successful_local_strategies)} /{" "}
              {formatNumber(benchmark.summary.local_strategy_count)}
            </strong>
          </div>
          <div>
            <span>closest provider</span>
            <strong>{compactText(benchmark.summary.closest_to_provider_strategy, "not comparable")}</strong>
          </div>
          <div>
            <span>provider route</span>
            <strong>
              {formatNumber(benchmark.summary.provider_available_count)} /{" "}
              {formatNumber(benchmark.summary.provider_count)}
            </strong>
          </div>
          <div>
            <span>local sources</span>
            <strong>{countSummary(benchmark.summary.local_distance_source_counts, 2)}</strong>
          </div>
        </div>
      ) : null}

      <TruthStrip truth={truthForBenchmark(localCandidate, roadCandidate, roadLabel, benchmark)} />
    </div>
  );
}
