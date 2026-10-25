export function ConfidenceBar({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  const pct = value != null ? Math.round(value * 100) : null;
  const color =
    pct == null
      ? "bg-slate-300 dark:bg-slate-600"
      : pct >= 70
        ? "bg-emerald-500"
        : pct >= 40
          ? "bg-amber-500"
          : "bg-red-500";
  // Text label of the percentage avoids relying on bar color alone.
  return (
    <div className="text-xs">
      <div className="flex justify-between">
        <span className="text-content-muted">{label}</span>
        <span className="tabular-nums font-medium text-content">
          {pct != null ? `${pct}%` : "—"}
        </span>
      </div>
      <div
        className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-muted"
        role="progressbar"
        aria-valuenow={pct ?? 0}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={`h-full rounded-full transition-[width] duration-300 ${color}`}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
    </div>
  );
}
