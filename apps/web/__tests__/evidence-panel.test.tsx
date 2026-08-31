import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EvidencePanel } from "../components/evidence-panel";
import WorkspaceView from "../app/(authed)/projects/[projectId]/workspace-view";

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

function sseResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  let index = 0;
  return {
    ok: true,
    status: 200,
    body: {
      getReader: () => ({
        read: async () =>
          index < chunks.length
            ? { value: encoder.encode(chunks[index++]), done: false }
            : { value: undefined, done: true },
      }),
    },
  };
}

const INVENTORY = {
  runs: [
    {
      run_id: "run-plan",
      kind: "lesson_plan",
      status: "complete",
      created_at: "2026-08-31T10:00:00+00:00",
      cursor: "0001|run-plan",
      model_calls: 6,
      model_call_cap: 20,
      round_count: null,
      brief_version: 1,
      blueprint_version: 1,
      difficulty: null,
      language_mode: "中英双语",
      complete_count: 6,
      total_count: 6,
      cost_usd_estimated: 0.0123,
      cost_estimate_complete: true,
      model_latency_ms_total: 12000,
      trace_event_count: 30,
      model_call_count: 6,
      tool_call_count: 12,
      evidence_kinds: ["model.generation_write_lesson", "run"],
      telemetry_gaps: [],
    },
    {
      run_id: "run-discovery",
      kind: "discovery",
      status: "draft_ready",
      created_at: "2026-08-31T09:00:00+00:00",
      cursor: "0000|run-discovery",
      model_calls: 2,
      model_call_cap: null,
      round_count: 0,
      brief_version: null,
      blueprint_version: null,
      difficulty: null,
      language_mode: null,
      complete_count: null,
      total_count: null,
      cost_usd_estimated: 0,
      cost_estimate_complete: false,
      model_latency_ms_total: 800,
      trace_event_count: 2,
      model_call_count: 2,
      tool_call_count: 0,
      evidence_kinds: ["model.gap_analysis"],
      telemetry_gaps: ["token_usage_not_recorded"],
    },
  ],
  next_cursor: null,
};

const SUMMARY = {
  ...INVENTORY.runs[0],
  updated_at: "2026-08-31T10:05:00+00:00",
  artifacts: [
    {
      id: "a-1",
      lesson_index: 1,
      status: "complete",
      failure_reason: null,
      retry_count: 0,
    },
    {
      id: "a-2",
      lesson_index: 2,
      status: "failed",
      failure_reason: "provider unavailable",
      retry_count: 1,
    },
  ],
  interview_message_count: null,
  superseded_by: null,
  recovery_view: "generation",
};

const SUMMARY_SUPERSEDED = {
  ...SUMMARY,
  status: "superseded",
  superseded_by: { brief_version: 2, blueprint_version: 2 },
  recovery_view: null,
};

function eventFixture(cursor: string, overrides: Record<string, unknown> = {}) {
  return {
    cursor,
    source: "trace",
    event_type: "model.generation_write_lesson",
    created_at: "2026-08-31T10:00:01+00:00",
    latency_ms: 1200,
    prompt_tokens: 800,
    completion_tokens: 600,
    cost_usd: 0.002,
    model: "fake:deepseek-chat",
    lesson_index: 1,
    payload: { prompt: { lesson: { lesson_index: 1 } }, response: { title: "第1课" } },
    ...overrides,
  };
}

const EVENTS_PAGE_1 = {
  run_id: "run-plan",
  events: [
    eventFixture("c1"),
    eventFixture("c2", { event_type: "run", source: "run_event", latency_ms: null, prompt_tokens: null, completion_tokens: null, cost_usd: null, model: null, lesson_index: null, payload: { status: "queued" } }),
    eventFixture("c3", { prompt_tokens: null, completion_tokens: null, cost_usd: null, model: null }),
  ],
  next_cursor: "c3",
};

const EVENTS_PAGE_2 = {
  run_id: "run-plan",
  events: [eventFixture("c4", { lesson_index: 2 })],
  next_cursor: null,
};

function defaultFetchMock(overrides: Record<string, unknown> = {}) {
  return vi.fn().mockImplementation((url: string) => {
    if (url.includes("/narrate/stream")) return Promise.resolve(sseResponse([
      'event: token\ndata: {"i":0,"t":"本次"}\n\n',
      'event: token\ndata: {"i":1,"t":"任务已完成。"}\n\n',
      'event: complete\ndata: {"i":2,"text":"本次任务已完成。"}\n\n',
    ]));
    if (url.includes("/narrate")) {
      return Promise.resolve(jsonResponse({ run_id: "run-plan", started: true }, 202));
    }
    if (url.includes("/run-plan/events")) {
      if (url.includes("after=c3")) return Promise.resolve(jsonResponse(EVENTS_PAGE_2));
      return Promise.resolve(jsonResponse(EVENTS_PAGE_1));
    }
    if (url.includes("/evidence/run-plan")) {
      return Promise.resolve(jsonResponse(overrides.summary ?? SUMMARY));
    }
    if (url.endsWith("/evidence")) {
      return Promise.resolve(jsonResponse(overrides.inventory ?? INVENTORY));
    }
    return Promise.resolve(jsonResponse({ runs: [], next_cursor: null }));
  });
}

describe("EvidencePanel", () => {
  it("renders the empty state and navigates to sources when no run exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ runs: [], next_cursor: null })),
    );
    const onNavigate = vi.fn();
    renderUi(<EvidencePanel projectId="p1" onNavigate={onNavigate} />);
    expect(await screen.findByText("还没有任何运行记录")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "前往「来源」开始" }));
    expect(onNavigate).toHaveBeenCalledWith("sources");
    vi.unstubAllGlobals();
  });

  it("shows the teacher summary first with usage, estimate labeling, and gaps", async () => {
    vi.stubGlobal("fetch", defaultFetchMock());
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText("教案生成")).toBeVisible();
    expect(screen.getByText(/绑定版本：教学简报 v1 · 单元蓝图 v1/)).toBeVisible();
    expect(screen.getAllByText(/模型调用 6\/20/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/估算/).length).toBeGreaterThan(0);
    expect(screen.getByText(/原因：provider unavailable/)).toBeVisible();
    expect(
      screen.getByRole("button", { name: "前往对应视图处理失败课程" }),
    ).toBeVisible();
    // Discovery rows surface interview status in teacher language.
    expect(screen.getByText("草稿就绪")).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("marks superseded runs with the newer version and no recovery action", async () => {
    vi.stubGlobal("fetch", defaultFetchMock({ summary: SUMMARY_SUPERSEDED }));
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText(/已被更新的已确认版本取代/)).toBeVisible();
    expect(screen.getByText(/简报 v2 · 蓝图 v2/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "前往对应视图处理失败课程" })).toBeNull();
    vi.unstubAllGlobals();
  });

  it("pages technical evidence, expands an inert payload, and copies it", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const fetchMock = defaultFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText("技术证据")).toBeVisible();
    const evidenceRows = await screen.findAllByRole("button", {
      name: /模型调用·撰写教案/,
    });
    expect(evidenceRows.length).toBeGreaterThan(0);
    expect(screen.getAllByText("未记录").length).toBeGreaterThan(0);
    expect(screen.getByText(/输入 800 \/ 输出 600/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "加载更多" }));
    expect(await screen.findByText("已全部加载。")).toBeVisible();
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("after=c3"),
        expect.anything(),
      ),
    );

    const firstRow = screen.getAllByRole("button", { name: /模型调用·撰写教案/ })[0];
    fireEvent.click(firstRow);
    expect(screen.getByText("复制原始数据")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "复制原始数据" }));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
    expect(JSON.parse(writeText.mock.calls[0][0] as string)).toHaveProperty("prompt");
    vi.unstubAllGlobals();
  });

  it("streams explanation narration with stop and maps quota exhaustion", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: { method?: string }) => {
      if (url.includes("/narrate/stream")) {
        return Promise.resolve(
          sseResponse(['event: token\ndata: {"i":0,"t":"讲解中……"}\n\n']),
        );
      }
      if (url.includes("/narrate")) {
        if (init?.method === "POST") {
          return Promise.resolve(
            jsonResponse(
              { error: { code: "QUOTA_EXCEEDED", message: "quota exceeded", correlation_id: null } },
              429,
            ),
          );
        }
        return Promise.resolve(jsonResponse({ stopped: true }));
      }
      return defaultFetchMock()(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText("技术证据")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "讲解本任务" }));
    expect(
      await screen.findByText(/已达工作区讲解次数上限/),
    ).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("issues no state-changing request other than narration", async () => {
    const fetchMock = defaultFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    await screen.findByText("技术证据");
    fireEvent.click(screen.getByRole("button", { name: "加载更多" }));
    await screen.findByText("已全部加载。");
    const methods = fetchMock.mock.calls.map(([, init]) => init?.method ?? "GET");
    expect(methods.every((method) => method === "GET")).toBe(true);
    vi.unstubAllGlobals();
  });

  it("defers technical evidence and narration below the desktop breakpoint", async () => {
    matchMediaMatches = false;
    vi.stubGlobal("fetch", defaultFetchMock());
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText(/绑定版本：教学简报 v1/)).toBeVisible();
    expect(screen.queryByText("技术证据")).toBeNull();
    expect(screen.queryByRole("button", { name: "讲解本任务" })).toBeNull();
    expect(screen.getByText(/查看技术证据或收听任务讲解/)).toBeVisible();
    vi.unstubAllGlobals();
  });
});

describe("WorkspaceView evidence tab", () => {
  it("navigates to the eighth 运行证据 view alongside the existing seven", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ runs: [], next_cursor: null })),
    );
    renderUi(<WorkspaceView projectId="p1" />);
    const tabs = screen.getAllByRole("button").map((button) => button.textContent);
    expect(tabs).toEqual(
      expect.arrayContaining(["来源", "需求访谈", "教学简报", "单元蓝图", "教案生成", "课件生成", "练习与答案", "运行证据"]),
    );
    fireEvent.click(screen.getByRole("button", { name: "运行证据" }));
    expect(await screen.findByText("还没有任何运行记录")).toBeVisible();
    vi.unstubAllGlobals();
  });
});
