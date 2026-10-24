import { getAnalyticsOverview } from "@/lib/api";
import { BarChart } from "@/components/BarChart";
import { TrendChart } from "@/components/TrendChart";

export const dynamic = "force-dynamic";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-5">
      <div className="text-2xl font-bold tabular-nums">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide opacity-60">
        {label}
      </div>
    </div>
  );
}

export default async function AnalyticsPage() {
  let data;
  try {
    data = await getAnalyticsOverview("boston", 60);
  } catch {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="mt-6 rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Could not load analytics. Ensure the backend is running and that
          Boston 311 data has been ingested:
          <code className="mt-2 block font-mono">
            python -m app.ingestion.cli --max 5000
          </code>
        </div>
      </main>
    );
  }

  const { summary } = data;
  const empty = summary.total === 0;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold">Boston 311 Analytics</h1>
        <p className="text-sm opacity-70">
          Historical reference data — kept separate from live complaints.
        </p>
      </header>

      {empty ? (
        <div className="mt-6 rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          No historical data yet. Ingest Boston 311 data with{" "}
          <code className="font-mono">python -m app.ingestion.cli --max 5000</code>.
        </div>
      ) : (
        <div className="mt-8 flex flex-col gap-6">
          <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Total cases" value={summary.total.toLocaleString()} />
            <StatCard label="Open" value={summary.open.toLocaleString()} />
            <StatCard label="Closed" value={summary.closed.toLocaleString()} />
            <StatCard
              label="Avg resolution (hrs)"
              value={
                summary.avg_resolution_hours != null
                  ? summary.avg_resolution_hours.toLocaleString()
                  : "—"
              }
            />
          </section>

          <TrendChart points={data.trend} />

          <section className="grid gap-6 lg:grid-cols-2">
            <BarChart title="Top categories (reason)" items={data.by_category} />
            <BarChart title="Top neighborhoods" items={data.by_neighborhood} />
            <BarChart title="By department" items={data.by_department} />
            <BarChart title="By status" items={data.by_status} />
          </section>
        </div>
      )}
    </main>
  );
}
