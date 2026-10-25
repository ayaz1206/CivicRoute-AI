"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  answerClarification,
  listClarifications,
  trackComplaint,
  type ComplaintPublic,
  type PublicClarification,
} from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { Container, PageHeader } from "@/components/ui/Page";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Skeleton } from "@/components/ui/feedback";
import { Icon } from "@/components/ui/Icon";

function DetailItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-content-subtle">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm text-content">{value}</dd>
    </div>
  );
}

function TrackInner() {
  const params = useSearchParams();
  const [code, setCode] = useState("");
  const [complaint, setComplaint] = useState<ComplaintPublic | null>(null);
  const [clarifications, setClarifications] = useState<PublicClarification[]>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function lookup(c: string) {
    setError(null);
    setComplaint(null);
    setClarifications([]);
    if (!c.trim()) return;
    setLoading(true);
    try {
      setComplaint(await trackComplaint(c.trim()));
      try {
        setClarifications(await listClarifications(c.trim()));
      } catch {
        /* clarifications are optional */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lookup failed.");
    } finally {
      setLoading(false);
    }
  }

  async function submitAnswer(id: number) {
    const text = (answers[id] ?? "").trim();
    if (!text) return;
    setBusyId(id);
    try {
      await answerClarification(id, text);
      setClarifications((prev) => prev.filter((q) => q.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit answer.");
    } finally {
      setBusyId(null);
    }
  }

  // Prefill and auto-lookup if arriving from the submit page.
  useEffect(() => {
    const initial = params.get("code");
    if (initial) {
      setCode(initial);
      lookup(initial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Container size="narrow" className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Residents"
        title="Track a complaint"
        description="Enter the tracking code you received when you submitted."
      />

      <Card>
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              lookup(code);
            }}
            className="flex gap-2"
          >
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="CR-XXXXXXXX"
              aria-label="Tracking code"
              className="font-mono"
            />
            <Button type="submit" loading={loading} className="shrink-0">
              <Icon.search className="h-4 w-4" />
              Track
            </Button>
          </form>
        </CardBody>
      </Card>

      {error && <Alert tone="error">{error}</Alert>}

      {loading && (
        <Card>
          <CardBody className="flex flex-col gap-3">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
          </CardBody>
        </Card>
      )}

      {complaint && !loading && (
        <section className="flex flex-col gap-6">
          <Card>
            <CardBody>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 className="text-lg font-semibold text-content">
                  {complaint.title}
                </h2>
                <StatusBadge status={complaint.status} />
              </div>
              <p className="mt-2 text-sm text-content-muted">
                {complaint.description}
              </p>
              <dl className="mt-5 grid grid-cols-2 gap-4">
                <DetailItem
                  label="Tracking code"
                  value={
                    <span className="font-mono">{complaint.tracking_code}</span>
                  }
                />
                {complaint.location_text && (
                  <DetailItem label="Location" value={complaint.location_text} />
                )}
                {complaint.category && (
                  <DetailItem label="Category" value={complaint.category} />
                )}
                <DetailItem
                  label="Submitted"
                  value={new Date(complaint.created_at).toLocaleDateString()}
                />
              </dl>
            </CardBody>
          </Card>

          {clarifications.length > 0 && (
            <Card className="border-amber-300 dark:border-amber-500/40">
              <CardHeader
                title={
                  <span className="flex items-center gap-2">
                    <Icon.alert className="h-4 w-4 text-amber-500" />
                    We need a bit more information
                  </span>
                }
                description="Answering these helps us route and resolve your complaint faster."
              />
              <CardBody>
                <ul className="flex flex-col gap-4">
                  {clarifications.map((q) => (
                    <li key={q.id} className="flex flex-col gap-2">
                      <label
                        htmlFor={`clar-${q.id}`}
                        className="text-sm text-content"
                      >
                        {q.question}
                      </label>
                      <div className="flex gap-2">
                        <Input
                          id={`clar-${q.id}`}
                          value={answers[q.id] ?? ""}
                          onChange={(e) =>
                            setAnswers((a) => ({ ...a, [q.id]: e.target.value }))
                          }
                          placeholder="Your answer"
                        />
                        <Button
                          variant="secondary"
                          onClick={() => submitAnswer(q.id)}
                          loading={busyId === q.id}
                          className="shrink-0"
                        >
                          Submit
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}

          <Card>
            <CardHeader title="Status timeline" />
            <CardBody>
              <Timeline entries={complaint.status_history} />
            </CardBody>
          </Card>
        </section>
      )}
    </Container>
  );
}

export default function TrackPage() {
  return (
    <Suspense
      fallback={
        <Container size="narrow">
          <Skeleton className="h-40 w-full" />
        </Container>
      }
    >
      <TrackInner />
    </Suspense>
  );
}
