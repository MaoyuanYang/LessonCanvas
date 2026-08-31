"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import {
  ArtifactProgressList,
  NarrationRegion,
  ReconnectBanner,
  RetainedList,
  RUN_STATUS_LABELS as STATUS_LABELS,
  RunOutcomeBanners,
  TERMINAL_RUN_STATUSES,
} from "@/components/artifact-run";
import { Alert, Button, ConfirmModal, EmptyState, SkeletonRows, StatusBadge } from "@/components/ui";
import {
  ApiClientError,
  downloadLessonPlan,
  generationStart,
  generationStatus,
  generationResume,
  generationStreamUrl,
  type GenerationArtifact,
  type GenerationSnapshot,
  type GenerationStreamEvent,
} from "@/lib/api";


function narrationText(event: GenerationStreamEvent): string | null {
  if (event.event_type === "run") {
    const status = String(event.payload.status ?? "");
    if (status === "queued") return "生成任务已创建，正在排队。";
    if (status === "superseded") return "检测到更新的已确认版本，本任务已安全停止。";
    if (TERMINAL_RUN_STATUSES.has(status)) {
      return `任务结束：${STATUS_LABELS[status] ?? status}`;
    }
    return null;
  }
  if (event.event_type === "phase") {
    const phase = String(event.payload.phase ?? "");
    if (phase === "generating") return "开始逐课生成教案。";
    if (phase === "validating") return "正在校验全部教案文件。";
    return null;
  }
  if (event.event_type === "lesson") {
    const index = event.payload.lesson_index as number;
    const status = String(event.payload.status ?? "");
    if (status === "drafting") return `正在起草第 ${index} 课教案……`;
    if (status === "rendering") return `正在渲染第 ${index} 课 DOCX 文件……`;
    if (status === "complete") return `第 ${index} 课教案已完成并通过校验。`;
    if (status === "failed") return `第 ${index} 课失败：${event.payload.reason ?? "未知原因"}`;
  }
  return null;
}

export function GenerationPanel({ projectId }: { projectId: string }) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const [error, setError] = useState<string | null>(null);
  const [gateBlocked, setGateBlocked] = useState(false);
  const [narrationLines, setNarrationLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [resumeOpen, setResumeOpen] = useState(false);
  const lastSeqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const snapshotQuery = useQuery({
    queryKey: ["generation", projectId],
    queryFn: async () => generationStatus(await getToken(), projectId),
    retry: false,
    // Polling fallback: the SSE stream is the fast path, but the authoritative
    // snapshot must converge even if the stream drops (D-RECN).
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !TERMINAL_RUN_STATUSES.has(status) ? 3000 : false;
    },
  });

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["generation", projectId] });
  }, [projectId, queryClient]);

  const startMutation = useMutation({
    mutationFn: async () => generationStart(await getToken(), projectId),
    onSuccess: () => {
      setGateBlocked(false);
      setNarrationLines([]);
      lastSeqRef.current = 0;
      invalidate();
    },
    onError: (err) => {
      if (err instanceof ApiClientError && err.code === "REQUIREMENT") {
        setGateBlocked(true);
      } else {
        setError(err instanceof ApiClientError ? err.message : "启动生成失败");
      }
    },
  });

  const resumeMutation = useMutation({
    mutationFn: async () => generationResume(await getToken(), projectId),
    onSuccess: () => {
      setResumeOpen(false);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "恢复失败"),
  });

  const snapshot: GenerationSnapshot | null = snapshotQuery.data ?? null;

  const consumeStream = useCallback(
    async (token: string | null) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setConnected(true);
      try {
        const response = await fetch(generationStreamUrl(projectId), {
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
            const idLine = rawEvent
              .split("\n")
              .find((line) => line.startsWith("id: "));
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
                const line = narrationText(parsed);
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

  if (snapshotQuery.isLoading) {
    return (
      <div>
        <h2 className="text-lg font-semibold">教案生成</h2>
        <SkeletonRows />
      </div>
    );
  }

  if (snapshotQuery.isError) {
    const notFound =
      snapshotQuery.error instanceof ApiClientError && snapshotQuery.error.code === "NOT_FOUND";
    if (notFound) {
      return (
        <div>
          <h2 className="text-lg font-semibold">教案生成</h2>
          <p className="mb-4 mt-2 text-sm text-ink-secondary">
            将已确认的单元蓝图转化为每课可编辑的 DOCX 教案。确认单元蓝图后即可开始生成全部教案。
          </p>
          {gateBlocked ? (
            <Alert tone="warning">
              需要先确认教学简报与单元蓝图，才能开始生成。请前往「单元蓝图」页签完成确认。
            </Alert>
          ) : null}
          {error ? <Alert tone="error">{error}</Alert> : null}
          {!isDesktop ? <DesktopRequiredNotice task="开始生成教案" /> : null}
          {isDesktop ? (
            <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
              {startMutation.isPending ? "正在启动……" : "开始生成"}
            </Button>
          ) : null}
        </div>
      );
    }
    return (
      <div>
        <h2 className="text-lg font-semibold">教案生成</h2>
        <Alert tone="error">
          {snapshotQuery.error instanceof ApiClientError
            ? snapshotQuery.error.message
            : "无法加载生成状态"}
        </Alert>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div>
        <h2 className="text-lg font-semibold">教案生成</h2>
        <EmptyState title="暂无生成任务" hint="确认单元蓝图后即可开始生成全部教案。" />
      </div>
    );
  }

  const resumable = snapshot.status === "partial_failure" || snapshot.status === "capped_failure";
  const failedLessons = snapshot.artifacts.filter(
    (artifact: GenerationArtifact) => artifact.status === "failed",
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">教案生成</h2>
        <StatusBadge status={snapshot.status} />
      </div>
      <p className="mb-4 text-sm text-ink-secondary">{`绑定版本：教学简报 v${snapshot.brief_version} · 单元蓝图 v${snapshot.blueprint_version} · 输出语言：${snapshot.language_mode} · 模型调用 ${snapshot.model_calls}/${snapshot.model_call_cap}`}</p>

      <ReconnectBanner visible={!connected && !TERMINAL_RUN_STATUSES.has(snapshot.status)} />

      <RunOutcomeBanners
        status={snapshot.status}
        totalCount={snapshot.total_count}
        modelCallCap={snapshot.model_call_cap}
        failedLessonIndexes={failedLessons.map((a) => a.lesson_index)}
        noun="教案"
        error={error}
      />

      <NarrationRegion lines={narrationLines} />

      <RetainedList
        retained={snapshot.retained_artifacts ?? []}
        noun="教案"
        renderActions={(retained) => <DownloadButton projectId={projectId} artifactId={retained.id} />}
      />

      <ArtifactProgressList
        completeCount={snapshot.complete_count}
        totalCount={snapshot.total_count}
        artifacts={snapshot.artifacts}
        renderActions={(artifact) =>
          artifact.status === "complete" && artifact.download_url ? (
            <DownloadButton projectId={projectId} artifactId={artifact.id} />
          ) : null
        }
      />

      {!isDesktop ? <DesktopRequiredNotice task="恢复失败课程" /> : null}
      {resumable && isDesktop ? (
        <Button variant="secondary" onClick={() => setResumeOpen(true)}>
          恢复未完成课程
        </Button>
      ) : null}

      <ConfirmModal
        open={resumeOpen}
        onOpenChange={setResumeOpen}
        title="恢复生成"
        description={`将重新派发同一任务，仅继续失败或未完成的课程（${failedLessons.length + (snapshot.total_count - snapshot.complete_count - failedLessons.length)} 课），已完成教案不会重跑。`}
        confirmLabel="确认恢复"
        onConfirm={() => resumeMutation.mutate()}
        busy={resumeMutation.isPending}
      />
    </div>
  );
}

function DownloadButton({ projectId, artifactId }: { projectId: string; artifactId: string }) {
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
            const blob = await downloadLessonPlan(await getToken(), projectId, artifactId);
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `lesson-plan-${artifactId.slice(0, 8)}.docx`;
            anchor.click();
            URL.revokeObjectURL(url);
          } catch {
            setFailed(true);
          } finally {
            setBusy(false);
          }
        }}
      >
        下载 DOCX
      </Button>
    </span>
  );
}
