"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  buildDrawableLayers,
  coordinateFromNode,
  type Coordinate,
  type RoutePreviewLayer,
} from "@/lib/route-geometry";
import type { RouteNode } from "@/lib/types";

function geometryKey(
  layers: RoutePreviewLayer[],
  origin?: RouteNode | null,
  destination?: RouteNode | null,
): string {
  return JSON.stringify({
    origin: origin ? [origin.longitude, origin.latitude] : null,
    destination: destination ? [destination.longitude, destination.latitude] : null,
    layers: buildDrawableLayers(layers).map((layer) => ({
      id: layer.id,
      color: layer.color,
      dash: layer.dash,
      coordinates: layer.coordinates,
    })),
  });
}

function hasDrawableGeometry(layers: RoutePreviewLayer[], origin?: RouteNode | null, destination?: RouteNode | null): boolean {
  const originCoordinate = coordinateFromNode(origin);
  const destinationCoordinate = coordinateFromNode(destination);
  const drawableCount = buildDrawableLayers(layers).filter((layer) => layer.coordinates.length >= 2).length;
  return drawableCount > 0 || Boolean(originCoordinate && destinationCoordinate);
}

function coordinateLabel(point: Coordinate): string {
  return `${point.lng.toFixed(5)}, ${point.lat.toFixed(5)}`;
}

export function RouteLeafletMap({
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
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<"idle" | "ready" | "degraded">("idle");
  const [message, setMessage] = useState<string>(
    tileUrl ? "正在加载瓦片地图" : "未配置 NEXT_PUBLIC_ROUTE_TILE_URL，使用 SVG 几何预览。",
  );
  const key = useMemo(() => geometryKey(layers, origin, destination), [layers, origin, destination]);
  const drawable = useMemo(() => hasDrawableGeometry(layers, origin, destination), [layers, origin, destination]);

  useEffect(() => {
    if (!tileUrl) {
      setStatus("degraded");
      setMessage("未配置 NEXT_PUBLIC_ROUTE_TILE_URL，使用 SVG 几何预览。");
      return;
    }
    if (!drawable) {
      setStatus("degraded");
      setMessage("暂无可投影到瓦片底图的 provider polyline。");
      return;
    }

    const activeTileUrl = tileUrl;
    let disposed = false;
    let mapInstance: import("leaflet").Map | null = null;

    async function mountMap() {
      try {
        const Leaflet = await import("leaflet");
        if (disposed || !containerRef.current) return;

        const drawableLayers = buildDrawableLayers(layers);
        const originCoordinate = coordinateFromNode(origin);
        const destinationCoordinate = coordinateFromNode(destination);
        mapInstance = Leaflet.map(containerRef.current, {
          attributionControl: true,
          scrollWheelZoom: false,
          zoomControl: true,
        });

        Leaflet.tileLayer(activeTileUrl, {
          attribution: tileAttribution || "",
          maxZoom: 19,
        }).addTo(mapInstance);

        const bounds = Leaflet.latLngBounds([]);
        for (const layer of drawableLayers) {
          if (layer.coordinates.length < 2) continue;
          const latLngs = layer.coordinates.map((point) => [point.lat, point.lng] as [number, number]);
          Leaflet.polyline(latLngs, {
            color: layer.color,
            dashArray: layer.dash,
            opacity: 0.88,
            weight: 5,
          })
            .bindTooltip(layer.label)
            .addTo(mapInstance);
          for (const latLng of latLngs) {
            bounds.extend(latLng);
          }
        }

        if (originCoordinate) {
          Leaflet.circleMarker([originCoordinate.lat, originCoordinate.lng], {
            color: "#0f9f95",
            fillColor: "#ffffff",
            fillOpacity: 1,
            radius: 7,
            weight: 3,
          })
            .bindTooltip(`起点 ${coordinateLabel(originCoordinate)}`)
            .addTo(mapInstance);
          bounds.extend([originCoordinate.lat, originCoordinate.lng]);
        }

        if (destinationCoordinate) {
          Leaflet.circleMarker([destinationCoordinate.lat, destinationCoordinate.lng], {
            color: "#2f6fed",
            fillColor: "#ffffff",
            fillOpacity: 1,
            radius: 7,
            weight: 3,
          })
            .bindTooltip(`终点 ${coordinateLabel(destinationCoordinate)}`)
            .addTo(mapInstance);
          bounds.extend([destinationCoordinate.lat, destinationCoordinate.lng]);
        }

        if (bounds.isValid()) {
          mapInstance.fitBounds(bounds, { padding: [28, 28], maxZoom: 13 });
        }
        setStatus("ready");
        setMessage("瓦片底图已加载，路线来自 provider polyline。");
      } catch (error) {
        setStatus("degraded");
        setMessage(error instanceof Error ? error.message : "Leaflet 地图加载失败，使用 SVG 几何预览。");
      }
    }

    void mountMap();

    return () => {
      disposed = true;
      if (mapInstance) {
        mapInstance.remove();
      }
    };
  }, [drawable, key, layers, origin, destination, tileAttribution, tileUrl]);

  return (
    <div className={`route-leaflet-shell route-leaflet-${status}`}>
      <div ref={containerRef} className="route-leaflet-map" aria-label="Leaflet 瓦片地图路线预览" />
      <div className="route-leaflet-status">
        <strong>{status === "ready" ? "瓦片地图" : "瓦片降级"}</strong>
        <span>{message}</span>
      </div>
    </div>
  );
}
