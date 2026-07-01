import type { RemoteResult } from "@/lib/types";
import { StatusPill } from "./status-pill";

export function DataState<T>({ result }: { result: RemoteResult<T> }) {
  if (result.ok) {
    return <StatusPill status="ok" label="connected" />;
  }
  return <StatusPill status="degraded" label={result.error || "degraded"} />;
}
