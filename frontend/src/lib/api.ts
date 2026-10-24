/**
 * Backend API client for CivicRoute AI (M1).
 * Covers health, cities, and the complaint lifecycle.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const API = `${API_URL}/api`;

// ---- Types (mirror backend schemas) ----

export type HealthStatus = { status: string; version?: string };

export type City = { id: number; name: string; slug: string; timezone: string };

export type Department = {
  id: number;
  city_id: number;
  name: string;
  slug: string;
  category_tags: string[];
  contact_email: string | null;
};

export type ComplaintStatus =
  | "submitted"
  | "triaged"
  | "in_progress"
  | "resolved"
  | "closed"
  | "rejected";

export type ComplaintPriority = "low" | "medium" | "high" | "urgent";

export type StatusHistoryEntry = {
  id: number;
  from_status: ComplaintStatus | null;
  to_status: ComplaintStatus;
  actor: string;
  note: string | null;
  created_at: string;
};

export type Complaint = {
  id: number;
  tracking_code: string;
  city_id: number;
  source: string;
  status: ComplaintStatus;
  title: string;
  description: string;
  reporter_name: string | null;
  reporter_email: string | null;
  location_text: string | null;
  latitude: number | null;
  longitude: number | null;
  category: string | null;
  priority: ComplaintPriority | null;
  department_id: number | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ComplaintDetail = Complaint & {
  status_history: StatusHistoryEntry[];
};

/** PII-free public view returned by the tracking endpoint. */
export type ComplaintPublic = {
  tracking_code: string;
  status: ComplaintStatus;
  title: string;
  description: string;
  location_text: string | null;
  category: string | null;
  priority: ComplaintPriority | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  status_history: StatusHistoryEntry[];
};

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type SubmitResult = {
  id: number;
  tracking_code: string;
  status: ComplaintStatus;
};

// ---- Error handling ----

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore parse failure */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// ---- Endpoints ----

export async function getHealth(): Promise<HealthStatus | null> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as HealthStatus;
  } catch {
    return null;
  }
}

export async function listCities(): Promise<City[]> {
  return json<City[]>(await fetch(`${API}/cities`, { cache: "no-store" }));
}

export async function listDepartments(cityId: number): Promise<Department[]> {
  return json<Department[]>(
    await fetch(`${API}/cities/${cityId}/departments`, { cache: "no-store" }),
  );
}

export type SubmitPayload = {
  city_id: number;
  title: string;
  description: string;
  reporter_name?: string;
  reporter_email?: string;
  location_text?: string;
};

export async function submitComplaint(
  payload: SubmitPayload,
): Promise<SubmitResult> {
  return json<SubmitResult>(
    await fetch(`${API}/complaints`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function trackComplaint(code: string): Promise<ComplaintPublic> {
  return json<ComplaintPublic>(
    await fetch(`${API}/complaints/track/${encodeURIComponent(code)}`, {
      cache: "no-store",
    }),
  );
}

export async function listComplaints(params: {
  cityId?: number;
  status?: ComplaintStatus;
  limit?: number;
  offset?: number;
}): Promise<Page<Complaint>> {
  const q = new URLSearchParams();
  if (params.cityId != null) q.set("city_id", String(params.cityId));
  if (params.status) q.set("status", params.status);
  if (params.limit != null) q.set("limit", String(params.limit));
  if (params.offset != null) q.set("offset", String(params.offset));
  return json<Page<Complaint>>(
    await fetch(`${API}/complaints?${q.toString()}`, { cache: "no-store" }),
  );
}

export async function updateStatus(
  complaintId: number,
  status: ComplaintStatus,
  note?: string,
): Promise<ComplaintDetail> {
  return json<ComplaintDetail>(
    await fetch(`${API}/complaints/${complaintId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, note }),
    }),
  );
}
