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

export async function narrate(token: string | null, projectId: string, text: string) {
  return apiFetch<{ run_id: string; started: boolean }>(
    `/projects/${projectId}/discovery/narrate`,
    {
      method: "POST",
      body: { text },
      token,
    },
  );
}

export async function stopNarration(token: string | null, projectId: string) {
  return apiFetch<{ stopped: boolean }>(`/projects/${projectId}/discovery/stop-narration`, {
    method: "POST",
    token,
  });
}

export async function reask(token: string | null, projectId: string, text: string) {
  return apiFetch<{ run_id: string; started: boolean }>(`/projects/${projectId}/discovery/reask`, {
    method: "POST",
    body: { text },
    token,
  });
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

export function streamUrl(projectId: string, offset = 0): string {
  return `${apiBaseUrl()}/projects/${projectId}/discovery/stream?offset=${offset}`;
}
