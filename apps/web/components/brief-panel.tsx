"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getApiToken } from "@/lib/auth";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, ConfirmModal } from "@/components/ui";
import { ApiClientError, confirmBrief, getBrief, patchDraft } from "@/lib/api";
import { MemoryProposalRegion } from "@/components/memory-proposal-region";

const FIELD_LABELS: Record<string, string> = {
  unit_theme: "单元主题",
  lesson_count: "课时数",
  student_context: "学情",
  teaching_objectives: "教学目标",
  material_positioning: "教材定位",
  output_language_mode: "输出语言",
  assessment_orientation: "评估倾向",
};

export function BriefPanel({
  projectId,
  readOnly = false,
}: {
  projectId: string;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const canWrite = isDesktop && !readOnly;
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [stale, setStale] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const briefQuery = useQuery({
    queryKey: ["brief", projectId],
    queryFn: async () => getBrief(await getApiToken(), projectId),
  });

  const invalidate = () => void queryClient.invalidateQueries({ queryKey: ["brief", projectId] });

  const patchMutation = useMutation({
    mutationFn: async () => {
      const base = briefQuery.data?.draft_revision;
      if (base == null) throw new Error("draft missing");
      return patchDraft(await getApiToken(), projectId, editing, base);
    },
    onSuccess: () => {
      setEditing({});
      setStale(false);
      invalidate();
    },
    onError: (err) => {
      if (err instanceof ApiClientError && err.code === "STALE_VERSION") {
        setStale(true);
        invalidate();
      } else {
        setError(err instanceof ApiClientError ? err.message : "保存失败");
      }
    },
  });

  const confirmMutation = useMutation({
    mutationFn: async () => confirmBrief(await getApiToken(), projectId),
    onSuccess: () => {
      setConfirmOpen(false);
      invalidate();
    },
    onError: (err) => {
      setError(err instanceof ApiClientError ? err.message : "确认失败");
    },
  });

  const brief = briefQuery.data;
  const fields = brief?.fields ?? null;
  const allPresent =
    fields !== null && Object.values(fields).every((entry) => Boolean(entry.value));

  return (
    <div className="space-y-4">
      <MemoryProposalRegion kinds={["brief_confirm"]} readOnly={readOnly} />
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-ink">教学简报</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            {brief?.confirmed_version
              ? `已确认版本 ${brief.confirmed_version}（不可变）`
              : `草稿修订 ${brief?.draft_revision ?? "—"}`}
          </p>
        </div>
        {canWrite && fields ? (
          <Button onClick={() => setConfirmOpen(true)} disabled={!allPresent}>
            确认简报
          </Button>
        ) : null}
      </div>

      {!canWrite && !readOnly ? <DesktopRequiredNotice task="编辑或确认简报" /> : null}
      {stale ? (
        <Alert tone="warning">存在更新的草稿修订，已为你加载最新内容，请重新编辑。</Alert>
      ) : null}
      {error ? <Alert tone="error">{error}</Alert> : null}

      {briefQuery.isLoading ? <p className="text-sm text-ink-secondary">加载中…</p> : null}
      {!fields && !briefQuery.isLoading ? (
        <p className="text-sm text-ink-secondary">访谈完成后将在此生成简报草稿。</p>
      ) : null}

      {fields ? (
        <ul className="space-y-3">
          {Object.entries(fields).map(([field, entry]) => (
            <li key={field} className="rounded border border-line bg-paper p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-ink">{FIELD_LABELS[field] ?? field}</span>
                {entry.unresolved ? (
                  <span className="rounded bg-warning/10 px-2 py-0.5 text-xs text-warning">
                    待补充
                  </span>
                ) : (
                  <span className="rounded bg-evidence/10 px-2 py-0.5 text-xs text-evidence">
                    {entry.grounding === "teacher-stated" ? "教师陈述" : "来源引用"}
                  </span>
                )}
              </div>
              {canWrite ? (
                <input
                  aria-label={`编辑${FIELD_LABELS[field] ?? field}`}
                  className="mt-2 w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
                  value={editing[field] ?? entry.value ?? ""}
                  onChange={(event) =>
                    setEditing((current) => ({ ...current, [field]: event.target.value }))
                  }
                />
              ) : (
                <p className="mt-2 text-sm text-ink-secondary">{entry.value ?? "—"}</p>
              )}
            </li>
          ))}
        </ul>
      ) : null}

      {canWrite && fields ? (
        <Button variant="secondary" onClick={() => patchMutation.mutate()}>
          保存修订
        </Button>
      ) : null}

      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="确认教学简报"
        description="确认后将生成不可变的简报版本，作为单元规划的唯一授权输入；后续修改会创建新草稿。"
        confirmLabel="确认"
        busy={confirmMutation.isPending}
        onConfirm={() => confirmMutation.mutate()}
      />
    </div>
  );
}
