"use client";

import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { getApiToken } from "@/lib/auth";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { ARTIFACT_STATUS_LABELS, RUN_STATUS_LABELS } from "@/components/artifact-run";
import { Alert, Button, EmptyState, SkeletonRows } from "@/components/ui";
import { ProductValidationRegion } from "@/components/product-validation-region";
import { TechnicalEvaluationRegion } from "@/components/technical-evaluation-region";
import type { WorkspaceTab } from "@/app/(authed)/projects/[projectId]/workspace-view";
import {
  ApiClientError,
  EVIDENCE_EVENT_LABELS,
  EVIDENCE_KIND_LABELS,
  evidenceInventory,
  evidenceNarrate,
  evidenceNarrateStop,
  evidenceNarrateStreamUrl,
  evidenceRunEvents,
  evidenceRunSummary,
  INTERVIEW_STATUS_LABELS,
  type EvidenceEvent,
} from "@/lib/api";

const INTERVIEW_KINDS = new Set(["discovery", "planning"]);
const PAGE_SIZE = 20;

function statusLabel(kind: string, status: string): string {
  if (INTERVIEW_KINDS.has(kind)) {
    return INTERVIEW_STATUS_LABELS[status] ?? status;
  }
  return RUN_STATUS_LABELS[status] ?? status;
}

function kindLabel(kind: string): string {
  return EVIDENCE_KIND_LABELS[kind as keyof typeof EVIDENCE_KIND_LABELS] ?? kind;
}

function eventLabel(eventType: string): string {
  return EVIDENCE_EVENT_LABELS[eventType] ?? eventType;
}

function formatCost(costUsd: number | null): string {
  if (costUsd === null) return "未记录";
  return `约 $${costUsd.toFixed(4)}（估算）`;
}

function formatTokens(event: EvidenceEvent): string {
  if (event.prompt_tokens === null || event.completion_tokens === null) return "未记录";
  return `输入 ${event.prompt_tokens} / 输出 ${event.completion_tokens}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("zh-CN", { hour12: false });
}

export function EvidencePanel({
  projectId,
  onNavigate,
  readOnly = false,
}: {
  projectId: string;
  onNavigate: (tab: WorkspaceTab) => void;
  readOnly?: boolean;
}) {
  const isDesktop = useDesktop();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<string>("");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [copiedCursor, setCopiedCursor] = useState<string | null>(null);
  const [narrationText, setNarrationText] = useState<string | null>(null);
  const [narrationStreaming, setNarrationStreaming] = useState(false);
  const [narrationError, setNarrationError] = useState<string | null>(null);
  const narrationAbortRef = useRef<AbortController | null>(null);

  const inventoryQuery = useQuery({
    queryKey: ["evidence-inventory", projectId],
    queryFn: async () => evidenceInventory(await getApiToken(), projectId),
    retry: false,
  });

  const runs = inventoryQuery.data?.runs ?? [];
  const selectedId = selectedRunId ?? runs[0]?.run_id ?? null;

  const summaryQuery = useQuery({
    queryKey: ["evidence-run", projectId, selectedId],
    queryFn: async () => evidenceRunSummary(await getApiToken(), projectId, selectedId as string),
    enabled: selectedId !== null,
    retry: false,
  });

  const eventsQuery = useInfiniteQuery({
    queryKey: ["evidence-events", projectId, selectedId, kindFilter],
    queryFn: async ({ pageParam }) =>
      evidenceRunEvents(await getApiToken(), projectId, selectedId as string, {
        after: pageParam as string | undefined,
        limit: PAGE_SIZE,
        kind: kindFilter || undefined,
      }),
    enabled: selectedId !== null && isDesktop,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    retry: false,
  });

  const stopNarrationMutation = useMutation({
    mutationFn: async () => {
      narrationAbortRef.current?.abort();
      return evidenceNarrateStop(await getApiToken(), projectId, selectedId as string);
    },
    onSettled: () => setNarrationStreaming(false),
  });

  const consumeNarration = useCallback(
    async (runId: string) => {
      narrationAbortRef.current?.abort();
      const controller = new AbortController();
      narrationAbortRef.current = controller;
      setNarrationStreaming(true);
      setNarrationError(null);
      try {
        const token = await getApiToken();
        const response = await fetch(evidenceNarrateStreamUrl(projectId, runId), {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (!response.ok || !response.body) {
          setNarrationError("讲解服务暂不可用，请稍后重试。");
          return;
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let text = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let boundary = buffer.indexOf("\n\n");
          while (boundary !== -1) {
            const rawEvent = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
            if (dataLine) {
              try {
                const parsed = JSON.parse(dataLine.slice(6)) as { t?: string; text?: string };
                if (parsed.t) text += parsed.t;
                if (parsed.text !== undefined) text = parsed.text;
                setNarrationText(text);
              } catch {
                // ignore malformed chunk
              }
            }
            boundary = buffer.indexOf("\n\n");
          }
        }
      } catch {
        setNarrationError("讲解流已中断；已生成的讲解会保留在证据记录中。");
      } finally {
        setNarrationStreaming(false);
      }
    },
    [projectId],
  );

  const narrateMutation = useMutation({
    mutationFn: async () => {
      const runId = selectedId as string;
      await evidenceNarrate(await getApiToken(), projectId, runId);
      return runId;
    },
    onSuccess: (runId) => void consumeNarration(runId),
    onError: (error) => {
      if (error instanceof ApiClientError && error.code === "QUOTA_EXCEEDED") {
        setNarrationError("已达工作区讲解次数上限；已记录的证据不受影响，可稍后再试。");
      } else {
        setNarrationError(error instanceof ApiClientError ? error.message : "讲解启动失败");
      }
    },
  });

  if (inventoryQuery.isLoading) {
    return (
      <div>
        <h2 className="text-lg font-semibold">运行证据</h2>
        <SkeletonRows />
      </div>
    );
  }

  if (inventoryQuery.isError) {
    return (
      <div>
        <h2 className="text-lg font-semibold">运行证据</h2>
        <Alert tone="error">
          {inventoryQuery.error instanceof ApiClientError
            ? inventoryQuery.error.message
            : "无法加载运行证据"}
        </Alert>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div>
        <h2 className="text-lg font-semibold">运行证据</h2>
        <TechnicalEvaluationRegion projectId={projectId} />
        <ProductValidationRegion projectId={projectId} />
        <EmptyState
          title="还没有任何运行记录"
          hint="前往「来源」或「需求访谈」开始第一次备课流程；每次访谈与生成都会在这里留下可解释的证据。"
        />
        <Button variant="secondary" className="mt-3" onClick={() => onNavigate("sources")}>
          前往「来源」开始
        </Button>
      </div>
    );
  }

  const summary = summaryQuery.data ?? null;
  const summaryLoading = selectedId !== null && summaryQuery.isLoading;
  const events =
    eventsQuery.data?.pages.flatMap((page) => page.events) ?? [];

  const toggleRow = (cursor: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(cursor)) next.delete(cursor);
      else next.add(cursor);
      return next;
    });
  };

  const copyPayload = async (event: EvidenceEvent) => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(event.payload, null, 2));
      setCopiedCursor(event.cursor);
      window.setTimeout(() => setCopiedCursor(null), 2000);
    } catch {
      setCopiedCursor(null);
    }
  };

  return (
    <div>
      <h2 className="text-lg font-semibold">运行证据</h2>
      <p className="mb-4 mt-1 text-sm text-ink-secondary">
        每次访谈与生成任务的教师摘要与技术证据。所有信息只读，不会影响任何任务状态。
      </p>

      <TechnicalEvaluationRegion projectId={projectId} />

      <ProductValidationRegion projectId={projectId} />

      <section aria-label="运行清单" className="mb-6">
        <ul className="space-y-2">
          {runs.map((run) => (
            <li key={run.run_id}>
              <button
                type="button"
                onClick={() => {
                  setSelectedRunId(run.run_id);
                  setKindFilter("");
                  setExpandedRows(new Set());
                  setNarrationText(null);
                  setNarrationError(null);
                }}
                aria-current={run.run_id === selectedId ? "true" : undefined}
                className={`flex w-full flex-wrap items-center gap-x-4 gap-y-1 rounded border p-3 text-left focus-visible:outline-2 focus-visible:outline-focus ${
                  run.run_id === selectedId
                    ? "border-accent bg-surface-alt"
                    : "border-line bg-paper hover:bg-surface-alt/60"
                }`}
              >
                <span className="font-medium">{kindLabel(run.kind)}</span>
                <span className="text-sm">{statusLabel(run.kind, run.status)}</span>
                <span className="text-sm text-ink-secondary">
                  {run.brief_version !== null
                    ? `简报 v${run.brief_version} · 蓝图 v${run.blueprint_version}`
                    : `访谈轮次 ${run.round_count ?? 0}`}
                </span>
                <span className="ml-auto text-sm text-ink-secondary">
                  {run.model_call_cap !== null
                    ? `模型调用 ${run.model_calls}/${run.model_call_cap}`
                    : `模型调用 ${run.model_calls}`}
                  {" · "}
                  {formatCost(run.cost_estimate_complete ? run.cost_usd_estimated : null)}
                </span>
                <span className="w-full text-xs text-ink-secondary">
                  {formatTime(run.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {selectedId === null ? null : summaryLoading ? (
        <SkeletonRows count={2} />
      ) : summary === null ? (
        <Alert tone="error">
          {summaryQuery.error instanceof ApiClientError
            ? summaryQuery.error.message
            : "无法加载该运行的摘要"}
        </Alert>
      ) : (
        <section aria-label="任务摘要" className="rounded border border-line bg-paper p-4">
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <h3 className="text-base font-medium">{kindLabel(summary.kind)}</h3>
            <span className="text-sm">{statusLabel(summary.kind, summary.status)}</span>
          </div>
          <p className="text-sm text-ink-secondary">
            {summary.brief_version !== null
              ? `绑定版本：教学简报 v${summary.brief_version} · 单元蓝图 v${summary.blueprint_version}`
              : "需求访谈运行"}
            {summary.difficulty ? ` · 难度档位：${summary.difficulty}` : ""}
            {summary.language_mode ? ` · 输出语言：${summary.language_mode}` : ""}
          </p>
          <p className="mt-1 text-sm text-ink-secondary">
            模型调用 {summary.model_calls}
            {summary.model_call_cap !== null ? `/${summary.model_call_cap}` : ""} · 模型耗时{" "}
            {summary.model_latency_ms_total} ms · 模型事件 {summary.model_call_count} · 工具事件{" "}
            {summary.tool_call_count} · 成本 {formatCost(
              summary.cost_estimate_complete ? summary.cost_usd_estimated : null,
            )}
          </p>

          {summary.status === "superseded" && summary.superseded_by ? (
            <div className="mt-3">
              <Alert tone="warning">
                该任务已被更新的已确认版本取代（简报 v{summary.superseded_by.brief_version} ·
                蓝图 v{summary.superseded_by.blueprint_version}）；以下为历史证据，不代表当前版本。
              </Alert>
            </div>
          ) : null}

          {summary.telemetry_gaps.length > 0 ? (
            <div className="mt-3">
              <Alert tone="info">
                部分早期记录未包含用量与模型信息，相关条目显示为「未记录」；任务状态以运行记录为准。
              </Alert>
            </div>
          ) : null}

          {summary.artifacts.length > 0 ? (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium">课程产出（只读）</h4>
              <ul className="space-y-1">
                {summary.artifacts.map((artifact) => (
                  <li
                    key={artifact.id}
                    className="flex flex-wrap items-center gap-x-3 rounded border border-line bg-surface-alt/50 px-3 py-2 text-sm"
                  >
                    <span className="font-medium">第 {artifact.lesson_index} 课</span>
                    <span>{ARTIFACT_STATUS_LABELS[artifact.status] ?? artifact.status}</span>
                    {artifact.status === "failed" && artifact.failure_reason ? (
                      <span className="text-severe">原因：{artifact.failure_reason}</span>
                    ) : null}
                    {artifact.retry_count > 0 ? (
                      <span className="text-ink-secondary">重试 {artifact.retry_count} 次</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {summary.recovery_view !== null ? (
            <div className="mt-4">
              <Button
                variant="secondary"
                onClick={() => onNavigate(summary.recovery_view as WorkspaceTab)}
              >
                前往对应视图处理失败课程
              </Button>
            </div>
          ) : null}

          {isDesktop && !readOnly ? (
            <div className="mt-4">
              <Button
                onClick={() => narrateMutation.mutate()}
                disabled={narrateMutation.isPending || narrationStreaming}
              >
                {narrationStreaming ? "讲解中……" : "讲解本任务"}
              </Button>{" "}
              {narrationStreaming ? (
                <Button
                  variant="secondary"
                  onClick={() => stopNarrationMutation.mutate()}
                  disabled={stopNarrationMutation.isPending}
                >
                  停止讲解
                </Button>
              ) : null}
              {narrationError ? (
                <div className="mt-2">
                  <Alert tone="error">{narrationError}</Alert>
                </div>
              ) : null}
              {narrationText !== null ? (
                <section
                  aria-label="任务讲解"
                  tabIndex={-1}
                  className="mt-3 max-h-56 overflow-y-auto rounded border border-line bg-surface-alt/50 p-3 text-sm"
                  aria-live="polite"
                >
                  {narrationText}
                </section>
              ) : null}
            </div>
          ) : null}

          {isDesktop ? (
            <div className="mt-6">
              <h4 className="text-sm font-medium">技术证据</h4>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <label htmlFor="evidence-kind-filter" className="text-sm text-ink-secondary">
                  类型筛选
                </label>
                <select
                  id="evidence-kind-filter"
                  value={kindFilter}
                  onChange={(event) => {
                    setKindFilter(event.target.value);
                    setExpandedRows(new Set());
                  }}
                  className="rounded border border-line bg-paper px-2 py-1 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                >
                  <option value="">全部类型</option>
                  {summary.evidence_kinds.map((kind) => (
                    <option key={kind} value={kind}>
                      {eventLabel(kind)}
                    </option>
                  ))}
                </select>
              </div>

              {eventsQuery.isLoading ? (
                <div className="mt-3">
                  <SkeletonRows count={2} />
                </div>
              ) : eventsQuery.isError ? (
                <div className="mt-3">
                  <Alert tone="error">
                    {eventsQuery.error instanceof ApiClientError
                      ? eventsQuery.error.message
                      : "无法加载技术证据"}
                  </Alert>
                </div>
              ) : (
                <div className="mt-3">
                  {events.length === 0 ? (
                    <p className="text-sm text-ink-secondary">
                      该筛选条件下没有记录；可能是早期运行未记录此类事件。
                    </p>
                  ) : (
                    <ul className="space-y-2" aria-label="技术证据事件">
                      {events.map((event) => {
                        const expanded = expandedRows.has(event.cursor);
                        return (
                          <li key={event.cursor} className="rounded border border-line bg-paper">
                            <button
                              type="button"
                              onClick={() => toggleRow(event.cursor)}
                              aria-expanded={expanded}
                              className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 p-3 text-left text-sm focus-visible:outline-2 focus-visible:outline-focus"
                            >
                              <span className="font-medium">{eventLabel(event.event_type)}</span>
                              {event.lesson_index !== null && event.lesson_index !== undefined ? (
                                <span>第 {event.lesson_index} 课</span>
                              ) : null}
                              <span className="text-ink-secondary">{formatTime(event.created_at)}</span>
                              <span className="text-ink-secondary">
                                {event.latency_ms !== null ? `${event.latency_ms} ms` : ""}
                              </span>
                              <span className="text-ink-secondary">{formatTokens(event)}</span>
                              <span className="text-ink-secondary">{formatCost(event.cost_usd)}</span>
                              {event.model !== null ? (
                                <span className="ml-auto text-xs text-ink-secondary">
                                  {event.model}
                                </span>
                              ) : null}
                            </button>
                            {expanded ? (
                              <div className="border-t border-line p-3">
                                <div className="mb-2 flex items-center gap-2">
                                  <Button
                                    variant="quiet"
                                    onClick={() => void copyPayload(event)}
                                  >
                                    复制原始数据
                                  </Button>
                                  {copiedCursor === event.cursor ? (
                                    <span className="text-xs text-ink-secondary">已复制</span>
                                  ) : null}
                                </div>
                                <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded border border-line bg-surface-alt/50 p-3 text-xs">
                                  {JSON.stringify(event.payload, null, 2)}
                                </pre>
                              </div>
                            ) : null}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  <div className="mt-3">
                    {eventsQuery.hasNextPage ? (
                      <Button
                        variant="secondary"
                        onClick={() => void eventsQuery.fetchNextPage()}
                        disabled={eventsQuery.isFetchingNextPage}
                      >
                        {eventsQuery.isFetchingNextPage ? "加载中……" : "加载更多"}
                      </Button>
                    ) : events.length > 0 ? (
                      <p className="text-sm text-ink-secondary">已全部加载。</p>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-4">
              <DesktopRequiredNotice task="查看技术证据或收听任务讲解" />
            </div>
          )}
        </section>
      )}
    </div>
  );
}
