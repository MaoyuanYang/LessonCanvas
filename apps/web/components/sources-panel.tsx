"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { getApiToken } from "@/lib/auth";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, StatusBadge } from "@/components/ui";
import {
  ApiClientError,
  deleteSource,
  listSources,
  retrySourceAnalysis,
  uploadSource,
} from "@/lib/api";
import type { Source } from "@/lib/api";

const EMBEDDING_STATUS_LABELS: Record<string, string> = {
  ok: "已嵌入",
  failed: "未嵌入",
  pending: "待嵌入",
};

// F014 U1/U5 (ux-ui.md): expandable per-source chunk view — the full-fidelity
// counterpart of citation tracing, with explicit 未嵌入 disclosure.
function SourceChunkRegion({ source }: { source: Source }) {
  const [expanded, setExpanded] = useState(false);
  const chunks = source.chunks ?? [];
  const failed = chunks.filter((chunk) => chunk.embedding_status !== "ok").length;
  return (
    <div className="mt-2">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        className="text-xs text-evidence focus-visible:outline-2 focus-visible:outline-focus"
      >
        查看切块（{chunks.length} 段{failed > 0 ? `，${failed} 段未嵌入` : ""}）
      </button>
      {expanded ? (
        <ol className="mt-2 space-y-2">
          {chunks.map((chunk) => (
            <li
              key={chunk.position}
              className="rounded border border-line bg-surface-alt/60 p-2 text-xs text-ink"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">第 {chunk.position} 段</span>
                <StatusBadge status={EMBEDDING_STATUS_LABELS[chunk.embedding_status] ?? chunk.embedding_status} />
                {chunk.embedding_status === "failed" && chunk.embedding_error ? (
                  <span className="text-ink-secondary">原因：{chunk.embedding_error}</span>
                ) : null}
              </div>
              <p className="mt-1 whitespace-pre-wrap break-words">{chunk.text}</p>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

// F016 U4 (ux-ui.md): per-source analysis badge, expandable digest with its
// own cost line, and the gated manual retry. Analysis failure never blocks
// the source (chunk view and deletion behave as before).
const ANALYSIS_STATUS_LABELS: Record<string, string> = {
  pending: "待分析",
  analyzing: "分析中",
  ready: "已分析",
  failed: "分析失败",
};

function formatAnalysisCost(analysis: NonNullable<Source["analysis"]>): string {
  if (analysis.cost_usd === null || analysis.cost_usd === undefined) return "未记录";
  return `约 $${analysis.cost_usd.toFixed(4)}（估算）`;
}

function SourceAnalysisRegion({
  source,
  canWrite,
  onRetry,
  retryPending,
}: {
  source: Source;
  canWrite: boolean;
  onRetry: (sourceId: string) => void;
  retryPending: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const analysis = source.analysis;
  if (!analysis) return null;
  const failed = analysis.status === "failed";
  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge
          status={ANALYSIS_STATUS_LABELS[analysis.status] ?? analysis.status}
        />
        {(analysis.status === "ready" || failed) && (
          <button
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
            className="text-xs text-evidence focus-visible:outline-2 focus-visible:outline-focus"
          >
            {failed ? "查看失败原因" : "查看来源分析"}
          </button>
        )}
        {failed && canWrite ? (
          <button
            type="button"
            disabled={retryPending}
            onClick={() => onRetry(source.id)}
            className="text-xs text-evidence underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-focus disabled:text-ink-secondary"
          >
            重试分析
          </button>
        ) : null}
      </div>
      {expanded ? (
        failed ? (
          <p className="mt-2 text-xs text-ink-secondary">原因：{analysis.error ?? "未知"}</p>
        ) : (
          <div className="mt-2 space-y-1 rounded border border-line bg-surface-alt/60 p-2 text-xs text-ink">
            {analysis.topics.length > 0 ? (
              <p>
                <span className="font-medium">主题：</span>
                {analysis.topics.join("；")}
              </p>
            ) : null}
            {analysis.language_points.length > 0 ? (
              <p>
                <span className="font-medium">语言点：</span>
                {analysis.language_points.join("；")}
              </p>
            ) : null}
            {analysis.key_passages.length > 0 ? (
              <p>
                <span className="font-medium">关键段落：</span>
                第 {analysis.key_passages.map((p) => p.chunk_position).join("、")} 段
              </p>
            ) : null}
            <p className="text-ink-secondary">
              模型 {analysis.model ?? "未记录"} · 延迟 {analysis.latency_ms ?? "未记录"} ms · 成本{" "}
              {formatAnalysisCost(analysis)}
            </p>
          </div>
        )
      ) : null}
    </div>
  );
}

export function SourcesPanel({
  projectId,
  readOnly = false,
}: {
  projectId: string;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const canWrite = isDesktop && !readOnly;
  const fileInput = useRef<HTMLInputElement>(null);
  const [rights, setRights] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ["sources", projectId],
    queryFn: async () => listSources(await getApiToken(), projectId),
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ file, acknowledged }: { file: File; acknowledged: boolean }) =>
      uploadSource(await getApiToken(), projectId, file, acknowledged),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
    },
    onError: (err) => {
      setError(err instanceof ApiClientError ? err.message : "上传失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (sourceId: string) => deleteSource(await getApiToken(), projectId, sourceId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sources", projectId] }),
  });

  const retryMutation = useMutation({
    mutationFn: async (sourceId: string) =>
      retrySourceAnalysis(await getApiToken(), projectId, sourceId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sources", projectId] }),
    onError: (err) => {
      if (err instanceof ApiClientError) setError(err.message);
      else setError("重试分析失败");
    },
  });

  const sources = sourcesQuery.data;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-ink">来源材料</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          支持 PDF、DOCX、TXT、MD，单个不超过 20MB，最多 10 个。含学生个人身份信息的材料将被拒绝。
        </p>
      </div>

      {!canWrite && !readOnly ? <DesktopRequiredNotice task="上传或删除来源" /> : null}

      {canWrite ? (
        <form
          className="flex flex-wrap items-center gap-3 rounded border border-line bg-surface-alt p-4"
          onSubmit={(event) => {
            event.preventDefault();
            const file = fileInput.current?.files?.[0];
            if (!file) {
              setError("请选择文件");
              return;
            }
            if (!rights) {
              setError("请先确认材料使用授权");
              return;
            }
            uploadMutation.mutate({ file, acknowledged: rights });
          }}
        >
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            aria-label="选择来源文件"
            className="text-sm text-ink-secondary"
          />
          <label className="flex items-center gap-2 text-sm text-ink-secondary">
            <input
              type="checkbox"
              checked={rights}
              onChange={(event) => setRights(event.target.checked)}
            />
            我确认有权使用该材料用于备课
          </label>
          <Button type="submit" disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? "上传中…" : "上传"}
          </Button>
        </form>
      ) : null}

      {error ? <Alert tone="error">{error}</Alert> : null}

      {sourcesQuery.isLoading ? <p className="text-sm text-ink-secondary">加载中…</p> : null}

      {sources && sources.length === 0 ? (
        <p className="text-sm text-ink-secondary">还没有来源材料。</p>
      ) : null}

      {sources && sources.length > 0 ? (
        <ul className="space-y-2">
          {sources.map((source) => (
            <li
              key={source.id}
              className="flex items-center justify-between gap-4 rounded border border-line bg-paper p-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <span className="truncate text-sm font-medium text-ink">{source.filename}</span>
                  <StatusBadge status={source.status} />
                </div>
                {source.rejection_message ? (
                  <p className="mt-1 text-xs text-severe">{source.rejection_message}</p>
                ) : null}
                {source.status === "delete_failed" ? (
                  <p className="mt-1 text-xs text-warning">
                    对象存储残留，删除未完成；再次点击「删除」即可修复。
                  </p>
                ) : null}
                {source.status === "ready" && (source.chunks?.length ?? 0) > 0 ? (
                  <SourceChunkRegion source={source} />
                ) : null}
                <SourceAnalysisRegion
                  source={source}
                  canWrite={canWrite}
                  onRetry={(sourceId) => retryMutation.mutate(sourceId)}
                  retryPending={retryMutation.isPending}
                />
              </div>
              {canWrite ? (
                <Button
                  variant="secondary"
                  onClick={() => deleteMutation.mutate(source.id)}
                  disabled={deleteMutation.isPending}
                >
                  删除
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
