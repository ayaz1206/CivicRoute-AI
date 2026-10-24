import type { TrendPoint } from "@/lib/api";

/** Minimal SVG line chart for daily complaint volume. */
export function TrendChart({ points }: { points: TrendPoint[] }) {
  const w = 600;
  const h = 160;
  const pad = 24;

  if (points.length === 0) {
    return (
      <div className="rounded-lg border p-5">
        <h3 className="mb-4 font-semibold">Daily volume trend</h3>
        <p className="text-sm opacity-60">No data.</p>
      </div>
    );
  }

  const max = points.reduce((m, p) => Math.max(m, p.count), 0) || 1;
  const stepX =
    points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;
  const scaleY = (c: number) => h - pad - (c / max) * (h - pad * 2);

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${pad + i * stepX} ${scaleY(p.count)}`)
    .join(" ");

  return (
    <div className="rounded-lg border p-5">
      <h3 className="mb-1 font-semibold">Daily volume trend</h3>
      <p className="mb-3 text-xs opacity-60">
        {points[0].date} → {points[points.length - 1].date} · peak {max}/day
      </p>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full"
        role="img"
        aria-label="Daily complaint volume trend"
      >
        <line
          x1={pad}
          y1={h - pad}
          x2={w - pad}
          y2={h - pad}
          stroke="currentColor"
          strokeOpacity={0.15}
        />
        <path d={path} fill="none" stroke="#3b82f6" strokeWidth={2} />
        {points.map((p, i) => (
          <circle
            key={p.date}
            cx={pad + i * stepX}
            cy={scaleY(p.count)}
            r={2.5}
            fill="#3b82f6"
          >
            <title>
              {p.date}: {p.count}
            </title>
          </circle>
        ))}
      </svg>
    </div>
  );
}
