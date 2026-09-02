import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GenerationPanel } from "../components/generation-panel";
import { VersionComparePanel } from "../components/version-compare-panel";
import WorkspaceView from "../app/(authed)/projects/[projectId]/workspace-view";

vi.mock("@/lib/auth", () => ({
  getApiToken: async () => "test-token",
  clearApiToken: () => {},
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

const TRANSITION = {
  first_version: false,
  from: { brief_version: 1, blueprint_version: 1 },
  to: { brief_version: 1, blueprint_version: 2 },
  intent_diff: [{ field: "assessment_orientation", old: "形成性评价为主", new: "终结性评价为主" }],
  verdicts: [
    { lesson_index: 2, family: "lesson_plan", verdict: "affected", reason: "blueprint.lesson[2].activity_outline" },
    { lesson_index: 1, family: "lesson_plan", verdict: "retained", reason: null },
    { lesson_index: 6, family: "lesson_plan", verdict: "historical", reason: "blueprint.lessons" },
  ],
  artifacts: [
    { lesson_index: 2, family: "lesson_plan", old: { status: "complete", download_available: true }, new: { status: "complete", download_available: true } },
    { lesson_index: 1, family: "lesson_plan", old: { status: "complete", download_available: true }, new: { status: null, download_available: false } },
    { lesson_index: 6, family: "lesson_plan", old: { status: "complete", download_available: true }, new: { status: null, download_available: false } },
  ],
};

const IMPACT = {
  affected_lessons: [2],
  affected_families: ["lesson_plan", "slide_deck", "exercise"],
  reasons: [{ field: "blueprint.lesson[2].activity_outline", scope: "lesson:2", detail: "蓝图课时层字段变更" }],
  structural: { added: [], removed: [6] },
  uncertain: false,
  no_delta: false,
};

const TRANSITION_FULL = { ...TRANSITION, impact: IMPACT };

const SCOPED_SNAPSHOT = {
  run_id: "run-2",
  status: "complete",
  brief_version: 1,
  blueprint_version: 2,
  language_mode: "中英双语",
  scope_lesson_indexes: [2],
  retained_artifacts: [
    {
      id: "plan-1",
      lesson_index: 1,
      source_brief_version: 1,
      source_blueprint_version: 1,
      source_run_id: "run-1",
      checksum: "abc",
      download_available: true,
    },
  ],
  model_calls: 1,
  model_call_cap: 20,
  artifacts: [
    {
      id: "plan-2",
      lesson_index: 2,
      status: "complete",
      language_mode: "中英双语",
      failure_reason: null,
      retry_count: 0,
      download_url: "/projects/p1/lesson-plans/plan-2/download",
    },
  ],
  complete_count: 1,
  total_count: 1,
};

describe("VersionComparePanel", () => {
  it("shows the first-version empty state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ first_version: true })),
    );
    renderUi(<VersionComparePanel projectId="p1" />);
    expect(await screen.findByText("尚无版本变迁")).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("renders the transition header, diff, verdict table, and on-demand impact preview", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/impact")) return Promise.resolve(jsonResponse(IMPACT));
      return Promise.resolve(jsonResponse(TRANSITION_FULL));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<VersionComparePanel projectId="p1" />);

    expect(await screen.findByText(/蓝图 v1 → 简报 v1 · 蓝图 v2/)).toBeVisible();
    expect(screen.getByText("assessment_orientation")).toBeVisible();
    expect(screen.getByText("受影响")).toBeVisible();
    expect(screen.getByText("沿用")).toBeVisible();
    expect(screen.getByText("历史")).toBeVisible();
    expect(screen.getByText("blueprint.lesson[2].activity_outline")).toBeVisible();

    expect(await screen.findByText(/受影响课时：/)).toBeVisible();
    expect(screen.getAllByText(/第 2 课/).length).toBeGreaterThan(0);
    expect(screen.getByText(/移除课时：第 6 课/)).toBeVisible();
    expect(screen.getByText(/蓝图课时层字段变更/)).toBeVisible();
    // Read-only view: no POST ever issued.
    const methods = fetchMock.mock.calls.map(([, init]) => init?.method ?? "GET");
    expect(methods.every((method) => method === "GET")).toBe(true);
    vi.unstubAllGlobals();
  });
});

describe("GenerationPanel retained rows", () => {
  it("renders retained provenance and downloads alongside scoped artifacts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/generation/events")) {
          return Promise.resolve({ ok: true, status: 200, body: null });
        }
        if (url.endsWith("/generation")) return Promise.resolve(jsonResponse(SCOPED_SNAPSHOT));
        return Promise.resolve(jsonResponse(SCOPED_SNAPSHOT));
      }),
    );
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText("沿用课程（1）")).toBeVisible();
    expect(screen.getByText(/源版本：简报 v1 · 蓝图 v1/)).toBeVisible();
    expect(screen.getByText(/教案未受本次修订影响/)).toBeVisible();
    const retainedDownload = screen.getAllByRole("button", { name: "下载 DOCX" });
    expect(retainedDownload.length).toBeGreaterThanOrEqual(2);
    vi.unstubAllGlobals();
  });
});

describe("WorkspaceView versions tab", () => {
  it("navigates to the ninth 版本对比 view alongside the existing eight", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ first_version: true })),
    );
    renderUi(<WorkspaceView projectId="p1" />);
    const tabs = screen.getAllByRole("button").map((button) => button.textContent);
    expect(tabs).toEqual(
      expect.arrayContaining([
        "来源", "需求访谈", "教学简报", "单元蓝图", "教案生成", "课件生成", "练习与答案", "运行证据", "版本对比",
      ]),
    );
    fireEvent.click(screen.getByRole("button", { name: "版本对比" }));
    expect(await screen.findByText("尚无版本变迁")).toBeVisible();
    vi.unstubAllGlobals();
  });
});

