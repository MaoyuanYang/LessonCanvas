import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BlueprintPayload } from "../lib/api";
import { BlueprintPanel } from "../components/blueprint-panel";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

let matchMediaMatches = true;

beforeEach(() => {
  vi.restoreAllMocks();
  matchMediaMatches = true;
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: matchMediaMatches,
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

const UNAVAILABLE = {
  available: false,
  draft_revision: null,
  draft: null,
  checks: [],
  findings: [],
  confirmed_version: null,
  confirmed_payload: null,
  confirmed_stale: null,
  stale: false,
  brief_diff: null,
  impact_summary: null,
};

function makeDraft(): BlueprintPayload {
  return {
    unit: {
      title: "人与自然",
      objectives: [
        {
          id: "obj-1",
          text: "理解人与自然主题语篇",
          citations: [
            { type: "standards", section_id: "std-05", snapshot_version: "2026-08-24-v1" },
          ],
        },
      ],
      assessment_intent: "形成性评价为主",
      citations: [],
    },
    lessons: [
      {
        index: 1,
        title: "第1课 人与自然",
        objective_ids: ["obj-1"],
        assessment_intent: "口头表达",
        period_count: 2,
        activity_outline: null,
        material_notes: null,
        citations: [],
      },
      {
        index: 2,
        title: "第2课 环境保护",
        objective_ids: [],
        assessment_intent: null,
        period_count: null,
        activity_outline: null,
        material_notes: null,
        citations: [],
      },
    ],
    findings: [
      {
        id: "f-1",
        tier: "waivable",
        kind: "source_conflict",
        message: "来源材料之间存在内容冲突",
        evidence: null,
        status: "open",
        reason: null,
      },
    ],
  };
}

function blueprintResponse(overrides: Record<string, unknown> = {}) {
  const draft = makeDraft();
  return {
    available: true,
    draft_revision: 1,
    draft,
    checks: [
      { id: "lesson_count", label: "课时数与已确认简报一致", passed: true, affected: [] },
      {
        id: "lesson_fields",
        label: "每课必填字段完整（标题/课时目标/评估意图）",
        passed: false,
        affected: [{ lesson_index: 2, missing: ["objective_ids", "assessment_intent"] }],
      },
      { id: "objective_coverage", label: "每个单元目标至少被一课覆盖", passed: true, affected: [] },
    ],
    findings: [
      draft.findings[0],
      {
        id: "check:lesson_fields",
        tier: "blocking",
        kind: "lesson_fields",
        message: "每课必填字段完整（标题/课时目标/评估意图）",
        evidence: "[]",
        status: "open",
        reason: null,
      },
    ],
    confirmed_version: null,
    confirmed_payload: null,
    confirmed_stale: null,
    stale: false,
    brief_diff: null,
    impact_summary: null,
    ...overrides,
  };
}

const PLANNING_READY = {
  run_id: "run-1",
  status: "draft_ready",
  round_count: 1,
  questions: [],
  draft: null,
};

function routeFetch(blueprint: unknown, planning: unknown = PLANNING_READY) {
  return vi.fn().mockImplementation((url: string) => {
    if (String(url).includes("/blueprint")) return jsonResponse(blueprint);
    if (String(url).includes("/planning")) return jsonResponse(planning);
    return jsonResponse({}, 404);
  });
}

describe("BlueprintPanel", () => {
  it("explains the brief gate when no confirmed brief exists", async () => {
    const planningMissing = jsonResponse(
      { error: { code: "NOT_FOUND", message: "missing", correlation_id: null, details: {} } },
      404,
    );
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes("/blueprint")) return jsonResponse(UNAVAILABLE);
        if (String(url).includes("/planning")) return planningMissing;
        return jsonResponse({}, 404);
      }),
    );
    renderUi(<BlueprintPanel projectId="p1" />);
    expect(await screen.findByText("尚未确认教学简报")).toBeInTheDocument();
    expect(screen.getByText(/先在“教学简报”页签完成确认/)).toBeInTheDocument();
  });

  it("shows failed checks, blocking finding, and gates confirmation", async () => {
    vi.stubGlobal("fetch", routeFetch(blueprintResponse()));
    renderUi(<BlueprintPanel projectId="p1" />);
    expect(await screen.findAllByText(/每课必填字段完整/)).not.toHaveLength(0);
    expect(screen.getByText(/✗/)).toBeInTheDocument();
    expect(screen.getAllByText(/阻断/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "确认蓝图" })).toBeDisabled();
  });

  it("records a waivable finding decision with a reason", async () => {
    const decided = blueprintResponse();
    decided.draft.findings[0].status = "decided";
    decided.draft.findings[0].reason = "以教材为准";
    decided.findings[0] = decided.draft.findings[0];
    const fetchMock = vi
      .fn()
      .mockImplementation((url: string, init?: { method?: string }) => {
        if (String(url).includes("/blueprint/decisions") && init?.method === "POST") {
          return jsonResponse(decided);
        }
        if (String(url).includes("/blueprint")) return jsonResponse(blueprintResponse());
        if (String(url).includes("/planning")) return jsonResponse(PLANNING_READY);
        return jsonResponse({}, 404);
      });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<BlueprintPanel projectId="p1" />);
    expect(await screen.findByText("规划发现")).toBeInTheDocument();
    await act(async () => {
      screen.getByRole("button", { name: "记录教师决策" }).click();
    });
    const reasonBox = await screen.findByLabelText(/决策理由（必填）/);
    fireEvent.change(reasonBox, { target: { value: "以教材为准" } });
    await act(async () => {
      screen.getByRole("button", { name: "记录决策" }).click();
    });
    const decisionCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).includes("/blueprint/decisions") && init?.method === "POST",
    );
    expect(decisionCall).toBeTruthy();
    const body = JSON.parse(String((decisionCall?.[1] as RequestInit)?.body));
    expect(body.finding_id).toBe("f-1");
    expect(body.reason).toBe("以教材为准");
  });

  it("shows the stale banner with brief diff and impact summary", async () => {
    vi.stubGlobal(
      "fetch",
      routeFetch(
        blueprintResponse({
          stale: true,
          confirmed_version: 1,
          confirmed_stale: true,
          brief_diff: [
            { field: "unit_theme", label: "单元主题", old: "人与自然", new: "气候变化" },
          ],
          impact_summary: {
            lesson_structure_changed: false,
            objectives_changed: true,
            details_changed: true,
            summary: "单元目标已变化，目标覆盖需要重新确认",
          },
        }),
      ),
    );
    renderUi(<BlueprintPanel projectId="p1" />);
    expect(await screen.findByText(/已标记为过期/)).toBeInTheDocument();
    expect(screen.getByText(/单元主题：人与自然 → 气候变化/)).toBeInTheDocument();
    expect(screen.getByText(/单元目标已变化/)).toBeInTheDocument();
  });

  it("requires desktop for structured editing on small screens", async () => {
    matchMediaMatches = false;
    vi.stubGlobal("fetch", routeFetch(blueprintResponse()));
    renderUi(<BlueprintPanel projectId="p1" />);
    expect(await screen.findByText(/需要在桌面端/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "确认蓝图" })).toBeNull();
    expect(screen.queryByRole("button", { name: "保存修订" })).toBeNull();
    expect(screen.getByText("第 1 课")).toBeInTheDocument();
  });
});
