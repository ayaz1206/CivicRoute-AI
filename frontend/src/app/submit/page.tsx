"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  listCities,
  submitComplaint,
  type City,
  type SubmitResult,
} from "@/lib/api";

export default function SubmitPage() {
  const [cities, setCities] = useState<City[]>([]);
  const [cityId, setCityId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [location, setLocation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmitResult | null>(null);

  useEffect(() => {
    listCities()
      .then((c) => {
        setCities(c);
        if (c.length > 0) setCityId(c[0].id);
      })
      .catch(() => setError("Could not load cities. Is the backend running?"));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (cityId === "") {
      setError("Please choose a city.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await submitComplaint({
        city_id: cityId,
        title,
        description,
        reporter_name: name || undefined,
        reporter_email: email || undefined,
        location_text: location || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <main className="mx-auto max-w-xl px-6 py-12">
        <div className="rounded-lg border border-green-300 bg-green-50 p-6">
          <h1 className="text-xl font-bold text-green-800">Complaint submitted</h1>
          <p className="mt-2 text-sm text-green-900">
            Save your tracking code to follow progress:
          </p>
          <p className="my-4 text-center text-2xl font-mono font-bold tracking-wider">
            {result.tracking_code}
          </p>
          <div className="flex gap-3 text-sm">
            <Link
              href={`/track?code=${result.tracking_code}`}
              className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              Track this complaint
            </Link>
            <button
              onClick={() => {
                setResult(null);
                setTitle("");
                setDescription("");
                setLocation("");
              }}
              className="rounded border px-4 py-2 hover:bg-gray-50"
            >
              Submit another
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-12">
      <h1 className="text-2xl font-bold">Submit a complaint</h1>
      <p className="mt-1 text-sm opacity-70">
        Report an issue. You&apos;ll receive a tracking code to follow progress.
      </p>

      {error && (
        <div className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          City
          <select
            value={cityId}
            onChange={(e) => setCityId(Number(e.target.value))}
            className="rounded border px-3 py-2"
            required
          >
            {cities.length === 0 && <option value="">Loading…</option>}
            {cities.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            minLength={3}
            maxLength={200}
            required
            placeholder="e.g. Large pothole on Main St"
            className="rounded border px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            minLength={10}
            required
            rows={4}
            placeholder="Describe the issue, including any safety concerns."
            className="rounded border px-3 py-2"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          Location (optional)
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            maxLength={300}
            placeholder="e.g. Main St & 1st Ave"
            className="rounded border px-3 py-2"
          />
        </label>

        <div className="grid grid-cols-2 gap-4">
          <label className="flex flex-col gap-1 text-sm">
            Your name (optional)
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={120}
              className="rounded border px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Email (optional)
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded border px-3 py-2"
            />
          </label>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Submitting…" : "Submit complaint"}
        </button>
      </form>
    </main>
  );
}
