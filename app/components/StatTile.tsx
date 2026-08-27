export default function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "text-[var(--color-success)]"
      : tone === "warning"
        ? "text-[var(--color-warning)]"
        : tone === "danger"
          ? "text-[var(--color-danger)]"
          : "text-[var(--color-text)]";

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-3 flex flex-col gap-1">
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className={`text-xl font-semibold tabular-nums ${toneClass}`}>{value}</span>
    </div>
  );
}
