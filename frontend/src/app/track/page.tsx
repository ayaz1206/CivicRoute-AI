"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  trackComplaint,
  type ComplaintPublic,
} from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";

function TrackInner() {
  const params = useSearchParams();
  const [code, setCode] = useState("");
  const [complaint, setComplaint] = useState<ComplaintPublic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function lookup(c: string) {
    setError(null);
    setComplaint(null);
    if (!c.trim()) return;
    setLoading(true);
    try {
      setComplaint(await trackComplaint(c.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lookup failed.");
    } finally {
      setLoading(false);
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
    <main className="mx-auto max-w-xl px-6 py-12">
      <h1 className="text-2xl font-bold">Track a complaint</h1>
      <p className="mt-1 text-sm opacity-70">
        Enter the tracking code you received when you submitted.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          lookup(code);
        }}
        className="mt-6 flex gap-2"
      >
        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="CR-XXXXXXXX"
          className="flex-1 rounded border px-3 py-2 font-mono"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "…" : "Track"}
        </button>
      </form>

      {error && (
        <div className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {complaint && (
        <section className="mt-8 flex flex-col gap-6">
          <div className="rounded-lg border p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{complaint.title}</h2>
              <StatusBadge status={complaint.status} />
            </div>
            <p className="mt-2 text-sm opacity-80">{complaint.description}</p>
            <dl className="mt-4 grid grid-cols-2 gap-2 text-xs opacity-70">
              <div>
                <dt className="font-medium">Tracking code</dt>
                <dd className="font-mono">{complaint.tracking_code}</dd>
              </div>
              {complaint.location_text && (
                <div>
                  <dt className="font-medium">Location</dt>
                  <dd>{complaint.location_text}</dd>
                </div>
              )}
              {complaint.category && (
                <div>
                  <dt className="font-medium">Category</dt>
                  <dd>{complaint.category}</dd>
                </div>
              )}
              <div>
                <dt className="font-medium">Submitted</dt>
                <dd>{new Date(complaint.created_at).toLocaleDateString()}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-lg border p-5">
            <h3 className="mb-4 font-semibold">Status timeline</h3>
            <Timeline entries={complaint.status_history} />
          </div>
        </section>
      )}
    </main>
  );
}

export default function TrackPage() {
  return (
    <Suspense fallback={<main className="mx-auto max-w-xl px-6 py-12">Loading…</main>}>
      <TrackInner />
    </Suspense>
  );
}
