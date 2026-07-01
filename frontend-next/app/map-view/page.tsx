import Link from "next/link";
import { ConsoleShell } from "@/components/console-shell";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { Panel } from "@/components/panel";
import { RouteAlgorithmBenchmark } from "@/components/route-algorithm-benchmark";
import { RoutePolylinePreview } from "@/components/route-polyline-preview";
import { RouteSequenceBenchmarkPanel } from "@/components/route-sequence-benchmark";
import { RouteSelectionAutocomplete } from "@/components/route-selection-autocomplete";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { getMapViewPageData, type RouteCompareInput } from "@/lib/api";
import { compactText, formatNumber } from "@/lib/format";
import type {
  MapProviderComponent,
  OrderSearchItem,
  ProviderStatus,
  RemoteResult,
  RouteCandidate,
  RouteNode,
  TruthMetadata,
} from "@/lib/types";

export const dynamic = "force-dynamic";

type MapViewSearchParams = Record<string, string | string[] | undefined>;

interface MapViewPageProps {
  searchParams?: Promise<MapViewSearchParams>;
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

function numericValue(value?: string | number | null): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.trunc(parsed);
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

function parseMapViewInput(params: MapViewSearchParams): RouteCompareInput {
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

function selectionHref(
  path: string,
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

  return `${path}${search.size ? `?${search.toString()}` : ""}`;
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

function componentStatus(component?: MapProviderComponent | null): ProviderStatus {
  return normalizeStatus(component?.provider_status, component?.success);
}

function resultStatus<T extends { success?: boolean; provider_status?: ProviderStatus | null }>(
  result: RemoteResult<T>,
): ProviderStatus {
  if (!result.ok) return "degraded";
  return normalizeStatus(result.data?.provider_status, result.data?.success);
}

function distanceSourceStatus(source?: string | null): ProviderStatus {
  if (source === "amap" || source === "cache") return "ok";
  if (source === "haversine_corrected" || source === "local_graph") return "degraded";
  return "unknown";
}

function booleanLabel(value?: boolean | null): string {
  if (value === true) return "yes";
  if (value === false) return "no";
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

function candidateTruth(candidate?: RouteCandidate | null, fallbackSource = "map_route"): TruthMetadata {
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

function componentTruth(
  name: string,
  component?: MapProviderComponent | null,
  fallbackReason?: string,
): TruthMetadata {
  return {
    data_source: "backend_provider_proxy",
    distance_source: component?.distance_source || component?.provider || name,
    path_source: `${name}_probe`,
    provider_status: componentStatus(component),
    fallback_reason: component?.fallback_reason || component?.error || fallbackReason,
    authenticity_level: componentStatus(component) === "ok" ? "B-provider-diagnostic" : "C-provider-degraded",
  };
}

function orderDisplayName(order: OrderSearchItem): string {
  return compactText(
    order.order_number || order.external_order_id || order.external_shipment_id || order.id,
    "unknown order",
  );
}

function orderLane(order: OrderSearchItem): string {
  return compactText(
    `${order.origin_name || order.origin_address || "origin"} -> ${
      order.destination_name || order.destination_address || "destination"
    }`,
    "unknown lane",
  );
}

function nodeDisplayName(node: RouteNode): string {
  return compactText(node.node_name || node.name || node.id, "unknown node");
}

function nodeLocation(node: RouteNode): string {
  return compactText(
    [node.province, node.city, node.district].filter(Boolean).join(" / ") ||
      node.address ||
      node.type ||
      "unknown location",
  );
}

export default async function MapViewPage({ searchParams }: MapViewPageProps) {
  const params = searchParams ? await searchParams : {};
  const selection = parseMapViewInput(params);
  const data = await getMapViewPageData(selection);
  const amapRoute = data.amapHealth.data?.components?.route;
  const amapWeather = data.amapHealth.data?.components?.weather;
  const amapTraffic = data.amapHealth.data?.components?.traffic;
  const cacheStats = data.amapDistanceCacheStats.data?.data;
  const distanceValidation = data.amapDistanceValidation.data?.data;
  const distanceInfo = distanceValidation?.distance;
  const distanceCache = distanceValidation?.cache;
  const distanceStatus = distanceSourceStatus(distanceInfo?.source);
  const routeTileUrl = process.env.NEXT_PUBLIC_ROUTE_TILE_URL || null;
  const routeTileAttribution = process.env.NEXT_PUBLIC_ROUTE_TILE_ATTRIBUTION || null;
  const tileConfigured = Boolean(routeTileUrl);
  const recommendation = data.routeRecommendation.data?.data;
  const amapCandidate =
    data.amapLocalCompare.data?.amap ||
    data.tiandituAmapCompare.data?.amap ||
    recommendation?.amap_route ||
    null;
  const localCandidate = data.amapLocalCompare.data?.local || recommendation?.local_route || null;
  const tiandituCandidate = data.tiandituAmapCompare.data?.tianditu || null;
  const roadCandidate = amapCandidate || tiandituCandidate;
  const recommendedCandidate = recommendation?.recommended_route || null;
  const origin = data.amapLocalCompare.data?.origin || recommendation?.origin || null;
  const destination = data.amapLocalCompare.data?.destination || recommendation?.destination || null;
  const displayedOriginId = origin?.id || selection.originId || 1;
  const displayedDestinationId = destination?.id || selection.destinationId || 2;
  const displayedOrderId = recommendation?.order_id || selection.orderId || "35692";
  const nodes = data.nodeInventory.data?.nodes || [];
  const orders = data.orderSample.data?.orders || [];
  const routeLayers = [
    { id: "tianditu", label: "天地图", role: "真实路网", candidate: tiandituCandidate },
    { id: "amap", label: "高德地图", role: "真实路网", candidate: amapCandidate },
    { id: "local", label: "本地图算法", role: "可解释/降级", candidate: localCandidate },
    { id: "recommended", label: "推荐结果", role: "订单推荐", candidate: recommendedCandidate },
  ];

  return (
    <ConsoleShell
      activePath="/map-view"
      apiBaseUrl={data.apiBaseUrl}
      generatedAt={data.generatedAt}
      eyebrow="地图视图"
      title="地图服务、真实路网与本地算法运行台"
    >
      <section className="metric-grid" aria-label="地图视图关键指标">
        <MetricCard
          label="高德路线"
          value={compactText(componentStatus(amapRoute))}
          helper={amapRoute?.fallback_reason || data.amapHealth.error || "route provider probe"}
          tone={componentStatus(amapRoute) === "ok" ? "good" : "warn"}
        />
        <MetricCard
          label="天气服务"
          value={compactText(componentStatus(amapWeather))}
          helper={amapWeather?.fallback_reason || "weather provider probe"}
          tone={componentStatus(amapWeather) === "ok" ? "good" : "warn"}
        />
        <MetricCard
          label="交通服务"
          value={compactText(componentStatus(amapTraffic))}
          helper={amapTraffic?.fallback_reason || "traffic provider probe"}
          tone={componentStatus(amapTraffic) === "ok" ? "good" : "warn"}
        />
        <MetricCard
          label="当前 OD 距离"
          value={`${formatNumber(distanceInfo?.distance_km, 2)} km`}
          helper={distanceInfo?.source || data.amapDistanceValidation.error || "distance validate"}
          tone={distanceStatus === "ok" ? "good" : "warn"}
        />
      </section>

      <section className="dashboard-grid">
        <Panel title="Map Provider Matrix" action={<DataState result={data.amapHealth} />}>
          <div className="provider-line">
            <span>amap route</span>
            <StatusPill status={componentStatus(amapRoute)} label={amapRoute?.provider_status || "unknown"} />
            <strong>{amapRoute?.fallback_reason || `${formatNumber(amapRoute?.distance_km, 2)} km probe`}</strong>
          </div>
          <div className="provider-line">
            <span>amap weather</span>
            <StatusPill status={componentStatus(amapWeather)} label={amapWeather?.provider_status || "unknown"} />
            <strong>{amapWeather?.fallback_reason || "weather probe ok"}</strong>
          </div>
          <div className="provider-line">
            <span>amap traffic</span>
            <StatusPill status={componentStatus(amapTraffic)} label={amapTraffic?.provider_status || "unknown"} />
            <strong>{amapTraffic?.fallback_reason || "traffic probe ok"}</strong>
          </div>
          <div className="provider-line">
            <span>tianditu</span>
            <StatusPill status={resultStatus(data.tiandituKeys)} label={data.tiandituKeys.data?.provider_status || data.tiandituKeys.error || "unknown"} />
            <strong>
              server {data.tiandituKeys.data?.server_key_configured ? "configured" : "missing"} / browser{" "}
              {data.tiandituKeys.data?.browser_key_configured ? "configured" : "missing"}
            </strong>
          </div>
          <TruthStrip truth={componentTruth("route", amapRoute, data.amapHealth.error)} />
        </Panel>

        <Panel title="Distance Cache Readiness" action={<DataState result={data.amapDistanceCacheStats} />}>
          <div className="diagnostic-grid">
            <article>
              <span>缓存条目</span>
              <strong>{formatNumber(cacheStats?.total_entries)}</strong>
              <p>distance cache totals</p>
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
              <span>过期条目</span>
              <strong>{formatNumber(cacheStats?.expired)}</strong>
              <p>需要重算或清理</p>
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
              after {booleanLabel(distanceCache?.exists_after_call)} / cached source{" "}
              {distanceCache?.cached_source || "not cached"}
            </strong>
          </div>
          <TruthStrip
            truth={{
              data_source: "amap_distance_cache",
              distance_source: distanceInfo?.source || "distance_validate_unavailable",
              path_source: "distance_validate_sample_od",
              provider_status: distanceStatus,
              fallback_reason: distanceValidation?.fallback_reason || data.amapDistanceValidation.error,
              authenticity_level:
                distanceInfo?.source === "amap" || distanceInfo?.source === "cache"
                  ? "B-real-distance-diagnostic"
                  : "C-distance-fallback-diagnostic",
            }}
          />
        </Panel>

        <Panel title="Map Workspace Preview" action={<StatusPill status={tileConfigured ? "ok" : "degraded"} label={tileConfigured ? "tile configured" : "svg fallback"} />} className="route-map-panel">
          <div className="map-workspace-canvas" aria-label="地图视图状态概览">
            <div className="map-layer-card map-layer-card-primary">
              <span>路网 provider</span>
              <strong>{componentStatus(amapRoute) === "ok" ? "真实路线可用" : "真实路线降级"}</strong>
              <p>{amapRoute?.fallback_reason || "AMap route probe controls the production route provider state."}</p>
            </div>
            <div className="map-layer-card">
              <span>瓦片底图</span>
              <strong>{tileConfigured ? "Leaflet tile enabled" : "SVG geometry fallback"}</strong>
              <p>{tileConfigured ? "浏览器安全瓦片 URL 已配置。" : "未配置 NEXT_PUBLIC_ROUTE_TILE_URL，暂不加载浏览器瓦片。"}</p>
            </div>
            <div className="map-layer-card">
              <span>天气/路况</span>
              <strong>{componentStatus(amapWeather)} / {componentStatus(amapTraffic)}</strong>
              <p>路况权限缺失时只降级 traffic，不影响路线和天气。</p>
            </div>
          </div>
          <div className="map-action-grid">
            <Link
              className="map-action-link"
              href={selectionHref("/route-compare", {
                ...selection,
                originId: numericValue(displayedOriginId),
                destinationId: numericValue(displayedDestinationId),
              })}
            >
              送去高级路径对比
            </Link>
            <Link
              className="map-action-link"
              href={selectionHref("/map-view", {
                ...selection,
                originId: null,
                destinationId: null,
                orderId: numericValue(displayedOrderId) || 35692,
                orderQuery: String(displayedOrderId || "35692"),
              })}
            >
              刷新当前订单路线
            </Link>
            <Link className="map-action-link" href="/network-design">
              查看真实 OD 网络设计
            </Link>
          </div>
        </Panel>

        <Panel
          title="Map Selection Console"
          action={<StatusPill status={selection.orderId || selection.originId || selection.destinationId ? "ok" : "degraded"} label={`OD ${displayedOriginId} → ${displayedDestinationId}`} />}
          className="route-map-panel"
        >
          <div className="summary-strip">
            <div>
              <span>origin</span>
              <strong>{compactText(origin?.node_name || origin?.name || displayedOriginId)}</strong>
            </div>
            <div>
              <span>destination</span>
              <strong>{compactText(destination?.node_name || destination?.name || displayedDestinationId)}</strong>
            </div>
            <div>
              <span>order</span>
              <strong>{compactText(recommendation?.order_number || displayedOrderId)}</strong>
            </div>
          </div>
          <form className="route-filter-form" action="/map-view">
            <label>
              <span>起点 Node ID</span>
              <input
                defaultValue={selection.originId || ""}
                inputMode="numeric"
                min="1"
                name="origin_id"
                placeholder={String(displayedOriginId)}
                type="number"
              />
            </label>
            <label>
              <span>终点 Node ID</span>
              <input
                defaultValue={selection.destinationId || ""}
                inputMode="numeric"
                min="1"
                name="destination_id"
                placeholder={String(displayedDestinationId)}
                type="number"
              />
            </label>
            <label>
              <span>订单 ID</span>
              <input
                defaultValue={selection.orderId || ""}
                inputMode="numeric"
                min="1"
                name="order_id"
                placeholder="35692"
                type="number"
              />
            </label>
            <label>
              <span>途经 Node IDs</span>
              <input
                defaultValue={waypointQuery(selection.waypointIds)}
                name="waypoint_ids"
                placeholder="2,3,4"
                type="text"
              />
            </label>
            <label>
              <span>推荐偏好</span>
              <select defaultValue={selection.preferSource || "auto"} name="prefer_source">
                <option value="auto">auto</option>
                <option value="amap">amap</option>
                <option value="local">local</option>
              </select>
            </label>
            <label>
              <span>天地图策略</span>
              <select defaultValue={selection.strategy || "0"} name="strategy">
                <option value="0">0 default</option>
                <option value="1">1 avoid jam</option>
                <option value="2">2 shortest</option>
                <option value="3">3 no highway</option>
              </select>
            </label>
            <div className="route-filter-actions">
              <button className="command-button" type="submit">刷新地图</button>
              <Link className="route-reset-link" href="/map-view">重置</Link>
            </div>
          </form>

          <div className="map-selection-autocomplete">
            <RouteSelectionAutocomplete selection={selection} targetPath="/map-view" />
          </div>

          <div className="route-search-grid">
            <form className="route-search-card" action="/map-view">
              {hiddenSelectionInputs(selection, ["node_query"])}
              <label>
                <span>节点关键词</span>
                <input
                  defaultValue={compactQuery(selection.nodeQuery)}
                  name="node_query"
                  placeholder="城市 / 仓 / 节点名"
                  type="search"
                />
              </label>
              <button className="command-button" type="submit">查节点</button>
            </form>
            <form className="route-search-card" action="/map-view">
              {hiddenSelectionInputs(selection, ["order_query"])}
              <label>
                <span>订单搜索</span>
                <input
                  defaultValue={compactQuery(selection.orderQuery)}
                  name="order_query"
                  placeholder="订单号 / 运单号 / 客户"
                  type="search"
                />
              </label>
              <button className="command-button" type="submit">查订单</button>
            </form>
          </div>
          <p className="panel-note">
            地图页现在可直接选择 Node 或订单作为运行对象；途经 Node IDs 会进入路线序列求解器 benchmark。自动补全仍通过同源 Next BFF 访问 Flask，浏览器脚本不会接触后端 token。
          </p>
        </Panel>

        <Panel title="Provider Polyline Preview" action={<StatusPill status={amapCandidate || tiandituCandidate ? "ok" : "degraded"} label="geometry" />} className="route-map-panel">
          <RoutePolylinePreview
            destination={destination}
            layers={routeLayers}
            origin={origin}
            tileAttribution={routeTileAttribution}
            tileUrl={routeTileUrl}
          />
        </Panel>

        <Panel title="Route Result Snapshot" action={<DataState result={data.amapLocalCompare.ok ? data.amapLocalCompare : data.tiandituAmapCompare} />}>
          <div className="solver-table" role="table" aria-label="地图页路线结果快照">
            <div className="solver-head route-head" role="row">
              <span>source</span>
              <span>distance</span>
              <span>duration</span>
              <span>status</span>
            </div>
            {routeLayers.map((layer) => (
              <div className="solver-row route-row" role="row" key={layer.id}>
                <span>{layer.label} · {layer.role}</span>
                <span>{formatNumber(routeDistanceKm(layer.candidate), 1)} km</span>
                <span>{formatNumber(routeDurationMinutes(layer.candidate), 1)} min</span>
                <StatusPill
                  status={candidateTruth(layer.candidate, layer.id).provider_status}
                  label={layer.candidate?.success === false ? "failed" : candidateTruth(layer.candidate, layer.id).provider_status || "unknown"}
                />
              </div>
            ))}
          </div>
          <p className="panel-note">
            地图页只展示样例 OD 和订单推荐的运行状态，正式路径选择仍进入高级路径对比页做策略切换和候选确认。
          </p>
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

        <Panel title="Node Inventory" action={<DataState result={data.nodeInventory} />}>
          <div className="data-list">
            {nodes.slice(0, 6).map((node) => (
              <article className="data-row map-data-row" key={`node-${node.id}`}>
                <span>{nodeDisplayName(node)}</span>
                <strong>{nodeLocation(node)}</strong>
                <p>
                  id {compactText(node.id)} · {compactText(node.status || node.type, "status unknown")} ·{" "}
                  {formatNumber(node.longitude as number | null, 4)}, {formatNumber(node.latitude as number | null, 4)}
                </p>
                <div className="route-picker-actions">
                  <Link
                    href={selectionHref("/map-view", {
                      ...selection,
                      originId: numericValue(node.id),
                      orderId: null,
                    })}
                  >
                    设为起点
                  </Link>
                  <Link
                    href={selectionHref("/map-view", {
                      ...selection,
                      destinationId: numericValue(node.id),
                      orderId: null,
                    })}
                  >
                    设为终点
                  </Link>
                  <Link
                    href={selectionHref("/map-view", {
                      ...selection,
                      waypointIds: addWaypoint(selection, numericValue(node.id)),
                      orderId: null,
                    })}
                  >
                    设为途经
                  </Link>
                </div>
              </article>
            ))}
            {!nodes.length ? (
              <p className="empty-note">{data.nodeInventory.error || data.nodeInventory.data?.error || "暂无节点样本，登录后读取 PostgreSQL nodes。"}</p>
            ) : null}
          </div>
          <TruthStrip
            truth={{
              data_source: "nodes",
              distance_source: "not_applicable",
              path_source: "node_inventory_for_map",
              provider_status: data.nodeInventory.ok ? "ok" : "degraded",
              fallback_reason: data.nodeInventory.error || data.nodeInventory.data?.error,
              authenticity_level: "B-real-operating-nodes",
            }}
          />
        </Panel>

        <Panel title="Order Route Contract" action={<DataState result={data.routeRecommendation} />}>
          <div className="data-list">
            <article className="data-row">
              <span>{recommendation?.order_number || `order ${displayedOrderId}`}</span>
              <strong>{recommendation?.recommendation_reason || data.routeRecommendation.data?.error || data.routeRecommendation.error || "等待订单路线推荐。"}</strong>
              <p>{recommendation?.data_source || "orders_or_shipment_facts"} · {recommendation?.provider_status || "provider unknown"}</p>
            </article>
            {orders.slice(0, 4).map((order) => (
              <article className="data-row map-data-row" key={`order-${order.id}`}>
                <span>{orderDisplayName(order)}</span>
                <strong>{orderLane(order)}</strong>
                <p>{order.data_source || data.orderSample.data?.data_source || "order"} · {order.status || "status unknown"} · {formatNumber(order.weight, 1)} kg</p>
                <div className="route-picker-actions">
                  <Link
                    href={selectionHref("/map-view", {
                      ...selection,
                      originId: null,
                      destinationId: null,
                      orderId: numericValue(order.id),
                      orderQuery: orderDisplayName(order),
                    })}
                  >
                    使用订单
                  </Link>
                </div>
              </article>
            ))}
          </div>
          <TruthStrip
            truth={{
              data_source: recommendation?.data_source || data.orderSample.data?.data_source || "orders_or_shipment_facts",
              distance_source: recommendation?.recommended_route?.distance_source || "recommendation_contract",
              path_source: recommendation?.recommended_route?.path_source || "recommendation_contract",
              provider_status: normalizeStatus(recommendation?.provider_status, data.routeRecommendation.data?.success),
              fallback_reason: recommendation?.fallback_reason || data.routeRecommendation.error || data.routeRecommendation.data?.error,
              authenticity_level: "B/C-by-selected-route-provider",
            }}
          />
        </Panel>

        <Panel title="Truth Boundary" action={<StatusPill status="degraded" label="mixed map sources" />}>
          <div className="constraint-list">
            <article>
              <span>真实地图</span>
              <strong>高德和天地图只通过后端代理进入页面，前端不读取服务器端 key，也不展示缓存数据库路径。</strong>
            </article>
            <article>
              <span>本地算法</span>
              <strong>本地图算法用于解释、降级和算法对照，不能与真实道路 provider 混成同一真实性等级。</strong>
            </article>
            <article>
              <span>后续增强</span>
              <strong>继续补地图页交互式节点选择、已认证真实 polyline 冒烟、浏览器安全瓦片配置和本地算法对比指标。</strong>
            </article>
          </div>
        </Panel>
      </section>
    </ConsoleShell>
  );
}
