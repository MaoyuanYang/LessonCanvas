import WorkspaceView from "./workspace-view";

export default async function ProjectWorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <WorkspaceView projectId={projectId} />;
}
