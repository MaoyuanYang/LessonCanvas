"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, ConfirmModal } from "@/components/ui";
import {
  apiFetch,
  getAccountAudit,
  getAccountUsage,
  type AccountAuditPage,
  type AccountUsage,
} from "@/lib/api";
import { getApiToken } from "@/lib/auth";

interface DeletionEvent {
  status: string;
  detail: string | null;
  created_at: string;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function formatRate(usage: AccountUsage): string {
  const rate = usage.request_rate;
  const used = rate.used;
  return `${used}/${rate.limit}（本窗口）`;
}

export default function AccountPage() {
  const isDesktop = useDesktop();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
  const [result, setResult] = useState<{ purged: boolean } | null>(null);

  const statusQuery = useQuery({
    queryKey: ["account-deletion-status"],
    queryFn: async () => apiFetch<DeletionEvent[]>("/account/deletion-status", { token: await getApiToken() }),
  });

  const usageQuery = useQuery({
    queryKey: ["account-usage"],
    queryFn: async () => getAccountUsage(await getApiToken()),
  });

  const auditQuery = useQuery({
    queryKey: ["account-audit"],
    queryFn: async () => getAccountAudit(await getApiToken(), 50),
    enabled: auditOpen,
  });

  const deleteMutation = useMutation({
    mutationFn: async () =>
      apiFetch<{ purged: boolean }>("/account", {
        method: "DELETE",
        token: await getApiToken(),
      }),
    onSuccess: (body) => {
      setResult(body);
      setConfirmOpen(false);
    },
  });

  const events = statusQuery.data ?? [];
  const purgeFailed = events.some((event) => event.status === "purge_failed");
  const usage: AccountUsage | null = usageQuery.data ?? null;
  const audit: AccountAuditPage | null = auditQuery.data ?? null;

  return (
    <main className="mx-auto w-full max-w-3xl space-y-8 px-6 py-8">
      <div>
        <h1 className="text-2xl font-semibold text-ink">账号与数据</h1>
        <p className="mt-2 text-sm text-ink-secondary">
          登录身份：本浏览器工作区（由浏览器本地令牌标识；清除浏览器数据将获得新的空白工作区）。你的上传、生成内容与完整运行记录仅属于你的工作区。
        </p>
      </div>

      <section aria-labelledby="usage-heading" className="space-y-3">
        <h2 id="usage-heading" className="text-base font-semibold text-ink">
          使用与限额
        </h2>
        {usageQuery.isLoading ? <p className="text-sm text-ink-secondary">加载中…</p> : null}
        {usageQuery.isError ? (
          <Alert tone="error">用量读取失败，请重试。</Alert>
        ) : null}
        {usage ? (
          <dl className="grid grid-cols-1 gap-2 rounded border border-line bg-surface-alt p-4 text-sm sm:grid-cols-2">
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">请求速率（当前窗口）</dt>
              <dd className="font-medium text-ink">{formatRate(usage)}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">高频写操作（当前窗口）</dt>
              <dd className="font-medium text-ink">
                {usage.expensive_rate.used}/{usage.expensive_rate.limit}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">并发生成运行</dt>
              <dd className="font-medium text-ink">
                {usage.concurrent_generation_runs.active}/{usage.concurrent_generation_runs.limit}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">并发实时流</dt>
              <dd className="font-medium text-ink">
                {usage.concurrent_sse_streams.active}/{usage.concurrent_sse_streams.limit}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">今日上传量</dt>
              <dd className="font-medium text-ink">
                {formatBytes(usage.upload_daily_bytes.used)}/{formatBytes(usage.upload_daily_bytes.limit)}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">项目数</dt>
              <dd className="font-medium text-ink">
                {usage.projects.used}/{usage.projects.limit}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">规划运行数</dt>
              <dd className="font-medium text-ink">
                {usage.planning_runs.used}/{usage.planning_runs.limit}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-ink-secondary">讲解生成</dt>
              <dd className="font-medium text-ink">
                {usage.evidence_narration.used}/{usage.evidence_narration.limit}
              </dd>
            </div>
          </dl>
        ) : null}
        <p className="text-xs text-ink-secondary">
          所有限额按工作区独立计算，窗口到点自动恢复；达到上限时操作会被拒绝并提示恢复时间。
        </p>
      </section>

      <section aria-labelledby="privacy-heading" className="space-y-2">
        <h2 id="privacy-heading" className="text-base font-semibold text-ink">
          隐私与运营访问
        </h2>
        <ul className="list-disc space-y-1 rounded border border-line bg-paper p-4 pl-8 text-sm text-ink-secondary">
          <li>你的来源、意图版本、运行轨迹、评估与文件只有你本人能通过本应用访问。</li>
          <li>本应用没有运营人员账号，也不提供任何读取教师内容的运营入口。</li>
          <li>
            故障排查时，项目运营者仅能通过模型服务（DeepSeek）、对象存储（MinIO）、数据库/缓存（PostgreSQL/Redis）的管理控制台接触底层基础设施，属于纵深防御层，内容不会被复制出工作区边界。
          </li>
          <li>
            删除账号后，系统仅保留一份不含任何内容的极简安全台账（操作类型、时间、工作区标识），用于安全审计；
            提示词、文件名、标题与轨迹绝不会保留。
          </li>
        </ul>
      </section>

      <section aria-labelledby="audit-heading" className="space-y-2">
        <h2 id="audit-heading" className="text-base font-semibold text-ink">
          敏感操作审计
        </h2>
        {!isDesktop ? <DesktopRequiredNotice task="查看敏感操作审计" /> : null}
        {isDesktop ? (
          <>
            <Button variant="secondary" aria-expanded={auditOpen} onClick={() => setAuditOpen((open) => !open)}>
              {auditOpen ? "收起审计记录" : "展开审计记录"}
            </Button>
            {auditQuery.isError ? <Alert tone="error">审计记录读取失败，请重试。</Alert> : null}
            {audit && audit.events.length === 0 ? (
              <p className="text-sm text-ink-secondary">暂无敏感操作记录。</p>
            ) : null}
            {audit && audit.events.length > 0 ? (
              <ul className="space-y-1 rounded border border-line bg-paper p-4 text-sm">
                {audit.events.map((event) => (
                  <li key={`${event.action}-${event.created_at}`} className="flex justify-between gap-4">
                    <span className="text-ink">{event.action}</span>
                    <span className="text-ink-secondary">{new Date(event.created_at).toLocaleString("zh-CN")}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}
      </section>

      <section aria-labelledby="deletion-heading">
        {result ? (
          result.purged ? (
            <Alert tone="info">工作区数据已清除。清除浏览器数据后将获得新的空白工作区。</Alert>
          ) : (
            <Alert tone="warning">
              工作区清除未完成（个别存储暂不可用），可再次点击「删除账号」重试修复。
            </Alert>
          )
        ) : purgeFailed ? (
          <Alert tone="warning">
            上次删除尝试未完全清除工作区数据；可再次点击「删除账号」重试修复。
          </Alert>
        ) : null}

        {isDesktop ? (
          <div className="mt-6 rounded border border-severe/40 bg-severe/5 p-4">
            <h2 id="deletion-heading" className="text-base font-semibold text-severe">
              删除账号
            </h2>
            <p className="mt-1 text-sm text-ink-secondary">
              将清除本浏览器工作区全部数据（来源、简报、运行与轨迹，含检查点与对象存储）。若个别存储暂不可用，删除会显示未完成并可重试修复。该操作无法撤销。
            </p>
            <Button variant="destructive" className="mt-3" onClick={() => setConfirmOpen(true)}>
              删除账号
            </Button>
          </div>
        ) : (
          <DesktopRequiredNotice task="删除账号" />
        )}
      </section>

      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="删除账号"
        description="将清除本浏览器工作区全部数据，无法撤销。"
        confirmLabel="确认删除"
        destructive
        busy={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </main>
  );
}
