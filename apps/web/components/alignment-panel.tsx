"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { getApiToken } from "@/lib/auth";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, EmptyState, Modal, SkeletonRows } from "@/components/ui";
import type { WorkspaceTab } from "@/app/(authed)/projects/[projectId]/workspace-view";
import {
  ApiClientError,
  createDeliveryExport,
  downloadDeliveryExport,
  getAlignment,
  listDeliveryExports,
  PRODUCT_VALIDATION_STATUS_LABELS,
  recordAlignmentOverride,
  withdrawAlignmentOverride,
  type AlignmentFinding,
  type AlignmentView,
} from "@/lib/api";

const FAMILY_LABELS: Record<string, string> = {
  lesson_plan: "教案",
  slide_deck: "课件",
  exercise: "练习与答案",
};

const FAMILY_TABS: Record<string, WorkspaceTab> = {
  lesson_plan: "generation",
  slide_deck: "decks",
  exercise: "exercises",
};

const MEMBER_STATE_LABELS: Record<string, string> = {
  complete: "已覆盖",
  failed: "校验未通过",
  in_progress: "生成中",
  missing: "缺失",
};

const RECOVERY_LABELS: Record<string, string> = {
  revise_intent: "修正意图",
  wait_or_resume: "等待或恢复生成",
  override_or_regenerate: "记录理由并覆盖 / 重新生成",
  regenerate: "定向再生成",
};

function RecoveryAction({
  finding,
  onOverride,
  onNavigate,
  readOnly = false,
}: {
  finding: AlignmentFinding;
  onOverride: (finding: AlignmentFinding) => void;
  onNavigate: (tab: WorkspaceTab) => void;
  readOnly?: boolean;
}) {
  if (finding.resolved) {
    return <span className="text-xs text-ink-secondary">已按教师覆盖记录处理</span>;
  }
  return (
    <span className="flex flex-wrap gap-2">
      {finding.recovery_action === "revise_intent" ? (
        <Button variant="secondary" onClick={() => onNavigate("blueprint")}>
          {RECOVERY_LABELS.revise_intent}
        </Button>
      ) : null}
      {finding.recovery_action === "regenerate" || finding.recovery_action === "wait_or_resume" ? (
        <Button
          variant="secondary"
          onClick={() => onNavigate(FAMILY_TABS[finding.family ?? "lesson_plan"] ?? "generation")}
        >
          {finding.family ? FAMILY_LABELS[finding.family] : ""}生成
        </Button>
      ) : null}
      {finding.overridable && !readOnly ? (
        <Button variant="secondary" onClick={() => onOverride(finding)}>
          记录理由并覆盖
        </Button>
      ) : null}
    </span>
  );
}

export function AlignmentPanel({
  projectId,
  onNavigate,
  readOnly = false,
}: {
  projectId: string;
  onNavigate: (tab: WorkspaceTab) => void;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const [overrideTarget, setOverrideTarget] = useState<AlignmentFinding | null>(null);
  const [overrideReason, setOverrideReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [withdrawId, setWithdrawId] = useState<string | null>(null);

  const alignmentQuery = useQuery({
    queryKey: ["alignment", projectId],
    queryFn: async () => getAlignment(await getApiToken(), projectId),
    retry: false,
  });
  const exportsQuery = useQuery({
    queryKey: ["delivery-exports", projectId],
    queryFn: async () => listDeliveryExports(await getApiToken(), projectId),
    retry: false,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["alignment", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["delivery-exports", projectId] });
  };

  const overrideMutation = useMutation({
    mutationFn: async () => {
      if (!overrideTarget) throw new Error("no finding");
      return recordAlignmentOverride(await getApiToken(), projectId, overrideTarget.key, overrideReason);
    },
    onSuccess: () => {
      setOverrideTarget(null);
      setOverrideReason("");
      setActionError(null);
      invalidate();
    },
    onError: (error) => {
      setActionError(
        error instanceof ApiClientError ? error.message : "覆盖记录失败，请稍后重试。",
      );
    },
  });

  const withdrawMutation = useMutation({
    mutationFn: async () => {
      if (!withdrawId) throw new Error("no override");
      return withdrawAlignmentOverride(await getApiToken(), projectId, withdrawId);
    },
    onSuccess: () => {
      setWithdrawId(null);
      setActionError(null);
      invalidate();
    },
    onError: (error) => {
      setActionError(
        error instanceof ApiClientError ? error.message : "撤销覆盖失败，请稍后重试。",
      );
    },
  });

  const exportMutation = useMutation({
    mutationFn: async (label: "draft" | "validated") =>
      createDeliveryExport(await getApiToken(), projectId, label),
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
    onError: (error) => {
      if (error instanceof ApiClientError) {
        if (error.code === "STALE_VERSION") {
          invalidate();
          setActionError("版本已更新，正在刷新；请在最新版本上重新决定。");
          return;
        }
        const blocking = error.details?.blocking_findings;
        if (Array.isArray(blocking) && blocking.length > 0) {
          setActionError(
            `交付校验包被阻止：${blocking
              .map((item) => String((item as { title?: string }).title ?? ""))
              .join("；")}`,
          );
          return;
        }
        setActionError(error.message);
        return;
      }
      setActionError("导出失败，请稍后重试。");
    },
  });

  const downloadMutation = useMutation({
    mutationFn: async (exportId: string) => {
      const blob = await downloadDeliveryExport(await getApiToken(), projectId, exportId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `lessoncanvas-export-${exportId.slice(0, 8)}.zip`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    },
  });

  if (alignmentQuery.isLoading) {
    return (
      <div>
        <h2 className="text-lg font-semibold">对齐与交付</h2>
        <SkeletonRows />
      </div>
    );
  }

  if (alignmentQuery.isError) {
    const error = alignmentQuery.error;
    const requirement = error instanceof ApiClientError && error.code === "REQUIREMENT";
    return (
      <div>
        <h2 className="text-lg font-semibold">对齐与交付</h2>
        {requirement ? (
          <EmptyState
            title="尚未确认简报与蓝图版本"
            hint="对齐评审绑定当前确认的版本对；请先完成教学简报与单元蓝图的确认。"
          />
        ) : (
          <Alert tone="error">
            {error instanceof ApiClientError ? error.message : "无法加载对齐视图"}
          </Alert>
        )}
      </div>
    );
  }

  const alignment = alignmentQuery.data as AlignmentView;
  const severe = alignment.findings.filter((f) => f.severity === "severe");
  const warnings = alignment.findings.filter((f) => f.severity === "warning");
  const validated = alignment.technical_status === "validated";
  const exports = exportsQuery.data ?? [];

  return (
    <div>
      <h2 className="text-lg font-semibold">对齐与交付</h2>
      <p className="mb-4 mt-1 text-sm text-ink-secondary">
        绑定版本：简报 v{alignment.brief_version} · 蓝图 v{alignment.blueprint_version}。对齐结果由结构化数据确定性计算，不调用模型。
      </p>

      <div className="mb-6 flex flex-wrap items-center gap-3" aria-label="状态对">
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${
            validated ? "bg-evidence/10 text-evidence" : "bg-warning/10 text-warning"
          }`}
        >
          技术校验状态：{validated ? "技术校验通过" : "未完成（存在未解决严重问题）"}
        </span>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${
            alignment.product_validation_status === "passed"
              ? "bg-evidence/10 text-evidence"
              : alignment.product_validation_status === "failed"
                ? "bg-severe/10 text-severe"
                : alignment.product_validation_status === "not_evaluated"
                  ? "bg-stale/10 text-stale"
                  : "bg-warning/10 text-warning"
          }`}
        >
          产品验证状态：
          {PRODUCT_VALIDATION_STATUS_LABELS[alignment.product_validation_status] ??
            alignment.product_validation_status}
        </span>
      </div>

      {isDesktop ? (
        <section aria-label="教学目标覆盖" className="mb-6">
          <h3 className="mb-2 text-base font-medium">教学目标覆盖</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-ink-secondary">
                  <th scope="col" className="py-2 pr-4">教学目标</th>
                  <th scope="col" className="py-2 pr-4">课时</th>
                  <th scope="col" className="py-2 pr-4">教案</th>
                  <th scope="col" className="py-2 pr-4">课件</th>
                  <th scope="col" className="py-2 pr-4">练习与答案</th>
                  <th scope="col" className="py-2">汇总</th>
                </tr>
              </thead>
              <tbody>
                {alignment.objectives.map((objective) => (
                  <tr key={objective.id} className="border-b border-line">
                    <td className="py-2 pr-4">{objective.text ?? objective.id}</td>
                    <td className="py-2 pr-4">第 {objective.lessons.join("、") || "—"} 课</td>
                    <td className="py-2 pr-4">{objective.support.lesson_plan ? "已覆盖" : "缺失"}</td>
                    <td className="py-2 pr-4">{objective.support.slide_deck ? "已覆盖" : "缺失"}</td>
                    <td className="py-2 pr-4">{objective.support.exercise ? "已覆盖" : "缺失"}</td>
                    <td className="py-2">{objective.summary === "supported" ? "完整支持" : objective.summary === "partial" ? "部分支持" : "缺失"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <div className="mb-6">
          <DesktopRequiredNotice task="查看完整覆盖矩阵与打印报告" />
        </div>
      )}

      <section aria-label="发现的问题" className="mb-6">
        <h3 className="mb-2 text-base font-medium">发现的问题</h3>
        {alignment.findings.length === 0 ? (
          <p className="text-sm text-ink-secondary">未发现覆盖缺口或冲突。</p>
        ) : (
          <div className="space-y-4">
            <div>
              <h4 className="mb-1 text-sm font-medium">严重（{severe.length}）</h4>
              {severe.length === 0 ? (
                <p className="text-sm text-ink-secondary">无</p>
              ) : (
                <ul className="space-y-2" aria-label="严重问题列表">
                  {severe.map((finding) => (
                    <li key={finding.key} className="rounded border border-line p-3">
                      <p className="text-sm font-medium">
                        {finding.title}
                        {finding.resolved ? "（已按覆盖记录处理）" : ""}
                      </p>
                      {finding.evidence?.failure_reason ? (
                        <p className="mt-1 text-xs text-ink-secondary">
                          证据：{String(finding.evidence.failure_reason)}
                        </p>
                      ) : null}
                      <div className="mt-2">
                        <RecoveryAction
                          finding={finding}
                          onOverride={setOverrideTarget}
                          onNavigate={onNavigate}
                          readOnly={readOnly}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h4 className="mb-1 text-sm font-medium">警告（{warnings.length}）</h4>
              {warnings.length === 0 ? (
                <p className="text-sm text-ink-secondary">无</p>
              ) : (
                <ul className="space-y-1" aria-label="警告列表">
                  {warnings.map((finding) => (
                    <li key={finding.key} className="text-sm text-ink-secondary">
                      {finding.title}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </section>

      {alignment.overrides.length > 0 ? (
        <section aria-label="覆盖记录" className="mb-6">
          <h3 className="mb-2 text-base font-medium">覆盖记录</h3>
          <ul className="space-y-2">
            {alignment.overrides.map((override) => (
              <li key={override.id} className="rounded border border-line p-3 text-sm">
                <p className="font-medium">{override.finding_key}</p>
                <p className="mt-1 text-ink-secondary">理由：{override.reason}</p>
                <p className="mt-1 text-xs text-ink-secondary">
                  {override.status === "recorded" ? "已记录" : "已撤销"} · {override.created_at}
                </p>
                {override.status === "recorded" && !readOnly ? (
                  <Button
                    variant="quiet"
                    className="mt-1"
                    onClick={() => setWithdrawId(override.id)}
                  >
                    撤销覆盖
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-label="交付">
        <h3 className="mb-2 text-base font-medium">交付</h3>
        <p className="mb-3 text-sm text-ink-secondary">
          {validated
            ? "当前版本已通过技术校验，可交付校验包；草稿包也始终可导出。"
            : "存在未解决的严重问题：可导出明确标注的草稿包；交付校验包需先修正或覆盖全部严重问题。"}
        </p>
        {!readOnly ? (
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate("draft")}
            >
              {exportMutation.isPending ? "处理中…" : "导出草稿包（标注草稿）"}
            </Button>
            <Button
              disabled={!validated || exportMutation.isPending}
              onClick={() => exportMutation.mutate("validated")}
            >
              {exportMutation.isPending ? "处理中…" : "交付校验包"}
            </Button>
          </div>
        ) : null}
        {isDesktop ? (
          <div className="flex flex-wrap gap-3">
            <Button variant="quiet" onClick={() => window.open(`/projects/${projectId}/report?source=current`, "_blank")}>
              打印对齐报告
            </Button>
          </div>
        ) : null}
        {actionError ? (
          <div className="mt-3">
            <Alert tone="error">{actionError}</Alert>
          </div>
        ) : null}

        <h4 className="mb-2 mt-6 text-sm font-medium">导出历史</h4>
        {exports.length === 0 ? (
          <p className="text-sm text-ink-secondary">尚无导出记录。</p>
        ) : (
          <ul className="space-y-2" aria-label="导出历史">
            {exports.map((row) => (
              <li key={row.id} className="rounded border border-line p-3 text-sm">
                <p>
                  <span className="font-medium">{row.label === "draft" ? "草稿" : "校验包"}</span>
                  {" · "}
                  简报 v{row.brief_version} / 蓝图 v{row.blueprint_version} · {row.status === "ready" ? "就绪" : row.status === "building" ? "构建中" : "失败"}
                </p>
                {row.failure_reason ? (
                  <p className="mt-1 text-xs text-severe">{row.failure_reason}</p>
                ) : null}
                <div className="mt-2 flex gap-2">
                  {row.download_available ? (
                    <>
                      <Button
                        variant="secondary"
                        disabled={downloadMutation.isPending}
                        onClick={() => downloadMutation.mutate(row.id)}
                      >
                        下载 ZIP
                      </Button>
                      {isDesktop ? (
                        <Button
                          variant="quiet"
                          onClick={() =>
                            window.open(
                              `/projects/${projectId}/report?source=export&exportId=${row.id}`,
                              "_blank",
                            )
                          }
                        >
                          查看导出时报告快照
                        </Button>
                      ) : null}
                    </>
                  ) : row.status === "failed" && !readOnly ? (
                    <Button
                      variant="secondary"
                      disabled={exportMutation.isPending}
                      onClick={() => exportMutation.mutate(row.label)}
                    >
                      重新导出
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Modal
        open={overrideTarget !== null}
        onOpenChange={(open) => {
          if (!open) setOverrideTarget(null);
        }}
        title="记录理由并覆盖"
        description="覆盖不会修改被评内容，仅记录教学判断；理由将随对齐证据保存。"
      >
        <p className="mb-2 text-sm font-medium">{overrideTarget?.title}</p>
        <label className="block text-sm text-ink-secondary" htmlFor="override-reason">
          覆盖理由（必填，至少 10 个字符）
        </label>
        <textarea
          id="override-reason"
          className="mt-1 w-full rounded border border-line bg-paper p-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
          rows={3}
          value={overrideReason}
          onChange={(event) => setOverrideReason(event.target.value)}
        />
        <p className="mt-1 text-xs text-ink-secondary">{overrideReason.length} 个字符</p>
        <div className="mt-3 flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setOverrideTarget(null)}>
            取消
          </Button>
          <Button
            disabled={overrideReason.trim().length < 10 || overrideMutation.isPending}
            onClick={() => overrideMutation.mutate()}
          >
            {overrideMutation.isPending ? "处理中…" : "确认覆盖"}
          </Button>
        </div>
      </Modal>

      {withdrawId ? (
        <Modal
          open
          onOpenChange={(open) => {
            if (!open) setWithdrawId(null);
          }}
          title="撤销覆盖"
          description="撤销后该问题将重新回到未解决状态，状态会立即重新计算。"
        >
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setWithdrawId(null)}>
              取消
            </Button>
            <Button variant="destructive" disabled={withdrawMutation.isPending} onClick={() => withdrawMutation.mutate()}>
              {withdrawMutation.isPending ? "处理中…" : "确认撤销"}
            </Button>
          </div>
        </Modal>
      ) : null}

      {!isDesktop ? (
        <div className="mt-6">
          <DesktopRequiredNotice task="查看完整覆盖矩阵与打印报告" />
        </div>
      ) : null}
    </div>
  );
}
