"use client";

import { useQuery } from "@tanstack/react-query";
import { getApiToken } from "@/lib/auth";
import WorkspaceView from "@/app/(authed)/projects/[projectId]/workspace-view";
import { Alert, Button, EmptyState, SkeletonRows } from "@/components/ui";
import { ApiClientError, getSampleProject } from "@/lib/api";

function formatError(error: unknown): { message: string; correlationId: string | null } {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      AUTH_REQUIRED: "登录状态已失效，请重新登录。",
      PROVIDER_TRANSIENT: "服务暂时不可用，请稍后重试。",
    };
    return {
      message: messages[error.code] ?? `操作失败（${error.code}）。`,
      correlationId: error.correlationId,
    };
  }
  return { message: "网络不可用，请检查连接后重试。", correlationId: null };
}

export default function SampleView() {

  const sampleQuery = useQuery({
    queryKey: ["sample"],
    queryFn: async () => getSampleProject(await getApiToken()),
    retry: false,
  });

  if (sampleQuery.isLoading) {
    return (
      <section aria-label="示例项目">
        <h1 className="text-2xl font-semibold text-ink">示例项目</h1>
        <div className="mt-6">
          <SkeletonRows />
        </div>
      </section>
    );
  }

  if (sampleQuery.isError) {
    const error = sampleQuery.error;
    const notFound = error instanceof ApiClientError && error.code === "NOT_FOUND";
    const { message, correlationId } = formatError(error);
    return (
      <section aria-label="示例项目">
        <h1 className="text-2xl font-semibold text-ink">示例项目</h1>
        <div className="mt-6">
          {notFound ? (
            <div>
              <EmptyState
                title="示例项目暂不可用"
                hint="请稍后重试，或联系部署者重新种入示例。"
              />
              <div className="mt-3">
                <Button variant="secondary" onClick={() => sampleQuery.refetch()}>
                  重试
                </Button>
              </div>
            </div>
          ) : (
            <Alert tone="error">
              {message}
              {correlationId ? (
                <span className="mt-1 block text-xs">参考编号：{correlationId}</span>
              ) : null}
              <Button variant="secondary" className="mt-3" onClick={() => sampleQuery.refetch()}>
                重试
              </Button>
            </Alert>
          )}
        </div>
      </section>
    );
  }

  const sample = sampleQuery.data;
  if (!sample) {
    return null;
  }

  return (
    <section aria-label="示例项目">
      <h1 className="text-2xl font-semibold text-ink">示例项目</h1>
      <div className="mt-4">
        <Alert tone="info">示例项目为只读演示，不会影响任何任务状态。</Alert>
      </div>
      <div className="mt-6">
        <WorkspaceView projectId={sample.project_id} readOnly />
      </div>
    </section>
  );
}
