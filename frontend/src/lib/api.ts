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

// ---- Analytics ----

export type CountItem = { key: string; count: number };
export type TrendPoint = { date: string; count: number };

export type AnalyticsOverview = {
  city: string;
  summary: {
    total: number;
    open: number;
    closed: number;
    avg_resolution_hours: number | null;
  };
  by_category: CountItem[];
  by_neighborhood: CountItem[];
  by_department: CountItem[];
  by_status: CountItem[];
  trend: TrendPoint[];
};

export async function getAnalyticsOverview(
  city = "boston",
  trendDays = 30,
): Promise<AnalyticsOverview> {
  const q = new URLSearchParams({ city, trend_days: String(trendDays) });
  return json<AnalyticsOverview>(
    await fetch(`${API}/analytics/overview?${q.toString()}`, {
      cache: "no-store",
    }),
  );
}

// ---- Agent / review ----

export type AgentStep = {
  id: number;
  node_name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  confidence: number | null;
  latency_ms: number | null;
};

export type Recommendation = {
  id: number;
  agent_run_id: number;
  complaint_id: number;
  extracted: Record<string, unknown>;
  category: string | null;
  category_confidence: number | null;
  priority: ComplaintPriority | null;
  priority_confidence: number | null;
  priority_rationale: string | null;
  department_slug: string | null;
  department_confidence: number | null;
  routing_evidence: Record<string, unknown>;
  overall_confidence: number | null;
  status: "pending" | "approved" | "overridden" | "rejected";
  requires_review: boolean;
  review_severity: "routine" | "low_confidence" | "high_risk";
  review_reason: string | null;
  reviewer: string | null;
  reviewed_at: string | null;
  final_category: string | null;
  final_priority: ComplaintPriority | null;
  final_department_slug: string | null;
  review_note: string | null;
  created_at: string;
};

export type AgentRunDetail = {
  id: number;
  complaint_id: number;
  graph_version: string;
  status: "running" | "completed" | "needs_review" | "failed";
  llm_provider: string;
  llm_model: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  steps: AgentStep[];
  recommendation: Recommendation | null;
};

export async function runTriage(complaintId: number): Promise<AgentRunDetail> {
  return json<AgentRunDetail>(
    await fetch(`${API}/agent/complaints/${complaintId}/triage`, {
      method: "POST",
    }),
  );
}

export async function getReviewQueue(
  cityId?: number,
): Promise<Page<Recommendation>> {
  const q = new URLSearchParams();
  if (cityId != null) q.set("city_id", String(cityId));
  return json<Page<Recommendation>>(
    await fetch(`${API}/agent/review-queue?${q.toString()}`, {
      cache: "no-store",
    }),
  );
}

export type DecisionPayload = {
  decision: "approve" | "override" | "reject";
  reviewer?: string;
  note?: string;
  category?: string;
  priority?: ComplaintPriority;
  department_slug?: string;
};

export async function decideRecommendation(
  recommendationId: number,
  payload: DecisionPayload,
): Promise<Recommendation> {
  return json<Recommendation>(
    await fetch(`${API}/agent/recommendations/${recommendationId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

// ---- Duplicates ----

export type DuplicateCandidate = {
  link_id: number;
  candidate_complaint_id: number;
  candidate_tracking_code: string;
  candidate_title: string;
  candidate_status: string;
  similarity: number;
  combined_score: number;
  evidence: Record<string, unknown>;
  decision: "pending" | "confirmed" | "rejected";
};

export async function detectDuplicates(
  complaintId: number,
): Promise<DuplicateCandidate[]> {
  return json<DuplicateCandidate[]>(
    await fetch(`${API}/duplicates/complaints/${complaintId}/detect`, {
      method: "POST",
    }),
  );
}

export async function listDuplicateCandidates(
  complaintId: number,
): Promise<DuplicateCandidate[]> {
  return json<DuplicateCandidate[]>(
    await fetch(`${API}/duplicates/complaints/${complaintId}/candidates`, {
      cache: "no-store",
    }),
  );
}

export async function decideDuplicate(
  linkId: number,
  decision: "confirm" | "reject",
  note?: string,
): Promise<DuplicateCandidate> {
  return json<DuplicateCandidate>(
    await fetch(`${API}/duplicates/links/${linkId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reviewer: "staff", note }),
    }),
  );
}

// ---- Clarifications (public, by tracking code) ----

export type PublicClarification = {
  id: number;
  field: string;
  question: string;
  status: "pending" | "answered" | "dismissed";
};

export async function listClarifications(
  trackingCode: string,
): Promise<PublicClarification[]> {
  return json<PublicClarification[]>(
    await fetch(
      `${API}/clarifications/track/${encodeURIComponent(trackingCode)}`,
      { cache: "no-store" },
    ),
  );
}

export async function answerClarification(
  clarificationId: number,
  answer: string,
): Promise<PublicClarification> {
  return json<PublicClarification>(
    await fetch(`${API}/clarifications/${clarificationId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    }),
  );
}
