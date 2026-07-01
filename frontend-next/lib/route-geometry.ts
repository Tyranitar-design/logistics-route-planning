import type { ProviderStatus, RouteCandidate, RouteNode } from "@/lib/types";

export interface Coordinate {
  lng: number;
  lat: number;
}

export interface RoutePreviewLayer {
  id: string;
  label: string;
  role: string;
  candidate?: RouteCandidate | null;
}

export interface DrawableLayer extends RoutePreviewLayer {
  coordinates: Coordinate[];
  color: string;
  dash?: string;
}

export interface ProjectedPoint {
  x: number;
  y: number;
}

export const LAYER_STYLES: Record<string, { color: string; dash?: string }> = {
  tianditu: { color: "#0f9f95" },
  amap: { color: "#2f6fed" },
  recommended: { color: "#b7791f", dash: "8 6" },
  local: { color: "#c2413d", dash: "5 5" },
};

export function asFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function coordinateFromArray(value: unknown): Coordinate | null {
  if (!Array.isArray(value) || value.length < 2) return null;
  const lng = asFiniteNumber(value[0]);
  const lat = asFiniteNumber(value[1]);
  return lng === null || lat === null ? null : { lng, lat };
}

function coordinateFromObject(value: unknown): Coordinate | null {
  if (!value || typeof value !== "object") return null;
  const point = value as Record<string, unknown>;
  const lng =
    asFiniteNumber(point.lng) ||
    asFiniteNumber(point.lon) ||
    asFiniteNumber(point.longitude) ||
    asFiniteNumber(point.x);
  const lat =
    asFiniteNumber(point.lat) ||
    asFiniteNumber(point.latitude) ||
    asFiniteNumber(point.y);
  return lng === null || lat === null ? null : { lng, lat };
}

function parsePolylineString(polyline: string): Coordinate[] {
  return polyline
    .split(";")
    .map((point) => coordinateFromArray(point.split(",")))
    .filter((point): point is Coordinate => Boolean(point));
}

export function parseCoordinateCollection(value: unknown): Coordinate[] {
  if (!value) return [];
  if (typeof value === "string") return parsePolylineString(value);
  if (!Array.isArray(value)) return [];
  return value
    .flatMap((item) => {
      if (typeof item === "string") return parsePolylineString(item);
      return coordinateFromArray(item) || coordinateFromObject(item) || [];
    })
    .filter((point): point is Coordinate => Boolean(point));
}

function coordinatesFromSteps(steps: unknown): Coordinate[] {
  if (!Array.isArray(steps)) return [];
  return steps.flatMap((step) => {
    if (!step || typeof step !== "object") return [];
    const item = step as Record<string, unknown>;
    return parseCoordinateCollection(item.polyline || item.points || item.path);
  });
}

export function coordinatesFromCandidate(candidate?: RouteCandidate | null): Coordinate[] {
  if (!candidate) return [];
  return [
    ...parseCoordinateCollection(candidate.polyline),
    ...coordinatesFromSteps(candidate.steps),
    ...parseCoordinateCollection(candidate.path),
  ];
}

export function coordinateFromNode(node?: RouteNode | null): Coordinate | null {
  const lng = asFiniteNumber(node?.longitude);
  const lat = asFiniteNumber(node?.latitude);
  return lng === null || lat === null ? null : { lng, lat };
}

export function buildDrawableLayers(layers: RoutePreviewLayer[]): DrawableLayer[] {
  return layers.map((layer) => {
    const style = LAYER_STYLES[layer.id] || { color: "#627386" };
    return {
      ...layer,
      ...style,
      coordinates: coordinatesFromCandidate(layer.candidate),
    };
  });
}

export function simplifyCoordinates(points: Coordinate[], maxPoints = 260): Coordinate[] {
  if (points.length <= maxPoints) return points;
  const step = Math.ceil(points.length / maxPoints);
  const simplified = points.filter((_, index) => index % step === 0);
  const last = points[points.length - 1];
  return simplified[simplified.length - 1] === last ? simplified : [...simplified, last];
}

export function routeDistanceKm(candidate?: RouteCandidate | null): number | null {
  if (typeof candidate?.distance_km === "number") return candidate.distance_km;
  if (typeof candidate?.distance === "number") {
    return candidate.distance > 1000 ? candidate.distance / 1000 : candidate.distance;
  }
  return null;
}

export function routeDurationMinutes(candidate?: RouteCandidate | null): number | null {
  if (typeof candidate?.duration_minutes === "number") return candidate.duration_minutes;
  if (typeof candidate?.duration === "number") {
    return candidate.duration > 10000 ? candidate.duration / 60 : candidate.duration;
  }
  return null;
}

export function normalizeCandidateStatus(candidate?: RouteCandidate | null): ProviderStatus {
  if (candidate?.provider_status) return candidate.provider_status;
  if (candidate?.success === true) return "ok";
  if (candidate?.success === false) return "failed";
  if (candidate) return "unknown";
  return "degraded";
}

export function createBounds(points: Coordinate[]) {
  const lngs = points.map((point) => point.lng);
  const lats = points.map((point) => point.lat);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  return {
    minLng,
    maxLng: minLng === maxLng ? maxLng + 0.01 : maxLng,
    minLat,
    maxLat: minLat === maxLat ? maxLat + 0.01 : maxLat,
  };
}

export function projectPoint(
  point: Coordinate,
  bounds: ReturnType<typeof createBounds>,
  width: number,
  height: number,
  padding: number,
): ProjectedPoint {
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const x = padding + ((point.lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * usableWidth;
  const y = padding + ((bounds.maxLat - point.lat) / (bounds.maxLat - bounds.minLat)) * usableHeight;
  return { x, y };
}

export function pathForCoordinates(
  points: Coordinate[],
  bounds: ReturnType<typeof createBounds>,
  width: number,
  height: number,
  padding: number,
): string {
  return simplifyCoordinates(points)
    .map((point, index) => {
      const projected = projectPoint(point, bounds, width, height, padding);
      return `${index === 0 ? "M" : "L"} ${projected.x.toFixed(1)} ${projected.y.toFixed(1)}`;
    })
    .join(" ");
}
