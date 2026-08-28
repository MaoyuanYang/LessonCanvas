export interface Project {
  id: string;
  name: string;
  unit_hints: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  unit_hints?: string | null;
}

export type ApiErrorCode =
  | "AUTH_REQUIRED"
  | "NOT_FOUND"
  | "REQUIREMENT"
  | "SOURCE_POLICY"
  | "STALE_VERSION"
  | "QUOTA_EXCEEDED"
  | "PROVIDER_TRANSIENT"
  | "PARTIAL_RECOVERY"
  | "UNEXPECTED";

export class ApiClientError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly correlationId: string | null;
  readonly details: Record<string, unknown>;

  constructor(
    code: ApiErrorCode,
    message: string,
    status: number,
    correlationId: string | null,
    details: Record<string, unknown>,
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.correlationId = correlationId;
    this.details = details;
  }
}

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

interface ApiFetchOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token: string | null;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions): Promise<T> {
  const { method = "GET", body, token } = options;
  const headers: Record<string, string> = { accept: "application/json" };
  if (body !== undefined) headers["content-type"] = "application/json";
  if (token) headers.authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("UNEXPECTED", "network unavailable", 0, null, {});
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = payload?.error ?? {};
    throw new ApiClientError(
      errorBody.code ?? "UNEXPECTED",
      errorBody.message ?? "request failed",
      response.status,
      errorBody.correlation_id ?? null,
      errorBody.details ?? {},
    );
  }

  return payload as T;
}

export async function listProjects(token: string | null): Promise<Project[]> {
  return apiFetch<Project[]>("/projects", { token });
}

export async function createProject(
  token: string | null,
  input: ProjectCreateInput,
): Promise<Project> {
  return apiFetch<Project>("/projects", { method: "POST", body: input, token });
}

export async function deleteProject(token: string | null, projectId: string): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}`, { method: "DELETE", token });
}

export interface Source {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  rejection_code: string | null;
  rejection_message: string | null;
  rights_acknowledged: boolean;
  created_at: string;
  updated_at: string;
}

export async function listSources(token: string | null, projectId: string): Promise<Source[]> {
  return apiFetch<Source[]>(`/projects/${projectId}/sources`, { token });
}

export async function uploadSource(
  token: string | null,
  projectId: string,
  file: File,
  rightsAcknowledged: boolean,
): Promise<Source> {
  const form = new FormData();
  form.append("file", file);
  form.append("rights_acknowledged", String(rightsAcknowledged));
  const headers: Record<string, string> = {};
  if (token) headers.authorization = `Bearer ${token}`;
  const response = await fetch(`${apiBaseUrl()}/projects/${projectId}/sources`, {
    method: "POST",
    headers,
    body: form,
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const errorBody = payload?.error ?? {};
    throw new ApiClientError(
      errorBody.code ?? "UNEXPECTED",
      errorBody.message ?? "upload failed",
      response.status,
      errorBody.correlation_id ?? null,
      errorBody.details ?? {},
    );
  }
  return payload as Source;
}

export async function deleteSource(
  token: string | null,
  projectId: string,
  sourceId: string,
): Promise<void> {
  return apiFetch<void>(`/projects/${projectId}/sources/${sourceId}`, { method: "DELETE", token });
}

export interface DiscoveryStatus {
  run_id: string;
  status: string;
  round_count: number;
  questions: { field: string; question: string }[];
  draft: Record<
    string,
    { value: string | null; grounding: string | null; unresolved: boolean }
  > | null;
}

export async function discoveryStart(token: string | null, projectId: string) {
  return apiFetch<DiscoveryStatus>(`/projects/${projectId}/discovery/start`, {
    method: "POST",
    token,
  });
}

export async function discoveryStatus(token: string | null, projectId: string) {
  return apiFetch<DiscoveryStatus>(`/projects/${projectId}/discovery`, { token });
}

export async function discoveryAnswers(
  token: string | null,
  projectId: string,
  answers: Record<string, string>,
) {
  return apiFetch<DiscoveryStatus>(`/projects/${projectId}/discovery/answers`, {
    method: "POST",
    body: { answers },
    token,
  });
}

export type ConversationKind = "discovery" | "planning";

export async function narrate(
  token: string | null,
  projectId: string,
  text: string,
  kind: ConversationKind = "discovery",
) {
  return apiFetch<{ run_id: string; started: boolean }>(
    `/projects/${projectId}/${kind}/narrate`,
    {
      method: "POST",
      body: { text },
      token,
    },
  );
}

export async function stopNarration(
  token: string | null,
  projectId: string,
  kind: ConversationKind = "discovery",
) {
  return apiFetch<{ stopped: boolean }>(`/projects/${projectId}/${kind}/stop-narration`, {
    method: "POST",
    token,
  });
}

export async function reask(
  token: string | null,
  projectId: string,
  text: string,
  kind: ConversationKind = "discovery",
) {
  return apiFetch<{ run_id: string; started: boolean }>(
    `/projects/${projectId}/${kind}/reask`,
    {
      method: "POST",
      body: { text },
      token,
    },
  );
}

export interface BriefState {
  draft_revision: number | null;
  fields: Record<
    string,
    { value: string | null; grounding: string | null; unresolved: boolean }
  > | null;
  confirmed_version: number | null;
  confirmed_fields: Record<
    string,
    { value: string | null; grounding: string | null; unresolved: boolean }
  > | null;
}

export async function getBrief(token: string | null, projectId: string) {
  return apiFetch<BriefState>(`/projects/${projectId}/brief`, { token });
}

export async function patchDraft(
  token: string | null,
  projectId: string,
  fields: Record<string, string>,
  baseRevision: number,
) {
  return apiFetch<BriefState>(`/projects/${projectId}/brief/draft`, {
    method: "PATCH",
    body: { fields, base_revision: baseRevision },
    token,
  });
}

export async function confirmBrief(token: string | null, projectId: string) {
  return apiFetch<{ version: number; fields: BriefState["fields"] }>(
    `/projects/${projectId}/brief/confirm`,
    { method: "POST", token },
  );
}

export function streamUrl(projectId: string, offset = 0, kind: ConversationKind = "discovery") {
  return `${apiBaseUrl()}/projects/${projectId}/${kind}/stream?offset=${offset}`;
}

export interface PlanningStatus {
  run_id: string;
  status: string;
  round_count: number;
  questions: { field: string; question: string }[];
  draft: BlueprintPayload | null;
}

export async function planningStart(token: string | null, projectId: string) {
  return apiFetch<PlanningStatus>(`/projects/${projectId}/planning/start`, {
    method: "POST",
    token,
  });
}

export async function planningStatus(token: string | null, projectId: string) {
  return apiFetch<PlanningStatus>(`/projects/${projectId}/planning`, { token });
}

export async function planningAnswers(
  token: string | null,
  projectId: string,
  answers: Record<string, string>,
) {
  return apiFetch<PlanningStatus>(`/projects/${projectId}/planning/answers`, {
    method: "POST",
    body: { answers },
    token,
  });
}

export async function planningRetry(token: string | null, projectId: string) {
  return apiFetch<PlanningStatus>(`/projects/${projectId}/planning/retry`, {
    method: "POST",
    token,
  });
}

export interface BlueprintCitation {
  type: "source" | "standards";
  source_id?: string | null;
  filename?: string | null;
  section_id?: string | null;
  snapshot_version?: string | null;
}

export interface BlueprintObjective {
  id: string;
  text: string;
  citations: BlueprintCitation[];
}

export interface BlueprintLesson {
  index: number;
  title: string | null;
  objective_ids: string[];
  assessment_intent: string | null;
  period_count: number | null;
  activity_outline: string | null;
  material_notes: string | null;
  citations: BlueprintCitation[];
}

export interface BlueprintFinding {
  id: string;
  tier: "blocking" | "waivable";
  kind: string;
  message: string;
  evidence: string | null;
  status: "open" | "resolved" | "decided";
  reason: string | null;
}

export interface BlueprintPayload {
  unit: {
    title: string | null;
    objectives: BlueprintObjective[];
    assessment_intent: string | null;
    citations: BlueprintCitation[];
  };
  lessons: BlueprintLesson[];
  findings: BlueprintFinding[];
}

export interface BlueprintCheck {
  id: string;
  label: string;
  passed: boolean;
  affected: Record<string, unknown>[];
}

export interface BriefDiffEntry {
  field: string;
  label: string;
  old: string | null;
  new: string | null;
}

export interface BlueprintState {
  available: boolean;
  draft_revision: number | null;
  draft: BlueprintPayload | null;
  checks: BlueprintCheck[];
  findings: BlueprintFinding[];
  confirmed_version: number | null;
  confirmed_payload: BlueprintPayload | null;
  confirmed_stale: boolean | null;
  stale: boolean;
  brief_diff: BriefDiffEntry[] | null;
  impact_summary: {
    lesson_structure_changed: boolean;
    objectives_changed: boolean;
    details_changed: boolean;
    summary: string;
  } | null;
}

export async function getBlueprint(token: string | null, projectId: string) {
  return apiFetch<BlueprintState>(`/projects/${projectId}/blueprint`, { token });
}

export async function patchBlueprintDraft(
  token: string | null,
  projectId: string,
  payload: BlueprintPayload,
  baseRevision: number,
) {
  return apiFetch<BlueprintState>(`/projects/${projectId}/blueprint/draft`, {
    method: "PATCH",
    body: { payload, base_revision: baseRevision },
    token,
  });
}

export async function recordBlueprintDecision(
  token: string | null,
  projectId: string,
  findingId: string,
  reason: string,
  baseRevision: number,
) {
  return apiFetch<BlueprintState>(`/projects/${projectId}/blueprint/decisions`, {
    method: "POST",
    body: { finding_id: findingId, reason, base_revision: baseRevision },
    token,
  });
}

export async function confirmBlueprint(
  token: string | null,
  projectId: string,
  baseRevision: number,
) {
  return apiFetch<{ version: number; payload: BlueprintPayload }>(
    `/projects/${projectId}/blueprint/confirm`,
    { method: "POST", body: { base_revision: baseRevision }, token },
  );
}
