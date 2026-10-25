import { getAnalyticsOverview } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { BarChart } from "@/components/BarChart";
import { TrendChart } from "@/components/TrendChart";
import { Container, PageHeader } from "@/components/ui/Page";
import { StatCard } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage() {
  let data;
  try {
    data = await getAnalyticsOverview("boston", 60);
  } catch {
    return (
      <Container className="flex flex-col gap-6">
        <PageHeader
          eyebrow="Staff"
          title="Boston 311 analytics"
          description="Historical reference data — kept separate from live complaints."
        />
        <Alert tone="warning" title="Could not load analytics">
          Ensure the backend is running and that Boston 311 data has been
          ingested:
          <code className="mt-2 block rounded bg-surface-muted px-2 py-1 font-mono text-xs">
            python -m app.ingestion.cli --max 5000
          </code>
        </Alert>
      </Container>
    );
  }

  const { summary } = data;
  const empty = summary.total === 0;

  return (
    <Container className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Staff"
        title="Boston 311 analytics"
        description="Historical reference data — kept separate from live complaints."
      />

      {empty ? (
        <Alert tone="warning" title="No historical data yet">
          Ingest Boston 311 data with{" "}
          <code className="font-mono">python -m app.ingestion.cli --max 5000</code>
          .
        </Alert>
      ) : (
        <div className="flex flex-col gap-6">
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Total cases"
              value={formatNumber(summary.total)}
              tone="brand"
            />
            <StatCard
              label="Open"
              value={formatNumber(summary.open)}
              tone="warning"
            />
            <StatCard
              label="Closed"
              value={formatNumber(summary.closed)}
              tone="success"
            />
            <StatCard
              label="Avg resolution (hrs)"
              value={
                summary.avg_resolution_hours != null
                  ? formatNumber(summary.avg_resolution_hours)
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
    </Container>
  );
}
