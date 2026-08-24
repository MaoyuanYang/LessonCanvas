"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { DesktopRequiredNotice, useDesktop } from "@/components/desktop-gate";
import {
  Alert,
  Button,
  ConfirmModal,
  EmptyState,
  Modal,
  SkeletonRows,
  StatusBadge,
} from "@/components/ui";
import {
  ApiClientError,
  createProject,
  deleteProject,
  listProjects,
  type Project,
} from "@/lib/api";

const PROJECTS_KEY = ["projects"];

function formatError(error: unknown): { message: string; correlationId: string | null } {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      AUTH_REQUIRED: "登录状态已失效，请重新登录。",
      NOT_FOUND: "所请求的项目不存在或不可访问。",
      REQUIREMENT: "输入不符合要求，请检查后重试。",
      QUOTA_EXCEEDED: "已达到项目数量上限，请删除不再使用的项目后重试。",
      PROVIDER_TRANSIENT: "服务暂时不可用，请稍后重试。",
    };
    return {
      message: messages[error.code] ?? `操作失败（${error.code}）。`,
      correlationId: error.correlationId,
    };
  }
  return { message: "网络不可用，请检查连接后重试。", correlationId: null };
}

function ProjectCard({
  project,
  onDelete,
  canManage,
}: {
  project: Project;
  onDelete: (project: Project) => void;
  canManage: boolean;
}) {
  return (
    <li className="flex items-center justify-between gap-4 rounded border border-line bg-paper p-4">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${project.id}`}
            className="truncate font-medium text-ink hover:text-accent focus-visible:outline-2 focus-visible:outline-focus"
          >
            {project.name}
          </Link>
          <StatusBadge status={project.status} />
        </div>
        <p className="mt-1 text-xs text-ink-secondary">
          最近活动：{new Date(project.updated_at).toLocaleString("zh-CN")}
        </p>
      </div>
      {canManage ? (
        <Button variant="secondary" onClick={() => onDelete(project)}>
          删除
        </Button>
      ) : null}
    </li>
  );
}

export default function ProjectsView() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();

  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);

  const projectsQuery = useQuery({
    queryKey: PROJECTS_KEY,
    queryFn: async () => listProjects(await getToken()),
  });

  const createMutation = useMutation({
    mutationFn: async (input: { name: string; unit_hints?: string | null }) =>
      createProject(await getToken(), input),
    onSuccess: () => {
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (projectId: string) => deleteProject(await getToken(), projectId),
    onSuccess: () => {
      setDeleteTarget(null);
      void queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
    },
  });

  const projects = projectsQuery.data;

  return (
    <section aria-label="项目列表">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">备课项目</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            每个项目对应一个单元的备课工作，内容与记录仅你可见。
          </p>
        </div>
        {isDesktop ? <Button onClick={() => setCreateOpen(true)}>新建备课项目</Button> : null}
      </div>

      {!isDesktop ? <DesktopRequiredNotice task="新建或删除项目" /> : null}

      {projectsQuery.isLoading ? <SkeletonRows /> : null}

      {projectsQuery.isError ? (
        <Alert tone="error">
          {formatError(projectsQuery.error).message}
          {formatError(projectsQuery.error).correlationId ? (
            <span className="mt-1 block text-xs">
              参考编号：{formatError(projectsQuery.error).correlationId}
            </span>
          ) : null}
          <Button variant="secondary" className="mt-3" onClick={() => projectsQuery.refetch()}>
            重试
          </Button>
        </Alert>
      ) : null}

      {projects && projects.length === 0 ? (
        <EmptyState
          title="还没有备课项目"
          hint="创建第一个项目，添加你的单元材料，Agent 将帮助你梳理教学需求。"
        />
      ) : null}

      {projects && projects.length > 0 ? (
        <ul className="space-y-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={setDeleteTarget}
              canManage={isDesktop}
            />
          ))}
        </ul>
      ) : null}

      <Modal
        open={createOpen}
        onOpenChange={(open) => {
          setCreateOpen(open);
          if (!open) createMutation.reset();
        }}
        title="新建备课项目"
        description="为这个单元的备课工作命名，稍后可以补充单元线索。"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const name = String(data.get("name") ?? "").trim();
            const hints = String(data.get("unit_hints") ?? "").trim();
            createMutation.mutate({ name, unit_hints: hints || null });
          }}
        >
          <label className="block text-sm font-medium text-ink" htmlFor="project-name">
            项目名称（必填，最多 60 字）
          </label>
          <input
            id="project-name"
            name="name"
            required
            maxLength={60}
            placeholder="例如：外研社必修一 Unit 3"
            className="mt-1 w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
          />
          <label className="mt-4 block text-sm font-medium text-ink" htmlFor="project-hints">
            单元线索（可选）
          </label>
          <textarea
            id="project-hints"
            name="unit_hints"
            maxLength={200}
            rows={2}
            placeholder="教材、单元主题、课时安排等"
            className="mt-1 w-full rounded border border-line bg-paper px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-focus"
          />
          {createMutation.isError ? (
            <div className="mt-3">
              <Alert tone="error">{formatError(createMutation.error).message}</Alert>
            </div>
          ) : null}
          <div className="mt-5 flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>
              取消
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "创建中…" : "创建项目"}
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null);
            deleteMutation.reset();
          }
        }}
        title="删除备课项目"
        description={`将删除「${deleteTarget?.name ?? ""}」及其全部材料、记录与轨迹。该操作无法撤销。`}
        confirmLabel="确认删除"
        destructive
        busy={deleteMutation.isPending}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
        }}
      />
      {deleteMutation.isError ? (
        <div className="mt-3">
          <Alert tone="error">{formatError(deleteMutation.error).message}</Alert>
        </div>
      ) : null}
    </section>
  );
}
