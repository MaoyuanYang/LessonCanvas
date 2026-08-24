"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Alert, Button } from "@/components/ui";
import {
  ApiClientError,
  discoveryAnswers,
  discoveryStart,
  discoveryStatus,
  narrate,
  reask,
  stopNarration,
  streamUrl,
} from "@/lib/api";

export function DiscoveryPanel({ projectId }: { projectId: string }) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [narration, setNarration] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const statusQuery = useQuery({
    queryKey: ["discovery", projectId],
    queryFn: async () => discoveryStatus(await getToken(), projectId),
    retry: false,
  });

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["discovery", projectId] });

  const startMutation = useMutation({
    mutationFn: async () => discoveryStart(await getToken(), projectId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "启动失败"),
  });

  const answersMutation = useMutation({
    mutationFn: async () => discoveryAnswers(await getToken(), projectId, answers),
    onSuccess: () => {
      setAnswers({});
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "提交失败"),
  });

  const stopMutation = useMutation({
    mutationFn: async () => stopNarration(await getToken(), projectId),
    onSuccess: () => abortRef.current?.abort(),
  });

  async function startStream() {
    const token = await getToken();
    setStreaming(true);
    setNarration("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(streamUrl(projectId), {
        headers: token ? { authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            if (data.t) setNarration((current) => current + data.t);
          }
        }
      }
    } catch {
      // stopped or closed by user
    } finally {
      setStreaming(false);
      invalidate();
    }
  }

  const narrateMutation = useMutation({
    mutationFn: async () => narrate(await getToken(), projectId, "请叙述下一步访谈。"),
    onSuccess: () => void startStream(),
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "叙述失败"),
  });

  const reaskMutation = useMutation({
    mutationFn: async () => reask(await getToken(), projectId, "请重新提问。"),
    onSuccess: () => void startStream(),
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "重问失败"),
  });

  useEffect(() => () => abortRef.current?.abort(), []);

  const status = statusQuery.data;
  const notFound = statusQuery.error instanceof ApiClientError && statusQuery.error.status === 404;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-ink">需求访谈</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          Agent 只针对材料中缺失的教学需求提问，最多 6 轮、每轮最多 3 问。
        </p>
      </div>

      {error ? <Alert tone="error">{error}</Alert> : null}

      {statusQuery.isLoading ? <p className="text-sm text-ink-secondary">加载中…</p> : null}
      {notFound ? (
        <Button onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
          开始访谈
        </Button>
      ) : null}

      {status && status.status === "provider_failed" ? (
        <Alert tone="warning">模型服务暂时不可用，状态已保留，可重试。</Alert>
      ) : null}

      {status && status.questions.length > 0 && status.status === "questioning" ? (
        <div className="space-y-3 rounded border border-line bg-surface-alt p-4">
          <p className="text-sm font-medium text-ink">
            第 {status.round_count} 轮提问（{status.questions.length} 问）
          </p>
          {status.questions.map((question) => (
            <div key={question.field}>
              <label className="text-sm text-ink-secondary" htmlFor={`answer-${question.field}`}>
                {question.question}
              </label>
              <textarea
                id={`answer-${question.field}`}
                rows={2}
                className="mt-1 w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                value={answers[question.field] ?? ""}
                onChange={(event) =>
                  setAnswers((current) => ({ ...current, [question.field]: event.target.value }))
                }
              />
            </div>
          ))}
          <Button onClick={() => answersMutation.mutate()} disabled={answersMutation.isPending}>
            {answersMutation.isPending ? "提交中…" : "提交回答"}
          </Button>
        </div>
      ) : null}

      {status && status.status === "draft_ready" ? (
        <Alert tone="info">访谈已完成，请在“教学简报”页签查看并确认草稿。</Alert>
      ) : null}

      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          onClick={() => narrateMutation.mutate()}
          disabled={narrateMutation.isPending || streaming || notFound}
        >
          生成叙述
        </Button>
        {streaming ? (
          <Button variant="quiet" onClick={() => stopMutation.mutate()}>
            停止
          </Button>
        ) : narration ? (
          <Button variant="quiet" onClick={() => reaskMutation.mutate()}>
            重新提问
          </Button>
        ) : null}
      </div>

      {narration ? (
        <p aria-live="polite" className="rounded border border-line bg-paper p-4 text-sm text-ink">
          {narration}
        </p>
      ) : null}
    </div>
  );
}
