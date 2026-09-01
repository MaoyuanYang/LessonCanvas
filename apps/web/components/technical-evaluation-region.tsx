"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, Button, EmptyState, Modal, SkeletonRows } from "@/components/ui";
import {
  ApiClientError,
  EVALUATION_CRITERION_LABELS,
  EVALUATION_MODE_LABELS,
  EVALUATION_OUTCOME_LABELS,
  EVALUATION_STATUS_LABELS,
  EVALUATION_UNIT_LABELS,
  technicalEvaluationCreate,
  technicalEvaluationOverview,
  type TechnicalEvaluationPass,
} from "@/lib/api";

const UNIT_KEYS = ["travelling-around", "natural-disasters", "cultural-heritage"] as const;
const TERMINAL_STATES = new Set(["completed", "provider_unavailable", "failed"]);

function outcomeTone(outcome: string | null): string {
  if (outcome === "pass") return "text-success";
  if (outcome === "fail") return "text-severe";
  if (outcome === "missing_evidence") return "text-warning";
  return "text-ink-secondary";
}

function criterionLabel(key: string): string {
  return EVALUATION_CRITERION_LABELS[key] ?? key;
}

function PassRow({ pass }: { pass: TechnicalEvaluationPass }) {
  const [expanded, setExpanded] = useState(false);
  const blocking = pass.criteria.filter((item) => item.classification === "blocking");
  const diagnostics = pass.criteria.filter((item) => item.classification === "diagnostic");

  return (
    <li className="rounded border border-line bg-paper">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 p-3 text-left focus-visible:outline-2 focus-visible:outline-focus"
      >
        <span className="font-medium">
          {EVALUATION_UNIT_LABELS[pass.unit_key] ?? pass.unit_key}
        </span>
        <span className="text-sm">第 {pass.pass_index} 遍</span>
        <span className="text-sm">{EVALUATION_MODE_LABELS[pass.mode] ?? pass.mode}</span>
        <span className="text-sm text-ink-secondary">
          {pass.scenario === "full_pipeline"
            ? "完整管线"
            : pass.scenario.startsWith("fault:")
              ? `故障注入 ${pass.scenario.slice(6)}`
              : pass.scenario}
        </span>
        <span className="text-sm">{EVALUATION_STATUS_LABELS[pass.status] ?? pass.status}</span>
        {pass.status === "completed" && pass.overall_outcome ? (
          <span className={`text-sm font-medium ${outcomeTone(pass.overall_outcome)}`}>
            {EVALUATION_OUTCOME_LABELS[pass.overall_outcome]}
          </span>
        ) : null}
        {pass.superseded_configuration ? (
          <span className="text-sm text-stale">配置已过时</span>
        ) : null}
      </button>
      {expanded ? (
        <div className="border-t border-line p-3 text-sm">
          <p className="mb-2 text-xs text-ink-secondary">
            绑定版本：简报 {pass.brief_version_id ?? "—"} · 蓝图 {pass.blueprint_version_id ?? "—"} ·
            数据集 {pass.dataset_revision} · 记忆状态：{String(pass.memory_state?.memory_state ?? "—")}
          </p>
          {blocking.length > 0 ? (
            <>
              <h4 className="mb-1 font-medium">阻断判定</h4>
              <ul className="mb-3 space-y-1">
                {blocking.map((item) => (
                  <li key={item.criterion_key} className="flex flex-wrap gap-x-3">
                    <span>{criterionLabel(item.criterion_key)}</span>
                    <span className={outcomeTone(item.outcome)}>
                      {item.outcome ? EVALUATION_OUTCOME_LABELS[item.outcome] : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {diagnostics.length > 0 ? (
            <>
              <h4 className="mb-1 font-medium">诊断指标（非阻断）</h4>
              <ul className="space-y-1 text-ink-secondary">
                {diagnostics.map((item) => (
                  <li key={item.criterion_key}>
                    {criterionLabel(item.criterion_key)}
                    {item.measured ? `：${JSON.stringify(item.measured)}` : ""}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {pass.failure_reason ? (
            <p className="mt-2 text-severe">{pass.failure_reason}</p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

export function TechnicalEvaluationRegion({ projectId }: { projectId: string }) {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [unitKey, setUnitKey] = useState<string>(UNIT_KEYS[0]);
  const [passIndex, setPassIndex] = useState(1);
  const [mode, setMode] = useState<"deterministic" | "live">("deterministic");
  const [createNotice, setCreateNotice] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["technical-evaluation", projectId],
    queryFn: async () => technicalEvaluationOverview(await getToken(), projectId),
    retry: false,
    refetchInterval: (query) =>
      (query.state.data?.passes ?? []).some((pass) => !TERMINAL_STATES.has(pass.status))
        ? 4000
        : false,
  });

  const createMutation = useMutation({
    mutationFn: async () =>
      technicalEvaluationCreate(await getToken(), projectId, {
        unit_key: unitKey,
        pass_index: passIndex,
        mode,
      }),
    onSuccess: (result) => {
      setModalOpen(false);
      setCreateNotice(
        result.created
          ? "评估遍次已启动；完成后结果会出现在下方列表。"
          : "该遍次已存在：已为您定位到现有记录，未重复执行管线。",
      );
      setCreateError(null);
      void queryClient.invalidateQueries({ queryKey: ["technical-evaluation", projectId] });
    },
    onError: (error) => {
      setCreateError(
        error instanceof ApiClientError ? error.message : "评估启动失败，请稍后重试。",
      );
    },
  });

  return (
    <section aria-label="技术评估" className="mb-6 rounded border border-line bg-surface-alt/50 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <h3 className="font-semibold">技术评估</h3>
        <span className="text-sm text-ink-secondary">
          数据集版本：{overviewQuery.data?.dataset_revision ?? "加载中"}
        </span>
        <Button
          variant="secondary"
          className="ml-auto"
          onClick={() => {
            setCreateNotice(null);
            setCreateError(null);
            setModalOpen(true);
          }}
        >
          启动评估
        </Button>
        <a
          className="text-sm underline focus-visible:outline-2 focus-visible:outline-focus"
          href={`/projects/${projectId}/technical-evaluation/report`}
          target="_blank"
          rel="noreferrer"
        >
          打印技术评估报告
        </a>
      </div>

      {overviewQuery.isLoading ? (
        <SkeletonRows count={2} />
      ) : overviewQuery.isError ? (
        <Alert tone="error">
          {overviewQuery.error instanceof ApiClientError
            ? overviewQuery.error.message
            : "无法加载技术评估状态"}
        </Alert>
      ) : overviewQuery.data?.dataset_governance_error ? (
        <Alert tone="error">评估数据集未通过治理校验：{overviewQuery.data.dataset_governance_error}</Alert>
      ) : (overviewQuery.data?.passes ?? []).length === 0 ? (
        <EmptyState
          title="尚未运行技术评估"
          hint="选择固定评估单元启动第一遍受控评估；结果会绑定固定的版本、配置与数据集。"
        />
      ) : (
        <ul className="space-y-2" aria-live="polite">
          {(overviewQuery.data?.passes ?? []).map((pass) => (
            <PassRow key={pass.evaluation_id} pass={pass} />
          ))}
        </ul>
      )}

      {createNotice ? (
        <p className="mt-3 text-sm" role="status">
          {createNotice}
        </p>
      ) : null}

      <Modal
        open={modalOpen}
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) createMutation.reset();
        }}
        title="启动技术评估"
        description="受控评估会按固定脚本执行完整备课管线并记录判定证据。"
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
          <label className="block text-sm">
            遍次
            <select
              className="mt-1 w-full rounded border border-line bg-paper p-2"
              value={passIndex}
              onChange={(event) => setPassIndex(Number(event.target.value))}
            >
              <option value={1}>第 1 遍</option>
              <option value={2}>第 2 遍</option>
            </select>
          </label>
          <fieldset className="text-sm">
            <legend className="mb-1">运行模式</legend>
            <label className="mr-4 inline-flex items-center gap-1">
              <input
                type="radio"
                name="evaluation-mode"
                checked={mode === "deterministic"}
                onChange={() => setMode("deterministic")}
              />
              确定性（脚本模型）
            </label>
            <label className="inline-flex items-center gap-1">
              <input
                type="radio"
                name="evaluation-mode"
                checked={mode === "live"}
                onChange={() => setMode("live")}
              />
              真实模型
            </label>
          </fieldset>
          {mode === "live" ? (
            <p className="text-sm text-warning">
              真实模型运行将产生实际模型费用；每遍会执行完整备课管线（访谈、确认与三类产物生成）。
            </p>
          ) : null}
          {createError ? <Alert tone="error">{createError}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button variant="quiet" onClick={() => setModalOpen(false)}>
              取消
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "启动中…" : "确认启动"}
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}
