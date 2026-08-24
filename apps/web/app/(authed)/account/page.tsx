"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, ConfirmModal } from "@/components/ui";
import { apiFetch } from "@/lib/api";

interface DeletionEvent {
  status: string;
  detail: string | null;
  created_at: string;
}

export default function AccountPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const isDesktop = useDesktop();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [result, setResult] = useState<{ purged: boolean; clerk_deleted: boolean } | null>(null);

  const statusQuery = useQuery({
    queryKey: ["account-deletion-status"],
    queryFn: async () => apiFetch<DeletionEvent[]>("/account/deletion-status", { token: await getToken() }),
  });

  const deleteMutation = useMutation({
    mutationFn: async () =>
      apiFetch<{ purged: boolean; clerk_deleted: boolean }>("/account", {
        method: "DELETE",
        token: await getToken(),
      }),
    onSuccess: (body) => {
      setResult(body);
      setConfirmOpen(false);
    },
  });

  const events = statusQuery.data ?? [];
  const clerkFailed = events.some((event) => event.status === "clerk_failed");

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-8">
      <h1 className="text-2xl font-semibold text-ink">账号与数据</h1>
      <p className="mt-2 text-sm text-ink-secondary">
        登录身份：{user?.emailAddresses[0]?.emailAddress ?? "未知"}。你的上传、生成内容与完整运行记录仅属于你的工作区。
      </p>

      {!isDesktop ? <DesktopRequiredNotice task="删除账号" /> : null}

      {result && !result.clerk_deleted ? (
        <Alert tone="warning">工作区数据已清除，但 Clerk 账号删除失败，请稍后重试或联系运营。</Alert>
      ) : null}
      {clerkFailed && !result ? (
        <Alert tone="warning">上次账号删除中 Clerk 侧失败，数据已清除；如需彻底删除请重试。</Alert>
      ) : null}

      {isDesktop ? (
        <div className="mt-6 rounded border border-severe/40 bg-severe/5 p-4">
          <h2 className="text-base font-semibold text-severe">删除账号</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            将先清除工作区全部数据（来源、简报、运行与轨迹），再删除 Clerk 账号。该操作无法撤销。
          </p>
          <Button variant="destructive" className="mt-3" onClick={() => setConfirmOpen(true)}>
            删除账号
          </Button>
        </div>
      ) : null}

      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="删除账号"
        description="将清除工作区全部数据并删除账号，无法撤销。"
        confirmLabel="确认删除"
        destructive
        busy={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </main>
  );
}
