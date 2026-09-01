import TechnicalEvaluationReportView from "./technical-evaluation-report-view";

export default async function TechnicalEvaluationReportPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <TechnicalEvaluationReportView projectId={projectId} />;
}
