"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { getApiToken } from "@/lib/auth";
import { Alert, SkeletonRows } from "@/components/ui";
import { MemoryCategoryChip } from "@/components/memory-shared";
import {
  MEMORY_CATEGORY_LABELS,
  getProjectMemory,
  setMemoryOverride,
  type MemoryCategory,
  type MemoryEffective,
} from "@/lib/api";

/**
 * F013 U3/U5: the evidence panel's 教师记忆（本项目） region — the project's
 * effective set with per-record project toggles (future runs), plus the
 * selected run's applied snapshot (history), conflicts, and budget skips.
 * A view over recorded trace state, never a second authority.
 */
export function MemoryContextRegion({
  projectId,
  runMemory,
  readOnly = false,
}: {
  projectId: string;
  runMemory: MemoryEffective | null;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const viewQuery = useQuery({
    queryKey: ["project-memory", projectId],
    queryFn: async () => getProjectMemory(await getApiToken(), projectId),
    retry: false,
  });

  const overrideMutation = useMutation({
    mutationFn: async (input: { recordId: string; enabled: boolean }) =>
      setMemoryOverride(await getApiToken(), projectId, input.recordId, input.enabled),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["project-memory", projectId] }),
  });

  const view = viewQuery.data;
  const records = view?.records ?? [];
  const effective = view?.effective;

  if (viewQuery.isLoading) return <SkeletonRows count={1} />;
  if (viewQuery.isError) {
    return <Alert tone="error">教师记忆读取失败，请重试。</Alert>;
  }
  if (!records.length && !runMemory) return null;

  const disabledIds = new Set(
    (effective?.project_disabled ?? []).map((entry) => entry.id),
  );

  return (
    <section
      aria-labelledby="project-memory-heading"
      className="rounded border border-line bg-surface-alt/60 p-4"
    >
      <h3 id="project-memory-heading" className="text-sm font-semibold text-ink">
        教师记忆（本项目）
      </h3>
      <p className="mt-1 text-xs text-ink-secondary">
        已确认的记忆默认应用于本项目；停用只影响本项目今后的运行。管理全部记忆请前往
        <Link className="ml-1 underline focus-visible:outline-2 focus-visible:outline-focus" href="/account">
          账号与数据
        </Link>
        。
      </p>

      {records.length === 0 ? (
        <p className="mt-2 text-sm text-ink-secondary">工作区尚未确认任何教师记忆。</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {records.map((record) => {
            const isDisabled = disabledIds.has(record.id) || record.project_enabled === false;
            return (
              <li
                key={record.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded border border-line bg-paper p-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <MemoryCategoryChip category={record.category} />
                    {runMemory?.conflicts.some((entry) => entry.id === record.id) ? (
                      <span className="rounded bg-warning/10 px-2 py-0.5 text-xs text-warning">
                        与当前确认版本冲突，已按确认版本执行
                      </span>
                    ) : null}
                    {runMemory?.budget_skipped.some((entry) => entry.id === record.id) ? (
                      <span className="rounded bg-stale/10 px-2 py-0.5 text-xs text-stale">
                        未注入（超出记忆预算）
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm text-ink">{record.content}</p>
                </div>
                {readOnly ? null : (
                  <label className="flex items-center gap-2 text-xs text-ink-secondary">
                    <input
                      type="checkbox"
                      className="focus-visible:outline-2 focus-visible:outline-focus"
                      checked={!isDisabled}
                      disabled={overrideMutation.isPending}
                      aria-label={`在本项目${isDisabled ? "启用" : "停用"}该记忆`}
                      onChange={(event) =>
                        overrideMutation.mutate({
                          recordId: record.id,
                          enabled: event.target.checked,
                        })
                      }
                    />
                    本项目应用
                  </label>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {runMemory ? (
        <div className="mt-3 border-t border-line pt-3">
          <h4 className="text-xs font-semibold text-ink-secondary">
            当前运行的应用快照（{runMemory.applied.length} 条，共 {runMemory.injected_chars} 字符）
          </h4>
          {runMemory.applied.length ? (
            <ul className="mt-1 space-y-1 text-sm text-ink">
              {runMemory.applied.map((entry) => (
                <li key={entry.id} className="flex flex-wrap items-center gap-2">
                  <MemoryCategoryChip category={entry.category} />
                  <span>{entry.content}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-sm text-ink-secondary">
              本次运行未应用教师记忆
              {runMemory.conflicts.length || runMemory.budget_skipped.length || runMemory.project_disabled.length
                ? "（存在被冲突、预算或项目停用跳过的记录，见上方标注）"
                : ""}
              。
            </p>
          )}
          {runMemory.project_disabled.length ? (
            <p className="mt-1 text-xs text-stale">
              项目停用跳过：
              {runMemory.project_disabled
                .map((entry) => MEMORY_CATEGORY_LABELS[entry.category as MemoryCategory] ?? entry.category)
                .join("、")}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
