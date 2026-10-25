"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideRecommendation,
  getReviewQueue,
  type Recommendation,
} from "@/lib/api";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Container, PageHeader } from "@/components/ui/Page";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field, Input, Select } from "@/components/ui/Field";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, Skeleton } from "@/components/ui/feedback";
import { Icon } from "@/components/ui/Icon";

const PRIORITIES = ["low", "medium", "high", "urgent"] as const;

export default function ReviewPage() {
  const [queue, setQueue] = useState<Recommendation[]>([]);
  const [selected, setSelected] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // Override form state.
  const [ovCategory, setOvCategory] = useState("");
  const [ovPriority, setOvPriority] = useState("");
  const [ovDept, setOvDept] = useState("");
  const [note, setNote] = useState("");

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const page = await getReviewQueue();
      setQueue(page.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function select(rec: Recommendation) {
    setSelected(rec);
    setOvCategory(rec.category ?? "");
    setOvPriority(rec.priority ?? "");
    setOvDept(rec.department_slug ?? "");
    setNote("");
  }

  async function decide(decision: "approve" | "override" | "reject") {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await decideRecommendation(selected.id, {
        decision,
        reviewer: "staff",
        note: note || undefined,
        ...(decision === "override"
          ? {
              category: ovCategory || undefined,
              priority: (ovPriority || undefined) as never,
              department_slug: ovDept || undefined,
            }
          : {}),
      });
      setSelected(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed.");
    } finally {
      setBusy(false);
    }
  }

  const flagged = queue.filter((r) => r.review_severity !== "routine");
  const routine = queue.filter((r) => r.review_severity === "routine");

  const row = (r: Recommendation) => (
    <li key={r.id}>
      <button
        onClick={() => select(r)}
        className={`w-full border-t border-border px-4 py-3 text-left text-sm transition-colors hover:bg-surface-muted ${
          selected?.id === r.id ? "bg-brand-50 dark:bg-brand-500/10" : ""
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-content">
            {r.category ?? "Uncategorized"}
          </span>
          <SeverityBadge severity={r.review_severity} />
        </div>
        <div className="mt-1 flex items-center justify-between gap-2 text-xs text-content-muted">
          <span>complaint #{r.complaint_id}</span>
          {r.review_reason && (
            <span className="truncate pl-2" title={r.review_reason}>
              {r.review_reason}
            </span>
          )}
        </div>
      </button>
    </li>
  );

  return (
    <Container className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Staff · Human-in-the-loop"
        title="AI review queue"
        description="Inspect AI recommendations, evidence, and confidence. AI output is kept separate from complaint data until you approve or override it."
        actions={
          <Button variant="secondary" size="sm" onClick={refresh}>
            Refresh
          </Button>
        }
      />

      {error && <Alert tone="error">{error}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Queue */}
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-border bg-surface-muted px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-content-subtle">
            <span>Pending ({queue.length})</span>
          </div>

          {loading ? (
            <div className="flex flex-col gap-2 p-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : queue.length === 0 ? (
            <div className="p-4">
              <EmptyState
                tone="success"
                icon={<Icon.check className="h-8 w-8" />}
                title="Queue is empty"
                description="No AI recommendations are awaiting review."
              />
            </div>
          ) : (
            <>
              {flagged.length > 0 && (
                <>
                  <div className="flex items-center gap-2 bg-red-50 px-4 py-1.5 text-xs font-semibold uppercase text-red-800 dark:bg-red-500/10 dark:text-red-300">
                    <Icon.alert className="h-3.5 w-3.5" />
                    Needs attention — high-risk / low-confidence ({flagged.length})
                  </div>
                  <ul>{flagged.map(row)}</ul>
                </>
              )}
              {routine.length > 0 && (
                <>
                  <div className="bg-surface-muted px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-content-subtle">
                    Routine — awaiting mandatory approval ({routine.length})
                  </div>
                  <ul>{routine.map(row)}</ul>
                </>
              )}
            </>
          )}
        </Card>

        {/* Detail */}
        <Card>
          {!selected ? (
            <CardBody>
              <EmptyState
                icon={<Icon.sparkles className="h-8 w-8" />}
                title="Select a recommendation"
                description="Choose an item from the queue to inspect its evidence, confidence, and decide."
              />
            </CardBody>
          ) : (
            <CardBody className="flex flex-col gap-5 text-sm">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge tone="brand" icon={<Icon.sparkles className="h-3.5 w-3.5" />}>
                      AI recommendation
                    </Badge>
                    <span className="text-xs text-content-subtle">
                      complaint #{selected.complaint_id}
                    </span>
                  </div>
                  <SeverityBadge severity={selected.review_severity} />
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-3">
                  <KV label="Category" value={selected.category} />
                  <KV label="Priority" value={selected.priority} />
                  <KV label="Department" value={selected.department_slug} />
                  <KV
                    label="Overall confidence"
                    value={
                      selected.overall_confidence != null
                        ? `${Math.round(selected.overall_confidence * 100)}%`
                        : "—"
                    }
                  />
                </dl>
              </div>

              <div className="flex flex-col gap-2.5 rounded-xl border border-border bg-surface-muted p-3">
                <ConfidenceBar
                  label="Classification"
                  value={selected.category_confidence}
                />
                <ConfidenceBar
                  label="Priority"
                  value={selected.priority_confidence}
                />
                <ConfidenceBar
                  label="Routing"
                  value={selected.department_confidence}
                />
              </div>

              {selected.priority_rationale && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-content-subtle">
                    Priority rationale
                  </h3>
                  <p className="mt-1 text-content">
                    {selected.priority_rationale}
                  </p>
                </div>
              )}

              <details className="group">
                <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-content-subtle">
                  Routing evidence &amp; extracted details
                </summary>
                <div className="mt-2 flex flex-col gap-2">
                  <pre className="overflow-x-auto rounded-lg bg-surface-muted p-2.5 text-xs text-content">
                    {JSON.stringify(selected.routing_evidence, null, 2)}
                  </pre>
                  <pre className="overflow-x-auto rounded-lg bg-surface-muted p-2.5 text-xs text-content">
                    {JSON.stringify(selected.extracted, null, 2)}
                  </pre>
                </div>
              </details>

              {/* Human override — visually separated from the AI proposal. */}
              <div className="rounded-xl border border-border p-3">
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-subtle">
                  <Icon.user className="h-3.5 w-3.5" />
                  Human override (optional)
                </h3>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <Input
                    value={ovCategory}
                    onChange={(e) => setOvCategory(e.target.value)}
                    placeholder="category"
                    aria-label="Override category"
                    className="text-xs"
                  />
                  <Select
                    value={ovPriority}
                    onChange={(e) => setOvPriority(e.target.value)}
                    aria-label="Override priority"
                    className="text-xs"
                  >
                    <option value="">priority</option>
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </Select>
                  <Input
                    value={ovDept}
                    onChange={(e) => setOvDept(e.target.value)}
                    placeholder="dept slug"
                    aria-label="Override department slug"
                    className="text-xs"
                  />
                </div>
                <Input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="note (optional)"
                  aria-label="Review note"
                  className="mt-2 text-xs"
                />
              </div>

              <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                <Button
                  variant="success"
                  loading={busy}
                  onClick={() => decide("approve")}
                >
                  <Icon.check className="h-4 w-4" />
                  Approve
                </Button>
                <Button
                  variant="secondary"
                  loading={busy}
                  onClick={() => decide("override")}
                >
                  Override
                </Button>
                <Button
                  variant="ghost"
                  loading={busy}
                  onClick={() => decide("reject")}
                >
                  Reject
                </Button>
              </div>
            </CardBody>
          )}
        </Card>
      </div>
    </Container>
  );
}

function KV({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-content-subtle">
        {label}
      </dt>
      <dd className="mt-0.5 font-medium text-content">{value ?? "—"}</dd>
    </div>
  );
}
