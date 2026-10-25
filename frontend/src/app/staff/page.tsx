"use client";

import { useCallback, useEffect, useState } from "react";
import {
  detectDuplicates,
  decideDuplicate,
  getComplaintDetail,
  getReviewQueue,
  listCities,
  listComplaints,
  listDepartments,
  runTriage,
  trackComplaint,
  updateStatus,
  type City,
  type Complaint,
  type ComplaintDetail,
  type ComplaintPublic,
  type ComplaintStatus,
  type Department,
  type DuplicateCandidate,
  type Recommendation,
} from "@/lib/api";
import { ApiError } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { Container, PageHeader } from "@/components/ui/Page";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field, Select } from "@/components/ui/Field";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/feedback";
import { Icon } from "@/components/ui/Icon";

function authHint(err: unknown): string {
  if (err instanceof ApiError && err.status === 401) {
    return "Please sign in as staff to use this page.";
  }
  return err instanceof Error ? err.message : "Request failed.";
}

const STATUSES: ComplaintStatus[] = [
  "submitted",
  "triaged",
  "in_progress",
  "resolved",
  "closed",
  "rejected",
];

// Allowed next statuses (mirrors backend transition rules for a better UX;
// the backend remains the source of truth and rejects illegal transitions).
const NEXT: Record<ComplaintStatus, ComplaintStatus[]> = {
  submitted: ["triaged", "in_progress", "rejected"],
  triaged: ["in_progress", "rejected"],
  in_progress: ["resolved", "rejected"],
  resolved: ["closed", "in_progress"],
  closed: [],
  rejected: [],
};

export default function StaffPage() {
  const [cities, setCities] = useState<City[]>([]);
  const [cityId, setCityId] = useState<number | "">("");
  const [status, setStatus] = useState<ComplaintStatus | "">("");
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<ComplaintPublic | null>(null);
  const [detail, setDetail] = useState<ComplaintDetail | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [pendingRec, setPendingRec] = useState<Recommendation | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  // Duplicate-detection lifecycle so we can distinguish "not run yet" from
  // "ran and found nothing": idle | loading | done | error.
  const [dupState, setDupState] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [dupError, setDupError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listCities()
      .then((c) => {
        setCities(c);
        if (c.length > 0) setCityId(c[0].id);
      })
      .catch(() => setError("Could not load cities. Is the backend running?"));
  }, []);

  // Load the selected city's departments so department_id can be shown by name.
  useEffect(() => {
    if (cityId === "") return;
    listDepartments(cityId)
      .then(setDepartments)
      .catch(() => setDepartments([]));
  }, [cityId]);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const page = await listComplaints({
        cityId: cityId === "" ? undefined : cityId,
        status: status === "" ? undefined : status,
        limit: 50,
      });
      setComplaints(page.items);
      setTotal(page.total);
    } catch (err) {
      setError(authHint(err));
    }
  }, [cityId, status]);

  useEffect(() => {
    if (cityId !== "") refresh();
  }, [cityId, status, refresh]);

  async function openDetail(id: number) {
    const found = complaints.find((c) => c.id === id);
    if (!found) return;
    setSelectedId(id);
    setDuplicates([]);
    setDupState("idle");
    setDupError(null);
    setDetail(null);
    setPendingRec(null);
    setNotice(null);
    try {
      setSelected(await trackComplaint(found.tracking_code));
      // Staff-only full detail (category/priority/department_id) + any pending
      // AI recommendation awaiting approval for this complaint.
      try {
        setDetail(await getComplaintDetail(id));
      } catch {
        /* detail is best-effort; panel still shows tracking info */
      }
      try {
        const queue = await getReviewQueue(cityId === "" ? undefined : cityId);
        setPendingRec(
          queue.items.find(
            (r) => r.complaint_id === id && r.status === "pending",
          ) ?? null,
        );
      } catch {
        /* review queue is best-effort */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load detail.");
    }
  }

  function departmentName(deptId: number | null | undefined): string | null {
    if (deptId == null) return null;
    return departments.find((d) => d.id === deptId)?.name ?? `#${deptId}`;
  }

  async function changeStatus(next: ComplaintStatus) {
    if (selectedId == null) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateStatus(selectedId, next);
      // Re-use the PII-free public projection for display consistency.
      setSelected(updated);
      try {
        setDetail(await getComplaintDetail(selectedId));
      } catch {
        /* best-effort */
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Status update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function triage() {
    if (selectedId == null) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const run = await runTriage(selectedId);
      const r = run.recommendation;
      const msg = r
        ? `AI run ${run.status}: ${r.category ?? "?"} / ${r.priority ?? "?"} / ${
            r.department_slug ?? "no dept"
          }${r.requires_review ? " — sent to AI Review queue" : ""}`
        : `AI run ${run.status}${run.error ? `: ${run.error}` : ""}`;
      setNotice(msg);
      // Refresh the pending recommendation shown in the detail panel.
      try {
        const queue = await getReviewQueue(cityId === "" ? undefined : cityId);
        setPendingRec(
          queue.items.find(
            (x) => x.complaint_id === selectedId && x.status === "pending",
          ) ?? null,
        );
      } catch {
        /* best-effort */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Triage failed.");
    } finally {
      setBusy(false);
    }
  }

  async function detectDup() {
    if (selectedId == null) return;
    setBusy(true);
    setDupState("loading");
    setDupError(null);
    try {
      const found = await detectDuplicates(selectedId);
      setDuplicates(found);
      setDupState("done");
    } catch (err) {
      setDupError(
        err instanceof Error ? err.message : "Duplicate detection failed.",
      );
      setDupState("error");
    } finally {
      setBusy(false);
    }
  }

  async function decideDup(linkId: number, decision: "confirm" | "reject") {
    setBusy(true);
    try {
      const updated = await decideDuplicate(linkId, decision);
      setDuplicates((prev) =>
        prev.map((d) => (d.link_id === linkId ? updated : d)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Staff"
        title="Complaint dashboard"
        description="Live complaints only. Historical 311 data is kept separate."
      />

      {/* Filters */}
      <Card>
        <CardBody className="flex flex-wrap items-end gap-4">
          <Field label="City" htmlFor="f-city" className="min-w-[10rem]">
            <Select
              id="f-city"
              value={cityId}
              onChange={(e) => setCityId(Number(e.target.value))}
            >
              {cities.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Status" htmlFor="f-status" className="min-w-[10rem]">
            <Select
              id="f-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as ComplaintStatus | "")}
            >
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
          </Field>
          <Button variant="secondary" onClick={refresh} className="mb-0.5">
            Refresh
          </Button>
          <span className="mb-2 text-sm text-content-muted">{total} total</span>
        </CardBody>
      </Card>

      {error && <Alert tone="error">{error}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* List */}
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-muted text-left text-xs font-semibold uppercase tracking-wide text-content-subtle">
                <tr>
                  <th className="px-4 py-2.5">Code</th>
                  <th className="px-4 py-2.5">Title</th>
                  <th className="px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {complaints.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-10">
                      <EmptyState
                        icon={<Icon.inbox className="h-8 w-8" />}
                        title="No complaints"
                        description="No complaints match the current filters."
                      />
                    </td>
                  </tr>
                )}
                {complaints.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => openDetail(c.id)}
                    className={`cursor-pointer border-t border-border transition-colors hover:bg-surface-muted ${
                      selectedId === c.id ? "bg-brand-50 dark:bg-brand-500/10" : ""
                    }`}
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-content-muted">
                      {c.tracking_code}
                    </td>
                    <td className="px-4 py-2.5 text-content">{c.title}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Detail */}
        <Card>
          {!selected ? (
            <CardBody>
              <EmptyState
                icon={<Icon.clipboard className="h-8 w-8" />}
                title="Select a complaint"
                description="Choose a complaint to view details, run AI triage, detect duplicates, and manage its status."
              />
            </CardBody>
          ) : (
            <CardBody className="flex flex-col gap-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 className="font-semibold text-content">{selected.title}</h2>
                <StatusBadge status={selected.status} />
              </div>
              <p className="text-sm text-content-muted">{selected.description}</p>

              {notice && (
                <Alert tone="info" role="status">
                  {notice}
                </Alert>
              )}

              {/* Assigned (approved) complaint fields — the source of truth. */}
              <div className="rounded-xl border border-border p-3">
                <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-content-subtle">
                  <Icon.check className="h-3.5 w-3.5" />
                  Assigned details
                </h3>
                <dl className="grid grid-cols-3 gap-3 text-sm">
                  <AssignedField
                    label="Category"
                    value={detail?.category ?? selected.category}
                  />
                  <AssignedField
                    label="Priority"
                    value={detail?.priority ?? selected.priority}
                  />
                  <AssignedField
                    label="Department"
                    value={departmentName(detail?.department_id)}
                  />
                </dl>
                <p className="mt-2 text-xs text-content-subtle">
                  Set when staff approve or override an AI recommendation, or
                  assign manually.
                </p>
              </div>

              {/* Pending AI recommendation — visually distinct from assigned. */}
              {pendingRec && (
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 dark:border-amber-500/40 dark:bg-amber-500/10">
                  <div className="mb-2 flex items-center gap-2">
                    <Badge
                      tone="brand"
                      icon={<Icon.sparkles className="h-3.5 w-3.5" />}
                    >
                      AI recommendation
                    </Badge>
                    <span className="text-xs font-medium text-amber-800 dark:text-amber-300">
                      pending approval
                    </span>
                  </div>
                  <dl className="grid grid-cols-3 gap-3 text-sm">
                    <AssignedField label="Category" value={pendingRec.category} />
                    <AssignedField label="Priority" value={pendingRec.priority} />
                    <AssignedField
                      label="Department"
                      value={pendingRec.department_slug}
                    />
                  </dl>
                  <p className="mt-2 text-xs text-amber-800 dark:text-amber-300">
                    Not yet applied. Approve or override it in the{" "}
                    <a href="/review" className="font-medium underline">
                      AI Review queue
                    </a>
                    .
                  </p>
                </div>
              )}

              {/* AI actions */}
              <div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    loading={busy}
                    onClick={triage}
                  >
                    <Icon.sparkles className="h-4 w-4" />
                    Run AI triage
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={busy && dupState === "loading"}
                    onClick={detectDup}
                  >
                    <Icon.search className="h-4 w-4" />
                    {dupState === "loading" ? "Searching…" : "Find duplicates"}
                  </Button>
                </div>
                <p className="mt-1.5 text-xs text-content-subtle">
                  AI recommendations and duplicate links never change the
                  complaint until a human approves or confirms them.
                </p>
              </div>

              {/* Duplicate detection states */}
              {dupState === "loading" && (
                <div className="flex items-center gap-2 rounded-xl border border-border p-3 text-sm text-content-muted">
                  <Icon.search className="h-4 w-4" />
                  Searching for duplicates…
                </div>
              )}

              {dupState === "error" && (
                <Alert
                  tone="error"
                  action={
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={busy}
                      onClick={detectDup}
                    >
                      Retry
                    </Button>
                  }
                >
                  {dupError ?? "Duplicate detection failed."}
                </Alert>
              )}

              {dupState === "done" && duplicates.length === 0 && (
                <EmptyState
                  tone="success"
                  icon={<Icon.check className="h-7 w-7" />}
                  title="No potential duplicates found"
                  description="No existing complaints met the duplicate detection threshold."
                />
              )}

              {dupState === "done" && duplicates.length > 0 && (
                <div className="rounded-xl border border-border p-3">
                  <h3 className="mb-3 text-sm font-medium text-content">
                    Possible duplicates
                    <span className="ml-1 font-normal text-content-subtle">
                      (human-confirmed, never auto-merged)
                    </span>
                  </h3>
                  <ul className="flex flex-col gap-3">
                    {duplicates.map((d) => (
                      <li
                        key={d.link_id}
                        className="rounded-lg border border-border p-2.5 text-sm"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className="truncate text-content"
                            title={d.candidate_title}
                          >
                            #{d.candidate_complaint_id} {d.candidate_title}
                          </span>
                          <span className="shrink-0 tabular-nums text-xs text-content-subtle">
                            {Math.round(d.similarity * 100)}% sim ·{" "}
                            {Math.round(d.combined_score * 100)}% score
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-content-subtle">
                          location:{" "}
                          {(d.evidence.location as { type?: string })?.type ??
                            "n/a"}{" "}
                          · status {d.candidate_status}
                        </div>
                        {d.decision === "pending" ? (
                          <div className="mt-2 flex gap-2">
                            <Button
                              variant="success"
                              size="sm"
                              loading={busy}
                              onClick={() => decideDup(d.link_id, "confirm")}
                            >
                              Confirm duplicate
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              loading={busy}
                              onClick={() => decideDup(d.link_id, "reject")}
                            >
                              Not a duplicate
                            </Button>
                          </div>
                        ) : (
                          <Badge
                            tone={
                              d.decision === "confirmed" ? "success" : "neutral"
                            }
                            className="mt-2"
                          >
                            {d.decision}
                          </Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Status management */}
              <div className="border-t border-border pt-4">
                <h3 className="mb-2 text-sm font-medium text-content">
                  Change status
                </h3>
                {NEXT[selected.status].length === 0 ? (
                  <p className="text-xs text-content-muted">
                    Terminal state — no further transitions.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {NEXT[selected.status].map((s) => (
                      <Button
                        key={s}
                        variant="secondary"
                        size="sm"
                        loading={busy}
                        onClick={() => changeStatus(s)}
                      >
                        → {s}
                      </Button>
                    ))}
                  </div>
                )}
              </div>

              {/* Timeline */}
              <div>
                <h3 className="mb-3 text-sm font-medium text-content">Timeline</h3>
                <Timeline entries={selected.status_history} />
              </div>
            </CardBody>
          )}
        </Card>
      </div>
    </Container>
  );
}

/**
 * Labeled value that renders a muted "Not assigned" placeholder when empty.
 * Readable in light and dark modes.
 */
function AssignedField({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-content-subtle">
        {label}
      </dt>
      <dd className="mt-0.5 font-medium text-content">
        {value ? (
          value
        ) : (
          <span className="font-normal italic text-content-subtle">
            Not assigned
          </span>
        )}
      </dd>
    </div>
  );
}
