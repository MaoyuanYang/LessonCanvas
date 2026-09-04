/**
 * F016 TS-018..TS-020: the specialist-stage web surfaces — evidence-panel
 * review-round chips (U1), the sources analysis region with gated retry
 * (U4), and the read-only findings/design regions on artifact rows (U2/U3).
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EvidencePanel } from "../components/evidence-panel";
import { SourcesPanel } from "../components/sources-panel";
import {
  ArtifactProgressList,
  ARTIFACT_STATUS_LABELS,
} from "../components/artifact-run";

vi.mock("@/lib/auth", () => ({
  getApiToken: async () => "test-token",
  clearApiToken: () => {},
}));

beforeEach(() => {
  vi.restoreAllMocks();
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    })),
  });
});

function renderUi(node: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{node}</QueryClientProvider>);
}

function jsonResponse(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function sseResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  let index = 0;
  return {
    ok: true,
    status: 200,
    body: {
      getReader: () => ({
        read: async () => {
          if (index < chunks.length) {
            return { done: false, value: encoder.encode(chunks[index++]) };
          }
          return { done: true };
        },
      }),
    },
  };
}

// --- shared evidence fixtures (TS-018) -------------------------------------

const INVENTORY = {
  runs: [
    {
      run_id: "run-plan",
      kind: "lesson_plan",
      status: "complete",
      created_at: "2026-09-04T10:00:00+00:00",
      cursor: "0001|run-plan",
      model_calls: 18,
      model_call_cap: 32,
      round_count: null,
      brief_version: 1,
      blueprint_version: 1,
      difficulty: null,
      language_mode: "中英双语",
      complete_count: 6,
      total_count: 6,
      cost_usd_estimated: 0.03,
      cost_estimate_complete: true,
      model_latency_ms_total: 20000,
      trace_event_count: 40,
      model_call_count: 18,
      tool_call_count: 12,
      evidence_kinds: ["model.generation_review_lesson"],
      telemetry_gaps: [],
    },
  ],
  next_cursor: null,
};

const SUMMARY = {
  ...INVENTORY.runs[0],
  updated_at: "2026-09-04T10:05:00+00:00",
  artifacts: [],
  interview_message_count: null,
  superseded_by: null,
  recovery_view: "generation",
};

function reviewEvent(cursor: string, overrides: Record<string, unknown> = {}) {
  return {
    cursor,
    source: "trace",
    event_type: "model.generation_review_lesson",
    created_at: "2026-09-04T10:00:01+00:00",
    latency_ms: 900,
    prompt_tokens: 800,
    completion_tokens: 200,
    cost_usd: 0.001,
    model: "fake:deepseek-chat",
    lesson_index: 1,
    payload: {
      prompt: { lesson: { lesson_index: 1 } },
      response: {},
      round: 1,
      severe_count: 1,
      minor_count: 0,
      parse_failed: false,
    },
    ...overrides,
  };
}

describe("F016 evidence-panel specialist-stage surfaces (TS-018)", () => {
  it("labels the new stage events and shows review-round chips", async () => {
    const events = {
      run_id: "run-plan",
      events: [
        {
          cursor: "c1",
          source: "trace",
          event_type: "model.generation_design_lesson",
          created_at: "2026-09-04T10:00:00+00:00",
          latency_ms: 800,
          prompt_tokens: 500,
          completion_tokens: 300,
          cost_usd: 0.001,
          model: "fake:deepseek-chat",
          lesson_index: 1,
          payload: { prompt: { lesson: { lesson_index: 1 } }, response: {} },
        },
        reviewEvent("c2"),
        {
          ...reviewEvent("c3"),
          event_type: "model.generation_revise_lesson",
          payload: {
            prompt: { lesson: { lesson_index: 1 }, findings: [{ severity: "severe" }] },
            response: {},
          },
        },
      ],
      next_cursor: null,
    };
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/narrate/stream")) return Promise.resolve(sseResponse([]));
      if (url.includes("/narrate")) return Promise.resolve(jsonResponse({}, 202));
      if (url.includes("/run-plan/events")) return Promise.resolve(jsonResponse(events));
      if (url.includes("/evidence/run-plan")) return Promise.resolve(jsonResponse(SUMMARY));
      if (url.endsWith("/evidence")) return Promise.resolve(jsonResponse(INVENTORY));
      return Promise.resolve(jsonResponse({ runs: [], next_cursor: null }));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("模型调用·活动设计")).toBeTruthy();
    });
    expect(screen.getAllByText("模型调用·质量评审（教案）").length).toBeGreaterThan(0);
    expect(screen.getAllByText("模型调用·修订重写（教案）").length).toBeGreaterThan(0);
    expect(screen.getByText("第 1 轮")).toBeTruthy();
    expect(screen.getByText("严重 1 · 轻微 0")).toBeTruthy();
    expect(screen.getByText("触发修订")).toBeTruthy();
    expect(screen.getByText("修订重写")).toBeTruthy();
    expect(screen.getByText("携带发现 1 条")).toBeTruthy();
  });

  it("marks unparseable review output honestly on the chip", async () => {
    const events = {
      run_id: "run-plan",
      events: [reviewEvent("c1", { payload: { round: 1, severe_count: 0, minor_count: 0, parse_failed: true } })],
      next_cursor: null,
    };
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/narrate/stream")) return Promise.resolve(sseResponse([]));
      if (url.includes("/narrate")) return Promise.resolve(jsonResponse({}, 202));
      if (url.includes("/run-plan/events")) return Promise.resolve(jsonResponse(events));
      if (url.includes("/evidence/run-plan")) return Promise.resolve(jsonResponse(SUMMARY));
      if (url.endsWith("/evidence")) return Promise.resolve(jsonResponse(INVENTORY));
      return Promise.resolve(jsonResponse({ runs: [], next_cursor: null }));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("评审输出不可解析")).toBeTruthy();
    });
  });
});

// --- TS-019: sources analysis region ----------------------------------------

const ANALYZED_SOURCE = {
  id: "s-1",
  filename: "reader.txt",
  content_type: "text/plain",
  size_bytes: 100,
  status: "ready",
  rejection_code: null,
  rejection_message: null,
  rights_acknowledged: true,
  content_sha256: "hash",
  chunks: [],
  analysis: {
    status: "ready",
    topics: ["主题一", "主题二"],
    language_points: ["核心词汇"],
    suitability: { recommended: true },
    key_passages: [{ chunk_position: 2, digest: "摘录" }],
    error: null,
    model: "fake:deepseek-chat",
    latency_ms: 1200,
    prompt_tokens: 300,
    completion_tokens: 200,
    cost_usd: null,
    updated_at: "2026-09-04T10:00:00+00:00",
  },
  created_at: "2026-09-04T09:00:00+00:00",
  updated_at: "2026-09-04T10:00:00+00:00",
};

const FAILED_SOURCE = {
  ...ANALYZED_SOURCE,
  id: "s-2",
  filename: "broken.txt",
  analysis: {
    ...ANALYZED_SOURCE.analysis,
    status: "failed",
    error: "model provider unavailable",
    topics: [],
  },
};

describe("F016 sources analysis region (TS-019)", () => {
  it("shows the analyzed badge, digest, and cost line; failed sources offer retry", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/analyze")) {
        return Promise.resolve(jsonResponse({ ...FAILED_SOURCE, analysis: ANALYZED_SOURCE.analysis }));
      }
      if (url.endsWith("/sources")) {
        return Promise.resolve(jsonResponse([ANALYZED_SOURCE, FAILED_SOURCE]));
      }
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<SourcesPanel projectId="p1" />);

    await waitFor(() => {
      expect(screen.getAllByText("已分析").length).toBeGreaterThan(0);
      expect(screen.getAllByText("分析失败").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByText("查看来源分析"));
    expect(await screen.findByText("主题一；主题二")).toBeTruthy();
    expect(screen.getByText(/第 2 段/)).toBeTruthy();
    expect(screen.getByText(/未记录/)).toBeTruthy();

    fireEvent.click(screen.getByText("重试分析"));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/projects/p1/sources/s-2/analyze"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("hides the retry action in read-only contexts", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith("/sources")) return Promise.resolve(jsonResponse([FAILED_SOURCE]));
      return Promise.resolve(jsonResponse({}));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<SourcesPanel projectId="p1" readOnly />);
    await waitFor(() => {
      expect(screen.getAllByText("分析失败").length).toBeGreaterThan(0);
    });
    expect(screen.queryByText("重试分析")).toBeNull();
  });
});

// --- TS-020: artifact stage statuses and read-only detail regions -----------

describe("F016 artifact stage surfaces (TS-020)", () => {
  it("labels the new statuses and renders findings/design read-only", () => {
    expect(ARTIFACT_STATUS_LABELS.designing).toBe("设计中");
    expect(ARTIFACT_STATUS_LABELS.reviewing).toBe("评审中");

    const artifact = {
      id: "a-1",
      lesson_index: 3,
      status: "complete",
      failure_reason: null,
      design: {
        objective_ids: ["obj-1"],
        activities: [
          { name: "导入", type: "warmup", description: "图片与问题导入", timing_minutes: 5 },
        ],
        assessment_approach: "形成性评价",
        evidence_references: [{ chunk_position: 2 }],
      },
      review_findings: [
        { dimension: "objective_coverage", severity: "severe", message: "补齐目标", reference: null },
        { dimension: "consistency", severity: "minor", message: "时长不一致", reference: null },
      ],
      review_rounds: 2,
      review_outcome: "passed_after_revise",
    };
    renderUi(
      <ArtifactProgressList
        completeCount={1}
        totalCount={1}
        artifacts={[artifact]}
      />,
    );

    fireEvent.click(screen.getByText("查看活动设计与评审发现"));
    expect(screen.getByText(/修订后第 2 轮/)).toBeTruthy();
    expect(screen.getByText(/修订后评审通过/)).toBeTruthy();
    expect(screen.getByText("严重")).toBeTruthy();
    expect(screen.getByText("轻微")).toBeTruthy();
    expect(screen.getByText("目标覆盖")).toBeTruthy();
    expect(screen.getByText("内在一致性")).toBeTruthy();
    const activityItem = screen
      .getAllByText(/5 分钟/)
      .find((el) => el.textContent?.includes("图片与问题导入"));
    expect(activityItem).toBeTruthy();
    expect(screen.getByText(/运行中间产物，仅查看/)).toBeTruthy();
  });

  it("shows the clean-pass empty state for a reviewed artifact without findings", () => {
    renderUi(
      <ArtifactProgressList
        completeCount={1}
        totalCount={1}
        artifacts={[
          {
            id: "a-2",
            lesson_index: 1,
            status: "complete",
            failure_reason: null,
            review_findings: [],
            review_rounds: 1,
            review_outcome: "passed",
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByText("查看评审发现"));
    expect(screen.getByText("评审通过，无严重或轻微发现。")).toBeTruthy();
    expect(screen.getByText(/第 1 轮/)).toBeTruthy();
  });

  it("names the review stage on failed-after-revise failure reasons", () => {
    renderUi(
      <ArtifactProgressList
        completeCount={0}
        totalCount={1}
        artifacts={[
          {
            id: "a-3",
            lesson_index: 2,
            status: "failed",
            failure_reason:
              "review stage: severe findings persisted on the 教案 draft after one revise round",
            review_findings: [
              { dimension: "grounding", severity: "severe", message: "依据缺失", reference: null },
            ],
            review_rounds: 2,
            review_outcome: "failed_after_revise",
          },
        ]}
      />,
    );
    expect(
      screen.getByText(/review stage: severe findings persisted/),
    ).toBeTruthy();
    fireEvent.click(screen.getByText("查看评审发现"));
    expect(screen.getByText(/修订后仍未通过/)).toBeTruthy();
  });
});

// --- narration sentences (U2) -----------------------------------------------

describe("F016 narration sentences (TS-020)", () => {
  it("maps the specialist stage statuses to teacher-readable sentences", async () => {
    const { narrationText } = await import("../components/generation-panel");
    const lesson = (status: string, reason?: string) =>
      ({
        run_id: "run-1",
        seq: 1,
        event_type: "lesson",
        payload: { lesson_index: 2, status, ...(reason ? { reason } : {}) },
        created_at: "2026-09-04T10:00:00+00:00",
      }) as Parameters<typeof narrationText>[0];
    expect(narrationText(lesson("designing"))).toBe("正在设计第 2 课活动……");
    expect(narrationText(lesson("reviewing"))).toBe("第 2 课进入质量评审……");
    expect(narrationText(lesson("revising"))).toBe("第 2 课触发一轮修订……");
    expect(narrationText(lesson("failed", "review stage: severe findings persisted"))).toBe(
      "第 2 课评审未通过（修订后仍存在严重问题）：review stage: severe findings persisted",
    );

    const deck = await import("../components/deck-panel");
    expect(
      deck.deckNarrationText(
        { run_id: "r", seq: 1, event_type: "lesson", payload: { lesson_index: 1, status: "reviewing" }, created_at: "t" },
      ),
    ).toBe("第 1 课课件进入质量评审……");
    const exercise = await import("../components/exercise-panel");
    expect(
      exercise.exerciseNarrationText(
        { run_id: "r", seq: 1, event_type: "lesson", payload: { lesson_index: 3, status: "revising" }, created_at: "t" },
      ),
    ).toBe("第 3 课练习触发一轮修订……");
  });
});
