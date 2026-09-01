"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";

import {
  EVALUATION_CRITERION_LABELS,
  EVALUATION_MODE_LABELS,
  EVALUATION_OUTCOME_LABELS,
  EVALUATION_STATUS_LABELS,
  EVALUATION_UNIT_LABELS,
  technicalEvaluationReport,
  type TechnicalEvaluationPass,
  type TechnicalEvaluationReport,
} from "@/lib/api";

function outcomeText(outcome: string | null): string {
  return outcome ? (EVALUATION_OUTCOME_LABELS[outcome] ?? outcome) : "—";
}

function criterionText(key: string): string {
  return EVALUATION_CRITERION_LABELS[key] ?? key;
}

function PassSection({ pass }: { pass: TechnicalEvaluationPass }) {
  const blocking = pass.criteria.filter((item) => item.classification === "blocking");
  const diagnostics = pass.criteria.filter((item) => item.classification === "diagnostic");
  return (
    <section
      aria-label={`${EVALUATION_UNIT_LABELS[pass.unit_key] ?? pass.unit_key} 第 ${pass.pass_index} 遍`}
      className="mt-6"
    >
      <h2 className="text-base font-medium">
        {EVALUATION_UNIT_LABELS[pass.unit_key] ?? pass.unit_key} · 第 {pass.pass_index} 遍 ·{" "}
        {EVALUATION_MODE_LABELS[pass.mode] ?? pass.mode}
      </h2>
      <p className="mt-1 text-sm text-ink-secondary print:text-black">
        {pass.scenario === "full_pipeline"
          ? "完整管线"
          : pass.scenario.startsWith("fault:")
            ? `故障注入（${pass.scenario.slice(6)}）`
            : pass.scenario}
        {" · "}
        {EVALUATION_STATUS_LABELS[pass.status] ?? pass.status}
        {" · 总体判定："}
        {outcomeText(pass.overall_outcome)}
        {pass.superseded_configuration ? " · 配置已过时" : ""}
      </p>
      <p className="mt-1 text-xs text-ink-secondary print:text-black">
        数据集 {pass.dataset_revision} · 简报 {pass.brief_version_id ?? "—"} · 蓝图{" "}
        {pass.blueprint_version_id ?? "—"} · 记忆状态：
        {String(pass.memory_state?.memory_state ?? "—")}
      </p>
      {blocking.length > 0 ? (
        <table className="mt-2 w-full text-sm">
          <caption className="sr-only">阻断判定结果</caption>
          <thead>
            <tr className="border-b border-line text-left print:border-black">
              <th scope="col" className="py-1 pr-3">阻断判据</th>
              <th scope="col" className="py-1">判定</th>
            </tr>
          </thead>
          <tbody>
            {blocking.map((item) => (
              <tr key={item.criterion_key} className="border-b border-line print:border-black">
                <td className="py-1 pr-3">{criterionText(item.criterion_key)}</td>
                <td className="py-1">{outcomeText(item.outcome)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {diagnostics.length > 0 ? (
        <ul className="mt-2 space-y-1 text-sm text-ink-secondary print:text-black">
          {diagnostics.map((item) => (
            <li key={item.criterion_key}>
              诊断（非阻断）· {criterionText(item.criterion_key)}
              {item.measured ? `：${JSON.stringify(item.measured)}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
      {pass.failure_reason ? (
        <p className="mt-2 text-sm text-severe print:text-black">{pass.failure_reason}</p>
      ) : null}
    </section>
  );
}

export default function TechnicalEvaluationReportView({
  projectId,
}: {
  projectId: string;
}) {
  const { getToken } = useAuth();
  const reportQuery = useQuery({
    queryKey: ["technical-evaluation-report", projectId],
    queryFn: async () => technicalEvaluationReport(await getToken(), projectId),
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
          无法加载技术评估报告，请返回工作区重试。
        </p>
      </main>
    );
  }

  const report = reportQuery.data as TechnicalEvaluationReport;
  const comparable = report.comparisons.filter((item) => item.comparison_available);
  const unavailable = report.comparisons.filter((item) => !item.comparison_available);

  return (
    <main className="mx-auto max-w-3xl p-8 print:p-0">
      <h1 className="text-xl font-semibold">技术评估报告</h1>
      <p className="mt-1 text-sm text-ink-secondary print:text-black">
        数据集版本：{report.dataset_revision ?? "—"}
      </p>
      <p className="mt-3 text-sm print:text-black">
        总体结果：
        {report.overall_outcome ? EVALUATION_OUTCOME_LABELS[report.overall_outcome] : "尚无完整判定"}
        {"；"}产品验证状态 = 未评估（技术评估与教师产品验证为两个独立状态）。
      </p>
      <p className="mt-1 text-sm print:text-black">{report.technical_note}</p>
      <p className="mt-3 text-xs text-ink-secondary no-print print:hidden">
        打印提示：报告完整渲染后，可使用浏览器打印（Ctrl/Cmd+P）保存为 PDF。
      </p>

      {report.passes.length === 0 ? (
        <p className="mt-6 text-sm text-ink-secondary print:text-black">
          尚未运行任何技术评估遍次。
        </p>
      ) : (
        report.passes.map((pass) => <PassSection key={pass.evaluation_id} pass={pass} />)
      )}

      {comparable.length > 0 ? (
        <section aria-label="跨遍对比" className="mt-6">
          <h2 className="text-base font-medium">跨遍对比（同单元、同数据集版本、同配置）</h2>
          <ul className="mt-2 space-y-1 text-sm print:text-black">
            {comparable.map((item) => (
              <li key={item.evaluation_id}>
                {EVALUATION_UNIT_LABELS[item.unit_key] ?? item.unit_key} 第 {item.pass_index} 遍
                与第 {item.comparable_pass_indexes.join("、")} 遍并列呈现原始指标；逐遍判定，失败不被聚合掩盖。
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {unavailable.length > 0 ? (
        <section aria-label="对比不可用" className="mt-6">
          <h2 className="text-base font-medium">对比不可用</h2>
          <ul className="mt-2 space-y-1 text-sm text-ink-secondary print:text-black">
            {unavailable.map((item) => (
              <li key={item.evaluation_id}>
                {EVALUATION_UNIT_LABELS[item.unit_key] ?? item.unit_key} 第 {item.pass_index} 遍：
                {item.comparison_unavailable_reason ?? "对比数据不足"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
