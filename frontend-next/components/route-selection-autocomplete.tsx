"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  OrderSearchItem,
  RouteNode,
  RouteSuggestionKind,
  RouteSuggestionResponse,
} from "@/lib/types";

const SEARCH_DEBOUNCE_MS = 320;
const MAX_QUERY_LENGTH = 80;

type SearchStatus = "idle" | "loading" | "ready" | "error";

export interface RouteSelectionState {
  originId?: number | null;
  destinationId?: number | null;
  waypointIds?: number[] | null;
  orderId?: number | null;
  preferSource?: string | null;
  strategy?: string | null;
  nodeQuery?: string | null;
  orderQuery?: string | null;
}

interface SuggestionState {
  status: SearchStatus;
  nodes: RouteNode[];
  orders: OrderSearchItem[];
  total: number;
  dataSource?: string | null;
  error?: string | null;
}

interface AutocompleteBoxProps {
  kind: RouteSuggestionKind;
  title: string;
  placeholder: string;
  initialQuery?: string | null;
  selection: RouteSelectionState;
  targetPath: string;
}

function compactQuery(value?: string | null): string {
  return value?.trim().slice(0, MAX_QUERY_LENGTH) || "";
}

function numericValue(value?: string | number | null): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.trunc(parsed);
}

function waypointQuery(value?: number[] | null): string | null {
  const ids = Array.from(new Set((value || []).filter((item) => Number.isFinite(item) && item > 0)));
  return ids.length ? ids.join(",") : null;
}

function addWaypoint(selection: RouteSelectionState, nodeId?: number | null): number[] {
  if (!nodeId) return selection.waypointIds || [];
  const blocked = new Set([selection.originId, selection.destinationId].filter(Boolean));
  if (blocked.has(nodeId)) return selection.waypointIds || [];
  return Array.from(new Set([...(selection.waypointIds || []), nodeId])).slice(0, 6);
}

function selectionHref(
  selection: RouteSelectionState,
  targetPath: string,
  overrides: Partial<RouteSelectionState> = {},
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

  return `${targetPath}${search.size ? `?${search.toString()}` : ""}`;
}

function emptySuggestionState(status: SearchStatus = "idle"): SuggestionState {
  return {
    status,
    nodes: [],
    orders: [],
    total: 0,
  };
}

function nodeDisplayName(node: RouteNode): string {
  return String(node.node_name || node.name || node.id || "unknown node");
}

function nodeSubLabel(node: RouteNode): string {
  return (
    [node.province, node.city, node.district].filter(Boolean).join(" / ") ||
    node.address ||
    node.type ||
    "node location unknown"
  );
}

function nodeCoordinateLabel(node: RouteNode): string {
  if (typeof node.longitude === "number" && typeof node.latitude === "number") {
    return `${node.longitude.toFixed(4)}, ${node.latitude.toFixed(4)}`;
  }
  return "missing coordinates";
}

function orderDisplayName(order: OrderSearchItem): string {
  return String(order.order_number || order.external_order_id || order.external_shipment_id || order.id || "unknown order");
}

function orderSubLabel(order: OrderSearchItem): string {
  return `${order.origin_name || order.origin_address || "origin"} -> ${order.destination_name || order.destination_address || "destination"}`;
}

function queryEndpoint(kind: RouteSuggestionKind, query: string): string {
  const search = new URLSearchParams();
  search.set("kind", kind);
  search.set("q", query);
  return `/api/route-compare/suggestions?${search.toString()}`;
}

async function fetchSuggestions(
  kind: RouteSuggestionKind,
  query: string,
  signal: AbortSignal,
): Promise<SuggestionState> {
  const response = await fetch(queryEndpoint(kind, query), {
    cache: "no-store",
    credentials: "same-origin",
    signal,
  });
  const payload = (await response.json().catch(() => null)) as RouteSuggestionResponse | null;

  if (!response.ok || !payload?.success) {
    return {
      ...emptySuggestionState("error"),
      dataSource: payload?.data_source,
      error: payload?.error || `HTTP_${response.status}`,
    };
  }

  return {
    status: "ready",
    nodes: payload.nodes || [],
    orders: payload.orders || [],
    total: payload.total || 0,
    dataSource: payload.data_source,
  };
}

function NodeSuggestions({
  nodes,
  selection,
  targetPath,
}: {
  nodes: RouteNode[];
  selection: RouteSelectionState;
  targetPath: string;
}) {
  if (!nodes.length) return null;

  return (
    <div className="route-autocomplete-results" role="list" aria-label="节点自动补全结果">
      {nodes.map((node) => (
        <article className="route-autocomplete-row" key={`ac-node-${node.id}`} role="listitem">
          <div>
            <span>{nodeDisplayName(node)}</span>
            <strong>{nodeSubLabel(node)}</strong>
            <p>{nodeCoordinateLabel(node)} · {node.status || node.type || "status unknown"}</p>
          </div>
          <div className="route-picker-actions">
            <a href={selectionHref(selection, targetPath, { originId: numericValue(node.id), orderId: null })}>起点</a>
            <a href={selectionHref(selection, targetPath, { destinationId: numericValue(node.id), orderId: null })}>终点</a>
            <a href={selectionHref(selection, targetPath, { waypointIds: addWaypoint(selection, numericValue(node.id)), orderId: null })}>途经</a>
          </div>
        </article>
      ))}
    </div>
  );
}

function OrderSuggestions({
  orders,
  selection,
  targetPath,
}: {
  orders: OrderSearchItem[];
  selection: RouteSelectionState;
  targetPath: string;
}) {
  if (!orders.length) return null;

  return (
    <div className="route-autocomplete-results" role="list" aria-label="订单自动补全结果">
      {orders.map((order) => (
        <article className="route-autocomplete-row" key={`ac-order-${order.id}`} role="listitem">
          <div>
            <span>{orderDisplayName(order)}</span>
            <strong>{orderSubLabel(order)}</strong>
            <p>{order.data_source || "order"} · {order.status || "status unknown"} · {order.weight ?? "-"} kg</p>
          </div>
          <div className="route-picker-actions">
            <a
              href={selectionHref(selection, targetPath, {
                originId: null,
                destinationId: null,
                orderId: numericValue(order.id),
                orderQuery: orderDisplayName(order),
              })}
            >
              使用
            </a>
          </div>
        </article>
      ))}
    </div>
  );
}

function AutocompleteBox({
  kind,
  title,
  placeholder,
  initialQuery,
  selection,
  targetPath,
}: AutocompleteBoxProps) {
  const [query, setQuery] = useState(() => compactQuery(initialQuery));
  const [suggestions, setSuggestions] = useState<SuggestionState>(() => emptySuggestionState());
  const normalizedQuery = useMemo(() => compactQuery(query), [query]);

  useEffect(() => {
    if (!normalizedQuery) {
      setSuggestions(emptySuggestionState());
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      setSuggestions((current) => ({
        ...current,
        status: "loading",
        error: null,
      }));
      fetchSuggestions(kind, normalizedQuery, controller.signal)
        .then(setSuggestions)
        .catch((error: unknown) => {
          if (controller.signal.aborted) return;
          setSuggestions({
            ...emptySuggestionState("error"),
            error: error instanceof Error ? error.message : "建议搜索失败",
          });
        });
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [kind, normalizedQuery]);

  const countLabel = suggestions.status === "ready"
    ? `${suggestions.total} total`
    : suggestions.status;

  return (
    <section className="route-autocomplete-card">
      <div className="route-picker-head">
        <strong>{title}</strong>
        <span>{suggestions.dataSource || countLabel}</span>
      </div>
      <label className="route-autocomplete-input">
        <span>{kind === "node" ? "节点关键词" : "订单关键词"}</span>
        <input
          aria-label={title}
          type="search"
          value={query}
          placeholder={placeholder}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {suggestions.status === "loading" ? (
        <p className="route-autocomplete-note">正在查询真实 PostgreSQL 数据...</p>
      ) : null}
      {suggestions.status === "error" ? (
        <p className="route-autocomplete-error">{suggestions.error || "建议搜索失败"}</p>
      ) : null}
      {suggestions.status === "ready" && !suggestions.nodes.length && !suggestions.orders.length ? (
        <p className="route-autocomplete-note">没有匹配候选，可换一个城市、节点名、订单号或运单号。</p>
      ) : null}
      {kind === "node" ? (
        <NodeSuggestions
          nodes={suggestions.nodes}
          selection={{ ...selection, nodeQuery: normalizedQuery }}
          targetPath={targetPath}
        />
      ) : (
        <OrderSuggestions
          orders={suggestions.orders}
          selection={{ ...selection, orderQuery: normalizedQuery }}
          targetPath={targetPath}
        />
      )}
    </section>
  );
}

export function RouteSelectionAutocomplete({
  selection,
  targetPath = "/route-compare",
}: {
  selection: RouteSelectionState;
  targetPath?: string;
}) {
  return (
    <div className="route-autocomplete-grid">
      <AutocompleteBox
        kind="node"
        title="节点自动补全"
        placeholder="广州 / 上海仓 / 节点名"
        initialQuery={selection.nodeQuery}
        selection={selection}
        targetPath={targetPath}
      />
      <AutocompleteBox
        kind="order"
        title="订单自动补全"
        placeholder="35692 / 运单号 / 客户"
        initialQuery={selection.orderQuery}
        selection={selection}
        targetPath={targetPath}
      />
    </div>
  );
}
