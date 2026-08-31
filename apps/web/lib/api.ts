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

export interface GenerationArtifact {
  id: string;
  lesson_index: number;
  status: string;
  language_mode: string;
  failure_reason: string | null;
  retry_count: number;
  download_url: string | null;
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
