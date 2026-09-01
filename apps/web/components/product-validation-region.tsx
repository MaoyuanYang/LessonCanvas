"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { useDesktop } from "@/components/desktop-gate";
import { Alert, Button, EmptyState, Modal, SkeletonRows } from "@/components/ui";
import {
  ApiClientError,
  EVALUATION_UNIT_LABELS,
  PRODUCT_VALIDATION_RULE_LABELS,
  PRODUCT_VALIDATION_STALE_REASON_LABELS,
  PRODUCT_VALIDATION_STATE_LABELS,
  PRODUCT_VALIDATION_STATUS_LABELS,
  RUBRIC_DIMENSION_LABELS,
  SEVERE_FINDING_CLASS_LABELS,
  downloadProductValidationDocument,
  productValidationConclude,
  productValidationCreateAssignment,
  productValidationDetail,
  productValidationImportEvidence,
  productValidationOverview,
  type ProductValidationAssignmentRow,
  type ProductValidationDetail,
  type SevereFindingEntry,
} from "@/lib/api";

const UNIT_KEYS = ["travelling-around", "natural-disasters", "cultural-heritage"] as const;
const DIMENSION_KEYS = [
  "knowledge_correctness",
  "language_quality",
  "exercise_answer_correctness",
  "objective_alignment",
  "teaching_usability",
] as const;
const SEVERE_CLASSES = [
  "knowledge_error",
  "language_error",
  "answer_error",
  "objective_alignment_error",
] as const;

function stateTone(state: string): string {
  if (state === "passed") return "text-success";
  if (state === "failed") return "text-severe";
  if (state === "stale") return "text-stale";
  if (state === "not_complete") return "text-warning";
  return "text-ink-secondary";
}

function overallTone(status: string): string {
  if (status === "passed") return "bg-evidence/10 text-evidence";
  if (status === "failed") return "bg-severe/10 text-severe";
  if (status === "not_complete" || status === "in_progress") return "bg-warning/10 text-warning";
  return "bg-stale/10 text-stale";
}

function findFirstViolationsFocusTarget(violations: string[]): string | null {
  const first = violations[0];
  return first ? first.split(":")[0] : null;
}

/** Inline import form: five dimension scores with notes, a severe-finding
 * repeater, the structural-rework question, attestation, and the required
 * original document. Every server-returned violation is listed at once. */
function ImportForm({
  projectId,
  assignment,
  onDone,
  onCancel,
}: {
  projectId: string;
  assignment: ProductValidationAssignmentRow;
  onDone: (message: string) => void;
  onCancel: () => void;
}) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const violationsRef = useRef<HTMLDivElement>(null);
  const [revision, setRevision] = useState("r1");
  const [scores, setScores] = useState<Record<string, { score: number; note: string }>>(() =>
    Object.fromEntries(DIMENSION_KEYS.map((key) => [key, { score: 4, note: "" }])),
  );
  const [findings, setFindings] = useState<SevereFindingEntry[]>([]);
  const [rework, setRework] = useState(false);
  const [reworkReason, setReworkReason] = useState("");
  const [evaluatorReference, setEvaluatorReference] = useState("外部高中英语教师-01");
  const [completedDate, setCompletedDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [violations, setViolations] = useState<string[] | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (violations && violations.length > 0) violationsRef.current?.focus();
  }, [violations]);

  const importMutation = useMutation({
    mutationFn: async () => {
      const file = fileRef.current?.files?.[0];
      if (!file) {
        throw new ApiClientError("REQUIREMENT", "请上传评审教师填写的原始量表文档。", 422, null, {
          violations: ["document: 原始量表文档为必填"],
        });
      }
      return productValidationImportEvidence(
        await getToken(),
        projectId,
        assignment.id,
        revision,
        {
          scores,
          severe_findings: findings,
          structural_rework_required: rework,
          structural_rework_reason: rework ? reworkReason : null,
          attestation: { evaluator_reference: evaluatorReference, completed_date: completedDate },
        },
        file,
      );
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["product-validation", projectId] });
      onDone(
        result.created
          ? `量表证据已导入，单元判定：${result.outcome === "passed" ? "通过" : "失败"}。`
          : `该量表版本已导入：已定位到现有记录，未重复计算。`,
      );
    },
    onError: (error) => {
      if (error instanceof ApiClientError && error.details?.violations) {
        setViolations(error.details.violations as string[]);
        setFormError(error.message);
      } else {
        setViolations(null);
        setFormError(
          error instanceof ApiClientError ? error.message : "导入失败，请稍后重试。",
        );
      }
    },
  });

  /** Client-side pre-validation mirroring the fixed schema (ux-ui Forms
   * table); the server remains the rubric-schema authority and re-validates. */
  function clientViolations(): string[] {
    const issues: string[] = [];
    for (const key of DIMENSION_KEYS) {
      const entry = scores[key];
      if (!Number.isInteger(entry.score) || entry.score < 1 || entry.score > 5) {
        issues.push(`scores.${key}.score: must be an integer 1-5`);
      }
      if (!entry.note.trim()) {
        issues.push(`scores.${key}.note: required evidence note missing`);
      }
    }
    findings.forEach((finding, index) => {
      if (!String(finding.lesson_reference).trim()) {
        issues.push(`severe_findings[${index}].lesson_reference: required lesson reference missing`);
      }
      if (!finding.evidence.trim()) {
        issues.push(`severe_findings[${index}].evidence: required evidence text missing`);
      }
    });
    if (rework && !reworkReason.trim()) {
      issues.push("structural_rework_reason: required when structural rework is true");
    }
    if (!evaluatorReference.trim()) {
      issues.push("attestation.evaluator_reference: required pseudonymous reference missing");
    }
    if (!completedDate) {
      issues.push("attestation.completed_date: required YYYY-MM-DD date missing");
    }
    return issues;
  }

  return (
    <form
      className="space-y-4 border-t border-line p-3 text-sm"
      onSubmit={(event) => {
        event.preventDefault();
        setViolations(null);
        setFormError(null);
        const issues = clientViolations();
        if (issues.length > 0) {
          setViolations(issues);
          return;
        }
        importMutation.mutate();
      }}
    >
      <div className="flex flex-wrap gap-4">
        <label className="block">
          量表提交版本（修订号）
          <input
            aria-label="量表提交版本（修订号）"
            className="mt-1 w-40 rounded border border-line bg-paper p-2"
            value={revision}
            onChange={(event) => setRevision(event.target.value)}
          />
        </label>
        <label className="block">
          评审者标识（伪匿名）
          <input
            aria-label="评审者标识（伪匿名）"
            className="mt-1 w-56 rounded border border-line bg-paper p-2"
            value={evaluatorReference}
            onChange={(event) => setEvaluatorReference(event.target.value)}
          />
        </label>
        <label className="block">
          完成日期
          <input
            aria-label="完成日期"
            type="date"
            className="mt-1 w-44 rounded border border-line bg-paper p-2"
            value={completedDate}
            onChange={(event) => setCompletedDate(event.target.value)}
          />
        </label>
      </div>

      <fieldset>
        <legend className="mb-1 font-medium">五维评分（1–5 分，均需证据说明）</legend>
        <div className="space-y-2">
          {DIMENSION_KEYS.map((key) => (
            <div key={key} className="flex flex-wrap items-start gap-2">
              <label className="w-44 shrink-0">
                {RUBRIC_DIMENSION_LABELS[key]}
                <select
                  aria-label={`${RUBRIC_DIMENSION_LABELS[key]}评分`}
                  className="mt-1 w-full rounded border border-line bg-paper p-1.5"
                  value={scores[key].score}
                  onChange={(event) =>
                    setScores((prev) => ({
                      ...prev,
                      [key]: { ...prev[key], score: Number(event.target.value) },
                    }))
                  }
                >
                  {[1, 2, 3, 4, 5].map((value) => (
                    <option key={value} value={value}>
                      {value} 分
                    </option>
                  ))}
                </select>
              </label>
              <label className="min-w-56 flex-1">
                证据说明
                <textarea
                  aria-label={`${RUBRIC_DIMENSION_LABELS[key]}证据说明`}
                  className="mt-1 w-full rounded border border-line bg-paper p-1.5"
                  rows={2}
                  value={scores[key].note}
                  onChange={(event) =>
                    setScores((prev) => ({
                      ...prev,
                      [key]: { ...prev[key], note: event.target.value },
                    }))
                  }
                />
              </label>
            </div>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-1 font-medium">严重问题（会误导教学或需结构性返工；无则留空）</legend>
        {findings.map((finding, index) => (
          <div key={index} className="mb-2 flex flex-wrap items-start gap-2">
            <select
              aria-label={`严重问题 ${index + 1} 类别`}
              className="rounded border border-line bg-paper p-1.5"
              value={finding.class}
              onChange={(event) =>
                setFindings((prev) =>
                  prev.map((row, i) => (i === index ? { ...row, class: event.target.value } : row)),
                )
              }
            >
              {SEVERE_CLASSES.map((cls) => (
                <option key={cls} value={cls}>
                  {SEVERE_FINDING_CLASS_LABELS[cls]}
                </option>
              ))}
            </select>
            <input
              aria-label={`严重问题 ${index + 1} 课时`}
              placeholder="课时，如 3"
              className="w-28 rounded border border-line bg-paper p-1.5"
              value={String(finding.lesson_reference)}
              onChange={(event) =>
                setFindings((prev) =>
                  prev.map((row, i) =>
                    i === index ? { ...row, lesson_reference: event.target.value } : row,
                  ),
                )
              }
            />
            <input
              aria-label={`严重问题 ${index + 1} 证据`}
              placeholder="证据说明"
              className="min-w-48 flex-1 rounded border border-line bg-paper p-1.5"
              value={finding.evidence}
              onChange={(event) =>
                setFindings((prev) =>
                  prev.map((row, i) => (i === index ? { ...row, evidence: event.target.value } : row)),
                )
              }
            />
            <Button
              type="button"
              variant="quiet"
              onClick={() => setFindings((prev) => prev.filter((_, i) => i !== index))}
            >
              移除
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="secondary"
          onClick={() =>
            setFindings((prev) => [
              ...prev,
              { class: "knowledge_error", lesson_reference: "", evidence: "" },
            ])
          }
        >
          添加严重问题
        </Button>
      </fieldset>

      <fieldset>
        <legend className="mb-1 font-medium">结构性返工</legend>
        <label className="mr-4 inline-flex items-center gap-1">
          <input
            type="radio"
            name="structural-rework"
            checked={!rework}
            onChange={() => setRework(false)}
          />
          不需要
        </label>
        <label className="inline-flex items-center gap-1">
          <input
            type="radio"
            name="structural-rework"
            checked={rework}
            onChange={() => setRework(true)}
          />
          需要（须说明原因）
        </label>
        {rework ? (
          <textarea
            aria-label="结构性返工原因"
            className="mt-2 w-full rounded border border-line bg-paper p-1.5"
            rows={2}
            value={reworkReason}
            onChange={(event) => setReworkReason(event.target.value)}
          />
        ) : null}
      </fieldset>

      <label className="block">
        评审教师填写的原始量表文档（必填，作为私有证据保留）
        <input
          ref={fileRef}
          aria-label="原始量表文档"
          type="file"
          accept=".pdf,.docx,.xlsx,.txt,.png,.jpg,.jpeg"
          className="mt-1 block w-full text-sm"
        />
      </label>

      {violations && violations.length > 0 ? (
        <div
          role="alert"
          tabIndex={-1}
          ref={violationsRef}
          data-first-field={findFirstViolationsFocusTarget(violations)}
          className="rounded border border-severe/40 bg-severe/5 p-2 text-severe focus-visible:outline-2 focus-visible:outline-focus"
        >
          <p className="font-medium">以下字段未通过量表校验，请逐项修正后重新提交：</p>
          <ul className="mt-1 list-disc pl-5">
            {violations.map((violation) => (
              <li key={violation}>{violation}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {formError && !(violations && violations.length > 0) ? (
        <Alert tone="error">{formError}</Alert>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="quiet" onClick={onCancel}>
          收起
        </Button>
        <Button type="submit" disabled={importMutation.isPending}>
          {importMutation.isPending ? "导入中…" : "导入量表证据"}
        </Button>
      </div>
    </form>
  );
}

function EvidenceHistory({
  projectId,
  detail,
}: {
  projectId: string;
  detail: ProductValidationDetail;
}) {
  const { getToken } = useAuth();
  if (detail.evidence_history.length === 0) {
    return <p className="text-ink-secondary">尚未导入量表证据。</p>;
  }
  return (
    <div>
      <h4 className="mb-1 font-medium">量表证据与判定（采集方式：所有者代录）</h4>
      <ul className="space-y-2">
        {detail.evidence_history.map((row) => (
          <li key={row.id} className="rounded border border-line bg-paper p-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-medium">提交版本 {row.evidence_revision}</span>
              <span className={row.status === "current" ? "text-success" : "text-stale"}>
                {row.status === "current" ? "当前" : "历史版本"}
              </span>
              <span className={stateTone(row.outcome)}>
                判定：{row.outcome === "passed" ? "通过" : "失败"}
              </span>
              <span className="text-ink-secondary">核心均值 {row.outcome_detail.core_mean}</span>
              {row.outcome_detail.violated_rules.length > 0 ? (
                <span className="text-severe">
                  {row.outcome_detail.violated_rules
                    .map((rule) => PRODUCT_VALIDATION_RULE_LABELS[rule] ?? rule)
                    .join("、")}
                </span>
              ) : null}
            </div>
            <ul className="mt-1 space-y-0.5 text-ink-secondary">
              {Object.entries(row.evidence.scores).map(([key, entry]) => (
                <li key={key}>
                  {RUBRIC_DIMENSION_LABELS[key] ?? key}：{entry.score} 分 — {entry.note}
                </li>
              ))}
            </ul>
            {row.evidence.severe_findings.length > 0 ? (
              <ul className="mt-1 space-y-0.5 text-severe">
                {row.evidence.severe_findings.map((finding, index) => (
                  <li key={index}>
                    {SEVERE_FINDING_CLASS_LABELS[finding.class] ?? finding.class}（第{" "}
                    {String(finding.lesson_reference)} 课）：{finding.evidence}
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-ink-secondary">
              <span>
                评审者：{row.evidence.attestation.evaluator_reference} · 完成于{" "}
                {row.evidence.attestation.completed_date}
              </span>
              {row.document.downloadable ? (
                <Button
                  variant="quiet"
                  onClick={async () => {
                    const blob = await downloadProductValidationDocument(
                      await getToken(),
                      projectId,
                      detail.id,
                      row.id,
                    ).catch(() => null);
                    if (!blob) return;
                    const url = URL.createObjectURL(blob);
                    const anchor = document.createElement("a");
                    anchor.href = url;
                    anchor.download = row.document.filename ?? "rubric-evidence";
                    anchor.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  下载原始文档（私有）
                </Button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Printable rubric hand-out rendered from the assignment's fixed sheet data
 * (zh-Hans labels, fixed schema order) so the owner can hand exactly this
 * rubric to the evaluator (ux-ui UIQ-002). */
function RubricSheetBlock({ detail }: { detail: ProductValidationDetail }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded border border-line bg-paper p-2">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className="text-left focus-visible:outline-2 focus-visible:outline-focus"
      >
        评审量表（{detail.rubric_sheet.rubric_revision}，交付给评审教师）{open ? "收起" : "展开"}
      </button>
      {open ? (
        <div className="mt-2 space-y-2">
          <p className="font-medium">{detail.rubric_sheet.title}</p>
          <ol className="list-decimal space-y-1 pl-5">
            {detail.rubric_sheet.dimensions.map((dim) => (
              <li key={dim.key}>
                <span className="font-medium">{dim.label}</span>（1–5 分）：{dim.description}
              </li>
            ))}
          </ol>
          <p className="text-ink-secondary">
            严重问题类别：
            {detail.rubric_sheet.severe_finding_classes
              .map((entry) => entry.label)
              .join("、")}
            ；{detail.rubric_sheet.structural_rework_question}
          </p>
          <p className="text-ink-secondary">
            通过门槛：零严重问题 · 五维均值 ≥ 4.0 · 不需要结构性返工。完成后请签名（伪匿名标识）并注明完成日期。
          </p>
        </div>
      ) : null}
    </div>
  );
}

function AssignmentRow({
  projectId,
  assignment,
  isDesktop,
  onNotice,
}: {
  projectId: string;
  assignment: ProductValidationAssignmentRow;
  isDesktop: boolean;
  onNotice: (message: string) => void;
}) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [concluding, setConcluding] = useState(false);
  const [concludeReason, setConcludeReason] = useState("");

  const detailQuery = useQuery({
    queryKey: ["product-validation-detail", assignment.id],
    queryFn: async () => productValidationDetail(await getToken(), projectId, assignment.id),
    enabled: expanded,
  });

  const concludeMutation = useMutation({
    mutationFn: async () =>
      productValidationConclude(await getToken(), projectId, assignment.id, concludeReason),
    onSuccess: () => {
      setConcluding(false);
      void queryClient.invalidateQueries({ queryKey: ["product-validation", projectId] });
      onNotice("该单元已诚实记录为「未完成」；补充评审后可重新分派。");
    },
    onError: (error) => {
      onNotice(error instanceof ApiClientError ? error.message : "记录未完成失败，请重试。");
    },
  });

  const stale = assignment.state === "stale";

  return (
    <li className="rounded border border-line bg-paper">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 p-3 text-left focus-visible:outline-2 focus-visible:outline-focus"
      >
        <span className="font-medium">
          {EVALUATION_UNIT_LABELS[assignment.unit_key] ?? assignment.unit_key}
        </span>
        <span className={`text-sm font-medium ${stateTone(assignment.state)}`}>
          {PRODUCT_VALIDATION_STATE_LABELS[assignment.state] ?? assignment.state}
        </span>
        <span className="text-sm text-ink-secondary">
          量表 {assignment.rubric_revision} · 数据集 {assignment.dataset_revision}
        </span>
        {assignment.outcome ? (
          <span className={`text-sm ${stateTone(assignment.outcome)}`}>
            判定：{assignment.outcome === "passed" ? "通过" : "失败"}
          </span>
        ) : null}
        {stale && assignment.staleness ? (
          <span className="text-sm text-stale">
            {PRODUCT_VALIDATION_STALE_REASON_LABELS[assignment.staleness.reason] ??
              assignment.staleness.reason}
            （{assignment.staleness.superseded_by}）
          </span>
        ) : null}
      </button>
      {expanded ? (
        <div className="border-t border-line p-3 text-sm">
          {detailQuery.isLoading ? (
            <SkeletonRows count={2} />
          ) : detailQuery.isError ? (
            <Alert tone="error">
              {detailQuery.error instanceof ApiClientError
                ? detailQuery.error.message
                : "无法加载评审详情"}
            </Alert>
          ) : detailQuery.data ? (
            <div className="space-y-3">
              <p className="text-xs text-ink-secondary">
                绑定包：简报版本 {detailQuery.data.package.brief_version} · 蓝图版本{" "}
                {detailQuery.data.package.blueprint_version} ·{" "}
                {detailQuery.data.package.lessons.length} 个课时 × 三类产物
              </p>
              {detailQuery.data.state === "not_complete" &&
              detailQuery.data.not_complete_reason ? (
                <p className="text-warning">未完成原因：{detailQuery.data.not_complete_reason}</p>
              ) : null}
              <RubricSheetBlock detail={detailQuery.data} />
              <EvidenceHistory projectId={projectId} detail={detailQuery.data} />
            </div>
          ) : null}

          {isDesktop && !stale ? (
            <div className="mt-3">
              {importOpen ? (
                <ImportForm
                  projectId={projectId}
                  assignment={assignment}
                  onDone={(message) => {
                    setImportOpen(false);
                    onNotice(message);
                  }}
                  onCancel={() => setImportOpen(false)}
                />
              ) : assignment.state === "pending_evidence" ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="secondary" onClick={() => setImportOpen(true)}>
                    导入量表证据
                  </Button>
                  <Button variant="quiet" onClick={() => setConcluding(true)}>
                    记录为未完成
                  </Button>
                </div>
              ) : (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setImportOpen(true);
                    onNotice("将导入新的量表提交版本；此前版本会保留为历史记录。");
                  }}
                >
                  导入修正后的量表（新版本）
                </Button>
              )}
            </div>
          ) : null}
          {stale ? (
            <p className="mt-2 text-stale">
              该分派绑定的包已被取代；历史结果保留可读，请在新包上重新创建分派后再导入。
            </p>
          ) : null}
        </div>
      ) : null}

      {concluding ? (
        <Modal
          open={concluding}
          onOpenChange={(open) => {
            setConcluding(open);
            if (!open) concludeMutation.reset();
          }}
          title="记录为未完成"
          description="评审教师无法完成该单元时，诚实记录原因；状态不会伪造为通过或失败。"
        >
          <div className="space-y-3">
            <label className="block text-sm">
              原因
              <textarea
                aria-label="未完成原因"
                className="mt-1 w-full rounded border border-line bg-paper p-2"
                rows={2}
                value={concludeReason}
                onChange={(event) => setConcludeReason(event.target.value)}
              />
            </label>
            <div className="flex justify-end gap-2">
              <Button variant="quiet" onClick={() => setConcluding(false)}>
                取消
              </Button>
              <Button
                onClick={() => concludeMutation.mutate()}
                disabled={concludeMutation.isPending || concludeReason.trim().length < 5}
              >
                {concludeMutation.isPending ? "记录中…" : "确认记录"}
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </li>
  );
}

export function ProductValidationRegion({ projectId }: { projectId: string }) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const isDesktop = useDesktop();
  const [modalOpen, setModalOpen] = useState(false);
  const [unitKey, setUnitKey] = useState<string>(UNIT_KEYS[0]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["product-validation", projectId],
    queryFn: async () => productValidationOverview(await getToken(), projectId),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: async () =>
      productValidationCreateAssignment(await getToken(), projectId, unitKey),
    onSuccess: (row) => {
      setModalOpen(false);
      setCreateError(null);
      setNotice(
        row.created === false
          ? "该分派已存在：已定位到现有记录，未重复创建。"
          : `分派已创建（${EVALUATION_UNIT_LABELS[row.unit_key] ?? row.unit_key}）；` +
              "请导出该单元的交付包与量表，交由外部教师评审后导入结果。",
      );
      void queryClient.invalidateQueries({ queryKey: ["product-validation", projectId] });
    },
    onError: (error) => {
      const details = error instanceof ApiClientError ? error.details : null;
      if (details && Array.isArray(details.gaps)) {
        const gapText = (details.gaps as Array<{ lesson_index: number; family: string }>)
          .map((gap) => `第 ${gap.lesson_index} 课 ${gap.family}`)
          .join("、");
        setCreateError(`该单元包尚不完整（缺失：${gapText}）；请先补齐后再分派评审。`);
      } else if (
        error instanceof ApiClientError &&
        error.message.includes("已存在")
      ) {
        setCreateError("该分派已存在：已定位到现有记录。");
      } else {
        setCreateError(error instanceof ApiClientError ? error.message : "创建分派失败，请重试。");
      }
    },
  });

  const overall = overviewQuery.data?.overall_status ?? null;

  return (
    <section
      aria-label="产品验证"
      className="mb-6 rounded border border-line bg-surface-alt/50 p-4"
    >
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <h3 className="font-semibold">产品验证</h3>
        {overall ? (
          <span
            className={`rounded px-2 py-0.5 text-xs font-medium ${overallTone(overall)}`}
            aria-live="polite"
          >
            产品验证状态：{PRODUCT_VALIDATION_STATUS_LABELS[overall] ?? overall}
          </span>
        ) : null}
        <span className="text-sm text-ink-secondary">
          量表 {overviewQuery.data?.rubric_revision ?? "加载中"}
        </span>
        {isDesktop ? (
          <Button
            variant="secondary"
            className="ml-auto"
            onClick={() => {
              setCreateError(null);
              setModalOpen(true);
            }}
          >
            创建评审分派
          </Button>
        ) : null}
      </div>
      <p className="mb-3 text-xs text-ink-secondary">{overviewQuery.data?.bounded_conclusion}</p>

      {overviewQuery.isLoading ? (
        <SkeletonRows count={2} />
      ) : overviewQuery.isError ? (
        <Alert tone="error">
          {overviewQuery.error instanceof ApiClientError
            ? overviewQuery.error.message
            : "无法加载产品验证状态"}
        </Alert>
      ) : (overviewQuery.data?.assignments ?? []).length === 0 ? (
        <EmptyState
          title="尚未进行产品验证"
          hint="创建评审分派会把当前完整单元包固定为待评版本；外部教师评审完成后导入量表证据，状态将与技术校验分开呈现。"
        />
      ) : (
        <ul className="space-y-2">
          {(overviewQuery.data?.assignments ?? []).map((assignment) => (
            <AssignmentRow
              key={assignment.id}
              projectId={projectId}
              assignment={assignment}
              isDesktop={isDesktop}
              onNotice={setNotice}
            />
          ))}
        </ul>
      )}

      {notice ? (
        <p className="mt-3 text-sm" role="status">
          {notice}
        </p>
      ) : null}

      <Modal
        open={modalOpen}
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) createMutation.reset();
        }}
        title="创建评审分派"
        description="分派会固定当前确认版本对与全部三类产物的校验和；同一包重复创建会返回已有分派。"
      >
        <div className="space-y-4">
          <label className="block text-sm">
            评估单元
            <select
              className="mt-1 w-full rounded border border-line bg-paper p-2"
              value={unitKey}
              onChange={(event) => setUnitKey(event.target.value)}
            >
              {UNIT_KEYS.map((key) => (
                <option key={key} value={key}>
                  {EVALUATION_UNIT_LABELS[key]}
                </option>
              ))}
            </select>
          </label>
          <p className="text-xs text-ink-secondary">
            要求：该单元在当前确认版本对下，每一课时的教案、课件、练习与答案均已完成并通过结构校验。
          </p>
          {createError ? <Alert tone="error">{createError}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button variant="quiet" onClick={() => setModalOpen(false)}>
              取消
            </Button>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              {createMutation.isPending ? "创建中…" : "确认分派"}
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}
