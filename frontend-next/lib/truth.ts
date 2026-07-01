import type { RemoteResult, TruthMetadata } from "./types";

export function truthFromResult<T extends TruthMetadata>(result: RemoteResult<T>): TruthMetadata {
  return {
    data_source: result.data?.data_source || "not_connected",
    distance_source: result.data?.distance_source,
    path_source: result.data?.path_source,
    provider_status: result.data?.provider_status || (result.ok ? "ok" : "degraded"),
    fallback_reason: result.data?.fallback_reason || result.error,
    authenticity_level: result.data?.authenticity_level,
  };
}
