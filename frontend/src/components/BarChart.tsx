import type { CountItem } from "@/lib/api";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

/** Horizontal bar chart using CSS widths — no chart library needed. */
export function BarChart({
  title,
  items,
}: {
  title: string;
  items: CountItem[];
}) {
  const max = items.reduce((m, i) => Math.max(m, i.count), 0) || 1;
  return (
    <Card>
      <CardHeader title={title} />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-content-muted">No data.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((i) => (
              <li key={i.key} className="text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-content" title={i.key}>
                    {i.key}
                  </span>
                  <span className="shrink-0 tabular-nums text-content-muted">
                    {i.count.toLocaleString()}
                  </span>
                </div>
                <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-surface-muted">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-600 transition-[width] duration-500"
                    style={{ width: `${(i.count / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
