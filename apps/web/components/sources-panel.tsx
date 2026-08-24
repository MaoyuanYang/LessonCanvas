"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import { Alert, Button, StatusBadge } from "@/components/ui";
import { ApiClientError, deleteSource, listSources, uploadSource } from "@/lib/api";

export function SourcesPanel({ projectId }: { projectId: string }) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const fileInput = useRef<HTMLInputElement>(null);
  const [rights, setRights] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ["sources", projectId],
    queryFn: async () => listSources(await getToken(), projectId),
  });

  const uploadMutation = useMutation({
    mutationFn: async ({ file, acknowledged }: { file: File; acknowledged: boolean }) =>
      uploadSource(await getToken(), projectId, file, acknowledged),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["sources", projectId] });
    },
    onError: (err) => {
      setError(err instanceof ApiClientError ? err.message : "上传失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (sourceId: string) => deleteSource(await getToken(), projectId, sourceId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sources", projectId] }),
  });

  const sources = sourcesQuery.data;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-ink">来源材料</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          支持 PDF、DOCX、TXT、MD，单个不超过 20MB，最多 10 个。含学生个人身份信息的材料将被拒绝。
        </p>
      </div>

      {!isDesktop ? <DesktopRequiredNotice task="上传或删除来源" /> : null}

      {isDesktop ? (
        <form
          className="flex flex-wrap items-center gap-3 rounded border border-line bg-surface-alt p-4"
          onSubmit={(event) => {
            event.preventDefault();
            const file = fileInput.current?.files?.[0];
            if (!file) {
              setError("请选择文件");
              return;
            }
            if (!rights) {
              setError("请先确认材料使用授权");
              return;
            }
            uploadMutation.mutate({ file, acknowledged: rights });
          }}
        >
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            aria-label="选择来源文件"
            className="text-sm text-ink-secondary"
          />
          <label className="flex items-center gap-2 text-sm text-ink-secondary">
            <input
              type="checkbox"
              checked={rights}
              onChange={(event) => setRights(event.target.checked)}
            />
            我确认有权使用该材料用于备课
          </label>
          <Button type="submit" disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? "上传中…" : "上传"}
          </Button>
        </form>
      ) : null}

      {error ? <Alert tone="error">{error}</Alert> : null}

      {sourcesQuery.isLoading ? <p className="text-sm text-ink-secondary">加载中…</p> : null}

      {sources && sources.length === 0 ? (
        <p className="text-sm text-ink-secondary">还没有来源材料。</p>
      ) : null}

      {sources && sources.length > 0 ? (
        <ul className="space-y-2">
          {sources.map((source) => (
            <li
              key={source.id}
              className="flex items-center justify-between gap-4 rounded border border-line bg-paper p-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <span className="truncate text-sm font-medium text-ink">{source.filename}</span>
                  <StatusBadge status={source.status} />
                </div>
                {source.rejection_message ? (
                  <p className="mt-1 text-xs text-severe">{source.rejection_message}</p>
                ) : null}
              </div>
              {isDesktop ? (
                <Button
                  variant="secondary"
                  onClick={() => deleteMutation.mutate(source.id)}
                  disabled={deleteMutation.isPending}
                >
                  删除
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
