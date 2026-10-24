/**
 * Minimal backend API client for M0.
 * Only the health endpoint is wired up at this milestone.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthStatus = {
  status: string;
  version?: string;
};

/** Fetch backend liveness. Returns null if the backend is unreachable. */
export async function getHealth(): Promise<HealthStatus | null> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as HealthStatus;
  } catch {
    return null;
  }
}
