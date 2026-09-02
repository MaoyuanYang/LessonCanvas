"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getApiToken } from "@/lib/auth";
import { Alert, Button } from "@/components/ui";
import {
  ApiClientError,
  MEMORY_CATEGORY_LABELS,
  MEMORY_RECORD_LIMIT_CHARS,
  confirmMemoryProposal,
  rejectMemoryProposal,
  type MemoryCategory,
  type MemoryProposal,
} from "@/lib/api";

/** F013 U4: category chip — text label, never color alone. */
export function MemoryCategoryChip({ category }: { category: MemoryCategory }) {
  return (
    <span className="inline-flex items-center rounded bg-evidence/10 px-2 py-0.5 text-xs font-medium text-evidence">
      {MEMORY_CATEGORY_LABELS[category] ?? category}
    </span>
  );
}

/**
 * F013 U2: one proposal card. Confirm supports inline editing first (with the
 * live length counter); concurrent decisions surface the honest stale
 * message and refresh the list.
 */
export function MemoryProposalCard({ proposal }: { proposal: MemoryProposal }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<string | null>(null);
  const [staleMessage, setStaleMessage] = useState<string | null>(null);
  const [limitMessage, setLimitMessage] = useState<string | null>(null);

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["memory-overview"] });

  const handleStale = (err: unknown, fallback: string) => {
    if (err instanceof ApiClientError && err.code === "STALE_VERSION") {
      setStaleMessage("该提议已被处理，已为你刷新列表。");
      invalidate();
      return;
    }
    if (err instanceof ApiClientError && err.code === "MEMORY_LIMIT") {
      setLimitMessage(memoryLimitText(err));
      return;
    }
    setStaleMessage(err instanceof ApiClientError ? err.message : fallback);
  };

  const confirmMutation = useMutation({
    mutationFn: async () =>
      confirmMemoryProposal(await getApiToken(), proposal.id, editing ?? undefined),
    onSuccess: () => {
      setEditing(null);
      setStaleMessage(null);
      setLimitMessage(null);
      invalidate();
    },
    onError: (err) => handleStale(err, "确认失败，请重试。"),
  });

  const rejectMutation = useMutation({
    mutationFn: async () => rejectMemoryProposal(await getApiToken(), proposal.id),
    onSuccess: () => {
      setStaleMessage(null);
      invalidate();
    },
    onError: (err) => handleStale(err, "拒绝失败，请重试。"),
  });

  const draft = editing ?? proposal.content;
  const overLength = draft.length > MEMORY_RECORD_LIMIT_CHARS;

  return (
    <li className="rounded border border-line bg-paper p-4">
      <div className="flex items-center gap-2">
        <MemoryCategoryChip category={proposal.category} />
        <span className="text-xs text-ink-secondary">待确认记忆提议</span>
      </div>
      {editing === null ? (
        <p className="mt-2 text-sm text-ink">{proposal.content}</p>
      ) : (
        <div className="mt-2">
          <label className="sr-only" htmlFor={`memory-proposal-edit-${proposal.id}`}>
            编辑记忆内容
          </label>
          <textarea
            id={`memory-proposal-edit-${proposal.id}`}
            className="w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
            value={editing}
            rows={3}
            onChange={(event) => setEditing(event.target.value)}
          />
          <p className={`mt-1 text-xs ${overLength ? "text-severe" : "text-ink-secondary"}`}>
            {draft.length}/{MEMORY_RECORD_LIMIT_CHARS} 字符
          </p>
        </div>
      )}
      {staleMessage ? <Alert tone="warning">{staleMessage}</Alert> : null}
      {limitMessage ? <Alert tone="warning">{limitMessage}</Alert> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          disabled={confirmMutation.isPending || overLength || !draft.trim()}
          onClick={() => confirmMutation.mutate()}
        >
          {confirmMutation.isPending ? "确认中…" : "确认记住"}
        </Button>
        {editing === null ? (
          <Button variant="secondary" onClick={() => setEditing(proposal.content)}>
            编辑后确认
          </Button>
        ) : (
          <Button variant="secondary" onClick={() => setEditing(null)}>
            取消编辑
          </Button>
        )}
        <Button
          variant="quiet"
          disabled={rejectMutation.isPending}
          onClick={() => rejectMutation.mutate()}
        >
          拒绝
        </Button>
      </div>
    </li>
  );
}

function memoryLimitText(err: ApiClientError): string {
  const details = err.details as { limit?: number; max_chars?: number };
  if (details?.max_chars) {
    return `单条记忆不超过 ${details.max_chars} 字符，请精简后再确认。`;
  }
  return `记忆数量已达上限（${details?.limit ?? 20} 条）。可删除不再需要的记忆后再确认。`;
}
