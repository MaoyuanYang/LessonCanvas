"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getApiToken } from "@/lib/auth";
import { ConversationRegion } from "@/components/conversation-region";
import { Alert, Button } from "@/components/ui";
import { ApiClientError, discoveryAnswers, discoveryStart, discoveryStatus } from "@/lib/api";

export function DiscoveryPanel({
  projectId,
  readOnly = false,
}: {
  projectId: string;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: ["discovery", projectId],
    queryFn: async () => discoveryStatus(await getApiToken(), projectId),
    retry: false,
  });

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["discovery", projectId] });

  const startMutation = useMutation({
    mutationFn: async () => discoveryStart(await getApiToken(), projectId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "启动失败"),
  });

  const answersMutation = useMutation({
    mutationFn: async () => discoveryAnswers(await getApiToken(), projectId, answers),
    onSuccess: () => {
      setAnswers({});
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiClientError ? err.message : "提交失败"),
  });

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
      {notFound && !readOnly ? (
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
              {readOnly ? (
                <p className="text-sm text-ink-secondary">{question.question}</p>
              ) : (
                <>
                  <label
                    className="text-sm text-ink-secondary"
                    htmlFor={`answer-${question.field}`}
                  >
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

      {status && status.status === "draft_ready" ? (
        <Alert tone="info">访谈已完成，请在“教学简报”页签查看并确认草稿。</Alert>
      ) : null}

      {!notFound && !readOnly ? (
        <ConversationRegion
          projectId={projectId}
          kind="discovery"
          narrateText="请叙述下一步访谈。"
          onError={setError}
        />
      ) : null}
    </div>
  );
}
