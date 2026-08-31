"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArtifactProgressList,
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
  EXERCISE_DIFFICULTY_DESCRIPTIONS,
  EXERCISE_DIFFICULTY_LABELS,
  downloadExerciseFile,
  exerciseGenerationResume,
  exerciseGenerationStart,
  exerciseGenerationStatus,
  exerciseGenerationStreamUrl,
  generationStatus,
  type ExerciseArtifact,
  type ExerciseDifficulty,
  type ExerciseGenerationSnapshot,
  type GenerationSnapshot,
  type GenerationStreamEvent,
} from "@/lib/api";

const DIFFICULTY_TIERS: ExerciseDifficulty[] = ["foundation", "consolidation", "advanced"];

function exerciseNarrationText(event: GenerationStreamEvent): string | null {
  if (event.event_type === "run") {
    const status = String(event.payload.status ?? "");
    if (status === "queued") return "练习与答案生成任务已创建，正在排队。";
    if (status === "superseded") return "检测到更新的已确认版本，本任务已安全停止。";
    if (TERMINAL_RUN_STATUSES.has(status)) {
      return `任务结束：${RUN_STATUS_LABELS[status] ?? status}`;
    }
    return null;
  }
  if (event.event_type === "phase") {
    const phase = String(event.payload.phase ?? "");
    if (phase === "generating") return "开始逐课生成练习与答案。";
    if (phase === "validating") return "正在校验全部练习与答案配对。";
    return null;
  }
  if (event.event_type === "lesson") {
    const index = event.payload.lesson_index as number;
    const status = String(event.payload.status ?? "");
    if (status === "drafting") return `正在起草第 ${index} 课练习与答案……`;
    if (status === "rendering") return `正在渲染第 ${index} 课 DOCX 文件……`;
    if (status === "complete") {
      const itemCount = event.payload.item_count as number | undefined;
      const categoryCount = event.payload.category_count as number | undefined;
      const summary = itemCount
        ? `（共 ${itemCount} 题${categoryCount ? ` · ${categoryCount} 类` : ""}）`
        : "";
      return `第 ${index} 课练习与答案已完成并通过配对校验${summary}。`;
    }
    if (status === "failed") return `第 ${index} 课练习失败：${event.payload.reason ?? "未知原因"}`;
  }
  return null;
}

export function ExercisePanel({
  projectId,
  onNavigate,
}: {
  projectId: string;
  onNavigate?:
    | ((tab: "sources" | "discovery" | "brief" | "blueprint" | "generation" | "decks" | "exercises") => void)
    | undefined;
}) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const [error, setError] = useState<string | null>(null);
  const [gateBlocked, setGateBlocked] = useState<"blueprint" | "lesson_plans" | null>(null);
  const [tierError, setTierError] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<ExerciseDifficulty | null>(null);
  const [narrationLines, setNarrationLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [resumeOpen, setResumeOpen] = useState(false);
  const lastSeqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  // Prerequisite probe: exercise generation requires a complete lesson-plan run
  // for the current confirmed versions (Spec D3 / D-EXGEN); slide decks are not
  // a prerequisite.
  const planQuery = useQuery({
    queryKey: ["generation", projectId],
    queryFn: async () => generationStatus(await getToken(), projectId),
    retry: false,
  });

  const snapshotQuery = useQuery({
    queryKey: ["exerciseGeneration", projectId],
    queryFn: async () => exerciseGenerationStatus(await getToken(), projectId),
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !TERMINAL_RUN_STATUSES.has(status) ? 3000 : false;
    },
  });

  const invalidate = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["exerciseGeneration", projectId] });
  }, [projectId, queryClient]);

  const startMutation = useMutation({
    mutationFn: async () =>
      exerciseGenerationStart(await getToken(), projectId, difficulty as ExerciseDifficulty),
    onSuccess: () => {
      setGateBlocked(null);
      setTierError(null);
      setNarrationLines([]);
      lastSeqRef.current = 0;
      invalidate();
    },
    onError: (err) => {
      if (err instanceof ApiClientError && err.code === "REQUIREMENT") {
        const gate = (err.details as { gate?: string }).gate;
        if (gate === "blueprint" || gate === "lesson_plans") {
          setGateBlocked(gate);
        } else {
          setTierError("难度档位无效，请重新选择（基础 / 巩固 / 进阶）。");
        }
      } else {
        setError(err instanceof ApiClientError ? err.message : "启动练习生成失败");
      }
    },
  });

  // D-EXDIFF: the tier is an explicit required decision; submit is blocked
  // client-side until one is chosen (the server revalidates regardless).
  const handleStart = () => {
    if (!difficulty) {
      setTierError("请先选择难度档位（基础 / 巩固 / 进阶）。");
      return;
    }
    startMutation.mutate();
  };

  const resumeMutation = useMutation({
    mutationFn: async () => exerciseGenerationResume(await getToken(), projectId),
    onSuccess: () => {
      setResumeOpen(false);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "恢复失败"),
  });

  const snapshot: ExerciseGenerationSnapshot | null = snapshotQuery.data ?? null;
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
        const response = await fetch(exerciseGenerationStreamUrl(projectId), {
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
                const line = exerciseNarrationText(parsed);
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
        <h2 className="text-lg font-semibold">练习与答案</h2>
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
            <h2 className="text-lg font-semibold">练习与答案</h2>
            <p className="mb-4 mt-2 text-sm text-ink-secondary">
              练习与答案和已确认教案逐课对齐。需要先确认单元蓝图并生成全部教案，才能开始生成练习。
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
            <h2 className="text-lg font-semibold">练习与答案</h2>
            <p className="mb-4 mt-2 text-sm text-ink-secondary">
              当前已确认版本的教案任务尚未全部完成（状态：{planSnapshot ? RUN_STATUS_LABELS[planSnapshot.status] ?? planSnapshot.status : "未知"}）。完成全部教案后即可开始生成练习与答案。
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
      // Prerequisite met: show the start surface with the bound versions and
      // the required difficulty tier selection (D-EXDIFF, no default).
      return (
        <div>
          <h2 className="text-lg font-semibold">练习与答案</h2>
          <p className="mb-4 mt-2 text-sm text-ink-secondary">
            基于已完成的确认版教案，逐课生成配对的可编辑练习与答案 DOCX 文件；难度由教师在启动时选择并绑定到本次任务。
          </p>
          {planSnapshot ? (
            <p className="mb-4 text-sm text-ink-secondary">{`绑定版本：教学简报 v${planSnapshot.brief_version} · 单元蓝图 v${planSnapshot.blueprint_version} · 输出语言：${planSnapshot.language_mode} · 共 ${planSnapshot.total_count} 课`}</p>
          ) : null}
          <fieldset className="mb-4 max-w-xl">
            <legend className="mb-2 text-sm font-medium">难度档位（必选）</legend>
            <div className="space-y-2">
              {DIFFICULTY_TIERS.map((tier) => (
                <label key={tier} className="flex items-start gap-2 text-sm">
                  <input
                    type="radio"
                    name="exercise-difficulty"
                    value={tier}
                    checked={difficulty === tier}
                    onChange={() => {
                      setDifficulty(tier);
                      setTierError(null);
                    }}
                    className="mt-1"
                  />
                  <span>
                    <span className="font-medium">{EXERCISE_DIFFICULTY_LABELS[tier]}</span>
                    <span className="ml-2 text-ink-secondary">
                      {EXERCISE_DIFFICULTY_DESCRIPTIONS[tier]}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          {tierError ? <Alert tone="warning">{tierError}</Alert> : null}
          {gateBlocked ? (
            <Alert tone="warning">
              {gateBlocked === "blueprint"
                ? "需要先确认教学简报与单元蓝图，才能开始生成练习。"
                : "教案任务尚未全部完成，无法开始生成练习。"}
            </Alert>
          ) : null}
          {error ? <Alert tone="error">{error}</Alert> : null}
          {!isDesktop ? <DesktopRequiredNotice task="开始生成练习" /> : null}
          {isDesktop ? (
            <Button onClick={handleStart} disabled={startMutation.isPending}>
              {startMutation.isPending ? "正在启动……" : "开始生成练习与答案"}
            </Button>
          ) : null}
        </div>
      );
    }
    return (
      <div>
        <h2 className="text-lg font-semibold">练习与答案</h2>
        <Alert tone="error">
          {snapshotQuery.error instanceof ApiClientError
            ? snapshotQuery.error.message
            : "无法加载练习生成状态"}
        </Alert>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div>
        <h2 className="text-lg font-semibold">练习与答案</h2>
        <EmptyState title="暂无练习任务" hint="完成全部教案并选择难度后即可开始生成练习与答案。" />
      </div>
    );
  }

  const resumable = snapshot.status === "partial_failure" || snapshot.status === "capped_failure";
  const failedLessons = snapshot.artifacts.filter(
    (artifact: ExerciseArtifact) => artifact.status === "failed",
  );
  const tierLabel = snapshot.difficulty ? EXERCISE_DIFFICULTY_LABELS[snapshot.difficulty] : null;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">练习与答案</h2>
        <StatusBadge status={snapshot.status} />
      </div>
      <p className="mb-4 text-sm text-ink-secondary">{`绑定版本：教学简报 v${snapshot.brief_version} · 单元蓝图 v${snapshot.blueprint_version} · 输出语言：${snapshot.language_mode}${tierLabel ? ` · 难度档位：${tierLabel}` : ""} · 模型调用 ${snapshot.model_calls}/${snapshot.model_call_cap}`}</p>

      <ReconnectBanner visible={!connected && !TERMINAL_RUN_STATUSES.has(snapshot.status)} />

      <RunOutcomeBanners
        status={snapshot.status}
        totalCount={snapshot.total_count}
        modelCallCap={snapshot.model_call_cap}
        failedLessonIndexes={failedLessons.map((a) => a.lesson_index)}
        noun="练习"
        error={error}
      />

      <NarrationRegion lines={narrationLines} />

      <ArtifactProgressList
        completeCount={snapshot.complete_count}
        totalCount={snapshot.total_count}
        artifacts={snapshot.artifacts}
        renderActions={(artifact) => {
          const pair = artifact as ExerciseArtifact;
          return (
            <>
              {pair.status === "complete" && pair.item_count ? (
                <span className="text-xs text-ink-secondary">{`共 ${pair.item_count} 题${pair.category_count ? ` · ${pair.category_count} 类` : ""}`}</span>
              ) : null}
              {pair.status === "complete" && pair.exercise_download_url ? (
                <DownloadPairButton
                  projectId={projectId}
                  artifactId={pair.id}
                  file="exercise"
                />
              ) : null}
              {pair.status === "complete" && pair.answer_download_url ? (
                <DownloadPairButton projectId={projectId} artifactId={pair.id} file="answer" />
              ) : null}
            </>
          );
        }}
      />

      {!isDesktop ? <DesktopRequiredNotice task="恢复失败练习" /> : null}
      {resumable && isDesktop ? (
        <Button variant="secondary" onClick={() => setResumeOpen(true)}>
          恢复未完成练习
        </Button>
      ) : null}

      <ConfirmModal
        open={resumeOpen}
        onOpenChange={setResumeOpen}
        title="恢复练习与答案生成"
        description={`将重新派发同一任务，仅继续失败或未完成的课程（${failedLessons.length + (snapshot.total_count - snapshot.complete_count - failedLessons.length)} 课），已完成配对不会重跑。`}
        confirmLabel="确认恢复"
        onConfirm={() => resumeMutation.mutate()}
        busy={resumeMutation.isPending}
      />
    </div>
  );
}

function DownloadPairButton({
  projectId,
  artifactId,
  file,
}: {
  projectId: string;
  artifactId: string;
  file: "exercise" | "answer";
}) {
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
            const blob = await downloadExerciseFile(await getToken(), projectId, artifactId, file);
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${file}-${artifactId.slice(0, 8)}.docx`;
            anchor.click();
            URL.revokeObjectURL(url);
          } catch {
            setFailed(true);
          } finally {
            setBusy(false);
          }
        }}
      >
        {file === "exercise" ? "下载练习 DOCX" : "下载答案 DOCX"}
      </Button>
    </span>
  );
}
