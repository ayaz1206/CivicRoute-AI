import Link from "next/link";
import { getHealth, API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const health = await getHealth();
  const online = health?.status === "ok";

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 px-6 py-16">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">CivicRoute AI</h1>
        <p className="text-sm opacity-70">
          Agentic AI-powered smart city complaint management platform.
        </p>
        <span className="mt-1 w-fit rounded-full border px-2 py-0.5 text-xs opacity-70">
          Milestone M1 — Core Complaint Management
        </span>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/submit"
          className="rounded-lg border p-5 transition hover:border-blue-400"
        >
          <h2 className="font-semibold">Submit a complaint</h2>
          <p className="mt-1 text-xs opacity-60">Report an issue in your city.</p>
        </Link>
        <Link
          href="/track"
          className="rounded-lg border p-5 transition hover:border-blue-400"
        >
          <h2 className="font-semibold">Track a complaint</h2>
          <p className="mt-1 text-xs opacity-60">Follow progress by code.</p>
        </Link>
        <Link
          href="/staff"
          className="rounded-lg border p-5 transition hover:border-blue-400"
        >
          <h2 className="font-semibold">Staff dashboard</h2>
          <p className="mt-1 text-xs opacity-60">Review and manage complaints.</p>
        </Link>
        <Link
          href="/analytics"
          className="rounded-lg border p-5 transition hover:border-blue-400"
        >
          <h2 className="font-semibold">Boston 311 analytics</h2>
          <p className="mt-1 text-xs opacity-60">
            Historical trends by category, neighborhood & department.
          </p>
        </Link>
      </section>

      <section className="rounded-lg border p-5">
        <h2 className="mb-3 text-lg font-semibold">Backend status</h2>
        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              online ? "bg-green-500" : "bg-red-500"
            }`}
            aria-hidden
          />
          <span className="text-sm">
            {online
              ? `Online — API v${health?.version ?? "?"}`
              : "Offline — start the backend and refresh"}
          </span>
        </div>
        <p className="mt-3 text-xs opacity-60">
          Checking <code>{API_URL}/health</code>
        </p>
      </section>
    </main>
  );
}
