"use client";

import { useQuery } from "@tanstack/react-query";
import { getApiToken } from "@/lib/auth";
import { Alert, EmptyState, SkeletonRows } from "@/components/ui";
import { ApiClientError, getCurrentTransition, type ImpactPreview } from "@/lib/api";

const VERDICT_LABELS: Record<string, string> = {
  affected: "受影响",
  retained: "沿用",
  historical: "历史",
};

const FAMILY_LABELS: Record<string, string> = {
  lesson_plan: "教案",
  slide_deck: "课件",
  exercise: "练习",
};

export function ImpactRegion({ impact }: { impact: ImpactPreview }) {
  if (impact.no_delta) {
    return <Alert tone="info">未检测到实质变更；确认不会产生新的再生成范围。</Alert>;
  }
  return (
    <div>
      {impact.uncertain ? (
        <div className="mb-3">
          <Alert tone="warning">
            存在无法精确分类的变更，已保守扩大再生成范围；可缩窄修订意图后重新预览。
          </Alert>
        </div>
      ) : null}
      <p className="text-sm text-ink-secondary">
        预计受影响课时：
        {impact.affected_lessons === null
          ? "全部课时（单元级变更）"
          : `第 ${impact.affected_lessons.join("、")} 课`}
        {" · "}产物族：{impact.affected_families.map((f) => FAMILY_LABELS[f] ?? f).join("、") || "—"}
        {impact.structural.added.length
          ? ` · 新增课时：第 ${impact.structural.added.join("、")} 课`
          : ""}
        {impact.structural.removed.length
          ? ` · 移除课时：第 ${impact.structural.removed.join("、")} 课`
          : ""}
      </p>
      <ul className="mt-2 space-y-1" aria-label="影响原因">
        {impact.reasons.map((reason) => (
          <li key={reason.field} className="text-xs text-ink-secondary">
            {reason.field}：{reason.detail}（范围：{reason.scope}）
          </li>
        ))}
      </ul>
    </div>
  );
}

export function VersionComparePanel({
  projectId,
}: {
  projectId: string;
  readOnly?: boolean;
}) {

  const transitionQuery = useQuery({
    queryKey: ["current-transition", projectId],
    queryFn: async () => getCurrentTransition(await getApiToken(), projectId),
    retry: false,
  });

  if (transitionQuery.isLoading) {
    return (
      <div>
        <h2 className="text-lg font-semibold">版本对比</h2>
        <SkeletonRows />
      </div>
    );
  }

  if (transitionQuery.isError) {
    return (
      <div>
        <h2 className="text-lg font-semibold">版本对比</h2>
        <Alert tone="error">
          {transitionQuery.error instanceof ApiClientError
            ? transitionQuery.error.message
            : "无法加载版本对比"}
        </Alert>
      </div>
    );
  }

  const transition = transitionQuery.data;
  if (!transition || transition.first_version) {
    return (
      <div>
        <h2 className="text-lg font-semibold">版本对比</h2>
        <EmptyState
          title="尚无版本变迁"
          hint="首次确认的简报与蓝图即当前版本；修订并确认新版本后，这里会展示新旧对比与影响范围。"
        />
      </div>
    );
  }

  const verdicts = transition.verdicts ?? [];
  const artifacts = transition.artifacts ?? [];

  return (
    <div>
      <h2 className="text-lg font-semibold">版本对比</h2>
      <p className="mb-4 mt-1 text-sm text-ink-secondary">
        简报 v{transition.from?.brief_version} · 蓝图 v{transition.from?.blueprint_version}
        {" → "}
        简报 v{transition.to?.brief_version} · 蓝图 v{transition.to?.blueprint_version}。本视图只读，不会改变任何任务状态。
      </p>

      <section aria-label="意图差异" className="mb-6">
        <h3 className="mb-2 text-base font-medium">意图差异</h3>
        {transition.intent_diff.length === 0 ? (
          <p className="text-sm text-ink-secondary">简报字段无变更。</p>
        ) : (
          <ul className="space-y-1">
            {transition.intent_diff.map((entry) => (
              <li key={entry.field} className="text-sm">
                <span className="font-medium">{entry.field}</span>
                <span className="ml-2 text-ink-secondary">
                  {String(entry.old ?? "—")} → {String(entry.new ?? "—")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {"impact" in transition && transition.impact ? (
        <section aria-label="再生成范围" className="mb-6">
          <h3 className="mb-2 text-base font-medium">本次修订的再生成范围</h3>
          <ImpactRegion impact={transition.impact as ImpactPreview} />
        </section>
      ) : null}

      <section aria-label="课时判定与新旧状态">
        <h3 className="mb-2 text-base font-medium">课时判定与新旧状态</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-ink-secondary">
                <th scope="col" className="py-2 pr-4">课程</th>
                <th scope="col" className="py-2 pr-4">产物族</th>
                <th scope="col" className="py-2 pr-4">判定</th>
                <th scope="col" className="py-2 pr-4">触发变更</th>
                <th scope="col" className="py-2 pr-4">旧版本</th>
                <th scope="col" className="py-2">新版本</th>
              </tr>
            </thead>
            <tbody>
              {artifacts.map((row) => {
                const verdict = verdicts.find(
                  (v) => v.lesson_index === row.lesson_index && v.family === row.family,
                );
                return (
                  <tr key={`${row.lesson_index}-${row.family}`} className="border-b border-line">
                    <td className="py-2 pr-4">第 {row.lesson_index} 课</td>
                    <td className="py-2 pr-4">{FAMILY_LABELS[row.family] ?? row.family}</td>
                    <td className="py-2 pr-4">
                      {verdict ? VERDICT_LABELS[verdict.verdict] ?? verdict.verdict : "—"}
                    </td>
                    <td className="py-2 pr-4 text-xs text-ink-secondary">
                      {verdict?.reason ?? "—"}
                    </td>
                    <td className="py-2 pr-4">{row.old.status ?? "—"}</td>
                    <td className="py-2">{row.new.status ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
