import type { ComplaintStatus } from "@/lib/api";

const STYLES: Record<ComplaintStatus, string> = {
  submitted: "bg-blue-100 text-blue-800",
  triaged: "bg-indigo-100 text-indigo-800",
  in_progress: "bg-amber-100 text-amber-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-gray-200 text-gray-700",
  rejected: "bg-red-100 text-red-800",
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
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
