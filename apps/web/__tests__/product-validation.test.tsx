import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProductValidationRegion } from "../components/product-validation-region";
import { AlignmentPanel } from "../components/alignment-panel";
import TechnicalEvaluationReportView from "../app/(authed)/projects/[projectId]/technical-evaluation/report/technical-evaluation-report-view";
import * as api from "../lib/api";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
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

const ASSIGNMENT = {
  id: "a1",
  unit_key: "travelling-around",
  dataset_revision: "eval-datasets-r1",
  brief_version_id: "bv-1",
  blueprint_version_id: "bpv-1",
  rubric_revision: "rubric-r1",
  state: "pending_evidence",
  staleness: null,
  not_complete_reason: null,
  outcome: null,
  outcome_detail: null,
  created_at: "2026-09-01T00:00:00Z",
  concluded_at: null,
};

function overviewOf(assignments: Array<Record<string, unknown>>, overall = "in_progress") {
  return jsonResponse({
    rubric_revision: "rubric-r1",
    overall_status: overall,
    bounded_conclusion: "产品验证基于一位外部高中英语教师的有限评审证据，不可推广到其他教师、学校或地区。",
    assignments,
  });
}

const DETAIL = {
  id: "a1",
  unit_key: "travelling-around",
  dataset_revision: "eval-datasets-r1",
  rubric_revision: "rubric-r1",
  package: {
    brief_version: 2,
    blueprint_version: 3,
    lessons: [
      {
        index: 1,
        title: "第一课",
        members: { lesson_plan: { state: "complete" }, slide_deck: { state: "complete" }, exercise: { state: "complete" } },
      },
    ],
  },
  state: "pending_evidence",
  staleness: null,
  not_complete_reason: null,
  created_at: "2026-09-01T00:00:00Z",
  concluded_at: null,
  evidence_history: [],
  rubric_sheet: {
    rubric_revision: "rubric-r1",
    title: "LessonCanvas 单元教学包外部教师评审量表",
    dimensions: [],
    severe_finding_classes: [],
    structural_rework_question: "该单元包是否需要结构性返工才能用于课堂？",
  },
};

/** Route fetch mocks by URL so region, detail, and mutation endpoints coexist. */
function routeFetch(
  handlers: Array<{ match: (url: string, init?: RequestInit) => boolean; body: unknown; status?: number }>,
) {
  return vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    for (const handler of handlers) {
      if (handler.match(url, init)) {
        return Promise.resolve(jsonResponse(handler.body, handler.status ?? 200));
      }
    }
    return Promise.resolve(overviewOf([ASSIGNMENT]));
  });
}

describe("产品验证 region（TS-011）", () => {
  it("renders the empty not-evaluated state with bounded conclusion and create action", async () => {
    global.fetch = vi.fn().mockResolvedValue(overviewOf([], "not_evaluated")) as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    expect(await screen.findByText("尚未进行产品验证")).toBeTruthy();
    expect(screen.getByRole("button", { name: "创建评审分派" })).toBeTruthy();
    expect(screen.getByText(/不可推广/)).toBeTruthy();
    expect(screen.getByText(/产品验证状态：未评估/)).toBeTruthy();
  });

  it("renders every state vocabulary: pending, failed outcome, stale with reason", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      overviewOf(
        [
          ASSIGNMENT,
          {
            ...ASSIGNMENT,
            id: "a2",
            unit_key: "natural-disasters",
            state: "failed",
            outcome: "failed",
            outcome_detail: {
              outcome: "failed",
              core_mean: 4.6,
              core_mean_threshold: 4.0,
              severe_finding_count: 1,
              structural_rework_required: false,
              violated_rules: ["severe_finding_present"],
            },
          },
          {
            ...ASSIGNMENT,
            id: "a3",
            unit_key: "cultural-heritage",
            state: "stale",
            staleness: { reason: "newer_confirmed_pair", superseded_by: "简报 v3 · 蓝图 v3" },
          },
        ],
        "failed",
      ),
    ) as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    expect(await screen.findAllByText(/环游世界|自然灾害|文化遗产/)).toBeTruthy();
    expect(screen.getByText("待证据")).toBeTruthy();
    expect(screen.getByText("已过时（历史）")).toBeTruthy();
    expect(screen.getByText(/已有更新的确认版本对/)).toBeTruthy();
    expect(screen.getByText(/产品验证状态：失败/)).toBeTruthy();
  });

  it("create modal posts the assignment and surfaces the duplicate notice", async () => {
    let created = false;
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/product-validation/assignments") && init?.method === "POST") {
        created = true;
        return Promise.resolve(
          jsonResponse({ ...ASSIGNMENT, created: !created ? false : true }, 201),
        );
      }
      return Promise.resolve(overviewOf(created ? [ASSIGNMENT] : [], created ? "in_progress" : "not_evaluated"));
    });
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: "创建评审分派" }));
    const modal = await screen.findByRole("dialog");
    expect(modal.textContent).toContain("分派会固定当前确认版本对");
    fireEvent.click(screen.getByRole("button", { name: "确认分派" }));
    await waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain("分派已创建");
    });
  });

  it("create modal names the gap when the package is incomplete", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/product-validation/assignments") && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse(
            {
              error: {
                code: "REQUIREMENT",
                message: "the unit package is not technically complete",
                details: {
                  gate: "complete_package",
                  gaps: [{ lesson_index: 2, family: "slide_deck", state: "missing" }],
                },
              },
            },
            422,
          ),
        );
      }
      return Promise.resolve(overviewOf([]));
    });
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: "创建评审分派" }));
    fireEvent.click(screen.getByRole("button", { name: "确认分派" }));
    await waitFor(() => {
      expect(screen.getByText(/该单元包尚不完整（缺失：第 2 课 slide_deck）/)).toBeTruthy();
    });
  });

  it("import form lists every server violation at once and blocks resubmit until fixed", async () => {
    global.fetch = routeFetch([
      {
        match: (url, init) => url.endsWith("/evidence") && init?.method === "POST",
        status: 422,
        body: {
          error: {
            code: "REQUIREMENT",
            message: "rubric evidence does not satisfy the fixed schema",
            details: {
              violations: [
                "scores.knowledge_correctness.note: required evidence note missing",
                "severe_findings[0].evidence: required evidence text missing",
              ],
            },
          },
        },
      },
      { match: (url) => url.endsWith("/assignments/a1"), body: DETAIL },
    ]) as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: /环游世界/ }));
    fireEvent.click(await screen.findByRole("button", { name: "导入量表证据" }));
    for (const label of [
      "知识准确性证据说明",
      "语言质量证据说明",
      "练习与答案正确性证据说明",
      "目标对齐证据说明",
      "教学可用性证据说明",
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: `${label}：内容准确。` } });
    }
    const fileInput = await screen.findByLabelText("原始量表文档");
    fireEvent.change(fileInput, {
      target: { files: [new File(["pdf"], "rubric.pdf", { type: "application/pdf" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "导入量表证据" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("scores.knowledge_correctness.note");
    expect(alert.textContent).toContain("severe_findings[0].evidence");
  });

  it("client-side pre-validation blocks empty notes without calling the server", async () => {
    const fetchMock = routeFetch([
      { match: (url) => url.endsWith("/assignments/a1"), body: DETAIL },
    ]);
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: /环游世界/ }));
    fireEvent.click(await screen.findByRole("button", { name: "导入量表证据" }));
    fireEvent.change(await screen.findByLabelText("原始量表文档"), {
      target: { files: [new File(["pdf"], "rubric.pdf", { type: "application/pdf" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "导入量表证据" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("scores.knowledge_correctness.note");
    const posted = (fetchMock as ReturnType<typeof vi.fn>).mock.calls.some(
      ([input, init]) => String(input).endsWith("/evidence") && (init as RequestInit | undefined)?.method === "POST",
    );
    expect(posted).toBe(false);
  });

  it("duplicate evidence revision shows the idempotent notice", async () => {
    global.fetch = routeFetch([
      {
        match: (url, init) => url.endsWith("/evidence") && init?.method === "POST",
        status: 201,
        body: {
          id: "ev-1",
          evidence_revision: "r1",
          status: "current",
          capture_channel: "owner_mediated_import",
          outcome: "failed",
          outcome_detail: {
            outcome: "failed",
            core_mean: 4.2,
            core_mean_threshold: 4,
            severe_finding_count: 1,
            structural_rework_required: false,
            violated_rules: ["severe_finding_present"],
          },
          created: false,
          created_at: "2026-09-01T00:00:00Z",
        },
      },
      { match: (url) => url.endsWith("/assignments/a1"), body: DETAIL },
    ]) as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: /环游世界/ }));
    fireEvent.click(await screen.findByRole("button", { name: "导入量表证据" }));
    for (const label of [
      "知识准确性证据说明",
      "语言质量证据说明",
      "练习与答案正确性证据说明",
      "目标对齐证据说明",
      "教学可用性证据说明",
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: `${label}：内容准确。` } });
    }
    fireEvent.change(await screen.findByLabelText("原始量表文档"), {
      target: { files: [new File(["pdf"], "rubric.pdf", { type: "application/pdf" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "导入量表证据" }));

    await waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain("该量表版本已导入");
    });
  });

  it("stale rows disable import and show supersession guidance", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      overviewOf([
        { ...ASSIGNMENT, state: "stale", staleness: { reason: "package_changed", superseded_by: "当前包的工件记录已变化" } },
      ]),
    ) as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: /环游世界/ }));
    expect(await screen.findByText(/该分派绑定的包已被取代/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "导入量表证据" })).toBeNull();
  });

  it("records an honest not-complete conclusion with a reason", async () => {
    global.fetch = routeFetch([
      {
        match: (url, init) => url.endsWith("/conclusion") && init?.method === "POST",
        body: {
          ...ASSIGNMENT,
          state: "not_complete",
          not_complete_reason: "评审教师在交付窗口内无法完成评审",
        },
      },
      { match: (url) => url.endsWith("/assignments/a1"), body: DETAIL },
    ]) as unknown as typeof fetch;
    renderUi(<ProductValidationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: /环游世界/ }));
    fireEvent.click(await screen.findByRole("button", { name: "记录为未完成" }));
    const modal = await screen.findByRole("dialog");
    fireEvent.change(screen.getByLabelText("未完成原因"), {
      target: { value: "评审教师在交付窗口内无法完成评审" },
    });
    fireEvent.click(screen.getByRole("button", { name: "确认记录" }));
    await waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain("未完成");
    });
    expect(modal).toBeTruthy();
  });
});

// --- TS-012: live status vocabulary, separation, and report surfaces -------

const ALIGNMENT_BASE: api.AlignmentView = {
  brief_version: 2,
  blueprint_version: 3,
  brief_version_id: "b1",
  blueprint_version_id: "bp1",
  technical_status: "validated",
  draft_export_available: true,
  product_validation_status: "failed",
  objectives: [],
  lessons: [
    {
      lesson_index: 1,
      title: "第一课",
      members: {
        lesson_plan: { state: "complete", files: [{ role: "document", object_key: "k", checksum: "c" }] },
        slide_deck: { state: "complete" },
        exercise: { state: "complete" },
      },
    },
  ],
  findings: [],
  overrides: [],
};

describe("状态对与报告表面（TS-012）", () => {
  it("alignment panel keeps technical pass and product failure both explicit", async () => {
    vi.spyOn(api, "getAlignment").mockResolvedValue(ALIGNMENT_BASE);
    vi.spyOn(api, "listDeliveryExports").mockResolvedValue([]);

    renderUi(<AlignmentPanel projectId="p1" onNavigate={vi.fn()} />);

    expect(await screen.findByText(/技术校验状态：技术校验通过/)).toBeInTheDocument();
    expect(screen.getByText(/产品验证状态：失败/)).toBeInTheDocument();
  });

  it("technical-evaluation report renders the live product status beside the technical outcome", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        dataset_revision: "eval-datasets-r1",
        dataset_governance_error: null,
        passes: [],
        comparisons: [],
        blocking_criterion_outcomes: {},
        overall_outcome: "pass",
        product_validation_status: "not_complete",
        technical_note: "技术评估与教师产品验证为两个独立状态。",
      }),
    ) as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationReportView projectId="p1" />);

    const line = await screen.findByText(/产品验证状态 = 未完成/);
    expect(line.textContent).toContain("两个独立状态");
    expect(screen.getByText(/总体结果：通过/)).toBeTruthy();
  });
});
