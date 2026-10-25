import type { Recommendation } from "@/lib/api";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";

type Severity = Recommendation["review_severity"];

const TONES: Record<Severity, BadgeTone> = {
  high_risk: "danger",
  low_confidence: "warning",
  routine: "neutral",
};

const LABELS: Record<Severity, string> = {
  high_risk: "High-risk",
  low_confidence: "Low confidence",
  routine: "Awaiting approval",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const icon =
    severity === "routine" ? undefined : <Icon.alert className="h-3.5 w-3.5" />;
  return (
    <Badge tone={TONES[severity]} icon={icon}>
      {LABELS[severity]}
    </Badge>
  );
}
