"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getApiToken } from "@/lib/auth";
import { Alert, Button, ConfirmModal, EmptyState, Modal, SkeletonRows } from "@/components/ui";
import { MemoryCategoryChip, MemoryProposalCard } from "@/components/memory-shared";
import {
  ApiClientError,
  MEMORY_RECORD_LIMIT_CHARS,
  deleteMemoryRecord,
  editMemoryRecord,
  getMemoryOverview,
  type MemoryOverview,
  type MemoryRecord,
} from "@/lib/api";

/**
 * F013 U1: the account-area 教师记忆 section — workspace-level record
 * management plus the pending-proposal consolidation so a teacher with
 * several projects can address everything in one place.
 */
export function AccountMemorySection() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<MemoryRecord | null>(null);
  const [editContent, setEditContent] = useState("");
  const [deleting, setDeleting] = useState<MemoryRecord | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [limitMessage, setLimitMessage] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["memory-overview"],
    queryFn: async () => getMemoryOverview(await getApiToken()),
    // Poll lightly so proposal cards and the badge appear after
    // asynchronous passes settle (F013 D3 best-effort triggers).
    refetchInterval: 4000,
  });

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["memory-overview"] });

  const editMutation = useMutation({
    mutationFn: async (input: { record: MemoryRecord; content: string }) =>
      editMemoryRecord(await getApiToken(), input.record.id, input.content),
    onSuccess: () => {
      setEditing(null);
      setLimitMessage(null);
      invalidate();
    },
    onError: (err) => handleError(err, "保存失败，请重试。"),
  });

  const deleteMutation = useMutation({
    // The target is passed explicitly: radix closes the dialog (clearing the
    // selection state) before the composed click handler runs, so the
    // mutation must not depend on the latest render's closure.
    mutationFn: async (record: MemoryRecord) =>
      deleteMemoryRecord(await getApiToken(), record.id),
    onSuccess: () => {
      setFeedback("记忆已删除；今后的运行将不再应用它。");
      setDeleting(null);
      invalidate();
    },
    onError: (err) => handleError(err, "删除失败，请重试。"),
  });

  const handleError = (err: unknown, fallback: string) => {
    if (err instanceof ApiClientError && err.code === "MEMORY_LIMIT") {
      const details = err.details as { max_chars?: number };
      setLimitMessage(
        details?.max_chars
          ? `单条记忆不超过 ${details.max_chars} 字符，请精简后再保存。`
          : "记忆数量已达上限，请先删除不再需要的记忆。",
      );
      return;
    }
    setFeedback(err instanceof ApiClientError ? err.message : fallback);
  };

  const overview: MemoryOverview | undefined = overviewQuery.data;
  const pending = (overview?.proposals ?? []).filter((item) => item.status === "pending");

  return (
    <section aria-labelledby="memory-heading" className="space-y-3">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="memory-heading" className="text-base font-semibold text-ink">
          教师记忆
        </h2>
        {overview ? (
          <p className="text-sm text-ink-secondary" aria-label={`已确认记忆 ${overview.quota?.used ?? 0} 条，上限 ${overview.quota?.limit ?? 20} 条`}>
            {(overview.quota?.used ?? 0)}/{(overview.quota?.limit ?? 20)} 条
          </p>
        ) : null}
      </div>
      <p className="text-xs text-ink-secondary">
        仅保存你确认过的偏好，用于新项目的需求访谈与生成（作为从属上下文，永不覆盖已确认版本）；记录随工作区删除一并清除。
      </p>

      {feedback ? <Alert tone="info">{feedback}</Alert> : null}
      {limitMessage ? <Alert tone="warning">{limitMessage}</Alert> : null}

      {overviewQuery.isLoading ? <SkeletonRows /> : null}
      {overviewQuery.isError ? (
        <Alert tone="error">记忆读取失败，请重试。</Alert>
      ) : null}

      {overview && (overview.records ?? []).length === 0 && pending.length === 0 ? (
        <EmptyState
          title="尚未确认任何教师记忆"
          hint="确认简报、蓝图或完成生成后，Agent 会在此和工作区中提出值得记住的偏好。"
        />
      ) : null}

      {pending.length ? (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-ink">待确认提议（{pending.length}）</h3>
          <ul className="space-y-3">
            {pending.map((proposal) => (
              <MemoryProposalCard key={proposal.id} proposal={proposal} />
            ))}
          </ul>
        </div>
      ) : null}

      {overview && (overview.records ?? []).length ? (
        <ul className="space-y-2">
          {(overview.records ?? []).map((record) => (
            <li key={record.id} className="rounded border border-line bg-paper p-4">
              <div className="flex flex-wrap items-center gap-2">
                <MemoryCategoryChip category={record.category} />
                {record.conflicts_with_latest_brief ? (
                  <span className="rounded bg-warning/10 px-2 py-0.5 text-xs text-warning">
                    与最近确认简报冲突（已按确认版本执行）
                  </span>
                ) : null}
                {record.has_project_disabled ? (
                  <span className="rounded bg-stale/10 px-2 py-0.5 text-xs text-stale">
                    在部分项目已停用
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-ink">{record.content}</p>
              <div className="mt-3 flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditing(record);
                    setEditContent(record.content);
                    setLimitMessage(null);
                  }}
                >
                  编辑
                </Button>
                <Button variant="quiet" onClick={() => setDeleting(record)}>
                  删除
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <Modal
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) setEditing(null);
        }}
        title="编辑教师记忆"
        description={`单条记忆不超过 ${MEMORY_RECORD_LIMIT_CHARS} 字符；修改仅影响今后的运行。`}
      >
        <label className="sr-only" htmlFor="memory-edit-input">
          记忆内容
        </label>
        <textarea
          id="memory-edit-input"
          className="w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
          rows={4}
          value={editContent}
          onChange={(event) => setEditContent(event.target.value)}
        />
        <p
          className={`mt-1 text-xs ${
            editContent.length > MEMORY_RECORD_LIMIT_CHARS ? "text-severe" : "text-ink-secondary"
          }`}
        >
          {editContent.length}/{MEMORY_RECORD_LIMIT_CHARS} 字符
        </p>
        <div className="mt-4 flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setEditing(null)}>
            取消
          </Button>
          <Button
            disabled={
              editMutation.isPending ||
              !editContent.trim() ||
              editContent.length > MEMORY_RECORD_LIMIT_CHARS
            }
            onClick={() => {
            if (editing) editMutation.mutate({ record: editing, content: editContent });
          }}
          >
            {editMutation.isPending ? "保存中…" : "保存"}
          </Button>
        </div>
      </Modal>

      <ConfirmModal
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title="删除教师记忆"
        description="删除后今后的运行将不再应用该记忆；历史运行记录保持不变，并随项目删除一并移除。"
        confirmLabel="确认删除"
        destructive
        busy={deleteMutation.isPending}
        onConfirm={() => {
          if (deleting) deleteMutation.mutate(deleting);
        }}
      />
    </section>
  );
}
