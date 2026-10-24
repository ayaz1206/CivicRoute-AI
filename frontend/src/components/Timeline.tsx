import type { StatusHistoryEntry } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

export function Timeline({ entries }: { entries: StatusHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm opacity-60">No history yet.</p>;
  }
  return (
    <ol className="flex flex-col gap-4">
      {entries.map((e) => (
        <li key={e.id} className="flex gap-3">
          <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-blue-500" />
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <StatusBadge status={e.to_status} />
              <span className="text-xs opacity-60">
                {new Date(e.created_at).toLocaleString()}
              </span>
            </div>
            <span className="text-xs opacity-70">by {e.actor}</span>
            {e.note && <p className="text-sm">{e.note}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
