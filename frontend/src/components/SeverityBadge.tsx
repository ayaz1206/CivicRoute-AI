import type { Recommendation } from "@/lib/api";

type Severity = Recommendation["review_severity"];

const STYLES: Record<Severity, string> = {
  high_risk: "bg-red-100 text-red-800 border-red-300",
  low_confidence: "bg-amber-100 text-amber-800 border-amber-300",
  routine: "bg-gray-100 text-gray-700 border-gray-300",
};

const LABELS: Record<Severity, string> = {
  high_risk: "High-risk",
  low_confidence: "Low confidence",
  routine: "Awaiting approval",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${STYLES[severity]}`}
    >
      {LABELS[severity]}
    </span>
  );
}
