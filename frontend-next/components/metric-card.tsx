export function MetricCard({
  label,
  value,
  helper,
  tone = "default",
}: {
  label: string;
  value: string;
  helper?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  return (
    <section className={`metric-card metric-${tone}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      {helper ? <span>{helper}</span> : null}
    </section>
  );
}
