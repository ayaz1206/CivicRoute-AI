"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideRecommendation,
  getReviewQueue,
  type Recommendation,
} from "@/lib/api";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { SeverityBadge } from "@/components/SeverityBadge";

const PRIORITIES = ["low", "medium", "high", "urgent"] as const;

export default function ReviewPage() {
  const [queue, setQueue] = useState<Recommendation[]>([]);
  const [selected, setSelected] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Override form state.
  const [ovCategory, setOvCategory] = useState("");
  const [ovPriority, setOvPriority] = useState("");
  const [ovDept, setOvDept] = useState("");
  const [note, setNote] = useState("");

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const page = await getReviewQueue();
      setQueue(page.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queue.");
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

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-2xl font-bold">AI Review Queue</h1>
      <p className="mt-1 text-sm opacity-70">
        Inspect AI recommendations, evidence, and confidence. AI output is kept
        separate from complaint data until you approve or override it.
      </p>

      {error && (
        <div className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="overflow-hidden rounded-lg border">
          <div className="flex items-center justify-between border-b bg-gray-50 px-4 py-2 text-xs uppercase opacity-60">
            <span>Pending ({queue.length})</span>
            <button onClick={refresh} className="hover:underline">
              Refresh
            </button>
          </div>
          {(() => {
            const flagged = queue.filter((r) => r.review_severity !== "routine");
            const routine = queue.filter((r) => r.review_severity === "routine");
            const row = (r: Recommendation) => (
              <li
                key={r.id}
                onClick={() => select(r)}
                className={`cursor-pointer border-t px-4 py-3 text-sm hover:bg-blue-50 ${
                  selected?.id === r.id ? "bg-blue-50" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">
                    {r.category ?? "Uncategorized"}
                  </span>
                  <SeverityBadge severity={r.review_severity} />
                </div>
                <div className="mt-1 flex items-center justify-between text-xs opacity-70">
                  <span>complaint #{r.complaint_id}</span>
                  {r.review_reason && (
                    <span className="truncate pl-2" title={r.review_reason}>
                      {r.review_reason}
                    </span>
                  )}
                </div>
              </li>
            );
            return (
              <>
                {queue.length === 0 && (
                  <p className="px-4 py-6 text-center text-sm opacity-60">
                    Queue is empty.
                  </p>
                )}
                {flagged.length > 0 && (
                  <>
                    <div className="bg-red-50 px-4 py-1.5 text-xs font-semibold uppercase text-red-800">
                      Needs attention — high-risk / low-confidence ({flagged.length})
                    </div>
                    <ul>{flagged.map(row)}</ul>
                  </>
                )}
                {routine.length > 0 && (
                  <>
                    <div className="bg-gray-50 px-4 py-1.5 text-xs font-semibold uppercase opacity-60">
                      Routine — awaiting mandatory approval ({routine.length})
                    </div>
                    <ul>{routine.map(row)}</ul>
                  </>
                )}
              </>
            );
          })()}
        </div>

        <div className="rounded-lg border p-5">
          {!selected ? (
            <p className="text-sm opacity-60">
              Select a recommendation to inspect and decide.
            </p>
          ) : (
            <div className="flex flex-col gap-4 text-sm">
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold">AI recommendation</h2>
                  <SeverityBadge severity={selected.review_severity} />
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-2">
                  <Field label="Category" value={selected.category} />
                  <Field label="Priority" value={selected.priority} />
                  <Field label="Department" value={selected.department_slug} />
                  <Field
                    label="Overall"
                    value={
                      selected.overall_confidence != null
                        ? `${Math.round(selected.overall_confidence * 100)}%`
                        : "—"
                    }
                  />
                </dl>
              </div>

              <div className="flex flex-col gap-2">
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
                  <h3 className="text-xs font-medium uppercase opacity-60">
                    Priority rationale
                  </h3>
                  <p className="mt-1">{selected.priority_rationale}</p>
                </div>
              )}

              <div>
                <h3 className="text-xs font-medium uppercase opacity-60">
                  Routing evidence
                </h3>
                <pre className="mt-1 overflow-x-auto rounded bg-gray-50 p-2 text-xs">
                  {JSON.stringify(selected.routing_evidence, null, 2)}
                </pre>
              </div>

              <div>
                <h3 className="text-xs font-medium uppercase opacity-60">
                  Extracted details
                </h3>
                <pre className="mt-1 overflow-x-auto rounded bg-gray-50 p-2 text-xs">
                  {JSON.stringify(selected.extracted, null, 2)}
                </pre>
              </div>

              <div className="rounded border p-3">
                <h3 className="mb-2 text-xs font-medium uppercase opacity-60">
                  Override (optional)
                </h3>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    value={ovCategory}
                    onChange={(e) => setOvCategory(e.target.value)}
                    placeholder="category"
                    className="rounded border px-2 py-1 text-xs"
                  />
                  <select
                    value={ovPriority}
                    onChange={(e) => setOvPriority(e.target.value)}
                    className="rounded border px-2 py-1 text-xs"
                  >
                    <option value="">priority</option>
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                  <input
                    value={ovDept}
                    onChange={(e) => setOvDept(e.target.value)}
                    placeholder="dept slug"
                    className="rounded border px-2 py-1 text-xs"
                  />
                </div>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="note (optional)"
                  className="mt-2 w-full rounded border px-2 py-1 text-xs"
                />
              </div>

              <div className="flex gap-2">
                <button
                  disabled={busy}
                  onClick={() => decide("approve")}
                  className="rounded bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  disabled={busy}
                  onClick={() => decide("override")}
                  className="rounded bg-amber-600 px-4 py-2 text-white hover:bg-amber-700 disabled:opacity-50"
                >
                  Override
                </button>
                <button
                  disabled={busy}
                  onClick={() => decide("reject")}
                  className="rounded border px-4 py-2 hover:bg-gray-50 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase opacity-60">{label}</dt>
      <dd className="font-medium">{value ?? "—"}</dd>
    </div>
  );
}
