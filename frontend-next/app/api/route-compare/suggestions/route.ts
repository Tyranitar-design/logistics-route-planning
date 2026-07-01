import { NextResponse } from "next/server";
import { getAccessTokenCookie, setAuthCookies } from "@/lib/auth";
import { fetchFlaskApi, upstreamError } from "@/lib/server-api";
import { refreshAccessTokenFromCookie } from "@/lib/token-refresh";
import type {
  NodeSearchResult,
  OrderSearchItem,
  OrderSearchResult,
  RouteNode,
  RouteSuggestionKind,
  RouteSuggestionResponse,
} from "@/lib/types";

export const dynamic = "force-dynamic";

const MAX_QUERY_LENGTH = 80;
const NODE_LIMIT = 8;
const ORDER_LIMIT = 6;

type SuggestionUpstream = NodeSearchResult | OrderSearchResult;

function compactQuery(value: string | null): string {
  return (value || "").trim().slice(0, MAX_QUERY_LENGTH);
}

function parseKind(value: string | null): RouteSuggestionKind | null {
  if (value === "node" || value === "order") return value;
  return null;
}

function buildEndpoint(kind: RouteSuggestionKind, query: string): string {
  const search = new URLSearchParams();
  search.set("page", "1");

  if (kind === "node") {
    search.set("per_page", String(NODE_LIMIT));
    if (query) search.set("keyword", query);
    return `/nodes?${search.toString()}`;
  }

  search.set("per_page", String(ORDER_LIMIT));
  if (query) search.set("search", query);
  return `/orders?${search.toString()}`;
}

function sanitizeNode(node: RouteNode): RouteNode {
  return {
    id: node.id,
    name: node.name,
    node_name: node.node_name,
    type: node.type,
    city: node.city,
    province: node.province,
    district: node.district,
    address: node.address,
    longitude: node.longitude,
    latitude: node.latitude,
    status: node.status,
  };
}

function sanitizeOrder(order: OrderSearchItem): OrderSearchItem {
  return {
    id: order.id,
    order_number: order.order_number,
    external_order_id: order.external_order_id,
    external_shipment_id: order.external_shipment_id,
    data_source: order.data_source,
    origin_name: order.origin_name,
    origin_address: order.origin_address,
    destination_name: order.destination_name,
    destination_address: order.destination_address,
    cargo_name: order.cargo_name,
    goods_name: order.goods_name,
    cargo_type: order.cargo_type,
    weight: order.weight,
    volume: order.volume,
    freight: order.freight,
    status: order.status,
    created_at: order.created_at,
  };
}

function emptyPayload(kind: RouteSuggestionKind, query: string): RouteSuggestionResponse {
  return {
    success: true,
    kind,
    query,
    nodes: kind === "node" ? [] : undefined,
    orders: kind === "order" ? [] : undefined,
    total: 0,
    data_source: kind === "node" ? "nodes" : "orders_or_shipment_facts",
    provider_status: "degraded",
    fallback_reason: "EMPTY_QUERY",
    authenticity_level: "BFF-empty-query",
  };
}

async function fetchSuggestions(kind: RouteSuggestionKind, query: string, accessToken: string) {
  return fetchFlaskApi<SuggestionUpstream>(buildEndpoint(kind, query), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

function normalizePayload(
  kind: RouteSuggestionKind,
  query: string,
  upstreamData: SuggestionUpstream | null,
): RouteSuggestionResponse {
  if (kind === "node") {
    const data = upstreamData as NodeSearchResult | null;
    return {
      success: true,
      kind,
      query,
      nodes: (data?.nodes || []).map(sanitizeNode),
      total: data?.total || 0,
      data_source: "nodes",
      provider_status: "ok",
      authenticity_level: "BFF-postgresql-node-search",
    };
  }

  const data = upstreamData as OrderSearchResult | null;
  return {
    success: true,
    kind,
    query,
    orders: (data?.orders || []).map(sanitizeOrder),
    total: data?.total || 0,
    data_source: data?.data_source || "orders_or_shipment_facts",
    provider_status: "ok",
    authenticity_level: data?.data_source === "shipment_facts" ? "A-real-shipment-data" : "B-order-search",
  };
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const kind = parseKind(params.get("kind"));
  const query = compactQuery(params.get("q"));

  if (!kind) {
    return NextResponse.json(
      {
        success: false,
        error: "kind must be node or order",
      },
      { status: 400 },
    );
  }

  if (!query) {
    return NextResponse.json(emptyPayload(kind, query));
  }

  let accessToken = await getAccessTokenCookie().catch(() => null);
  let refreshedAccessToken: string | null = null;

  if (!accessToken) {
    const refresh = await refreshAccessTokenFromCookie();
    accessToken = refresh.accessToken || null;
    refreshedAccessToken = refresh.accessToken || null;
  }

  if (!accessToken) {
    return NextResponse.json({
      success: false,
      kind,
      query,
      error: "登录后可搜索真实节点和订单",
      data_source: kind === "node" ? "nodes" : "orders_or_shipment_facts",
      provider_status: "degraded",
      fallback_reason: "MISSING_ACCESS_TOKEN",
      authenticity_level: "BFF-auth-required",
    });
  }

  try {
    let upstream = await fetchSuggestions(kind, query, accessToken);
    if (!upstream.ok && upstream.status === 401) {
      const refresh = await refreshAccessTokenFromCookie();
      if (refresh.accessToken) {
        refreshedAccessToken = refresh.accessToken;
        upstream = await fetchSuggestions(kind, query, refresh.accessToken);
      }
    }

    if (!upstream.ok) {
      return NextResponse.json({
        success: false,
        kind,
        query,
        error: upstreamError(upstream.data, "建议搜索失败"),
        data_source: kind === "node" ? "nodes" : "orders_or_shipment_facts",
        provider_status: "degraded",
        fallback_reason: `HTTP_${upstream.status}`,
        authenticity_level: "BFF-upstream-degraded",
      });
    }

    const response = NextResponse.json(normalizePayload(kind, query, upstream.data));
    if (refreshedAccessToken) {
      setAuthCookies(response, {
        accessToken: refreshedAccessToken,
      });
    }
    return response;
  } catch (error) {
    return NextResponse.json({
      success: false,
      kind,
      query,
      error: error instanceof Error ? error.message : "建议搜索服务不可用",
      data_source: kind === "node" ? "nodes" : "orders_or_shipment_facts",
      provider_status: "degraded",
      fallback_reason: "BFF_REQUEST_FAILED",
      authenticity_level: "BFF-unavailable",
    });
  }
}
