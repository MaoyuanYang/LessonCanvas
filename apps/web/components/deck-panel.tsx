"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArtifactProgressList,
  RetainedList,
  NarrationRegion,
  ReconnectBanner,
  RunOutcomeBanners,
  RUN_STATUS_LABELS,
  TERMINAL_RUN_STATUSES,
} from "@/components/artifact-run";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, ConfirmModal, EmptyState, SkeletonRows, StatusBadge } from "@/components/ui";
import {
  ApiClientError,
  guardrailFeedback,
  deckGenerationResume,
  deckGenerationStart,
  deckGenerationStatus,
  deckGenerationStreamUrl,
  downloadSlideDeck,
  generationStatus,
  type DeckArtifact,
  type DeckGenerationSnapshot,
  type GenerationSnapshot,
  type GenerationStreamEvent,
} from "@/lib/api";

function deckNarrationText(event: GenerationStreamEvent): string | null {
  if (event.event_type === "run") {
    const status = String(event.payload.status ?? "");
    if (status === "queued") return "课件生成任务已创建，正在排队。";
    if (status === "superseded") return "检测到更新的已确认版本，本任务已安全停止。";
    if (TERMINAL_RUN_STATUSES.has(status)) {
      return `任务结束：${RUN_STATUS_LABELS[status] ?? status}`;
    }
    return null;
  }
  if (event.event_type === "phase") {
    const phase = String(event.payload.phase ?? "");
    if (phase === "generating") return "开始逐课生成课件。";
    if (phase === "validating") return "正在校验全部课件文件。";
    return null;
  }
  if (event.event_type === "lesson") {
    const index = event.payload.lesson_index as number;
    const status = String(event.payload.status ?? "");
    if (status === "drafting") return `正在起草第 ${index} 课课件……`;
    if (status === "rendering") return `正在渲染第 ${index} 课 PPTX 文件……`;
    if (status === "complete") {
      const slideCount = event.payload.slide_count as number | undefined;
      return `第 ${index} 课课件已完成并通过校验${slideCount ? `（共 ${slideCount} 页）` : ""}。`;
    }
    if (status === "failed") return `第 ${index} 课课件失败：${event.payload.reason ?? "未知原因"}`;
  }
  return null;
}

export function DeckPanel({
  projectId,
  onNavigate,
}: {
  projectId: string;
  onNavigate?: (tab: "sources" | "discovery" | "brief" | "blueprint" | "generation" | "decks" | "alignment") => void;
}) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const [error, setError] = useState<string | null>(null);
  const [gateBlocked, setGateBlocked] = useState<"blueprint" | "lesson_plans" | null>(null);
  const [narrationLines, setNarrationLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [resumeOpen, setResumeOpen] = useState(false);
  const lastSeqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  // Prerequisite probe: deck generation requires a complete lesson-plan run for
  // the current confirmed versions (Spec D3 / D-DECKGEN).
  const planQuery = useQuery({
    queryKey: ["generation", projectId],
    queryFn: async () => generationStatus(await getToken(), projectId),
    retry: false,
  });

  const snapshotQuery = useQuery({
    queryKey: ["deckGeneration", projectId],
    queryFn: async () => deckGenerationStatus(await getToken(), projectId),
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !TERMINAL_RUN_STATUSES.has(status) ? 3000 : false;
    },
  });

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["deckGeneration", projectId] });
  }, [projectId, queryClient]);

  const startMutation = useMutation({
    mutationFn: async () => deckGenerationStart(await getToken(), projectId),
    onSuccess: () => {
      setGateBlocked(null);
      setNarrationLines([]);
      lastSeqRef.current = 0;
      invalidate();
    },
    onError: (err) => {
      if (err instanceof ApiClientError && err.code === "REQUIREMENT") {
        const gate = (err.details as { gate?: string }).gate;
        setGateBlocked(gate === "blueprint" ? "blueprint" : "lesson_plans");
      } else {
        setError(
          guardrailFeedback(err) ??
            (err instanceof ApiClientError ? err.message : "启动课件生成失败"),
        );
      }
    },
  });

  const resumeMutation = useMutation({
    mutationFn: async () => deckGenerationResume(await getToken(), projectId),
    onSuccess: () => {
      setResumeOpen(false);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "恢复失败"),
  });

  const snapshot: DeckGenerationSnapshot | null = snapshotQuery.data ?? null;
  const planSnapshot: GenerationSnapshot | null = planQuery.data ?? null;
  const planMissing = planQuery.isError;
  const planIncomplete = planSnapshot !== null && planSnapshot.status !== "complete";

  const consumeStream = useCallback(
    async (token: string | null) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setConnected(true);
      try {
        const response = await fetch(deckGenerationStreamUrl(projectId), {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(lastSeqRef.current > 0 ? { "Last-Event-ID": String(lastSeqRef.current) } : {}),
          },
          signal: controller.signal,
        });
        if (!response.ok || !response.body) {
          setConnected(false);
          return;
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let boundary = buffer.indexOf("\n\n");
          while (boundary !== -1) {
            const rawEvent = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const idLine = rawEvent.split("\n").find((line) => line.startsWith("id: "));
            if (idLine) lastSeqRef.current = Number(idLine.slice(4));
            if (rawEvent.includes("event: end")) {
              invalidate();
              setConnected(false);
              return;
            }
            const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
            if (dataLine) {
              try {
                const parsed = JSON.parse(dataLine.slice(6)) as GenerationStreamEvent;
                const line = deckNarrationText(parsed);
                if (line) {
                  setNarrationLines((prev) => [...prev.slice(-40), line]);
                }
                invalidate();
              } catch {
                // ignore malformed chunk
              }
            }
            boundary = buffer.indexOf("\n\n");
          }
        }
        setConnected(false);
        throw new Error("stream ended");
      } catch {
        setConnected(false);
      }
    },
    [invalidate, projectId],
  );

  useEffect(() => {
    const runId = snapshot?.run_id;
    const status = snapshot?.status;
    const active = runId && status && !TERMINAL_RUN_STATUSES.has(status);
    if (!active) {
      abortRef.current?.abort();
      return;
    }
    let cancelled = false;
    const connectLoop = async () => {
      const token = await getToken();
      while (!cancelled) {
        try {
          await consumeStream(token);
        } catch {
          // stream ended or failed; reconnect with Last-Event-ID shortly
        }
        if (cancelled) break;
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    };
    void connectLoop();
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [consumeStream, getToken, snapshot?.run_id, snapshot?.status]);

  useEffect(() => () => abortRef.current?.abort(), []);

  if (snapshotQuery.isLoading || planQuery.isLoading) {
    return (
      <div>
        <h2 className="text-lg font-semibold">课件生成</h2>
        <SkeletonRows />
      </div>
    );
  }

  if (snapshotQuery.isError) {
    const notFound =
      snapshotQuery.error instanceof ApiClientError && snapshotQuery.error.code === "NOT_FOUND";
    if (notFound) {
      if (planMissing) {
        // No lesson-plan run exists for the current confirmed versions.
        return (
          <div>
            <h2 className="text-lg font-semibold">课件生成</h2>
            <p className="mb-4 mt-2 text-sm text-ink-secondary">
              课件与已确认教案逐课对齐。需要先确认单元蓝图并生成全部教案，才能开始生成课件。
            </p>
            {gateBlocked === "blueprint" ? (
              <Alert tone="warning">
                需要先确认教学简报与单元蓝图。请前往「单元蓝图」页签完成确认。
              </Alert>
            ) : null}
            {gateBlocked === "lesson_plans" ? (
              <Alert tone="warning">
                尚无已完成的教案任务。请前往「教案生成」先生成并完成全部教案。
              </Alert>
            ) : null}
            {error ? <Alert tone="error">{error}</Alert> : null}
            <div className="mt-4 flex gap-2">
              {onNavigate ? (
                <Button variant="secondary" onClick={() => onNavigate("generation")}>
                  前往「教案生成」
                </Button>
              ) : null}
            </div>
          </div>
        );
      }
      if (planIncomplete) {
        return (
          <div>
            <h2 className="text-lg font-semibold">课件生成</h2>
            <p className="mb-4 mt-2 text-sm text-ink-secondary">
              当前已确认版本的教案任务尚未全部完成（状态：{planSnapshot ? RUN_STATUS_LABELS[planSnapshot.status] ?? planSnapshot.status : "未知"}）。完成全部教案后即可开始生成课件。
            </p>
            {gateBlocked === "lesson_plans" ? (
              <Alert tone="warning">
                教案任务尚未全部完成。请前往「教案生成」完成或恢复剩余教案。
              </Alert>
            ) : null}
            {error ? <Alert tone="error">{error}</Alert> : null}
            <div className="mt-4 flex gap-2">
              {onNavigate ? (
                <Button variant="secondary" onClick={() => onNavigate("generation")}>
                  前往「教案生成」
                </Button>
              ) : null}
            </div>
          </div>
        );
      }
      // Prerequisite met: show the start surface with the bound versions.
      return (
        <div>
          <h2 className="text-lg font-semibold">课件生成</h2>
          <p className="mb-4 mt-2 text-sm text-ink-secondary">
            基于已完成的确认版教案，逐课生成可编辑 PPTX 课件；教师备注与来源引用写入演讲者备注。
          </p>
          {planSnapshot ? (
            <p className="mb-4 text-sm text-ink-secondary">{`绑定版本：教学简报 v${planSnapshot.brief_version} · 单元蓝图 v${planSnapshot.blueprint_version} · 输出语言：${planSnapshot.language_mode} · 共 ${planSnapshot.total_count} 课`}</p>
          ) : null}
          {gateBlocked ? (
            <Alert tone="warning">
              {gateBlocked === "blueprint"
                ? "需要先确认教学简报与单元蓝图，才能开始生成课件。"
                : "教案任务尚未全部完成，无法开始生成课件。"}
            </Alert>
          ) : null}
          {error ? <Alert tone="error">{error}</Alert> : null}
          {!isDesktop ? <DesktopRequiredNotice task="开始生成课件" /> : null}
          {isDesktop ? (
            <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
              {startMutation.isPending ? "正在启动……" : "开始生成课件"}
            </Button>
          ) : null}
        </div>
      );
    }
    return (
      <div>
        <h2 className="text-lg font-semibold">课件生成</h2>
        <Alert tone="error">
          {snapshotQuery.error instanceof ApiClientError
            ? snapshotQuery.error.message
            : "无法加载课件生成状态"}
        </Alert>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div>
        <h2 className="text-lg font-semibold">课件生成</h2>
        <EmptyState title="暂无课件任务" hint="完成全部教案后即可开始生成逐课课件。" />
      </div>
    );
  }

  const resumable = snapshot.status === "partial_failure" || snapshot.status === "capped_failure";
  const failedLessons = snapshot.artifacts.filter(
    (artifact: DeckArtifact) => artifact.status === "failed",
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">课件生成</h2>
        <StatusBadge status={snapshot.status} />
      </div>
      <p className="mb-4 text-sm text-ink-secondary">{`绑定版本：教学简报 v${snapshot.brief_version} · 单元蓝图 v${snapshot.blueprint_version} · 输出语言：${snapshot.language_mode} · 模型调用 ${snapshot.model_calls}/${snapshot.model_call_cap}`}</p>

      <ReconnectBanner visible={!connected && !TERMINAL_RUN_STATUSES.has(snapshot.status)} />

      <RunOutcomeBanners
        status={snapshot.status}
        totalCount={snapshot.total_count}
        modelCallCap={snapshot.model_call_cap}
        failedLessonIndexes={failedLessons.map((a) => a.lesson_index)}
        noun="课件"
        error={error}
        viewAlignment={onNavigate ? () => onNavigate("alignment") : undefined}
      />

      <NarrationRegion lines={narrationLines} />

      <RetainedList
        retained={snapshot.retained_artifacts ?? []}
        noun="课件"
        renderActions={(retained) => (
          <DownloadDeckButton projectId={projectId} artifactId={retained.id} />
        )}
      />

      <ArtifactProgressList
        completeCount={snapshot.complete_count}
        totalCount={snapshot.total_count}
        artifacts={snapshot.artifacts}
        renderActions={(artifact) => (
          <>
            {artifact.status === "complete" && (artifact as DeckArtifact).slide_count ? (
              <span className="text-xs text-ink-secondary">共 {(artifact as DeckArtifact).slide_count} 页</span>
            ) : null}
            {artifact.status === "complete" && artifact.download_url ? (
              <DownloadDeckButton projectId={projectId} artifactId={artifact.id} />
            ) : null}
          </>
        )}
      />

      {!isDesktop ? <DesktopRequiredNotice task="恢复失败课件" /> : null}
      {resumable && isDesktop ? (
        <Button variant="secondary" onClick={() => setResumeOpen(true)}>
          恢复未完成课件
        </Button>
      ) : null}

      <ConfirmModal
        open={resumeOpen}
        onOpenChange={setResumeOpen}
        title="恢复课件生成"
        description={`将重新派发同一任务，仅继续失败或未完成的课程（${failedLessons.length + (snapshot.total_count - snapshot.complete_count - failedLessons.length)} 课），已完成课件不会重跑。`}
        confirmLabel="确认恢复"
        onConfirm={() => resumeMutation.mutate()}
        busy={resumeMutation.isPending}
      />
    </div>
  );
}

function DownloadDeckButton({ projectId, artifactId }: { projectId: string; artifactId: string }) {
  const { getToken } = useAuth();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <span className="flex items-center gap-2">
      {failed ? <span className="text-xs text-ink-secondary">下载失败，可重试</span> : null}
      <Button
        variant="secondary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setFailed(false);
          try {
            const blob = await downloadSlideDeck(await getToken(), projectId, artifactId);
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `deck-${artifactId.slice(0, 8)}.pptx`;
            anchor.click();
            URL.revokeObjectURL(url);
          } catch {
            setFailed(true);
          } finally {
            setBusy(false);
          }
        }}
      >
        下载 PPTX
      </Button>
    </span>
  );
}
