import type { ProviderStatus, TruthMetadata } from "@/lib/types";

function statusClass(status?: ProviderStatus | null): string {
  if (status === "ok") return "status-pill status-ok";
  if (status === "failed") return "status-pill status-failed";
  if (status === "critical") return "status-pill status-critical";
  if (status === "high") return "status-pill status-high";
  if (status === "medium") return "status-pill status-medium";
  if (status === "low") return "status-pill status-low";
  if (status === "degraded") return "status-pill status-degraded";
  return "status-pill status-unknown";
}

export function StatusPill({
  status,
  label,
}: {
  status?: ProviderStatus | null;
  label?: string;
}) {
  const display = label || status || "unknown";
  return <span className={statusClass(status)}>{display}</span>;
}

export function TruthStrip({ truth }: { truth?: TruthMetadata }) {
  if (!truth) return null;
  return (
    <dl className="truth-strip">
      <div>
        <dt>数据源</dt>
        <dd>{truth.data_source || "unknown"}</dd>
      </div>
      <div>
        <dt>距离源</dt>
        <dd>{truth.distance_source || "not_reported"}</dd>
      </div>
      <div>
        <dt>路径源</dt>
        <dd>{truth.path_source || "not_reported"}</dd>
      </div>
      <div>
        <dt>真实性</dt>
        <dd>{truth.authenticity_level || "unknown"}</dd>
      </div>
      {truth.fallback_reason ? (
        <div>
          <dt>降级原因</dt>
          <dd>{truth.fallback_reason}</dd>
        </div>
      ) : null}
    </dl>
  );
}
