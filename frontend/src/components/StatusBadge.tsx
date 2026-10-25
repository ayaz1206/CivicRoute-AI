import type { ComplaintStatus } from "@/lib/api";
import { Badge, type BadgeTone } from "@/components/ui/Badge";

const TONES: Record<ComplaintStatus, BadgeTone> = {
  submitted: "info",
  triaged: "brand",
  in_progress: "warning",
  resolved: "success",
  closed: "neutral",
  rejected: "danger",
};

const LABELS: Record<ComplaintStatus, string> = {
  submitted: "Submitted",
  triaged: "Triaged",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
  rejected: "Rejected",
};

export function StatusBadge({ status }: { status: ComplaintStatus }) {
  // A leading dot gives a non-color cue in addition to tone + text label.
  return (
    <Badge tone={TONES[status]}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" aria-hidden />
      {LABELS[status]}
    </Badge>
  );
}
