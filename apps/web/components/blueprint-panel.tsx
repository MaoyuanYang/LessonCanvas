"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getApiToken } from "@/lib/auth";
import { ConversationRegion } from "@/components/conversation-region";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { ImpactRegion } from "@/components/version-compare-panel";
import { Alert, Button, ConfirmModal, EmptyState, Modal } from "@/components/ui";
import type { BlueprintFinding, BlueprintLesson, BlueprintPayload } from "@/lib/api";
import {
  getImpact,
  ApiClientError,
  confirmBlueprint,
  getBlueprint,
  patchBlueprintDraft,
  planningAnswers,
  planningRetry,
  planningStart,
  planningStatus,
  recordBlueprintDecision,
} from "@/lib/api";

const FINDING_KIND_LABELS: Record<string, string> = {
  source_conflict: "来源内容冲突",
  standards_warning: "课标对齐警示",
  period_warning: "课时分布警示",
};

function citationLabel(citation: {
  type: string;
  filename?: string | null;
  snapshot_version?: string | null;
}): string {
  if (citation.type === "standards") {
    return `课标 ${citation.snapshot_version ?? ""}`.trim();
  }
  return citation.filename ? `来源：${citation.filename}` : "项目来源";
}

export function BlueprintPanel({
  projectId,
  readOnly = false,
}: {
  projectId: string;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const canWrite = isDesktop && !readOnly;
  const [error, setError] = useState<string | null>(null);
  const [staleConflict, setStaleConflict] = useState(false);
  const [lessonEdits, setLessonEdits] = useState<Record<number, Partial<BlueprintLesson>>>({});
  const [decisionFinding, setDecisionFinding] = useState<BlueprintFinding | null>(null);
  const [decisionReason, setDecisionReason] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [impactError, setImpactError] = useState<string | null>(null);

  const impactQuery = useQuery({
    queryKey: ["impact", projectId],
    queryFn: async () => getImpact(await getApiToken(), projectId),
    enabled: false,
    retry: false,
  });

  const blueprintQuery = useQuery({
    queryKey: ["blueprint", projectId],
    queryFn: async () => getBlueprint(await getApiToken(), projectId),
  });

  const planningQuery = useQuery({
    queryKey: ["planning", projectId],
    queryFn: async () => planningStatus(await getApiToken(), projectId),
    retry: false,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["blueprint", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["planning", projectId] });
  };

  const startMutation = useMutation({
    mutationFn: async () => planningStart(await getApiToken(), projectId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "启动规划失败"),
  });

  const retryMutation = useMutation({
    mutationFn: async () => planningRetry(await getApiToken(), projectId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "重试失败"),
  });

  const [planningAnswers_, setPlanningAnswers] = useState<Record<string, string>>({});
  const answersMutation = useMutation({
    mutationFn: async () => planningAnswers(await getApiToken(), projectId, planningAnswers_),
    onSuccess: () => {
      setPlanningAnswers({});
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "提交失败"),
  });

  // F007 D-REVSEED: seed a fresh draft revision from the immutable confirmed
  // payload; editing then flows through the ordinary draft machinery.
  const seedMutation = useMutation({
    mutationFn: async () => {
      const state = blueprintQuery.data;
      if (state?.confirmed_payload == null) throw new Error("confirmed payload missing");
      const base = state.draft_revision;
      if (base == null) throw new Error("draft revision missing");
      return patchBlueprintDraft(await getApiToken(), projectId, state.confirmed_payload, base);
    },
    onSuccess: () => {
      setStaleConflict(false);
      invalidate();
    },
    onError: (err) =>
      setError(err instanceof ApiClientError ? err.message : "创建修订草稿失败"),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const base = blueprintQuery.data?.draft_revision;
      const draft = blueprintQuery.data?.draft;
      if (base == null || draft == null) throw new Error("draft missing");
      const payload: BlueprintPayload = {
        ...draft,
        lessons: draft.lessons.map((lesson) => ({
          ...lesson,
          ...(lessonEdits[lesson.index] ?? {}),
        })),
      };
      return patchBlueprintDraft(await getApiToken(), projectId, payload, base);
    },
    onSuccess: () => {
      setLessonEdits({});
      setStaleConflict(false);
      invalidate();
    },
    onError: (err) => {
      if (err instanceof ApiClientError && err.code === "STALE_VERSION") {
        setStaleConflict(true);
        invalidate();
      } else {
        setError(err instanceof ApiClientError ? err.message : "保存失败");
      }
    },
  });

  const decisionMutation = useMutation({
    mutationFn: async () => {
      const base = blueprintQuery.data?.draft_revision;
      if (decisionFinding == null || base == null) throw new Error("finding missing");
      return recordBlueprintDecision(
        await getApiToken(),
        projectId,
        decisionFinding.id,
        decisionReason,
        base,
      );
    },
    onSuccess: () => {
      setDecisionFinding(null);
      setDecisionReason("");
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "记录决策失败"),
  });

  const confirmMutation = useMutation({
    mutationFn: async () => {
      const base = blueprintQuery.data?.draft_revision;
      if (base == null) throw new Error("draft missing");
      return confirmBlueprint(await getApiToken(), projectId, base);
    },
    onSuccess: () => {
      setConfirmOpen(false);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "确认失败"),
  });

  const state = blueprintQuery.data;
  const planning = planningQuery.data;
  const planningNotFound =
    planningQuery.error instanceof ApiClientError && planningQuery.error.status === 404;

  const draft = state?.draft ?? null;
  const checks = state?.checks ?? [];
  const findings = state?.findings ?? [];
  const waivableOpen = findings.filter((f) => f.tier === "waivable" && f.status === "open");
  const blockingFindings = findings.filter((f) => f.tier === "blocking");
  const allChecksPassed = checks.length > 0 && checks.every((check) => check.passed);
  const confirmable = Boolean(
    draft && allChecksPassed && waivableOpen.length === 0 && !state?.stale,
  );

  const editedLessons = useMemo(
    () =>
      (draft?.lessons ?? []).map((lesson) => ({
        ...lesson,
        ...(lessonEdits[lesson.index] ?? {}),
      })),
    [draft, lessonEdits],
  );

  function updateLesson(index: number, patch: Partial<BlueprintLesson>) {
    setLessonEdits((current) => ({ ...current, [index]: { ...current[index], ...patch } }));
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-ink">单元蓝图</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          将已确认简报分配到每一课，确认后作为后续生成的唯一授权输入。
        </p>
      </div>

      {error ? <Alert tone="error">{error}</Alert> : null}
      {staleConflict ? (
        <Alert tone="warning">存在更新的草稿修订，已加载最新内容，请重新编辑后保存。</Alert>
      ) : null}

      {blueprintQuery.isLoading ? <p className="text-sm text-ink-secondary">加载中…</p> : null}

      {state && !state.available ? (
        <EmptyState
          title="尚未确认教学简报"
          hint="请先在“教学简报”页签完成确认，再开始单元规划。"
        />
      ) : null}

      {state?.stale ? (
        <div className="space-y-3 rounded border border-stale/40 bg-surface-alt p-4">
          <p className="text-sm font-medium text-ink">
            简报已更新：当前蓝图基于旧简报版本，已标记为过期，不能用于后续生成。
          </p>
          {state.brief_diff && state.brief_diff.length > 0 ? (
            <ul className="space-y-1 text-sm text-ink-secondary">
              {state.brief_diff.map((entry) => (
                <li key={entry.field}>
                  {entry.label}：{entry.old ?? "—"} → {entry.new ?? "—"}
                </li>
              ))}
            </ul>
          ) : null}
          {state.impact_summary ? <Alert tone="info">{state.impact_summary.summary}</Alert> : null}
          {canWrite ? (
            <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
              基于新简报重新规划
            </Button>
          ) : !readOnly ? (
            <DesktopRequiredNotice task="重新规划" />
          ) : null}
        </div>
      ) : null}

      {state && !state.stale && (planningNotFound || planning?.status === "superseded") && !draft ? (
        <div className="space-y-3">
          {!canWrite && !readOnly ? <DesktopRequiredNotice task="启动单元规划" /> : null}
          {canWrite ? (
            <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
              {startMutation.isPending ? "规划中…" : "开始单元规划"}
            </Button>
          ) : null}
        </div>
      ) : null}

      {planning?.status === "provider_failed" ? (
        <Alert tone="warning">
          模型服务暂时不可用，规划状态已保留。
          {!readOnly ? (
            <Button
            variant="quiet"
            className="ml-2"
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
          >
            重试规划
          </Button>
          ) : null}
        </Alert>
      ) : null}

      {planning && planning.status === "questioning" && planning.questions.length > 0 ? (
        <div className="space-y-3 rounded border border-line bg-surface-alt p-4">
          <p className="text-sm font-medium text-ink">
            第 {planning.round_count} 轮规划提问（{planning.questions.length} 问）
          </p>
          {planning.questions.map((question) => (
            <div key={question.field}>
              {readOnly ? (
                <p className="text-sm text-ink-secondary">{question.question}</p>
              ) : (
                <>
                  <label
                    className="text-sm text-ink-secondary"
                    htmlFor={`planning-answer-${question.field}`}
                  >
                    {question.question}
                  </label>
                  <textarea
                    id={`planning-answer-${question.field}`}
                    rows={2}
                    className="mt-1 w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                    value={planningAnswers_[question.field] ?? ""}
                    onChange={(event) =>
                      setPlanningAnswers((current) => ({
                        ...current,
                        [question.field]: event.target.value,
                      }))
                    }
                  />
                </>
              )}
            </div>
          ))}
          {!readOnly ? (
            <Button onClick={() => answersMutation.mutate()} disabled={answersMutation.isPending}>
              {answersMutation.isPending ? "提交中…" : "提交回答"}
            </Button>
          ) : null}
        </div>
      ) : null}

      {!planningNotFound && planning && !readOnly ? (
        <ConversationRegion
          projectId={projectId}
          kind="planning"
          narrateText="请叙述下一步规划。"
          onError={setError}
        />
      ) : null}

      {draft && !state?.stale ? (
        <>
          <div className="rounded border border-line bg-paper p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-base font-semibold text-ink">{draft.unit.title}</h3>
              <span className="text-sm text-ink-secondary">
                草稿修订 {state?.draft_revision}
                {state?.confirmed_version ? ` · 已确认版本 ${state.confirmed_version}` : ""}
              </span>
            </div>
            <ul className="mt-3 space-y-2">
              {draft.unit.objectives.map((objective) => (
                <li key={objective.id} className="text-sm text-ink">
                  <span className="mr-2 font-medium">{objective.id}</span>
                  {objective.text}
                  {objective.citations.map((citation, index) => (
                    <span
                      key={index}
                      className="ml-2 rounded bg-evidence/10 px-1.5 py-0.5 text-xs text-evidence"
                    >
                      {citationLabel(citation)}
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          </div>

          <section aria-label="完整性检查" className="rounded border border-line bg-paper p-4">
            <h3 className="text-base font-semibold text-ink">完整性检查</h3>
            <ul className="mt-2 space-y-1" aria-live="polite">
              {checks.map((check) => (
                <li
                  key={check.id}
                  className={`text-sm ${check.passed ? "text-success" : "text-severe"}`}
                >
                  {check.passed ? "✓" : "✗"} {check.label}
                  {!check.passed && check.affected.length > 0 ? (
                    <span className="ml-1 text-xs">
                      （受影响：{check.affected
                        .map((item) =>
                          "lesson_index" in item
                            ? `第${item.lesson_index}课`
                            : "objective_id" in item
                              ? String(item.objective_id)
                              : "expected" in item
                                ? `期望${item.expected}课/实际${item.actual}课`
                                : "",
                        )
                        .filter(Boolean)
                        .join("、")}）
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>

          {findings.length > 0 ? (
            <section aria-label="规划发现" className="space-y-2">
              <h3 className="text-base font-semibold text-ink">规划发现</h3>
              {findings.map((finding) => (
                <div key={finding.id} className="rounded border border-line bg-paper p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span
                      className={`text-xs font-medium ${
                        finding.tier === "blocking" ? "text-severe" : "text-warning"
                      }`}
                    >
                      {finding.tier === "blocking" ? "阻断" : "可决策"} ·{" "}
                      {FINDING_KIND_LABELS[finding.kind] ?? finding.kind}
                    </span>
                    <span className="text-xs text-ink-secondary">
                      {finding.status === "decided"
                        ? "已决策"
                        : finding.status === "resolved"
                          ? "已修正"
                          : "待处理"}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-ink">{finding.message}</p>
                  {finding.reason ? (
                    <p className="mt-1 text-xs text-ink-secondary">决策理由：{finding.reason}</p>
                  ) : null}
                  {canWrite &&
                  finding.tier === "waivable" &&
                  finding.status === "open" &&
                  !state?.stale ? (
                    <Button
                      variant="secondary"
                      className="mt-2"
                      onClick={() => setDecisionFinding(finding)}
                    >
                      记录教师决策
                    </Button>
                  ) : null}
                </div>
              ))}
            </section>
          ) : null}

          {!canWrite && !readOnly ? <DesktopRequiredNotice task="编辑或确认蓝图" /> : null}

          <section aria-label="课程列表" className="space-y-3">
            <h3 className="text-base font-semibold text-ink">课程安排（{draft.lessons.length} 课）</h3>
            {editedLessons.map((lesson) => (
              <div key={lesson.index} className="rounded border border-line bg-paper p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-ink">第 {lesson.index} 课</span>
                  {lesson.period_count ? (
                    <span className="text-xs text-ink-secondary">{lesson.period_count} 课时</span>
                  ) : null}
                </div>
                {canWrite ? (
                  <div className="mt-2 space-y-2">
                    <input
                      aria-label={`第${lesson.index}课标题`}
                      className="w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                      value={lesson.title ?? ""}
                      onChange={(event) => updateLesson(lesson.index, { title: event.target.value })}
                    />
                    <fieldset>
                      <legend className="text-xs text-ink-secondary">覆盖的单元目标</legend>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {draft.unit.objectives.map((objective) => {
                          const checked = lesson.objective_ids.includes(objective.id);
                          return (
                            <label
                              key={objective.id}
                              className="flex items-center gap-1 text-xs text-ink"
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(event) =>
                                  updateLesson(lesson.index, {
                                    objective_ids: event.target.checked
                                      ? [...lesson.objective_ids, objective.id]
                                      : lesson.objective_ids.filter((id) => id !== objective.id),
                                  })
                                }
                              />
                              {objective.id}
                            </label>
                          );
                        })}
                      </div>
                    </fieldset>
                    <input
                      aria-label={`第${lesson.index}课评估意图`}
                      placeholder="评估意图"
                      className="w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                      value={lesson.assessment_intent ?? ""}
                      onChange={(event) =>
                        updateLesson(lesson.index, { assessment_intent: event.target.value })
                      }
                    />
                    <textarea
                      aria-label={`第${lesson.index}课活动提纲`}
                      placeholder="活动提纲（可选）"
                      rows={2}
                      className="w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                      value={lesson.activity_outline ?? ""}
                      onChange={(event) =>
                        updateLesson(lesson.index, { activity_outline: event.target.value })
                      }
                    />
                  </div>
                ) : (
                  <div className="mt-2 space-y-1 text-sm text-ink-secondary">
                    <p>{lesson.title ?? "—"}</p>
                    <p>目标：{lesson.objective_ids.join("、") || "—"}</p>
                    <p>评估：{lesson.assessment_intent ?? "—"}</p>
                  </div>
                )}
              </div>
            ))}
          </section>

          {canWrite ? (
            <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <Button
                onClick={() => setConfirmOpen(true)}
                disabled={!confirmable || Object.keys(lessonEdits).length > 0}
                title={
                  !confirmable
                    ? "需先通过完整性检查并处理全部发现"
                    : Object.keys(lessonEdits).length > 0
                      ? "有未保存的编辑"
                      : undefined
                }
              >
                确认蓝图
              </Button>
              <Button
                variant="secondary"
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending || Object.keys(lessonEdits).length === 0}
              >
                {saveMutation.isPending ? "保存中…" : "保存修订"}
              </Button>
              {blockingFindings.length > 0 ? (
                <span className="text-xs text-severe">
                  存在 {blockingFindings.length} 项阻断发现，需修正后才能确认。
                </span>
              ) : null}
              {waivableOpen.length > 0 ? (
                <span className="text-xs text-warning">
                  {waivableOpen.length} 项可决策发现待处理。
                </span>
              ) : null}
            </div>
            <div aria-label="修订影响预览">
              <Button
                variant="quiet"
                onClick={() =>
                  impactQuery.refetch().then((result) => {
                    if (result.error) {
                      setImpactError(
                        result.error instanceof ApiClientError
                          ? result.error.message
                          : "预览失败，请稍后重试。",
                      );
                    } else {
                      setImpactError(null);
                    }
                  })
                }
              >
                {impactQuery.isFetching ? "预览中……" : "预览影响"}
              </Button>{" "}
              {impactError ? (
                <span className="text-xs text-severe">{impactError}</span>
              ) : impactQuery.data ? (
                <div className="mt-2">
                  <ImpactRegion impact={impactQuery.data} />
                </div>
              ) : (
                <span className="text-xs text-ink-secondary">
                  确认前可先预览本次修订将影响哪些课时与产物。
                </span>
              )}
            </div>
            </div>
          ) : null}
        </>
      ) : null}

      {state?.confirmed_version && !draft ? (
        <div className="flex flex-wrap items-center gap-3">
          <Alert tone="info">已确认蓝图版本 {state.confirmed_version}（不可变）。</Alert>
          {canWrite ? (
            <Button
              variant="secondary"
              disabled={seedMutation.isPending}
              onClick={() => seedMutation.mutate()}
            >
              {seedMutation.isPending ? "正在创建修订草稿……" : "基于已确认版本修订"}
            </Button>
          ) : null}
        </div>
      ) : null}

      <Modal
        open={decisionFinding != null}
        onOpenChange={(open) => {
          if (!open) setDecisionFinding(null);
        }}
        title="记录教师决策"
        description={`对「${decisionFinding ? (FINDING_KIND_LABELS[decisionFinding.kind] ?? decisionFinding.kind) : ""}」记录保留现状的理由；该理由会随蓝图版本留存。`}
      >
        <div className="space-y-3">
          <label className="text-sm text-ink-secondary" htmlFor="decision-reason">
            决策理由（必填）
          </label>
          <textarea
            id="decision-reason"
            rows={3}
            className="w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
            value={decisionReason}
            onChange={(event) => setDecisionReason(event.target.value)}
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setDecisionFinding(null)}>
              取消
            </Button>
            <Button
              onClick={() => decisionMutation.mutate()}
              disabled={decisionMutation.isPending || decisionReason.trim().length === 0}
            >
              {decisionMutation.isPending ? "记录中…" : "记录决策"}
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="确认单元蓝图"
        description="确认后将生成不可变的蓝图版本，作为每课内容生成的唯一授权输入；后续修改会创建新草稿，简报更新会使本版本过期。"
        confirmLabel="确认"
        busy={confirmMutation.isPending}
        onConfirm={() => confirmMutation.mutate()}
      />
    </div>
  );
}
