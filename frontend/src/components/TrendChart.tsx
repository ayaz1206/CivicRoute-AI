import type { TrendPoint } from "@/lib/api";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

/** SVG area/line chart for daily complaint volume. */
export function TrendChart({ points }: { points: TrendPoint[] }) {
  const w = 600;
  const h = 180;
  const pad = 28;

  if (points.length === 0) {
    return (
      <Card>
        <CardHeader title="Daily volume trend" />
        <CardBody>
          <p className="text-sm text-content-muted">No data.</p>
        </CardBody>
      </Card>
    );
  }

  const max = points.reduce((m, p) => Math.max(m, p.count), 0) || 1;
  const stepX = points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;
  const scaleY = (c: number) => h - pad - (c / max) * (h - pad * 2);
  const coords = points.map((p, i) => [pad + i * stepX, scaleY(p.count)] as const);

  const line = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x} ${y}`)
    .join(" ");
  // Closed area path under the line for a subtle fill.
  const area =
    `${line} L ${coords[coords.length - 1][0]} ${h - pad} ` +
    `L ${coords[0][0]} ${h - pad} Z`;

  return (
    <Card>
      <CardHeader
        title="Daily volume trend"
        description={`${points[0].date} → ${points[points.length - 1].date} · peak ${max}/day`}
      />
      <CardBody>
        <svg
          viewBox={`0 0 ${w} ${h}`}
          className="w-full text-brand-500"
          role="img"
          aria-label={`Daily complaint volume trend; peak ${max} per day`}
        >
          <defs>
            <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.18" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
          </defs>
          <line
            x1={pad}
            y1={h - pad}
            x2={w - pad}
            y2={h - pad}
            stroke="currentColor"
            strokeOpacity={0.15}
          />
          <path d={area} fill="url(#trend-fill)" />
          <path
            d={line}
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {coords.map(([x, y], i) => (
            <circle key={points[i].date} cx={x} cy={y} r={2.5} fill="currentColor">
              <title>
                {points[i].date}: {points[i].count}
              </title>
            </circle>
          ))}
        </svg>
      </CardBody>
    </Card>
  );
}
