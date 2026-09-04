"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { CitationChipGroup } from "@/components/citation-chip";
import { Alert } from "@/components/ui";
import type { BlueprintCitation } from "@/lib/api";

// Shared run/artifact progress surfaces promoted from F003 feature-local code
// (F004 D-DECKDS): the per-lesson artifact progress list and the run outcome
// banners. Both generation panels consume them with identical semantics.

export const RUN_STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  generating: "生成中",
  validating: "校验中",
  complete: "已完成",
  partial_failure: "部分失败",
  capped_failure: "已达调用上限",
  superseded: "已被新版本取代",
  terminal_failure: "失败",
};

export const ARTIFACT_STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  designing: "设计中",
  drafting: "起草中",
  reviewing: "评审中",
  rendering: "渲染中",
  validating: "校验中",
  complete: "已完成",
  failed: "失败",
};

export const TERMINAL_RUN_STATUSES = new Set([
  "complete",
  "partial_failure",
  "capped_failure",
  "superseded",
  "terminal_failure",
]);

export interface ReviewFindingRow {
  dimension: string;
  severity: string;
  message: string;
  reference: string | null;
}

export interface DesignRow {
  objective_ids: string[];
  activities: { name: string; type: string | null; description: string; timing_minutes: number }[];
  assessment_approach: string | null;
  evidence_references: { chunk_position: number }[];
}

export const REVIEW_DIMENSION_LABELS: Record<string, string> = {
  objective_coverage: "目标覆盖",
  plan_coverage: "教案对应",
  grounding: "依据支撑",
  consistency: "内在一致性",
};

export const REVIEW_OUTCOME_LABELS: Record<string, string> = {
  passed: "评审通过",
  passed_after_revise: "修订后评审通过",
  failed_after_revise: "修订后仍未通过",
  unparseable: "评审输出不可解析",
};

export interface ArtifactRow {
  id: string;
  lesson_index: number;
  status: string;
  failure_reason: string | null;
  download_url?: string | null;
  // F014 U1/U2: server-injected chunk citations and the honest per-lesson
  // grounding state ("retrieved" | "none"); absent on pre-F014 artifacts.
  citations?: BlueprintCitation[] | null;
  grounding_state?: string | null;
  // F016 U2/U3: the specialist stages' visible state (read-only, D4).
  design?: DesignRow | null;
  review_findings?: ReviewFindingRow[];
  review_rounds?: number;
  review_outcome?: string | null;
}

export function ReconnectBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <Alert tone="warning">
      连接已断开，正在重连……后台生成不会中断，重连后会补齐进度。
    </Alert>
  );
}

export function NarrationRegion({ lines }: { lines: string[] }) {
  if (lines.length === 0) return null;
  return (
    <section
      aria-label="生成叙述"
      className="mb-4 max-h-40 overflow-y-auto rounded border border-line bg-paper p-3 text-sm"
    >
      <ul className="space-y-1">
        {lines.map((line, index) => (
          <li
            key={`${index}-${line}`}
            className={index === lines.length - 1 ? "" : "text-ink-secondary"}
          >
            {line}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function RunOutcomeBanners({
  status,
  totalCount,
  modelCallCap,
  failedLessonIndexes,
  noun,
  error,
  viewAlignment,
}: {
  status: string;
  totalCount: number;
  modelCallCap: number;
  failedLessonIndexes: number[];
  noun: string;
  error?: string | null;
  viewAlignment?: () => void;
}) {
  return (
    <>
      {status === "complete" ? (
        <Alert tone="info">
          全部 {totalCount} 课{noun}已生成并通过结构校验，可逐课下载。
          {viewAlignment ? (
            <>
              {" "}
              <button
                type="button"
                className="underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-focus"
                onClick={viewAlignment}
              >
                查看对齐情况
              </button>
            </>
          ) : null}
        </Alert>
      ) : null}
      {status === "superseded" ? (
        <Alert tone="warning">
          本任务已被更新的已确认版本取代，历史结果保留；请基于新版本重新开始生成。
        </Alert>
      ) : null}
      {status === "capped_failure" ? (
        <Alert tone="warning">
          已达本任务模型调用上限（{modelCallCap} 次）。已完成{noun}仍可下载；可恢复剩余课程，或修订确认意图后重新生成。
        </Alert>
      ) : null}
      {status === "partial_failure" ? (
        <Alert tone="error">
          部分课程失败：{failedLessonIndexes.map((index) => `第 ${index} 课`).join("、")}。已完成{noun}保持可用。
        </Alert>
      ) : null}
      {status === "terminal_failure" ? (
        <Alert tone="error">生成失败且不可自动恢复。已完成{noun}保持可用。</Alert>
      ) : null}
      {error ? <Alert tone="error">{error}</Alert> : null}
    </>
  );
}

export interface RetainedRow {
  id: string;
  lesson_index: number;
  source_brief_version: number | null;
  source_blueprint_version: number | null;
  source_run_id: string;
}

// F007 retained variant (ux-ui.md D-RETAINDS): unaffected lessons under a
// version transition stay owned by their prior run; the row shows provenance
// and a download slot, never a resume action.
export function RetainedArtifactRow({
  retained,
  noun,
  renderActions,
}: {
  retained: RetainedRow;
  noun: string;
  renderActions?: (retained: RetainedRow) => ReactNode;
}) {
  return (
    <li className="flex items-center justify-between gap-4 rounded border border-line bg-surface-alt/60 p-3">
      <div>
        <span className="font-medium">第 {retained.lesson_index} 课</span>
        <span className="ml-3 text-sm text-evidence">沿用</span>
        <span className="ml-2 text-xs text-ink-secondary">
          源版本：简报 v{retained.source_brief_version} · 蓝图 v{retained.source_blueprint_version}（{noun}未受本次修订影响）
        </span>
      </div>
      <div className="flex items-center gap-2">{renderActions?.(retained)}</div>
    </li>
  );
}

export function ArtifactProgressList({
  completeCount,
  totalCount,
  artifacts,
  renderActions,
}: {
  completeCount: number;
  totalCount: number;
  artifacts: ArtifactRow[];
  renderActions?: (artifact: ArtifactRow) => ReactNode;
}) {
  return (
    <section aria-label="课程进度" className="mb-4">
      <h3 className="mb-2 text-base font-medium">
        课程进度（{completeCount}/{totalCount}）
      </h3>
      <ul className="space-y-2">
        {artifacts.map((artifact) => (
          <li
            key={artifact.id}
            className="flex items-center justify-between gap-4 rounded border border-line bg-paper p-3"
          >
            <div>
              <span className="font-medium">第 {artifact.lesson_index} 课</span>
              <span className="ml-3 text-sm text-ink-secondary">
                {ARTIFACT_STATUS_LABELS[artifact.status] ?? artifact.status}
              </span>
              {artifact.failure_reason ? (
                <p className="mt-1 text-xs text-ink-secondary">原因：{artifact.failure_reason}</p>
              ) : null}
              {artifact.status === "complete" && artifact.grounding_state === "none" ? (
                <p className="mt-1 text-xs text-ink-secondary">无强相关来源语料</p>
              ) : null}
              {artifact.status === "complete" ? (
                <span className="mt-1 flex flex-wrap items-center">
                  <CitationChipGroup citations={artifact.citations} />
                </span>
              ) : null}
              <ArtifactStageDetail artifact={artifact} />
            </div>
            <div className="flex items-center gap-2">{renderActions?.(artifact)}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function RetainedList({
  retained,
  noun,
  renderActions,
}: {
  retained: RetainedRow[];
  noun: string;
  renderActions?: (retained: RetainedRow) => ReactNode;
}) {
  if (retained.length === 0) return null;
  return (
    <section aria-label="沿用课程" className="mb-4">
      <h3 className="mb-2 text-base font-medium">沿用课程（{retained.length}）</h3>
      <ul className="space-y-2">
        {retained.map((item) => (
          <RetainedArtifactRow key={item.id} retained={item} noun={noun} renderActions={renderActions} />
        ))}
      </ul>
    </section>
  );
}


// F016 U3 (ux-ui.md): read-only review-findings and design regions. Both are
// progressive-disclosure expanders on the artifact row; no edit affordances
// exist by contract (Spec D4 — evidence-visible only).
export function ArtifactStageDetail({
  artifact,
}: {
  artifact: ArtifactRow;
}) {
  const [expanded, setExpanded] = useState(false);
  const findings = artifact.review_findings ?? [];
  const design = artifact.design ?? null;
  const hasDetail =
    findings.length > 0 ||
    (artifact.review_rounds ?? 0) > 0 ||
    (artifact.review_outcome ?? null) !== null ||
    design !== null;
  if (!hasDetail) return null;
  return (
    <div className="mt-2">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        className="text-xs text-evidence focus-visible:outline-2 focus-visible:outline-focus"
      >
        {design ? "查看活动设计与评审发现" : "查看评审发现"}
      </button>
      {expanded ? (
        <div className="mt-2 space-y-2 text-xs text-ink">
          {design ? (
            <div className="rounded border border-line bg-surface-alt/60 p-2">
              <p className="font-medium">
                活动设计（运行中间产物，仅查看）
              </p>
              <p className="mt-1 text-ink-secondary">
                绑定目标：{design.objective_ids.join("、") || "（无）"}
              </p>
              <ol className="mt-1 list-decimal space-y-1 pl-4">
                {design.activities.map((activity, index) => (
                  <li key={index}>
                    {activity.name}（{activity.timing_minutes} 分钟）：{activity.description}
                  </li>
                ))}
              </ol>
              {design.assessment_approach ? (
                <p className="mt-1 text-ink-secondary">评价：{design.assessment_approach}</p>
              ) : null}
              {design.evidence_references.length > 0 ? (
                <p className="mt-1 text-ink-secondary">
                  依据切块：第 {design.evidence_references.map((r) => r.chunk_position).join("、")} 段
                </p>
              ) : null}
            </div>
          ) : null}
          <div className="rounded border border-line bg-surface-alt/60 p-2">
            <p className="font-medium">
              评审发现
              {artifact.review_rounds
                ? `（${artifact.review_rounds === 2 ? "修订后第 2 轮" : "第 1 轮"}）`
                : ""}
              {artifact.review_outcome
                ? ` · ${REVIEW_OUTCOME_LABELS[artifact.review_outcome] ?? artifact.review_outcome}`
                : ""}
            </p>
            {findings.length === 0 ? (
              <p className="mt-1 text-ink-secondary">评审通过，无严重或轻微发现。</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {findings.map((finding, index) => (
                  <li key={index} className="flex flex-wrap items-center gap-2">
                    <span
                      className={
                        finding.severity === "severe"
                          ? "rounded bg-danger/10 px-1.5 py-0.5 font-medium text-danger"
                          : "rounded bg-evidence/10 px-1.5 py-0.5 text-evidence"
                      }
                    >
                      {finding.severity === "severe" ? "严重" : "轻微"}
                    </span>
                    <span className="text-ink-secondary">
                      {REVIEW_DIMENSION_LABELS[finding.dimension] ?? finding.dimension}
                    </span>
                    <span>{finding.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
