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
      ? "bg-gray-300"
      : pct >= 70
        ? "bg-green-500"
        : pct >= 40
          ? "bg-amber-500"
          : "bg-red-500";
  return (
    <div className="text-xs">
      <div className="flex justify-between">
        <span className="opacity-70">{label}</span>
        <span className="tabular-nums opacity-70">
          {pct != null ? `${pct}%` : "—"}
        </span>
      </div>
      <div className="mt-1 h-1.5 w-full rounded bg-gray-100">
        <div
          className={`h-1.5 rounded ${color}`}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
    </div>
  );
}
