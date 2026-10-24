import type { CountItem } from "@/lib/api";

/** Simple horizontal bar chart using CSS widths — no chart library needed. */
export function BarChart({
  title,
  items,
}: {
  title: string;
  items: CountItem[];
}) {
  const max = items.reduce((m, i) => Math.max(m, i.count), 0) || 1;
  return (
    <div className="rounded-lg border p-5">
      <h3 className="mb-4 font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm opacity-60">No data.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((i) => (
            <li key={i.key} className="text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate" title={i.key}>
                  {i.key}
                </span>
                <span className="shrink-0 tabular-nums opacity-60">
                  {i.count.toLocaleString()}
                </span>
              </div>
              <div className="mt-1 h-2 w-full rounded bg-gray-100">
                <div
                  className="h-2 rounded bg-blue-500"
                  style={{ width: `${(i.count / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
