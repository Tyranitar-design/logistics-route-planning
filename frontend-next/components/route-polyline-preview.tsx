import { RouteLeafletMap } from "@/components/route-leaflet-map";
import { StatusPill, TruthStrip } from "@/components/status-pill";
import { compactText, formatNumber } from "@/lib/format";
import {
  buildDrawableLayers,
  coordinateFromNode,
  createBounds,
  normalizeCandidateStatus,
  pathForCoordinates,
  projectPoint,
  routeDistanceKm,
  routeDurationMinutes,
  type RoutePreviewLayer,
} from "@/lib/route-geometry";
import type { RouteCandidate, RouteNode } from "@/lib/types";

export type { RoutePreviewLayer } from "@/lib/route-geometry";

function sourceLabel(candidate?: RouteCandidate | null, fallback = "not_reported"): string {
  return compactText(
    candidate?.path_source ||
      candidate?.distance_source ||
      candidate?.provider ||
      candidate?.source ||
      candidate?.algorithm ||
      fallback,
  );
}

export function RoutePolylinePreview({
  layers,
  origin,
  destination,
  tileUrl,
  tileAttribution,
}: {
  layers: RoutePreviewLayer[];
  origin?: RouteNode | null;
  destination?: RouteNode | null;
  tileUrl?: string | null;
  tileAttribution?: string | null;
}) {
  const originCoordinate = coordinateFromNode(origin);
  const destinationCoordinate = coordinateFromNode(destination);
  const drawableLayers = buildDrawableLayers(layers);
  const drawnLayers = drawableLayers.filter((layer) => layer.coordinates.length >= 2);
  const allPoints = [
    ...drawnLayers.flatMap((layer) => layer.coordinates),
    ...(originCoordinate ? [originCoordinate] : []),
    ...(destinationCoordinate ? [destinationCoordinate] : []),
  ];
  const hasMapGeometry = allPoints.length >= 2;
  const bounds = hasMapGeometry ? createBounds(allPoints) : null;
  const width = 960;
  const height = 360;
  const padding = 34;

  return (
    <div className="route-map-preview">
      <RouteLeafletMap
        destination={destination}
        layers={layers}
        origin={origin}
        tileAttribution={tileAttribution}
        tileUrl={tileUrl}
      />

      <div className="route-map-canvas" aria-label="provider polyline 坐标预览">
        {bounds ? (
          <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="路线 provider polyline 预览">
            <defs>
              <pattern id="route-grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" />
              </pattern>
            </defs>
            <rect className="route-map-grid" x="0" y="0" width={width} height={height} />
            {drawnLayers.map((layer) => (
              <path
                className="route-map-path"
                d={pathForCoordinates(layer.coordinates, bounds, width, height, padding)}
                key={layer.id}
                stroke={layer.color}
                strokeDasharray={layer.dash}
              />
            ))}
            {originCoordinate ? (
              <circle
                className="route-map-marker route-map-marker-origin"
                cx={projectPoint(originCoordinate, bounds, width, height, padding).x}
                cy={projectPoint(originCoordinate, bounds, width, height, padding).y}
                r="7"
              />
            ) : null}
            {destinationCoordinate ? (
              <circle
                className="route-map-marker route-map-marker-destination"
                cx={projectPoint(destinationCoordinate, bounds, width, height, padding).x}
                cy={projectPoint(destinationCoordinate, bounds, width, height, padding).y}
                r="7"
              />
            ) : null}
          </svg>
        ) : (
          <div className="route-map-empty">
            <strong>暂无可绘制 polyline</strong>
            <span>provider 未返回坐标序列，或当前接口处于未登录/降级状态。</span>
          </div>
        )}
      </div>

      <div className="route-map-legend">
        {drawableLayers.map((layer) => (
          <article className="route-map-legend-row" key={layer.id}>
            <span className="route-map-swatch" style={{ backgroundColor: layer.color }} />
            <div>
              <strong>{layer.label}</strong>
              <p>
                {layer.role} · {sourceLabel(layer.candidate, layer.id)} · {formatNumber(layer.coordinates.length)} points
              </p>
            </div>
            <span>{formatNumber(routeDistanceKm(layer.candidate), 1)} km</span>
            <span>{formatNumber(routeDurationMinutes(layer.candidate), 1)} min</span>
            <StatusPill status={normalizeCandidateStatus(layer.candidate)} label={compactText(normalizeCandidateStatus(layer.candidate))} />
          </article>
        ))}
      </div>

      <TruthStrip
        truth={{
          data_source: "nodes_and_route_providers",
          distance_source: drawnLayers.map((layer) => sourceLabel(layer.candidate, layer.id)).join(" / ") || "not_drawable",
          path_source: tileUrl ? "leaflet_tile_layer_plus_provider_polyline" : "provider_polyline_coordinate_preview",
          provider_status: drawnLayers.length ? "ok" : "degraded",
          fallback_reason: drawnLayers.length ? undefined : "NO_DRAWABLE_POLYLINE",
          authenticity_level: drawnLayers.some((layer) => ["amap", "tianditu"].includes(layer.id))
            ? "B-provider-polyline-preview"
            : "C-local-or-empty-preview",
        }}
      />
      <p className="panel-note">
        上方瓦片地图仅在配置 `NEXT_PUBLIC_ROUTE_TILE_URL` 后加载；下方 SVG 始终绘制 provider polyline 坐标序列，便于在无瓦片或 provider 降级时核对路线几何和来源。
      </p>
    </div>
  );
}
