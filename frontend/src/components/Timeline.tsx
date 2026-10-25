import type { StatusHistoryEntry } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { StatusBadge } from "./StatusBadge";

export function Timeline({ entries }: { entries: StatusHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-content-muted">No history yet.</p>;
  }
  return (
    <ol className="relative flex flex-col gap-5">
      {entries.map((e, i) => (
        <li key={e.id} className="relative flex gap-3">
          {/* connector line between dots (not after the last item) */}
          {i < entries.length - 1 && (
            <span
              className="absolute left-[5px] top-4 h-full w-px bg-border"
              aria-hidden
            />
          )}
          <span
            className="relative mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-brand-500 ring-4 ring-brand-500/15"
            aria-hidden
          />
          <div className="flex flex-col gap-1 pb-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={e.to_status} />
              <span className="text-xs text-content-subtle">
                {formatDateTime(e.created_at)}
              </span>
            </div>
            <span className="text-xs text-content-muted">by {e.actor}</span>
            {e.note && <p className="text-sm text-content">{e.note}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
