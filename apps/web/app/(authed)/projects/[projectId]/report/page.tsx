import PrintReportView from "./print-report-view";

export default async function AlignmentReportPage({
  params,
  searchParams,
}: {
  params: Promise<{ projectId: string }>;
  searchParams: Promise<{ source?: string; exportId?: string }>;
}) {
  const { projectId } = await params;
  const { source = "current", exportId } = await searchParams;
  return <PrintReportView projectId={projectId} source={source} exportId={exportId} />;
}
