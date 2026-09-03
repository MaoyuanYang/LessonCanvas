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
  | "RUN_ADMISSION"
  | "MEMORY_LIMIT"
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

// ADR-0006 D11: unauthenticated guest-workspace token issuance. Plain fetch,
// not apiFetch, because the caller has no token yet and errors surface as a
// simple failure to obtain one.
export interface GuestTokenResponse {
  token: string;
  subject: string;
}

export async function requestGuestToken(): Promise<GuestTokenResponse> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/auth/guest-token`, {
      method: "POST",
      headers: { accept: "application/json" },
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError("UNEXPECTED", "network unavailable", 0, null, {});
  }

  const payload = (await response.json().catch(() => null)) as GuestTokenResponse | null;
  if (!response.ok || !payload?.token) {
    throw new ApiClientError(
      "UNEXPECTED",
      "guest token request failed",
      response.status,
      null,
      {},
    );
  }
  return payload;
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

// F012 deployed portfolio proof (Spec AC-001 / U1): the sample pointer resolves
// server-side; the frontend never accepts a sample id from query params.
export interface SampleProject {
  project_id: string;
  name: string;
}

export async function getSampleProject(token: string | null): Promise<SampleProject> {
  return apiFetch<SampleProject>("/sample", { token });
}

// F011 account usage and audit surfaces (Spec AC-011 / D-USAGE / D-AUDITLIST).

export interface AccountWindowUsage {
  limit: number;
  window_seconds?: number;
  used: number;
  reset_at?: string;
  retry_after_seconds?: number;
}

export interface AccountUsage {
  request_rate: AccountWindowUsage;
  expensive_rate: AccountWindowUsage;
  concurrent_generation_runs: { limit: number; active: number };
  concurrent_sse_streams: { limit: number; active: number };
  upload_daily_bytes: AccountWindowUsage;
  projects: { limit: number; used: number };
  planning_runs: { limit: number; used: number };
  evidence_narration: { limit: number; used: number };
}

export interface AccountAuditEvent {
  action: string;
  target_type: string;
  target_id: string | null;
  created_at: string;
}

export interface AccountAuditPage {
  events: AccountAuditEvent[];
  next_before: string | null;
}

export async function getAccountUsage(token: string | null): Promise<AccountUsage> {
  return apiFetch<AccountUsage>("/account/usage", { token });
}

export async function getAccountAudit(
  token: string | null,
  limit = 50,
  before?: string,
): Promise<AccountAuditPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (before) params.set("before", before);
  return apiFetch<AccountAuditPage>(`/account/audit?${params.toString()}`, { token });
}

const GUARDRAIL_LIMIT_LABELS: Record<string, string> = {
  general: "请求速率",
  expensive: "高频写操作速率",
  upload_daily: "每日上传量",
  concurrent_sse_streams: "并发实时流",
  concurrent_generation_runs: "并发生成运行",
  projects: "项目数量",
  evidence_narration: "讲解生成",
};

/** F011 D-LIMITERR: named limit denial with recovery, never a vague toast. */
export function guardrailFeedback(err: unknown): string | null {
  if (!(err instanceof ApiClientError)) return null;
  if (err.status === 429 && err.code === "QUOTA_EXCEEDED") {
    const limit = typeof err.details.limit === "string" ? err.details.limit : "";
    const label = GUARDRAIL_LIMIT_LABELS[limit] ?? "使用限额";
    const retry = err.details.retry_after_seconds;
    const resetNote =
      typeof retry === "number" && retry > 0 ? `约 ${Math.min(Math.ceil(retry), 60)} 秒后自动恢复` : "";
    return `已达${label}上限。${resetNote}可在「账号与数据 - 使用与限额」查看用量。`;
  }
  if (err.status === 409 && err.code === "RUN_ADMISSION") {
    const active = Array.isArray(err.details.active_run_ids)
      ? err.details.active_run_ids.length
      : null;
    const count = typeof active === "number" ? `${active} 个` : "多个";
    return `已有 ${count}生成运行进行中（每个工作区最多 2 个）。可等待完成、安全停止后重试，或前往对应面板查看进行中的运行。`;
  }
  return null;
}

export interface SourceChunkView {
  position: number;
  text: string;
  embedding_status: string;
  embedding_error: string | null;
  text_sha256: string | null;
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
  content_sha256: string | null;
  chunks: SourceChunkView[];
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
  chunk_position?: number | null;
  text_sha256?: string | null;
  excerpt?: string | null;
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

export interface GenerationArtifact {
  id: string;
  lesson_index: number;
  status: string;
  language_mode: string;
  failure_reason: string | null;
  retry_count: number;
  download_url: string | null;
  citations: BlueprintCitation[];
  grounding_state: string | null;
}

export interface GenerationSnapshot {
  run_id: string;
  status: string;
  brief_version: number | null;
  blueprint_version: number | null;
  language_mode: string;
  scope_lesson_indexes?: number[] | null;
  retained_artifacts?: RetainedArtifact[];
  model_calls: number;
  model_call_cap: number;
  artifacts: GenerationArtifact[];
  complete_count: number;
  total_count: number;
}

export async function generationStart(
  token: string | null,
  projectId: string,
): Promise<GenerationSnapshot> {
  return apiFetch<GenerationSnapshot>(`/projects/${projectId}/generation/start`, {
    method: "POST",
    token,
  });
}

export async function generationStatus(
  token: string | null,
  projectId: string,
): Promise<GenerationSnapshot> {
  return apiFetch<GenerationSnapshot>(`/projects/${projectId}/generation`, { token });
}

export async function generationResume(
  token: string | null,
  projectId: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/projects/${projectId}/generation/resume`, {
    method: "POST",
    token,
  });
}

export async function downloadLessonPlan(
  token: string | null,
  projectId: string,
  artifactId: string,
): Promise<Blob> {
  const response = await fetch(
    `${apiBaseUrl()}/projects/${projectId}/lesson-plans/${artifactId}/download`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) {
    throw new ApiClientError(
      "UNEXPECTED_SYSTEM" as ApiErrorCode,
      "下载失败，请稍后重试。",
      response.status,
      null,
      {},
    );
  }
  return response.blob();
}

export interface GenerationStreamEvent {
  run_id: string;
  seq: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export function generationStreamUrl(projectId: string): string {
  return `${apiBaseUrl()}/projects/${projectId}/generation/events`;
}

export interface DeckArtifact {
  id: string;
  lesson_index: number;
  status: string;
  language_mode: string;
  slide_count: number | null;
  failure_reason: string | null;
  retry_count: number;
  download_url: string | null;
  citations: BlueprintCitation[];
  grounding_state: string | null;
}

export interface DeckGenerationSnapshot {
  run_id: string;
  status: string;
  brief_version: number | null;
  blueprint_version: number | null;
  language_mode: string;
  scope_lesson_indexes?: number[] | null;
  retained_artifacts?: RetainedArtifact[];
  model_calls: number;
  model_call_cap: number;
  artifacts: DeckArtifact[];
  complete_count: number;
  total_count: number;
}

export async function deckGenerationStart(
  token: string | null,
  projectId: string,
): Promise<DeckGenerationSnapshot> {
  return apiFetch<DeckGenerationSnapshot>(`/projects/${projectId}/decks/generation/start`, {
    method: "POST",
    token,
  });
}

export async function deckGenerationStatus(
  token: string | null,
  projectId: string,
): Promise<DeckGenerationSnapshot> {
  return apiFetch<DeckGenerationSnapshot>(`/projects/${projectId}/decks/generation`, { token });
}

export async function deckGenerationResume(
  token: string | null,
  projectId: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/projects/${projectId}/decks/generation/resume`, {
    method: "POST",
    token,
  });
}

export async function downloadSlideDeck(
  token: string | null,
  projectId: string,
  artifactId: string,
): Promise<Blob> {
  const response = await fetch(
    `${apiBaseUrl()}/projects/${projectId}/slide-decks/${artifactId}/download`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) {
    throw new ApiClientError(
      "UNEXPECTED_SYSTEM" as ApiErrorCode,
      "下载失败，请稍后重试。",
      response.status,
      null,
      {},
    );
  }
  return response.blob();
}

export function deckGenerationStreamUrl(projectId: string): string {
  return `${apiBaseUrl()}/projects/${projectId}/decks/generation/events`;
}

export type ExerciseDifficulty = "foundation" | "consolidation" | "advanced";

export const EXERCISE_DIFFICULTY_LABELS: Record<ExerciseDifficulty, string> = {
  foundation: "基础",
  consolidation: "巩固",
  advanced: "进阶",
};

export const EXERCISE_DIFFICULTY_DESCRIPTIONS: Record<ExerciseDifficulty, string> = {
  foundation: "面向课堂基础目标，覆盖核心词汇与基本理解",
  consolidation: "面向当堂巩固，强化重点句型与篇章理解",
  advanced: "面向拓展提升，侧重综合运用与表达输出",
};

export interface ExerciseArtifact {
  id: string;
  lesson_index: number;
  status: string;
  language_mode: string;
  category_count: number | null;
  item_count: number | null;
  failure_reason: string | null;
  retry_count: number;
  exercise_download_url: string | null;
  answer_download_url: string | null;
  citations: BlueprintCitation[];
  grounding_state: string | null;
}

export interface ExerciseGenerationSnapshot {
  run_id: string;
  status: string;
  brief_version: number | null;
  blueprint_version: number | null;
  language_mode: string;
  difficulty: ExerciseDifficulty | null;
  scope_lesson_indexes?: number[] | null;
  retained_artifacts?: RetainedArtifact[];
  model_calls: number;
  model_call_cap: number;
  artifacts: ExerciseArtifact[];
  complete_count: number;
  total_count: number;
}

export async function exerciseGenerationStart(
  token: string | null,
  projectId: string,
  difficulty: ExerciseDifficulty,
): Promise<ExerciseGenerationSnapshot> {
  return apiFetch<ExerciseGenerationSnapshot>(`/projects/${projectId}/exercises/generation/start`, {
    method: "POST",
    body: { difficulty },
    token,
  });
}

export async function exerciseGenerationStatus(
  token: string | null,
  projectId: string,
): Promise<ExerciseGenerationSnapshot> {
  return apiFetch<ExerciseGenerationSnapshot>(`/projects/${projectId}/exercises/generation`, {
    token,
  });
}

export async function exerciseGenerationResume(
  token: string | null,
  projectId: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/projects/${projectId}/exercises/generation/resume`, {
    method: "POST",
    token,
  });
}

export async function downloadExerciseFile(
  token: string | null,
  projectId: string,
  artifactId: string,
  file: "exercise" | "answer",
): Promise<Blob> {
  const response = await fetch(
    `${apiBaseUrl()}/projects/${projectId}/exercises/${artifactId}/download?file=${file}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) {
    throw new ApiClientError(
      "UNEXPECTED_SYSTEM" as ApiErrorCode,
      "下载失败，请稍后重试。",
      response.status,
      null,
      {},
    );
  }
  return response.blob();
}

export function exerciseGenerationStreamUrl(projectId: string): string {
  return `${apiBaseUrl()}/projects/${projectId}/exercises/generation/events`;
}

export type EvidenceRunKind =
  | "discovery"
  | "planning"
  | "lesson_plan"
  | "slide_deck"
  | "exercise";

export const EVIDENCE_KIND_LABELS: Record<EvidenceRunKind, string> = {
  discovery: "需求访谈",
  planning: "蓝图规划",
  lesson_plan: "教案生成",
  slide_deck: "课件生成",
  exercise: "练习生成",
};

export const INTERVIEW_STATUS_LABELS: Record<string, string> = {
  initializing: "初始化中",
  questioning: "提问中",
  draft_ready: "草稿就绪",
  provider_failed: "模型服务失败",
};

export const EVIDENCE_EVENT_LABELS: Record<string, string> = {
  "model.gap_analysis": "模型调用·需求缺口分析",
  "model.build_draft": "模型调用·起草简报",
  "model.planning_gap_analysis": "模型调用·规划缺口分析",
  "model.planning_build_draft": "模型调用·起草蓝图",
  "model.generation_write_lesson": "模型调用·撰写教案",
  "model.generation_write_deck": "模型调用·撰写课件",
  "model.generation_write_exercises": "模型调用·撰写练习",
  "model.narration": "模型调用·叙述",
  "model.evidence_narration": "模型调用·任务讲解",
  "tool.standards_search": "工具调用·课标检索",
  "retrieval.semantic_search": "语义检索",
  "tool.render_lesson_plan_docx": "工具调用·渲染教案文档",
  "tool.validate_lesson_plan_docx": "工具调用·校验教案文档",
  "tool.render_lesson_deck_pptx": "工具调用·渲染课件文档",
  "tool.validate_lesson_deck_pptx": "工具调用·校验课件文档",
  "tool.render_lesson_exercises_docx": "工具调用·渲染练习文档",
  "tool.validate_exercise_pair": "工具调用·校验练习配对",
  run: "运行状态",
  phase: "阶段",
  lesson: "课程",
  interview_round: "访谈轮次",
};

export interface EvidenceRunRow {
  run_id: string;
  kind: EvidenceRunKind;
  status: string;
  created_at: string;
  cursor: string;
  model_calls: number;
  model_call_cap: number | null;
  round_count: number | null;
  brief_version: number | null;
  blueprint_version: number | null;
  difficulty: string | null;
  language_mode: string | null;
  complete_count: number | null;
  total_count: number | null;
  cost_usd_estimated: number;
  cost_estimate_complete: boolean;
  model_latency_ms_total: number;
  trace_event_count: number;
  model_call_count: number;
  tool_call_count: number;
  evidence_kinds: string[];
  telemetry_gaps: string[];
}

export interface EvidenceInventory {
  runs: EvidenceRunRow[];
  next_cursor: string | null;
}

export interface EvidenceArtifactRow {
  id: string;
  lesson_index: number;
  status: string;
  failure_reason: string | null;
  retry_count: number;
  slide_count?: number | null;
  category_count?: number | null;
  item_count?: number | null;
}

export interface EvidenceRunDetail extends EvidenceRunRow {
  updated_at: string;
  artifacts: EvidenceArtifactRow[];
  interview_message_count: number | null;
  superseded_by: { brief_version: number | null; blueprint_version: number | null } | null;
  recovery_view: string | null;
  /** F013: the run's snapshot-once applied-memory section (null before
   * memory surfaces existed for the run's family). */
  memory: MemoryEffective | null;
}

export interface EvidenceEvent {
  cursor: string;
  source: "trace" | "run_event" | "interview";
  event_type: string;
  created_at: string;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_usd: number | null;
  model: string | null;
  lesson_index: number | null;
  payload: Record<string, unknown>;
}

export interface EvidenceEventsPage {
  run_id: string;
  events: EvidenceEvent[];
  next_cursor: string | null;
}

export async function evidenceInventory(
  token: string | null,
  projectId: string,
  after?: string,
): Promise<EvidenceInventory> {
  const query = after ? `?after=${encodeURIComponent(after)}` : "";
  return apiFetch<EvidenceInventory>(`/projects/${projectId}/evidence${query}`, { token });
}

export async function evidenceRunSummary(
  token: string | null,
  projectId: string,
  runId: string,
): Promise<EvidenceRunDetail> {
  return apiFetch<EvidenceRunDetail>(`/projects/${projectId}/evidence/${runId}`, { token });
}

export async function evidenceRunEvents(
  token: string | null,
  projectId: string,
  runId: string,
  options: { after?: string; limit?: number; kind?: string } = {},
): Promise<EvidenceEventsPage> {
  const params = new URLSearchParams();
  if (options.after) params.set("after", options.after);
  if (options.limit) params.set("limit", String(options.limit));
  if (options.kind) params.set("kind", options.kind);
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<EvidenceEventsPage>(
    `/projects/${projectId}/evidence/${runId}/events${query}`,
    { token },
  );
}

export async function evidenceNarrate(
  token: string | null,
  projectId: string,
  runId: string,
): Promise<{ run_id: string; started: boolean }> {
  return apiFetch<{ run_id: string; started: boolean }>(
    `/projects/${projectId}/evidence/${runId}/narrate`,
    { method: "POST", token },
  );
}

export async function evidenceNarrateStop(
  token: string | null,
  projectId: string,
  runId: string,
): Promise<{ stopped: boolean }> {
  return apiFetch<{ stopped: boolean }>(
    `/projects/${projectId}/evidence/${runId}/narrate/stop`,
    { method: "POST", token },
  );
}

export function evidenceNarrateStreamUrl(projectId: string, runId: string): string {
  return `${apiBaseUrl()}/projects/${projectId}/evidence/${runId}/narrate/stream`;
}

export interface RetainedArtifact {
  id: string;
  lesson_index: number;
  source_brief_version: number | null;
  source_blueprint_version: number | null;
  source_run_id: string;
  checksum: string | null;
  download_available: boolean;
}

export interface ImpactPreview {
  affected_lessons: number[] | null;
  affected_families: string[];
  reasons: { field: string; scope: string; detail: string }[];
  structural: { added: number[]; removed: number[] };
  uncertain: boolean;
  no_delta: boolean;
}

export interface VersionTransition {
  first_version: boolean;
  from: { brief_version: number; blueprint_version: number } | null;
  to: { brief_version: number; blueprint_version: number } | null;
  intent_diff: { field: string; old: string | null; new: string | null }[];
  verdicts?: { lesson_index: number; family: string; verdict: string; reason: string | null }[];
  artifacts?: {
    lesson_index: number;
    family: string;
    old: { status: string | null; download_available: boolean };
    new: { status: string | null; download_available: boolean };
  }[];
}

export async function getImpact(token: string | null, projectId: string): Promise<ImpactPreview> {
  return apiFetch<ImpactPreview>(`/projects/${projectId}/impact`, { token });
}

export async function getCurrentTransition(
  token: string | null,
  projectId: string,
): Promise<VersionTransition> {
  return apiFetch<VersionTransition>(`/projects/${projectId}/versions/current-transition`, {
    token,
  });
}

// --- F008 Alignment Review and Delivery ---

export interface AlignmentMemberFile {
  role: string;
  object_key: string;
  checksum: string | null;
}

export interface AlignmentMember {
  state: "complete" | "failed" | "in_progress" | "missing";
  provenance?: string;
  artifact_id?: string;
  run_id?: string;
  failure_reason?: string | null;
  files?: AlignmentMemberFile[];
}

export interface AlignmentFinding {
  key: string;
  kind: "gap" | "conflict" | "coverage";
  severity: "severe" | "warning";
  title: string;
  scope: string;
  lesson_index?: number;
  family?: string;
  objective_id?: string;
  evidence?: Record<string, unknown>;
  overridable: boolean;
  resolved: boolean;
  override_id?: string;
  recovery_action: string;
}

export interface AlignmentOverride {
  id: string;
  finding_key: string;
  reason: string;
  status: "recorded" | "withdrawn";
  created_at: string;
  withdrawn_at: string | null;
}

export interface AlignmentObjectiveCoverage {
  id: string;
  text: string | null;
  lessons: number[];
  support: Record<string, boolean>;
  summary: "supported" | "partial" | "missing";
}

export interface AlignmentView {
  brief_version: number;
  blueprint_version: number;
  brief_version_id: string;
  blueprint_version_id: string;
  technical_status: "incomplete" | "validated";
  draft_export_available: boolean;
  product_validation_status: string;
  objectives: AlignmentObjectiveCoverage[];
  lessons: {
    lesson_index: number;
    title: string | null;
    members: Record<string, AlignmentMember>;
  }[];
  findings: AlignmentFinding[];
  overrides: AlignmentOverride[];
  generated_at?: string;
}

export interface DeliveryExportRow {
  id: string;
  label: "draft" | "validated";
  status: "building" | "ready" | "failed";
  brief_version: number;
  blueprint_version: number;
  manifest_digest: string;
  failure_reason: string | null;
  created_at: string;
  ready_at: string | null;
  download_available: boolean;
}

export async function getAlignment(token: string | null, projectId: string): Promise<AlignmentView> {
  return apiFetch<AlignmentView>(`/projects/${projectId}/alignment`, { token });
}

export async function getAlignmentReport(
  token: string | null,
  projectId: string,
): Promise<AlignmentView> {
  return apiFetch<AlignmentView>(`/projects/${projectId}/alignment/report`, { token });
}

export async function getExportReport(
  token: string | null,
  projectId: string,
  exportId: string,
): Promise<AlignmentView> {
  return apiFetch<AlignmentView>(`/projects/${projectId}/delivery/exports/${exportId}/report`, {
    token,
  });
}

export async function recordAlignmentOverride(
  token: string | null,
  projectId: string,
  findingKey: string,
  reason: string,
): Promise<AlignmentOverride> {
  return apiFetch<AlignmentOverride>(`/projects/${projectId}/alignment/overrides`, {
    method: "POST",
    body: { finding_key: findingKey, reason },
    token,
  });
}

export async function withdrawAlignmentOverride(
  token: string | null,
  projectId: string,
  overrideId: string,
): Promise<AlignmentOverride> {
  return apiFetch<AlignmentOverride>(
    `/projects/${projectId}/alignment/overrides/${overrideId}`,
    { method: "DELETE", token },
  );
}

export async function createDeliveryExport(
  token: string | null,
  projectId: string,
  label: "draft" | "validated",
): Promise<DeliveryExportRow> {
  return apiFetch<DeliveryExportRow>(`/projects/${projectId}/delivery/exports`, {
    method: "POST",
    body: { label },
    token,
  });
}

export async function listDeliveryExports(
  token: string | null,
  projectId: string,
): Promise<DeliveryExportRow[]> {
  return apiFetch<DeliveryExportRow[]>(`/projects/${projectId}/delivery/exports`, { token });
}

export async function downloadDeliveryExport(
  token: string | null,
  projectId: string,
  exportId: string,
): Promise<Blob> {
  const response = await fetch(
    `${apiBaseUrl()}/projects/${projectId}/delivery/exports/${exportId}/download`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) {
    throw new ApiClientError(
      "UNEXPECTED_SYSTEM" as ApiErrorCode,
      "下载失败，请稍后重试。",
      response.status,
      null,
      {},
    );
  }
  return response.blob();
}

// --- F009 Technical Portfolio Evaluation ---

export interface TechnicalEvaluationCriterion {
  criterion_key: string;
  classification: "blocking" | "diagnostic";
  outcome: "pass" | "fail" | "missing_evidence" | null;
  measured: Record<string, unknown> | null;
  evidence: Record<string, unknown>;
}

export interface TechnicalEvaluationPass {
  evaluation_id: string;
  unit_key: string;
  pass_index: number;
  mode: "live" | "deterministic";
  scenario: string;
  status: string;
  overall_outcome: "pass" | "fail" | "missing_evidence" | null;
  failure_reason: string | null;
  dataset_revision: string;
  superseded_configuration: boolean;
  model_config: Record<string, unknown>;
  memory_state: Record<string, unknown>;
  brief_version_id: string | null;
  blueprint_version_id: string | null;
  created_at: string | null;
  completed_at: string | null;
  criteria: TechnicalEvaluationCriterion[];
}

export interface TechnicalEvaluationOverview {
  dataset_revision: string | null;
  dataset_governance_error: string | null;
  passes: TechnicalEvaluationPass[];
}

export interface TechnicalEvaluationComparison {
  evaluation_id: string;
  unit_key: string;
  pass_index: number;
  comparison_available: boolean;
  comparison_unavailable_reason: string | null;
  comparable_pass_indexes: number[];
}

export interface TechnicalEvaluationReport {
  dataset_revision: string | null;
  dataset_governance_error: string | null;
  passes: TechnicalEvaluationPass[];
  comparisons: TechnicalEvaluationComparison[];
  blocking_criterion_outcomes: Record<string, string[]>;
  overall_outcome: "pass" | "fail" | "missing_evidence" | null;
  product_validation_status: string;
  technical_note: string;
}

export async function technicalEvaluationOverview(
  token: string | null,
  projectId: string,
): Promise<TechnicalEvaluationOverview> {
  return apiFetch<TechnicalEvaluationOverview>(
    `/projects/${projectId}/technical-evaluation`,
    { token },
  );
}

export async function technicalEvaluationCreate(
  token: string | null,
  projectId: string,
  input: { unit_key: string; pass_index: number; mode: "live" | "deterministic"; scenario?: string },
): Promise<{ evaluation: TechnicalEvaluationPass; created: boolean }> {
  return apiFetch<{ evaluation: TechnicalEvaluationPass; created: boolean }>(
    `/projects/${projectId}/technical-evaluation/runs`,
    { method: "POST", body: input, token },
  );
}

export async function technicalEvaluationRunDetail(
  token: string | null,
  projectId: string,
  evaluationId: string,
): Promise<TechnicalEvaluationPass> {
  return apiFetch<TechnicalEvaluationPass>(
    `/projects/${projectId}/technical-evaluation/runs/${evaluationId}`,
    { token },
  );
}

export async function technicalEvaluationReport(
  token: string | null,
  projectId: string,
): Promise<TechnicalEvaluationReport> {
  return apiFetch<TechnicalEvaluationReport>(
    `/projects/${projectId}/technical-evaluation/report`,
    { token },
  );
}

export const EVALUATION_STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  active: "进行中",
  partial_evidence: "部分证据",
  completed: "已完成",
  provider_unavailable: "供应商不可用",
  failed: "失败",
};

export const EVALUATION_OUTCOME_LABELS: Record<string, string> = {
  pass: "通过",
  fail: "未通过",
  missing_evidence: "证据缺失",
};

export const EVALUATION_UNIT_LABELS: Record<string, string> = {
  "travelling-around": "环游世界（英文输出）",
  "natural-disasters": "自然灾害（中文输出）",
  "cultural-heritage": "文化遗产（双语输出）",
};

export const EVALUATION_MODE_LABELS: Record<string, string> = {
  deterministic: "确定性（脚本模型）",
  live: "真实模型",
};

export const EVALUATION_CRITERION_LABELS: Record<string, string> = {
  "C-TRACE-1": "执行轨迹完整",
  "C-GROUND-1": "引用可解析",
  "C-ART-1": "产物族完整",
  "C-IDEM-1": "重复提交幂等",
  "C-SUPER-1": "版本取代安全",
  "C-RECOV-1": "故障恢复不重复计费",
  "C-RENDER-1": "截断输出显式失败",
  "C-MEM-1": "记忆状态已钉扎",
  "M-LAT": "延迟分布",
  "M-COST": "成本估算",
  "M-VAR": "跨遍方差",
  "M-COVER": "对齐覆盖深度",
  "M-JUDGE": "模型评判意见",
};

// --- F010 Teacher Product Validation ---------------------------------------

export interface RubricScoreEntry {
  score: number;
  note: string;
}

export interface SevereFindingEntry {
  class: string;
  lesson_reference: string | number;
  evidence: string;
}

export interface RubricEvidencePayload {
  scores: Record<string, RubricScoreEntry>;
  severe_findings: SevereFindingEntry[];
  structural_rework_required: boolean;
  structural_rework_reason: string | null;
  overall_comment?: string;
  attestation: { evaluator_reference: string; completed_date: string };
}

export interface ProductValidationOutcomeDetail {
  outcome: "passed" | "failed";
  core_mean: number;
  core_mean_threshold: number;
  severe_finding_count: number;
  structural_rework_required: boolean;
  violated_rules: string[];
}

export interface ProductValidationAssignmentRow {
  id: string;
  unit_key: string;
  dataset_revision: string;
  rubric_revision: string;
  state: string;
  staleness: { reason: string; superseded_by: string } | null;
  not_complete_reason: string | null;
  outcome: "passed" | "failed" | null;
  outcome_detail: ProductValidationOutcomeDetail | null;
  created?: boolean;
  created_at: string;
  concluded_at: string | null;
}

export interface ProductValidationOverview {
  rubric_revision: string;
  overall_status: string;
  bounded_conclusion: string;
  assignments: ProductValidationAssignmentRow[];
}

export interface ProductValidationEvidenceHistoryRow {
  id: string;
  evidence_revision: string;
  status: string;
  capture_channel: string;
  outcome: "passed" | "failed";
  outcome_detail: ProductValidationOutcomeDetail;
  evidence: RubricEvidencePayload;
  document: {
    filename: string | null;
    content_type: string | null;
    size_bytes: number | null;
    checksum: string | null;
    downloadable: boolean;
  };
  created_at: string;
  superseded_by_evidence_id: string | null;
}

export interface ProductValidationDetail {
  id: string;
  unit_key: string;
  dataset_revision: string;
  rubric_revision: string;
  package: {
    brief_version: number;
    blueprint_version: number;
    lessons: Array<{
      index: number;
      title: string | null;
      members: Record<string, { state: string; artifact_id?: string }>;
    }>;
  };
  state: string;
  staleness: { reason: string; superseded_by: string } | null;
  not_complete_reason: string | null;
  created_at: string;
  concluded_at: string | null;
  evidence_history: ProductValidationEvidenceHistoryRow[];
  rubric_sheet: {
    rubric_revision: string;
    title: string;
    dimensions: Array<{ key: string; label: string; description: string }>;
    severe_finding_classes: Array<{ class: string; label: string }>;
    structural_rework_question: string;
  };
}

export async function productValidationOverview(
  token: string | null,
  projectId: string,
): Promise<ProductValidationOverview> {
  return apiFetch<ProductValidationOverview>(`/projects/${projectId}/product-validation`, {
    token,
  });
}

export async function productValidationCreateAssignment(
  token: string | null,
  projectId: string,
  unitKey: string,
): Promise<ProductValidationAssignmentRow> {
  return apiFetch<ProductValidationAssignmentRow>(
    `/projects/${projectId}/product-validation/assignments`,
    { method: "POST", body: { unit_key: unitKey }, token },
  );
}

export async function productValidationDetail(
  token: string | null,
  projectId: string,
  assignmentId: string,
): Promise<ProductValidationDetail> {
  return apiFetch<ProductValidationDetail>(
    `/projects/${projectId}/product-validation/assignments/${assignmentId}`,
    { token },
  );
}

export async function productValidationConclude(
  token: string | null,
  projectId: string,
  assignmentId: string,
  reason: string,
): Promise<ProductValidationAssignmentRow> {
  return apiFetch<ProductValidationAssignmentRow>(
    `/projects/${projectId}/product-validation/assignments/${assignmentId}/conclusion`,
    { method: "POST", body: { reason }, token },
  );
}

export async function productValidationImportEvidence(
  token: string | null,
  projectId: string,
  assignmentId: string,
  evidenceRevision: string,
  evidence: RubricEvidencePayload,
  document: File,
): Promise<{
  id: string;
  evidence_revision: string;
  status: string;
  capture_channel: string;
  outcome: "passed" | "failed";
  outcome_detail: ProductValidationOutcomeDetail;
  created: boolean;
  created_at: string;
}> {
  const form = new FormData();
  form.append("evidence_revision", evidenceRevision);
  form.append("evidence", JSON.stringify(evidence));
  form.append("document", document);
  const headers: Record<string, string> = { accept: "application/json" };
  if (token) headers.authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(
      `${apiBaseUrl()}/projects/${projectId}/product-validation/assignments/${assignmentId}/evidence`,
      { method: "POST", headers, body: form },
    );
  } catch {
    throw new ApiClientError("UNEXPECTED", "network unavailable", 0, null, {});
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
  return payload;
}

export async function downloadProductValidationDocument(
  token: string | null,
  projectId: string,
  assignmentId: string,
  evidenceId: string,
): Promise<Blob> {
  const response = await fetch(
    `${apiBaseUrl()}/projects/${projectId}/product-validation/assignments/${assignmentId}/evidence/${evidenceId}/document`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) {
    throw new ApiClientError(
      "UNEXPECTED_SYSTEM" as ApiErrorCode,
      "下载失败，请稍后重试。",
      response.status,
      null,
      {},
    );
  }
  return response.blob();
}

export const PRODUCT_VALIDATION_STATUS_LABELS: Record<string, string> = {
  not_evaluated: "未评估",
  in_progress: "进行中",
  not_complete: "未完成",
  passed: "通过",
  failed: "失败",
};

export const PRODUCT_VALIDATION_STATE_LABELS: Record<string, string> = {
  pending_evidence: "待证据",
  passed: "通过",
  failed: "失败",
  not_complete: "未完成",
  stale: "已过时（历史）",
};

export const PRODUCT_VALIDATION_STALE_REASON_LABELS: Record<string, string> = {
  newer_confirmed_pair: "已有更新的确认版本对",
  package_changed: "当前包的工件记录已变化",
};

export const RUBRIC_DIMENSION_LABELS: Record<string, string> = {
  knowledge_correctness: "知识准确性",
  language_quality: "语言质量",
  exercise_answer_correctness: "练习与答案正确性",
  objective_alignment: "目标对齐",
  teaching_usability: "教学可用性",
};

export const SEVERE_FINDING_CLASS_LABELS: Record<string, string> = {
  knowledge_error: "知识错误",
  language_error: "语言错误",
  answer_error: "答案错误",
  objective_alignment_error: "目标对齐错误",
};

export const PRODUCT_VALIDATION_RULE_LABELS: Record<string, string> = {
  severe_finding_present: "存在严重问题",
  core_mean_below_threshold: "核心均值低于 4.0",
  structural_rework_required: "需要结构性返工",
};

// ---------------------------------------------------------------------------
// F013: teacher memory (workspace-scoped, teacher-confirmed, subordinate)
// ---------------------------------------------------------------------------

export type MemoryCategory =
  | "language_mode"
  | "exercise_format"
  | "pacing_structure"
  | "assessment_style";

export const MEMORY_CATEGORY_LABELS: Record<MemoryCategory, string> = {
  language_mode: "语言模式",
  exercise_format: "练习格式",
  pacing_structure: "节奏结构",
  assessment_style: "测评风格",
};

export const MEMORY_TRIGGER_LABELS: Record<string, string> = {
  brief_confirm: "简报确认后",
  blueprint_confirm: "蓝图确认后",
  run_settled: "生成完成后",
};

export const MEMORY_RECORD_LIMIT_CHARS = 300;

export interface MemoryRecord {
  id: string;
  category: MemoryCategory;
  content: string;
  value: string | null;
  brief_version_id: string | null;
  blueprint_version_id: string | null;
  generation_run_id: string | null;
  created_at: string | null;
  has_project_disabled?: boolean;
  conflicts_with_latest_brief?: boolean;
  project_enabled?: boolean;
}

export interface MemoryProposal {
  id: string;
  category: MemoryCategory;
  content: string;
  value: string | null;
  status: "pending" | "confirmed" | "rejected" | "superseded";
  trigger_kind: string | null;
  brief_version_id: string | null;
  blueprint_version_id: string | null;
  generation_run_id: string | null;
  created_at: string | null;
  decided_at: string | null;
}

export interface MemoryPass {
  id: string;
  trigger_kind: string;
  trigger_id: string;
  status: "scheduled" | "running" | "completed" | "failed";
  proposal_count: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cost_usd: number | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface MemoryOverview {
  records: MemoryRecord[];
  proposals: MemoryProposal[];
  passes: MemoryPass[];
  quota: { used: number; limit: number };
}

export interface MemoryAppliedEntry {
  id: string;
  category: MemoryCategory;
  content: string;
}

export interface MemoryConflictEntry extends MemoryAppliedEntry {
  value: string | null;
  brief_value: string | null;
}

export interface MemoryEffective {
  applied: MemoryAppliedEntry[];
  conflicts: MemoryConflictEntry[];
  budget_skipped: { id: string; category: MemoryCategory }[];
  project_disabled: MemoryAppliedEntry[];
  injected_chars: number;
}

export interface ProjectMemoryView {
  effective: MemoryEffective;
  records: MemoryRecord[];
}

export async function getMemoryOverview(token: string | null): Promise<MemoryOverview> {
  return apiFetch<MemoryOverview>("/memory", { token });
}

export async function confirmMemoryProposal(
  token: string | null,
  proposalId: string,
  content?: string,
): Promise<MemoryRecord> {
  return apiFetch<MemoryRecord>(`/memory/proposals/${proposalId}/confirm`, {
    method: "POST",
    body: { content: content ?? null },
    token,
  });
}

export async function rejectMemoryProposal(
  token: string | null,
  proposalId: string,
): Promise<MemoryProposal> {
  return apiFetch<MemoryProposal>(`/memory/proposals/${proposalId}/reject`, {
    method: "POST",
    token,
  });
}

export async function retryMemoryPass(token: string | null, passId: string): Promise<MemoryPass> {
  return apiFetch<MemoryPass>(`/memory/passes/${passId}/retry`, {
    method: "POST",
    token,
  });
}

export async function editMemoryRecord(
  token: string | null,
  recordId: string,
  content: string,
): Promise<MemoryRecord> {
  return apiFetch<MemoryRecord>(`/memory/records/${recordId}`, {
    method: "PATCH",
    body: { content },
    token,
  });
}

export async function deleteMemoryRecord(
  token: string | null,
  recordId: string,
): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/memory/records/${recordId}`, {
    method: "DELETE",
    token,
  });
}

export async function getProjectMemory(
  token: string | null,
  projectId: string,
): Promise<ProjectMemoryView> {
  return apiFetch<ProjectMemoryView>(`/projects/${projectId}/memory`, { token });
}

export async function setMemoryOverride(
  token: string | null,
  projectId: string,
  recordId: string,
  enabled: boolean,
): Promise<{ record_id: string; enabled: boolean }> {
  return apiFetch<{ record_id: string; enabled: boolean }>(
    `/projects/${projectId}/memory/records/${recordId}/override`,
    { method: "POST", body: { enabled }, token },
  );
}

/** F013 D8: distinct, honest MEMORY_LIMIT copies — never a vague toast. */
export function memoryLimitFeedback(err: unknown): string | null {
  if (!(err instanceof ApiClientError) || err.code !== "MEMORY_LIMIT") return null;
  const details = err.details as { limit?: number; max_chars?: number };
  if (details?.max_chars) {
    return `单条记忆不超过 ${details.max_chars} 字符，请精简后再保存。`;
  }
  return `记忆数量已达上限（${details?.limit ?? 20} 条）。可删除不再需要的记忆后再确认。`;
}
