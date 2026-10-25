import Link from "next/link";
import { getHealth, API_URL } from "@/lib/api";
import { Container } from "@/components/ui/Page";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/Icon";

export const dynamic = "force-dynamic";

const RESIDENT_LINKS = [
  {
    href: "/submit",
    title: "Submit a complaint",
    desc: "Report an issue and receive a tracking code.",
    icon: <Icon.clipboard />,
  },
  {
    href: "/track",
    title: "Track a complaint",
    desc: "Follow status and answer any clarifications.",
    icon: <Icon.search />,
  },
];

const STAFF_LINKS = [
  {
    href: "/staff",
    title: "Staff dashboard",
    desc: "Review, triage, and manage live complaints.",
    icon: <Icon.inbox />,
  },
  {
    href: "/review",
    title: "AI review queue",
    desc: "Inspect AI recommendations, evidence & confidence.",
    icon: <Icon.sparkles />,
  },
  {
    href: "/analytics",
    title: "Boston 311 analytics",
    desc: "Historical trends by category, neighborhood & department.",
    icon: <Icon.chart />,
  },
];

function EntryCard({
  href,
  title,
  desc,
  icon,
}: {
  href: string;
  title: string;
  desc: string;
  icon: React.ReactNode;
}) {
  return (
    <Link href={href} className="group block">
      <Card className="h-full transition-shadow hover:shadow-card-hover">
        <CardBody className="flex items-start gap-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
            {icon}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 font-semibold text-content">
              {title}
              <Icon.arrowRight className="h-4 w-4 -translate-x-1 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
            </div>
            <p className="mt-1 text-sm text-content-muted">{desc}</p>
          </div>
        </CardBody>
      </Card>
    </Link>
  );
}

export default async function Home() {
  const health = await getHealth();
  const online = health?.status === "ok";

  return (
    <Container className="flex flex-col gap-10">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-brand-700 to-navy-900 px-6 py-12 text-white sm:px-10 sm:py-16">
        <div className="relative z-10 max-w-2xl">
          <Badge
            tone="brand"
            className="border-white/20 bg-white/10 text-white"
          >
            <Icon.sparkles className="h-3.5 w-3.5" />
            Agentic civic routing
          </Badge>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
            Report it once. Route it right.
          </h1>
          <p className="mt-3 text-base text-white/80">
            CivicRoute AI triages resident complaints with an auditable AI
            workflow — classifying, prioritizing, and routing each issue to the
            right department. Every recommendation is reviewed by a human before
            it takes effect.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/submit"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50"
            >
              <Icon.clipboard className="h-4 w-4" />
              Submit a complaint
            </Link>
            <Link
              href="/track"
              className="inline-flex items-center gap-2 rounded-lg border border-white/30 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/10"
            >
              <Icon.search className="h-4 w-4" />
              Track status
            </Link>
          </div>
        </div>
        <div
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/5 blur-2xl"
          aria-hidden
        />
      </section>

      {/* Resident entry points */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-content-subtle">
          For residents
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {RESIDENT_LINKS.map((l) => (
            <EntryCard key={l.href} {...l} />
          ))}
        </div>
      </section>

      {/* Staff entry points */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-content-subtle">
          For city staff
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STAFF_LINKS.map((l) => (
            <EntryCard key={l.href} {...l} />
          ))}
        </div>
      </section>

      {/* Backend status */}
      <section>
        <Card>
          <CardBody className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  online ? "bg-emerald-500" : "bg-red-500"
                }`}
                aria-hidden
              />
              <span className="text-sm font-medium text-content">
                {online
                  ? `Backend online — API v${health?.version ?? "?"}`
                  : "Backend offline"}
              </span>
              <Badge tone={online ? "success" : "danger"}>
                {online ? "Operational" : "Unavailable"}
              </Badge>
            </div>
            <code className="text-xs text-content-subtle">{API_URL}/health</code>
          </CardBody>
        </Card>
      </section>
    </Container>
  );
}
