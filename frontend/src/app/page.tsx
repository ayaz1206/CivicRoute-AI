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
          Milestone M0 — Foundation
        </span>
      </header>

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

      <footer className="text-xs opacity-50">
        Resident submission, AI classification, routing, and analytics arrive in
        later milestones.
      </footer>
    </main>
  );
}
