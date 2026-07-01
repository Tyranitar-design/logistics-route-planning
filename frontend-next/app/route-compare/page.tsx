import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { RouteAlgorithmBenchmark } from "@/components/route-algorithm-benchmark";
import { RoutePolylinePreview } from "@/components/route-polyline-preview";
import { RouteSequenceBenchmarkPanel } from "@/components/route-sequence-benchmark";
import { RouteSelectionAutocomplete } from "@/components/route-selection-autocomplete";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getRouteComparePageData, type RouteCompareInput } from "@/lib/api";
import { compactText, formatNumber } from "@/lib/format";
import type { OrderSearchItem, ProviderStatus, RemoteResult, RouteCandidate, RouteNode, TruthMetadata } from "@/lib/types";

export const dynamic = "force-dynamic";

type RouteCompareSearchParams = Record<string, string | string[] | undefined>;

interface RouteComparePageProps {
  searchParams?: Promise<RouteCompareSearchParams>;
}

function firstParam(value?: string | string[]): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveIntegerParam(value?: string | string[]): number | null {
  const raw = firstParam(value);
  if (!raw) return null;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.trunc(parsed);
}

function parseWaypointIds(value?: string | string[]): number[] {
  const rawValues = Array.isArray(value) ? value : value ? [value] : [];
  const ids: number[] = [];
  for (const raw of rawValues) {
    for (const part of raw.split(",")) {
      const parsed = Number(part.trim());
      if (Number.isFinite(parsed) && parsed > 0) {
        const id = Math.trunc(parsed);
        if (!ids.includes(id)) ids.push(id);
      }
    }
  }
  return ids.slice(0, 6);
}

function waypointQuery(value?: number[] | null): string {
  const ids = Array.from(new Set((value || []).filter((item) => Number.isFinite(item) && item > 0)));
  return ids.join(",");
}

function addWaypoint(selection: RouteCompareInput, nodeId?: number | null): number[] {
  if (!nodeId) return selection.waypointIds || [];
  const blocked = new Set([selection.originId, selection.destinationId].filter(Boolean));
  if (blocked.has(nodeId)) return selection.waypointIds || [];
  return Array.from(new Set([...(selection.waypointIds || []), nodeId])).slice(0, 6);
}

function optionParam(value: string | undefined, fallback: string, allowed: string[]): string {
  return value && allowed.includes(value) ? value : fallback;
}

function parseRouteCompareInput(params: RouteCompareSearchParams): RouteCompareInput {
  return {
    originId: positiveIntegerParam(params.origin_id),
    destinationId: positiveIntegerParam(params.destination_id),
    waypointIds: parseWaypointIds(params.waypoint_ids),
    orderId: positiveIntegerParam(params.order_id),
    preferSource: optionParam(firstParam(params.prefer_source), "auto", ["auto", "local", "amap"]),
    strategy: optionParam(firstParam(params.strategy), "0", ["0", "1", "2", "3"]),
    nodeQuery: firstParam(params.node_query) || "",
    orderQuery: firstParam(params.order_query) || "",
  };
}

function compactQuery(value?: string | null): string {
  return value?.trim().slice(0, 80) || "";
}

function routeCompareHref(
  selection: RouteCompareInput,
  overrides: Partial<RouteCompareInput> = {},
): string {
  const next = { ...selection, ...overrides };
  const search = new URLSearchParams();
  const values: Array<[string, string | number | null | undefined]> = [
    ["origin_id", next.originId],
    ["destination_id", next.destinationId],
    ["waypoint_ids", waypointQuery(next.waypointIds)],
    ["order_id", next.orderId],
    ["prefer_source", next.preferSource || "auto"],
    ["strategy", next.strategy || "0"],
    ["node_query", compactQuery(next.nodeQuery)],
    ["order_query", compactQuery(next.orderQuery)],
  ];

  for (const [key, value] of values) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }

  return `/route-compare${search.size ? `?${search.toString()}` : ""}`;
}

function hiddenSelectionInputs(selection: RouteCompareInput, omit: string[] = []) {
  const values: Array<[string, string | number | null | undefined]> = [
    ["origin_id", selection.originId],
    ["destination_id", selection.destinationId],
    ["waypoint_ids", waypointQuery(selection.waypointIds)],
    ["order_id", selection.orderId],
    ["prefer_source", selection.preferSource || "auto"],
    ["strategy", selection.strategy || "0"],
    ["node_query", compactQuery(selection.nodeQuery)],
    ["order_query", compactQuery(selection.orderQuery)],
  ];

  return values
    .filter(([name, value]) => !omit.includes(name) && value !== null && value !== undefined && value !== "")
    .map(([name, value]) => (
      <input key={name} name={name} type="hidden" value={String(value)} />
    ));
}

function normalizeStatus(status?: ProviderStatus | null, success?: boolean): ProviderStatus {
  if (status === "configured") return "ok";
  if (status) return status;
  if (success === true) return "ok";
  if (success === false) return "failed";
  return "unknown";
}

function routeDistanceKm(candidate?: RouteCandidate | null): number | null {
  if (typeof candidate?.distance_km === "number") return candidate.distance_km;
  if (typeof candidate?.distance === "number") {
    return candidate.distance > 1000 ? candidate.distance / 1000 : candidate.distance;
  }
  return null;
}

function routeDurationMinutes(candidate?: RouteCandidate | null): number | null {
  if (typeof candidate?.duration_minutes === "number") return candidate.duration_minutes;
  if (typeof candidate?.duration === "number") {
    return candidate.duration > 10000 ? candidate.duration / 60 : candidate.duration;
  }
  return null;
}

function pathCount(candidate?: RouteCandidate | null): number | null {
  return Array.isArray(candidate?.path) ? candidate.path.length : null;
}

function candidateTruth(candidate?: RouteCandidate | null, fallbackSource = "route_provider"): TruthMetadata {
  return {
    data_source: candidate?.data_source || candidate?.source || candidate?.provider || fallbackSource,
    distance_source:
      candidate?.distance_source ||
      candidate?.authenticity?.distance_source ||
      candidate?.provider ||
      candidate?.algorithm ||
      "not_reported",
    path_source:
      candidate?.path_source ||
      candidate?.authenticity?.duration_source ||
      candidate?.provider ||
      candidate?.algorithm ||
      "not_reported",
    provider_status: normalizeStatus(candidate?.provider_status, candidate?.success),
    fallback_reason: candidate?.fallback_reason || candidate?.error || candidate?.authenticity?.message,
    authenticity_level:
      candidate?.authenticity_level ||
      candidate?.authenticity?.level ||
      (candidate?.provider === "amap" || candidate?.provider === "tianditu" ? "B" : undefined),
  };
}

function routeCandidateRows(data: Awaited<ReturnType<typeof getRouteComparePageData>>) {
  const tianditu = data.tiandituAmapCompare.data?.tianditu || null;
  const amap =
    data.tiandituAmapCompare.data?.amap ||
    data.amapLocalCompare.data?.amap ||
    data.routeRecommendation.data?.data?.amap_route ||
    null;
  const local =
    data.amapLocalCompare.data?.local ||
    data.routeRecommendation.data?.data?.local_route ||
    null;
  const recommended = data.routeRecommendation.data?.data?.recommended_route || null;

  return [
    { id: "tianditu", label: "天地图", role: "真实路网", candidate: tianditu },
    { id: "amap", label: "高德地图", role: "真实路网", candidate: amap },
    { id: "local", label: "本地图算法", role: "可解释/降级", candidate: local },
    { id: "recommended", label: "推荐结果", role: "业务推荐", candidate: recommended },
  ];
}

function originLabel(data: Awaited<ReturnType<typeof getRouteComparePageData>>) {
  const origin = data.amapLocalCompare.data?.origin || data.routeRecommendation.data?.data?.origin;
  return compactText(origin?.node_name || origin?.name || origin?.id, "node-1");
}

function destinationLabel(data: Awaited<ReturnType<typeof getRouteComparePageData>>) {
  const destination = data.amapLocalCompare.data?.destination || data.routeRecommendation.data?.data?.destination;
  return compactText(destination?.node_name || destination?.name || destination?.id, "node-2");
}

function nodeDisplayName(node: RouteNode): string {
  return compactText(node.node_name || node.name || node.id, "unknown node");
}

function nodeSubLabel(node: RouteNode): string {
  return compactText(
    [node.province, node.city, node.district].filter(Boolean).join(" / ") ||
      node.address ||
      node.type ||
      "node location unknown",
    "node location unknown",
  );
}

function nodeCoordinateLabel(node: RouteNode): string {
  if (typeof node.longitude === "number" && typeof node.latitude === "number") {
    return `${formatNumber(node.longitude, 4)}, ${formatNumber(node.latitude, 4)}`;
  }
  return "missing coordinates";
}

function orderDisplayName(order: OrderSearchItem): string {
  return compactText(order.order_number || order.external_order_id || order.external_shipment_id || order.id, "unknown order");
}

function orderSubLabel(order: OrderSearchItem): string {
  return compactText(
    `${order.origin_name || order.origin_address || "origin"} -> ${order.destination_name || order.destination_address || "destination"}`,
  );
}

function providerSummaryStatus<T extends { success?: boolean; provider_status?: ProviderStatus | null }>(result: RemoteResult<T>) {
  return result.ok ? normalizeStatus(result.data?.provider_status, result.data?.success) : "degraded";
}

function booleanLabel(value?: boolean | null): string {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "unknown";
}

function distanceSourceStatus(source?: string | null): ProviderStatus {
  if (source === "amap" || source === "cache") return "ok";
  if (source === "haversine_corrected" || source === "local_graph") return "degraded";
  return "unknown";
}

function cacheProbeStatus(data: Awaited<ReturnType<typeof getRouteComparePageData>>): ProviderStatus {
  const validation = data.amapDistanceValidation.data?.data;
  if (!data.amapDistanceValidation.ok) return "failed";
  if (validation?.cache?.hit_before_call || validation?.cache?.exists_after_call) return "ok";
  if (validation?.distance?.source) return distanceSourceStatus(validation.distance.source);
  return "unknown";
}

export default async function RouteComparePage({ searchParams }: RouteComparePageProps) {
  const params = searchParams ? await searchParams : {};
  const selection = parseRouteCompareInput(params);
  const data = await getRouteComparePageData(selection);
  const rows = routeCandidateRows(data);
  const amapRouteProbe = data.amapHealth.data?.components?.route;
  const amapTrafficProbe = data.amapHealth.data?.components?.traffic;
  const comparison = data.tiandituAmapCompare.data?.comparison;
  const recommendation = data.routeRecommendation.data?.data;
  const localCandidate = rows.find((row) => row.id === "local")?.candidate;
  const roadCandidate = rows.find((row) => row.id === "amap")?.candidate || rows.find((row) => row.id === "tianditu")?.candidate;
  const originNode = data.amapLocalCompare.data?.origin || recommendation?.origin || null;
  const destinationNode = data.amapLocalCompare.data?.destination || recommendation?.destination || null;
  const displayedOriginId = data.amapLocalCompare.data?.origin?.id || recommendation?.origin?.id || selection.originId || 1;
  const displayedDestinationId = data.amapLocalCompare.data?.destination?.id || recommendation?.destination?.id || selection.destinationId || 2;
  const nodeCandidates = data.nodeSuggestions.data?.nodes || [];
  const orderCandidates = data.orderSuggestions.data?.orders || [];
  const routeTileUrl = process.env.NEXT_PUBLIC_ROUTE_TILE_URL || null;
  const routeTileAttribution = process.env.NEXT_PUBLIC_ROUTE_TILE_ATTRIBUTION || null;
  const routeTileConfigured = Boolean(routeTileUrl);
  const cacheStats = data.amapDistanceCacheStats.data?.data;
  const distanceValidation = data.amapDistanceValidation.data?.data;
  const distanceCache = distanceValidation?.cache;
  const distanceInfo = distanceValidation?.distance;
  const distanceStatus = distanceSourceStatus(distanceInfo?.source);

  return (
    <ConsoleShell
      activePath="/route-compare"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="高级路径对比"
      title="高德、天地图与本地图算法可信对照"
    >
      <section className="metric-grid" aria-label="路径对比关键指标">
        <MetricCard
          label="高德路由"
          value={compactText(amapRouteProbe?.provider_status || providerSummaryStatus(data.amapHealth))}
          helper={amapRouteProbe?.fallback_reason || data.amapHealth.error || "provider health"}
          tone={normalizeStatus(amapRouteProbe?.provider_status, amapRouteProbe?.success) === "ok" ? "good" : "warn"}
        />
        <MetricCard
          label="天地图 Key"
          value={compactText(data.tiandituKeys.data?.provider_status || providerSummaryStatus(data.tiandituKeys))}
          helper={data.tiandituKeys.data?.fallback_reason || data.tiandituKeys.error || "key status"}
          tone={providerSummaryStatus(data.tiandituKeys) === "ok" ? "good" : "warn"}
        />
        <MetricCard
          label="路网距离"
          value={`${formatNumber(routeDistanceKm(roadCandidate), 1)} km`}
          helper={roadCandidate?.provider || roadCandidate?.source || "road provider"}
        />
        <MetricCard
          label="本地路径"
          value={`${formatNumber(routeDistanceKm(localCandidate), 1)} km`}
          helper={`${formatNumber(pathCount(localCandidate))} nodes`}
          tone={localCandidate ? "good" : "warn"}
        />
      </section>

      <section className="dashboard-grid">
        <Panel title="Provider Health" action={<DataState result={data.amapHealth} />}>
          <div className="provider-line">
            <span>route</span>
            <StatusPill status={normalizeStatus(amapRouteProbe?.provider_status, amapRouteProbe?.success)} label={amapRouteProbe?.provider_status || "unknown"} />
            <strong>{amapRouteProbe?.fallback_reason || `${formatNumber(amapRouteProbe?.distance_km, 2)} km probe`}</strong>
          </div>
          <div className="provider-line">
            <span>traffic</span>
            <StatusPill status={normalizeStatus(amapTrafficProbe?.provider_status, amapTrafficProbe?.success)} label={amapTrafficProbe?.provider_status || "unknown"} />
            <strong>{amapTrafficProbe?.fallback_reason || "traffic probe"}</strong>
          </div>
          <div className="provider-line">
            <span>tianditu</span>
            <StatusPill status={providerSummaryStatus(data.tiandituKeys)} label={data.tiandituKeys.data?.provider_status || data.tiandituKeys.error || "unknown"} />
            <strong>
              server {data.tiandituKeys.data?.server_key_configured ? "configured" : "missing"} / browser {data.tiandituKeys.data?.browser_key_configured ? "configured" : "missing"}
            </strong>
          </div>
          <TruthStrip
            truth={{
              data_source: "backend_provider_proxy",
              distance_source: amapRouteProbe?.provider || "amap_health_probe",
              path_source: "provider_health",
              provider_status: normalizeStatus(amapRouteProbe?.provider_status, amapRouteProbe?.success),
              fallback_reason: amapRouteProbe?.fallback_reason || data.amapHealth.error,
              authenticity_level: "B-provider-diagnostic",
            }}
          />
        </Panel>

        <Panel
          title="Cache & Tile Diagnostics"
          action={<StatusPill status={cacheProbeStatus(data)} label="cache probe" />}
        >
          <div className="diagnostic-grid">
            <article>
              <span>缓存条目</span>
              <strong>{formatNumber(cacheStats?.total_entries)}</strong>
              <p>SQLite distance cache entries</p>
            </article>
            <article>
              <span>高德精确</span>
              <strong>{formatNumber(cacheStats?.amap_exact)}</strong>
              <p>source = amap</p>
            </article>
            <article>
              <span>Haversine 修正</span>
              <strong>{formatNumber(cacheStats?.haversine_corrected)}</strong>
              <p>source = haversine_corrected</p>
            </article>
            <article>
              <span>已过期</span>
              <strong>{formatNumber(cacheStats?.expired)}</strong>
              <p>需要后台清理或重算</p>
            </article>
          </div>
          <div className="provider-line">
            <span>current od</span>
            <StatusPill status={distanceStatus} label={distanceInfo?.source || "unknown"} />
            <strong>
              {formatNumber(distanceInfo?.distance_km, 2)} km / {formatNumber(distanceInfo?.duration_minutes, 1)} min
            </strong>
          </div>
          <div className="provider-line">
            <span>cache hit</span>
            <StatusPill
              status={distanceCache?.hit_before_call || distanceCache?.exists_after_call ? "ok" : "degraded"}
              label={`before ${booleanLabel(distanceCache?.hit_before_call)}`}
            />
            <strong>
              after {booleanLabel(distanceCache?.exists_after_call)} / cached source {distanceCache?.cached_source || "not cached"}
            </strong>
          </div>
          <div className="provider-line">
            <span>tile layer</span>
            <StatusPill status={routeTileConfigured ? "ok" : "degraded"} label={routeTileConfigured ? "configured" : "svg fallback"} />
            <strong>
              {routeTileConfigured
                ? "Leaflet tile layer enabled; provider polylines remain the truth source."
                : "NEXT_PUBLIC_ROUTE_TILE_URL 未配置，页面使用 SVG 坐标预览作为安全降级。"}
            </strong>
          </div>
          <p className="panel-note">
            缓存诊断只展示安全统计，不暴露服务端缓存数据库路径；当前 OD 验证会记录高德、缓存或 Haversine 降级来源。
          </p>
          <TruthStrip
            truth={{
              data_source: "amap_distance_cache",
              distance_source: distanceInfo?.source || "distance_validate_unavailable",
              path_source: routeTileConfigured ? "leaflet_tile_layer_plus_provider_polyline" : "svg_provider_polyline_preview",
              provider_status: distanceStatus,
              fallback_reason:
                distanceValidation?.fallback_reason ||
                data.amapDistanceValidation.error ||
                data.amapDistanceCacheStats.error,
              authenticity_level:
                distanceInfo?.source === "amap" || distanceInfo?.source === "cache"
                  ? "B-real-distance-diagnostic"
                  : "C-distance-fallback-diagnostic",
            }}
          />
        </Panel>

        <Panel title="Route Query" action={<StatusPill status="ok" label={`node ${displayedOriginId} → ${displayedDestinationId}`} />}>
          <div className="route-preview" aria-label="路径对比起终点示意">
            <div className="route-node route-node-origin">
              <span>起点</span>
              <strong>{originLabel(data)}</strong>
            </div>
            <div className="route-line">
              <span />
              <span />
              <span />
            </div>
            <div className="route-node route-node-destination">
              <span>终点</span>
              <strong>{destinationLabel(data)}</strong>
            </div>
          </div>
          <form className="route-filter-form" action="/route-compare">
            <label>
              <span>起点 Node ID</span>
              <input
                inputMode="numeric"
                min="1"
                name="origin_id"
                type="number"
                defaultValue={selection.originId || ""}
                placeholder={String(displayedOriginId)}
              />
            </label>
            <label>
              <span>终点 Node ID</span>
              <input
                inputMode="numeric"
                min="1"
                name="destination_id"
                type="number"
                defaultValue={selection.destinationId || ""}
                placeholder={String(displayedDestinationId)}
              />
            </label>
            <label>
              <span>订单 ID</span>
              <input
                inputMode="numeric"
                min="1"
                name="order_id"
                type="number"
                defaultValue={selection.orderId || ""}
                placeholder="35692"
              />
            </label>
            <label>
              <span>途经 Node IDs</span>
              <input
                name="waypoint_ids"
                type="text"
                defaultValue={waypointQuery(selection.waypointIds)}
                placeholder="2,3,4"
              />
            </label>
            <label>
              <span>推荐偏好</span>
              <select name="prefer_source" defaultValue={selection.preferSource || "auto"}>
                <option value="auto">auto</option>
                <option value="amap">amap</option>
                <option value="local">local</option>
              </select>
            </label>
            <label>
              <span>天地图策略</span>
              <select name="strategy" defaultValue={selection.strategy || "0"}>
                <option value="0">0 default</option>
                <option value="1">1 avoid jam</option>
                <option value="2">2 shortest</option>
                <option value="3">3 no highway</option>
              </select>
            </label>
            <div className="route-filter-actions">
              <button className="command-button" type="submit">对比</button>
              <a className="route-reset-link" href="/route-compare">重置</a>
            </div>
          </form>
          <p className="panel-note">
            可直接输入订单 ID 使用真实运单的起终点，也可以输入 Node ID 做手动 OD 对照；途经 Node IDs 会进入路线序列求解器 benchmark。所有请求仍走服务端代理和 httpOnly cookie，不把 token 暴露给浏览器脚本。
          </p>
        </Panel>

        <Panel
          title="Selection Assist"
          action={<StatusPill status={data.nodeSuggestions.ok || data.orderSuggestions.ok ? "ok" : "degraded"} label="autocomplete + SSR" />}
        >
          <RouteSelectionAutocomplete selection={selection} />
          <p className="panel-note">
            自动补全通过 Next BFF 读取 httpOnly cookie 后再访问 Flask，浏览器脚本不会获得后端 token；下方 SSR 搜索仍可生成可分享的查询 URL。
          </p>
          <div className="route-search-grid">
            <form className="route-search-card" action="/route-compare">
              {hiddenSelectionInputs(selection, ["node_query"])}
              <label>
                <span>节点关键词</span>
                <input
                  name="node_query"
                  type="search"
                  defaultValue={compactQuery(selection.nodeQuery)}
                  placeholder="城市 / 仓 / 节点名"
                />
              </label>
              <button className="command-button" type="submit">查节点</button>
            </form>
            <form className="route-search-card" action="/route-compare">
              {hiddenSelectionInputs(selection, ["order_query"])}
              <label>
                <span>订单搜索</span>
                <input
                  name="order_query"
                  type="search"
                  defaultValue={compactQuery(selection.orderQuery)}
                  placeholder="订单号 / 运单号 / 客户"
                />
              </label>
              <button className="command-button" type="submit">查订单</button>
            </form>
          </div>

          <div className="route-picker-grid">
            <section className="route-picker-list" aria-label="节点候选">
              <div className="route-picker-head">
                <strong>节点候选</strong>
                <span>{formatNumber(data.nodeSuggestions.data?.total)} total</span>
              </div>
              {nodeCandidates.length ? (
                nodeCandidates.map((node) => (
                  <article className="route-picker-row" key={`node-${node.id}`}>
                    <div>
                      <span>{nodeDisplayName(node)}</span>
                      <strong>{nodeSubLabel(node)}</strong>
                      <p>{nodeCoordinateLabel(node)} · {node.status || node.type || "status unknown"}</p>
                    </div>
                    <div className="route-picker-actions">
                      <a href={routeCompareHref(selection, { originId: Number(node.id), orderId: null })}>设为起点</a>
                      <a href={routeCompareHref(selection, { destinationId: Number(node.id), orderId: null })}>设为终点</a>
                      <a href={routeCompareHref(selection, { waypointIds: addWaypoint(selection, Number(node.id)), orderId: null })}>设为途经</a>
                    </div>
                  </article>
                ))
              ) : (
                <article className="route-picker-empty">
                  <strong>{data.nodeSuggestions.error || data.nodeSuggestions.data?.error || "暂无节点候选"}</strong>
                  <span>登录后会从 PostgreSQL Node 表读取真实运营节点。</span>
                </article>
              )}
            </section>

            <section className="route-picker-list" aria-label="订单候选">
              <div className="route-picker-head">
                <strong>订单候选</strong>
                <span>{data.orderSuggestions.data?.data_source || "orders/shipment_facts"}</span>
              </div>
              {orderCandidates.length ? (
                orderCandidates.map((order) => (
                  <article className="route-picker-row" key={`order-${order.id}`}>
                    <div>
                      <span>{orderDisplayName(order)}</span>
                      <strong>{orderSubLabel(order)}</strong>
                      <p>{order.data_source || data.orderSuggestions.data?.data_source || "order"} · {order.status || "status unknown"} · {formatNumber(order.weight, 1)} kg</p>
                    </div>
                    <div className="route-picker-actions">
                      <a href={routeCompareHref(selection, {
                        originId: null,
                        destinationId: null,
                        orderId: Number(order.id),
                        orderQuery: orderDisplayName(order),
                      })}>
                        使用订单
                      </a>
                    </div>
                  </article>
                ))
              ) : (
                <article className="route-picker-empty">
                  <strong>{data.orderSuggestions.error || data.orderSuggestions.data?.error || "暂无订单候选"}</strong>
                  <span>legacy orders 为空时会从真实 shipment_facts 搜索。</span>
                </article>
              )}
            </section>
          </div>
        </Panel>

        <Panel
          title="Provider Polyline Preview"
          action={<StatusPill status={roadCandidate ? "ok" : "degraded"} label="geometry" />}
          className="route-map-panel"
        >
          <RoutePolylinePreview
            layers={rows}
            origin={originNode}
            destination={destinationNode}
            tileAttribution={routeTileAttribution}
            tileUrl={routeTileUrl}
          />
        </Panel>

        <Panel title="Route Candidates" action={<DataState result={data.tiandituAmapCompare.ok ? data.tiandituAmapCompare : data.amapLocalCompare} />}>
          <div className="solver-table" role="table" aria-label="路径候选方案">
            <div className="solver-head route-head" role="row">
              <span>source</span>
              <span>distance</span>
              <span>duration</span>
              <span>status</span>
            </div>
            {rows.map((row) => (
              <div className="solver-row route-row" role="row" key={row.id}>
                <span>{row.label} · {row.role}</span>
                <span>{formatNumber(routeDistanceKm(row.candidate), 1)} km</span>
                <span>{formatNumber(routeDurationMinutes(row.candidate), 1)} min</span>
                <StatusPill status={candidateTruth(row.candidate, row.id).provider_status} label={row.candidate?.success === false ? "failed" : candidateTruth(row.candidate, row.id).provider_status || "unknown"} />
              </div>
            ))}
          </div>
          <p className="panel-note">
            高德/天地图代表真实路网 provider，本地图算法代表可解释图搜索与降级基线；距离和路径口径不能混用为同一真实性等级。
          </p>
        </Panel>

        <Panel title="Provider Difference" action={<DataState result={data.tiandituAmapCompare} />}>
          <div className="summary-strip">
            <div>
              <span>距离差</span>
              <strong>{formatNumber(comparison?.distance_diff, 2)} km</strong>
            </div>
            <div>
              <span>时长差</span>
              <strong>{formatNumber(comparison?.duration_diff, 1)} min</strong>
            </div>
            <div>
              <span>更短来源</span>
              <strong>{comparison?.better_distance || "unknown"}</strong>
            </div>
          </div>
          <p className="panel-note">
            {data.tiandituAmapCompare.error || data.tiandituAmapCompare.data?.error || "当两个 provider 同时可用时，这里展示道路距离和预计时长差异。"}
          </p>
          <TruthStrip
            truth={{
              data_source: "nodes",
              distance_source: "tianditu_vs_amap",
              path_source: "road_network_provider_compare",
              provider_status: providerSummaryStatus(data.tiandituAmapCompare),
              fallback_reason: data.tiandituAmapCompare.error || data.tiandituAmapCompare.data?.error,
              authenticity_level: "B-road-provider-comparison",
            }}
          />
        </Panel>

        <Panel title="Local Algorithm Benchmark" action={<DataState result={data.localBenchmark} />}>
          <RouteAlgorithmBenchmark
            benchmark={data.localBenchmark.data}
            localCandidate={localCandidate}
            roadCandidate={roadCandidate}
            roadLabel={roadCandidate?.provider || roadCandidate?.source || "高德/天地图"}
          />
        </Panel>

        <Panel title="Route Sequence Solver Benchmark" action={<DataState result={data.routeSequenceBenchmark} />}>
          <RouteSequenceBenchmarkPanel benchmark={data.routeSequenceBenchmark.data} />
        </Panel>

        <Panel title="Order Recommendation Contract" action={<DataState result={data.routeRecommendation} />}>
          <div className="data-list">
            <article className="data-row">
              <span>{recommendation?.order_number || "node preview"}</span>
              <strong>{recommendation?.recommendation_reason || data.routeRecommendation.data?.error || data.routeRecommendation.error || "等待路线推荐接口返回。"}</strong>
              <p>{recommendation?.data_source || "orders/recommend-route"} · {recommendation?.provider_status || "provider unknown"}</p>
            </article>
            {recommendation?.recommended_route ? (
              <article className="data-row">
                <span>recommended</span>
                <strong>{formatNumber(routeDistanceKm(recommendation.recommended_route), 1)} km · {formatNumber(routeDurationMinutes(recommendation.recommended_route), 1)} min</strong>
                <p>{candidateTruth(recommendation.recommended_route, "recommended_route").fallback_reason || "推荐结果已带来源，可用于订单管理页兼容校验。"}</p>
              </article>
            ) : null}
          </div>
          <TruthStrip
            truth={{
              data_source: recommendation?.data_source || "orders_or_shipment_facts",
              distance_source: recommendation?.recommended_route?.distance_source || "recommendation_contract",
              path_source: recommendation?.recommended_route?.path_source || "recommendation_contract",
              provider_status: normalizeStatus(recommendation?.provider_status, data.routeRecommendation.data?.success),
              fallback_reason: recommendation?.fallback_reason || data.routeRecommendation.error || data.routeRecommendation.data?.error,
              authenticity_level: "B/C-by-selected-source",
            }}
          />
        </Panel>

        <Panel title="Truth Boundary" action={<StatusPill status="degraded" label="mixed sources" />}>
          <div className="constraint-list">
            <article>
              <span>真实路网</span>
              <strong>高德和天地图结果可作为道路 provider 口径，但仍需要记录 key、网络、权限和缓存状态。</strong>
            </article>
            <article>
              <span>本地算法</span>
              <strong>本地图搜索适合解释、兜底和算法对照，不能伪装成真实道路距离。</strong>
            </article>
            <article>
              <span>下一步</span>
              <strong>继续做已认证真实 provider polyline 冒烟、节点/订单客户端 autocomplete，以及地图页完整迁移。</strong>
            </article>
          </div>
        </Panel>
      </section>
    </ConsoleShell>
  );
}
