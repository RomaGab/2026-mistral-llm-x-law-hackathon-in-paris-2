import type { DashboardDossier, FactValue } from "@/types/dashboard";

// Backend REST API (see distinguo-architecture-contrats.md §7). Inlined at build time.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string) {
    super(message);
  }
}

type CreatedCase = { id: string };

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "unreachable", `The analysis service is unreachable at ${API_URL}. Is the backend running?`);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body as { erreur?: { code?: string; message?: string } } | null)?.erreur;
    throw new ApiError(response.status, error?.code ?? "http", error?.message ?? `Request failed (${response.status}).`);
  }
  return body as T;
}

function json(body: unknown): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

/** POST /documents — a client document, stored as text for fact extraction. */
export async function uploadDocument(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  form.append("type", "cas");
  const created = await request<{ document_id: string }>("/documents", { method: "POST", body: form });
  return created.document_id;
}

/** POST /cas — Mistral extracts the facts (5 to 30 s). */
export async function createCase(input: { question: string; description: string; ressort: string | null; documentIds: string[] }): Promise<string> {
  const created = await request<CreatedCase>("/cas", json({
    question: input.question,
    description: input.description,
    ressort: input.ressort,
    document_ids: input.documentIds,
  }));
  return created.id;
}

/** POST /cas/{id}/analyse — with facts, a simulation that saves nothing. */
export function analyseCase(caseId: string, facts?: Record<string, FactValue>): Promise<DashboardDossier> {
  // No body for the baseline: an empty JSON object would fail validation (facteurs is required).
  return request<DashboardDossier>(`/cas/${encodeURIComponent(caseId)}/analyse`, facts ? json({ facteurs: facts }) : { method: "POST" });
}
