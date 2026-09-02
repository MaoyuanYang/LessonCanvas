"use client";

import { useQuery } from "@tanstack/react-query";
import { getApiToken } from "@/lib/auth";
import {
  getAlignmentReport,
  getExportReport,
  PRODUCT_VALIDATION_STATUS_LABELS,
  type AlignmentView,
} from "@/lib/api";

const FAMILY_LABELS: Record<string, string> = {
  lesson_plan: "教案",
  slide_deck: "课件",
  exercise: "练习与答案",
};

const MEMBER_STATE_LABELS: Record<string, string> = {
  complete: "已覆盖",
  failed: "校验未通过",
  in_progress: "生成中",
  missing: "缺失",
};

export default function PrintReportView({
  projectId,
  source,
  exportId,
}: {
  projectId: string;
  source: string;
  exportId?: string;
}) {
  const isSnapshot = source === "export" && exportId;

  const reportQuery = useQuery({
    queryKey: ["alignment-report", projectId, source, exportId],
    queryFn: async () =>
      isSnapshot
        ? getExportReport(await getApiToken(), projectId, exportId as string)
        : getAlignmentReport(await getApiToken(), projectId),
    retry: false,
  });

  if (reportQuery.isLoading) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p className="text-sm text-ink-secondary">报告加载中…</p>
      </main>
    );
  }
  if (reportQuery.isError) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p role="alert" className="text-sm text-severe">
          无法加载对齐报告，请返回工作区重试。
        </p>
      </main>
    );
  }

  const report = reportQuery.data as AlignmentView;
  const validated = report.technical_status === "validated";
  const severe = report.findings.filter((f) => f.severity === "severe" && !f.resolved);

  return (
    <main className="mx-auto max-w-3xl p-8 print:p-0">
      <h1 className="text-xl font-semibold">单元对齐报告</h1>
      <p className="mt-1 text-sm text-ink-secondary print:text-black">
        绑定版本：简报 v{report.brief_version} · 蓝图 v{report.blueprint_version}
        {isSnapshot ? ` · 导出快照（${exportId?.slice(0, 8)}）` : ""}
        {report.generated_at ? ` · 生成于 ${report.generated_at}` : ""}
      </p>
      <p className="mt-3 text-sm print:text-black">
        状态：技术校验状态 = {validated ? "技术校验通过" : "未完成"}
        {"；"}产品验证状态 ={" "}
        {PRODUCT_VALIDATION_STATUS_LABELS[report.product_validation_status] ??
          report.product_validation_status}
        （两者独立呈现，技术校验不代表课堂可用性）。
      </p>

      <section aria-label="目标覆盖汇总" className="mt-6">
        <h2 className="text-base font-medium">目标覆盖汇总</h2>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left print:border-black">
              <th scope="col" className="py-1 pr-3">教学目标</th>
              <th scope="col" className="py-1 pr-3">教案</th>
              <th scope="col" className="py-1 pr-3">课件</th>
              <th scope="col" className="py-1 pr-3">练习与答案</th>
              <th scope="col" className="py-1">课时</th>
            </tr>
          </thead>
          <tbody>
            {report.objectives.map((objective) => (
              <tr key={objective.id} className="border-b border-line print:border-black">
                <td className="py-1 pr-3">{objective.text ?? objective.id}</td>
                <td className="py-1 pr-3">{objective.support.lesson_plan ? "已覆盖" : "缺失"}</td>
                <td className="py-1 pr-3">{objective.support.slide_deck ? "已覆盖" : "缺失"}</td>
                <td className="py-1 pr-3">{objective.support.exercise ? "已覆盖" : "缺失"}</td>
                <td className="py-1">第 {objective.lessons.join("、") || "—"} 课</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-label="课时完成度" className="mt-6">
        <h2 className="text-base font-medium">课时完成度</h2>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left print:border-black">
              <th scope="col" className="py-1 pr-3">课时</th>
              <th scope="col" className="py-1 pr-3">教案</th>
              <th scope="col" className="py-1 pr-3">课件</th>
              <th scope="col" className="py-1">练习与答案</th>
            </tr>
          </thead>
          <tbody>
            {report.lessons.map((lesson) => (
              <tr key={lesson.lesson_index} className="border-b border-line print:border-black">
                <td className="py-1 pr-3">
                  第 {lesson.lesson_index} 课{lesson.title ? `（${lesson.title}）` : ""}
                </td>
                {(["lesson_plan", "slide_deck", "exercise"] as const).map((family) => (
                  <td key={family} className="py-1 pr-3">
                    {MEMBER_STATE_LABELS[lesson.members[family]?.state ?? "missing"]}
                    {lesson.members[family]?.provenance === "retained" ? "（沿用）" : ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section aria-label="发现与覆盖" className="mt-6">
        <h2 className="text-base font-medium">发现与覆盖</h2>
        {report.findings.length === 0 ? (
          <p className="mt-2 text-sm">未发现覆盖缺口或冲突。</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm">
            {report.findings.map((finding) => (
              <li key={finding.key}>
                [{finding.severity === "severe" ? "严重" : "警告"}] {finding.title}
                {finding.resolved ? "（已按教师覆盖记录处理）" : ""}
              </li>
            ))}
          </ul>
        )}
        {report.overrides.length > 0 ? (
          <div className="mt-3">
            <h3 className="text-sm font-medium">覆盖记录</h3>
            <ul className="mt-1 space-y-1 text-sm">
              {report.overrides.map((override) => (
                <li key={override.id}>
                  {override.finding_key}：{override.reason}（
                  {override.status === "recorded" ? "已记录" : "已撤销"}）
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <p className="mt-8 text-sm text-ink-secondary print:text-black">
        本报告由结构化数据确定性生成；草稿导出不代表技术或产品验证结论。
      </p>
      <p className="mt-2 no-print text-sm text-ink-secondary">
        报告已完整加载；可使用浏览器打印（快捷键 Ctrl/Cmd+P）保存为 PDF。
      </p>
    </main>
  );
}
