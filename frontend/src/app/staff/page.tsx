"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listCities,
  listComplaints,
  runTriage,
  trackComplaint,
  updateStatus,
  type City,
  type Complaint,
  type ComplaintPublic,
  type ComplaintStatus,
} from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";

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
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<ComplaintPublic | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listCities()
      .then((c) => {
        setCities(c);
        if (c.length > 0) setCityId(c[0].id);
      })
      .catch(() => setError("Could not load cities. Is the backend running?"));
  }, []);

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
      setError(err instanceof Error ? err.message : "Failed to load complaints.");
    }
  }, [cityId, status]);

  useEffect(() => {
    if (cityId !== "") refresh();
  }, [cityId, status, refresh]);

  async function openDetail(id: number) {
    const found = complaints.find((c) => c.id === id);
    if (found) {
      try {
        setSelectedId(id);
        setSelected(await trackComplaint(found.tracking_code));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load detail.");
      }
    }
  }

  async function changeStatus(next: ComplaintStatus) {
    if (selectedId == null) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateStatus(selectedId, next);
      // Re-use the PII-free public projection for display consistency.
      setSelected(updated);
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
    try {
      const run = await runTriage(selectedId);
      const r = run.recommendation;
      const msg = r
        ? `AI run ${run.status}: ${r.category ?? "?"} / ${r.priority ?? "?"} / ${
            r.department_slug ?? "no dept"
          }${r.requires_review ? " — sent to AI Review queue" : ""}`
        : `AI run ${run.status}${run.error ? `: ${run.error}` : ""}`;
      setError(msg); // reuse the banner as a status line
    } catch (err) {
      setError(err instanceof Error ? err.message : "Triage failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-2xl font-bold">Staff dashboard</h1>
      <p className="mt-1 text-sm opacity-70">
        Live complaints only. Historical 311 data is kept separate.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          City
          <select
            value={cityId}
            onChange={(e) => setCityId(Number(e.target.value))}
            className="rounded border px-3 py-2"
          >
            {cities.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Status
          <select
            value={status}
            onChange={(e) =>
              setStatus(e.target.value as ComplaintStatus | "")
            }
            className="rounded border px-3 py-2"
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={refresh}
          className="rounded border px-4 py-2 text-sm hover:bg-gray-50"
        >
          Refresh
        </button>
        <span className="text-sm opacity-60">{total} total</span>
      </div>

      {error && (
        <div className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase opacity-60">
              <tr>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {complaints.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center opacity-60">
                    No complaints.
                  </td>
                </tr>
              )}
              {complaints.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => openDetail(c.id)}
                  className={`cursor-pointer border-t hover:bg-blue-50 ${
                    selectedId === c.id ? "bg-blue-50" : ""
                  }`}
                >
                  <td className="px-4 py-2 font-mono text-xs">
                    {c.tracking_code}
                  </td>
                  <td className="px-4 py-2">{c.title}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-lg border p-5">
          {!selected ? (
            <p className="text-sm opacity-60">
              Select a complaint to view details and manage its status.
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">{selected.title}</h2>
                <StatusBadge status={selected.status} />
              </div>
              <p className="text-sm opacity-80">{selected.description}</p>

              <div>
                <button
                  disabled={busy}
                  onClick={triage}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  Run AI triage
                </button>
                <p className="mt-1 text-xs opacity-50">
                  Generates an AI recommendation (does not change the complaint
                  until approved in AI Review).
                </p>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-medium">Change status</h3>
                {NEXT[selected.status].length === 0 ? (
                  <p className="text-xs opacity-60">
                    Terminal state — no further transitions.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {NEXT[selected.status].map((s) => (
                      <button
                        key={s}
                        disabled={busy}
                        onClick={() => changeStatus(s)}
                        className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
                      >
                        → {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h3 className="mb-3 text-sm font-medium">Timeline</h3>
                <Timeline entries={selected.status_history} />
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
