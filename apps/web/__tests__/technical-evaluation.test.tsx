import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TechnicalEvaluationRegion } from "../components/technical-evaluation-region";
import TechnicalEvaluationReportView from "../app/(authed)/projects/[projectId]/technical-evaluation/report/technical-evaluation-report-view";

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

const PASS = {
  evaluation_id: "eval-1",
  unit_key: "travelling-around",
  pass_index: 1,
  mode: "deterministic",
  scenario: "full_pipeline",
  status: "completed",
  overall_outcome: "pass",
  failure_reason: null,
  dataset_revision: "eval-datasets-r1",
  superseded_configuration: false,
  model_config: { model_adapter: "fake" },
  memory_state: { memory_state: "empty (F013 not implemented)" },
  brief_version_id: "bv-1",
  blueprint_version_id: "bpv-1",
  created_at: "2026-09-01T00:00:00Z",
  completed_at: "2026-09-01T00:01:00Z",
  criteria: [
    { criterion_key: "C-TRACE-1", classification: "blocking", outcome: "pass", measured: null, evidence: {} },
    { criterion_key: "C-GROUND-1", classification: "blocking", outcome: "fail", measured: null, evidence: {} },
    { criterion_key: "M-COST", classification: "diagnostic", outcome: null, measured: { estimated_cost_usd: null }, evidence: {} },
  ],
};

describe("技术评估 region", () => {
  it("renders the empty not-run state with the single next action", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ dataset_revision: "eval-datasets-r1", dataset_governance_error: null, passes: [] }));
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationRegion projectId="p1" />);
    expect(await screen.findByText("尚未运行技术评估")).toBeTruthy();
    expect(screen.getByRole("button", { name: "启动评估" })).toBeTruthy();
  });

  it("renders pass states, outcomes, and criterion groups with non-blocking labels", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        dataset_revision: "eval-datasets-r1",
        dataset_governance_error: null,
        passes: [
          PASS,
          {
            ...PASS,
            evaluation_id: "eval-2",
            status: "provider_unavailable",
            overall_outcome: null,
            superseded_configuration: true,
          },
        ],
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationRegion projectId="p1" />);

    expect((await screen.findAllByText("环游世界（英文输出）")).length).toBe(2);
    expect(screen.getByText("供应商不可用")).toBeTruthy();
    expect(screen.getByText("配置已过时")).toBeTruthy();
    expect(screen.getByText("通过")).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button").find((button) => button.textContent?.includes("第 1 遍")) as HTMLElement);
    expect(await screen.findByText("阻断判定")).toBeTruthy();
    expect(screen.getByText("执行轨迹完整")).toBeTruthy();
    expect(screen.getByText("未通过")).toBeTruthy(); // C-GROUND-1 fail stays explicit
    expect(screen.getByText(/诊断指标（非阻断）/)).toBeTruthy();
    expect(screen.getByText(/记忆状态：empty \(F013 not implemented\)/)).toBeTruthy();
  });

  it("start modal warns about live-model cost and shows the duplicate notice", async () => {
    let created = false;
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/technical-evaluation/runs") && !created) {
        created = true;
        return Promise.resolve(
          jsonResponse(
            { evaluation: { ...PASS, status: "queued", overall_outcome: null }, created: false },
            201,
          ),
        );
      }
      return Promise.resolve(
        jsonResponse({
          dataset_revision: "eval-datasets-r1",
          dataset_governance_error: null,
          passes: created ? [PASS] : [],
        }),
      );
    });
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationRegion projectId="p1" />);

    fireEvent.click(await screen.findByRole("button", { name: "启动评估" }));
    const modal = await screen.findByRole("dialog");
    expect(modal.textContent).toContain("受控评估会按固定脚本执行完整备课管线");

    fireEvent.click(withinText(modal, "真实模型"));
    expect(modal.textContent).toContain("真实模型运行将产生实际模型费用");

    fireEvent.click(withinText(modal, "确认启动"));
    await waitFor(() =>
      expect(screen.getByText(/该遍次已存在：已为您定位到现有记录，未重复执行管线。/)).toBeTruthy(),
    );
  });

  it("maps dataset governance failures to the requirement notice", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        dataset_revision: null,
        dataset_governance_error: "dataset governance violation: file hash must match the manifest: units/x",
        passes: [],
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationRegion projectId="p1" />);
    expect(await screen.findByText(/评估数据集未通过治理校验/)).toBeTruthy();
  });
});

function withinText(container: HTMLElement, text: string): HTMLElement {
  const elements = Array.from(container.querySelectorAll<HTMLElement>("label, button"));
  const found = elements.find((element) => element.textContent?.includes(text));
  if (!found) throw new Error(`element containing "${text}" not found`);
  return found;
}

describe("技术评估报告视图", () => {
  it("renders outcomes, honest statuses, and comparison availability", async () => {
    const report = {
      dataset_revision: "eval-datasets-r1",
      dataset_governance_error: null,
      passes: [PASS],
      comparisons: [
        {
          evaluation_id: "eval-1",
          unit_key: "travelling-around",
          pass_index: 1,
          comparison_available: false,
          comparison_unavailable_reason: "该单元仅有此一遍",
          comparable_pass_indexes: [],
        },
      ],
      blocking_criterion_outcomes: { "C-GROUND-1": ["fail"] },
      overall_outcome: "fail",
      product_validation_status: "not_evaluated",
      technical_note: "技术评估与教师产品验证为两个独立状态；产品验证状态在 F010 前保持未评估。",
    };
    global.fetch = vi.fn().mockResolvedValue(jsonResponse(report)) as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationReportView projectId="p1" />);

    expect(await screen.findByText("技术评估报告")).toBeTruthy();
    expect(screen.getByText(/总体结果：/)).toBeTruthy();
    expect(screen.getAllByText(/未通过/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/未评估/).length).toBeGreaterThan(0);
    expect(screen.getByText("对比不可用")).toBeTruthy();
    expect(screen.getByText(/该单元仅有此一遍/)).toBeTruthy();
    expect(screen.getByText(/打印提示/)).toBeTruthy();
    expect(screen.getByText(/诊断（非阻断）· 成本估算/)).toBeTruthy();
  });

  it("renders the loading and error states honestly", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("network")) as unknown as typeof fetch;
    renderUi(<TechnicalEvaluationReportView projectId="p1" />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText(/无法加载技术评估报告/)).toBeTruthy();
  });
});
