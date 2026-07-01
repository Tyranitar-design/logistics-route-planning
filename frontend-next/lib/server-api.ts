import { getApiBaseUrl } from "./api-base";

export async function fetchFlaskApi<T>(
  endpoint: string,
  init: RequestInit = {},
): Promise<{
  ok: boolean;
  status: number;
  data: T | null;
}> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
    ...init,
    cache: "no-store",
    headers,
  });

  const data = (await response.json().catch(() => null)) as T | null;
  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

export function upstreamError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const candidate = data as { error?: unknown; message?: unknown };
  if (typeof candidate.error === "string") return candidate.error;
  if (typeof candidate.message === "string") return candidate.message;
  return fallback;
}
