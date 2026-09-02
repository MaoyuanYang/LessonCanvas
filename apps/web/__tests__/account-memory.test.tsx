import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AccountPage from "../app/(authed)/account/page";
import { MemoryProposalRegion } from "../components/memory-proposal-region";
import { MemoryContextRegion } from "../components/memory-context-region";
import { ApiClientError, type MemoryEffective } from "../lib/api";

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

function mockFetch(responses: Record<string, unknown>) {
  global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
    for (const [prefix, body] of Object.entries(responses)) {
      if (url.includes(prefix)) {
        return Promise.resolve({ ok: true, status: 200, json: async () => body });
      }
    }
    if (init?.method && init.method !== "GET") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => [] });
  });
}

const USAGE_BODY = {
  request_rate: { limit: 240, window_seconds: 60, used: 12, reset_at: "2026-09-01T12:01:00Z", retry_after_seconds: 34 },
  expensive_rate: { limit: 120, window_seconds: 60, used: 3, reset_at: "2026-09-01T12:01:00Z", retry_after_seconds: 34 },
  concurrent_generation_runs: { limit: 2, active: 1 },
  concurrent_sse_streams: { limit: 6, active: 0 },
  upload_daily_bytes: { limit: 209715200, used: 1048576, reset_at: "2026-09-02T00:00:00Z" },
  projects: { limit: 5, used: 2 },
  planning_runs: { limit: 50, used: 4 },
  evidence_narration: { limit: 50, used: 1 },
};

const OVERVIEW_EMPTY = {
  records: [],
  proposals: [],
  passes: [],
  quota: { used: 0, limit: 20 },
};

const OVERVIEW_LOADED = {
  records: [
    {
      id: "rec-1",
      category: "language_mode",
      content: "输出语言偏好保持「中英双语」",
      value: "bilingual",
      brief_version_id: "bv-1",
      blueprint_version_id: null,
      generation_run_id: null,
      created_at: "2026-09-02T10:00:00Z",
      has_project_disabled: true,
      conflicts_with_latest_brief: false,
    },
  ],
  proposals: [
    {
      id: "prop-1",
      category: "assessment_style",
      content: "测评风格延续「形成性评价为主」",
      value: null,
      status: "pending",
      trigger_kind: "brief_confirm",
      brief_version_id: "bv-2",
      blueprint_version_id: null,
      generation_run_id: null,
      created_at: "2026-09-02T11:00:00Z",
      decided_at: null,
    },
  ],
  passes: [],
  quota: { used: 1, limit: 20 },
};

const PROJECT_MEMORY = {
  effective: {
    applied: [
      { id: "rec-1", category: "language_mode", content: "输出语言偏好保持「中英双语」" },
    ],
    conflicts: [],
    budget_skipped: [{ id: "rec-2", category: "pacing_structure" }],
    project_disabled: [],
    injected_chars: 14,
  },
  records: [
    {
      id: "rec-1",
      category: "language_mode",
      content: "输出语言偏好保持「中英双语」",
      value: "bilingual",
      brief_version_id: "bv-1",
      blueprint_version_id: null,
      generation_run_id: null,
      created_at: "2026-09-02T10:00:00Z",
      project_enabled: true,
    },
  ],
};

// ---------------------------------------------------------------------------
// TS-020: account 教师记忆 section states
// ---------------------------------------------------------------------------

describe("account memory section (TS-020)", () => {
  it("renders the honest empty state before any confirmation", async () => {
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [], "/memory": OVERVIEW_EMPTY });
    renderUi(<AccountPage />);

    expect(await screen.findByText("教师记忆")).toBeVisible();
    expect(await screen.findByText("尚未确认任何教师记忆")).toBeVisible();
    expect(screen.getByText("0/20 条")).toBeVisible();
  });

  it("lists records with quota, project-disabled mark, and pending proposals", async () => {
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [], "/memory": OVERVIEW_LOADED });
    renderUi(<AccountPage />);

    expect(await screen.findByText("输出语言偏好保持「中英双语」")).toBeVisible();
    expect(screen.getByText("1/20 条")).toBeVisible();
    expect(screen.getByText("在部分项目已停用")).toBeVisible();
    expect(screen.getByText("待确认提议（1）")).toBeVisible();
    expect(screen.getByText("测评风格延续「形成性评价为主」")).toBeVisible();
    expect(screen.getByRole("button", { name: "确认记住" })).toBeVisible();
  });

  it("edit modal enforces the live 300-character counter", async () => {
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [], "/memory": OVERVIEW_LOADED });
    renderUi(<AccountPage />);

    fireEvent.click(await screen.findByRole("button", { name: "编辑" }));
    const textarea = await screen.findByLabelText("记忆内容");
    expect(textarea).toHaveValue("输出语言偏好保持「中英双语」");
    fireEvent.change(textarea, { target: { value: "长".repeat(301) } });
    expect(screen.getByText("301/300 字符")).toBeVisible();
    expect(screen.getByRole("button", { name: "保存" })).toBeDisabled();
    fireEvent.change(textarea, { target: { value: "偏好保持双语" } });
    expect(screen.getByRole("button", { name: "保存" })).toBeEnabled();
  });

  it("record deletion asks for explicit consequence confirmation", async () => {
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [], "/memory": OVERVIEW_LOADED });
    renderUi(<AccountPage />);

    fireEvent.click(await screen.findByRole("button", { name: "删除" }));
    expect(
      await screen.findByText(
        "删除后今后的运行将不再应用该记忆；历史运行记录保持不变，并随项目删除一并移除。",
      ),
    ).toBeVisible();
    const confirmButton = screen.getByRole("button", { name: "确认删除" });
    fireEvent.pointerDown(confirmButton);
    fireEvent.click(confirmButton);
    expect(
      await screen.findByText("记忆已删除；今后的运行将不再应用它。", {}, { timeout: 3000 }),
    ).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// TS-021: workspace proposal region states
// ---------------------------------------------------------------------------

describe("workspace proposal region (TS-021)", () => {
  it("renders nothing when there is no pending or failed pass", async () => {
    mockFetch({ "/memory": OVERVIEW_EMPTY });
    const { container } = renderUi(
      <MemoryProposalRegion kinds={["brief_confirm"]} />,
    );
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(container.querySelector("section")).toBeNull();
  });

  it("shows failed pass with retry and pending cards with edit-before-confirm", async () => {
    mockFetch({
      "/memory": {
        records: [],
        proposals: [
          {
            id: "prop-9",
            category: "language_mode",
            content: "输出语言偏好保持「全英文」",
            value: "english",
            status: "pending",
            trigger_kind: "brief_confirm",
            brief_version_id: "bv-9",
            blueprint_version_id: null,
            generation_run_id: null,
            created_at: "2026-09-02T12:00:00Z",
            decided_at: null,
          },
        ],
        passes: [
          {
            id: "pass-9",
            trigger_kind: "brief_confirm",
            trigger_id: "bv-9",
            status: "failed",
            proposal_count: 0,
            prompt_tokens: null,
            completion_tokens: null,
            cost_usd: null,
            created_at: "2026-09-02T12:00:00Z",
            completed_at: null,
          },
        ],
        quota: { used: 0, limit: 20 },
      },
    });
    renderUi(<MemoryProposalRegion kinds={["brief_confirm"]} />);

    expect(await screen.findByText("记忆提议")).toBeVisible();
    expect(screen.getByText("记忆提案生成失败，不影响当前流程。")).toBeVisible();
    expect(screen.getByRole("button", { name: "重试生成" })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "编辑后确认" }));
    const editor = await screen.findByLabelText("编辑记忆内容");
    expect(editor).toHaveValue("输出语言偏好保持「全英文」");
    expect(screen.getByText("13/300 字符")).toBeVisible();
  });

  it("filters proposals by the host panel's trigger kinds", async () => {
    mockFetch({
      "/memory": {
        records: [],
        proposals: [
          {
            id: "prop-run",
            category: "pacing_structure",
            content: "导入环节保持五分钟节奏",
            value: null,
            status: "pending",
            trigger_kind: "run_settled",
            brief_version_id: null,
            blueprint_version_id: null,
            generation_run_id: "run-1",
            created_at: "2026-09-02T12:00:00Z",
            decided_at: null,
          },
        ],
        passes: [],
        quota: { used: 0, limit: 20 },
      },
    });
    const { container } = renderUi(<MemoryProposalRegion kinds={["brief_confirm"]} />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(container.querySelector("section")).toBeNull();
  });

  it("surfaces the honest stale message when a proposal was decided concurrently", async () => {
    global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (url.includes("/confirm") && init?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 409,
          json: async () => ({
            error: { code: "STALE_VERSION", message: "proposal is not pending" },
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          url.includes("/memory")
            ? {
                records: [],
                proposals: [
                  {
                    id: "prop-s",
                    category: "language_mode",
                    content: "输出语言偏好保持「全英文」",
                    value: "english",
                    status: "pending",
                    trigger_kind: "brief_confirm",
                    brief_version_id: "bv-s",
                    blueprint_version_id: null,
                    generation_run_id: null,
                    created_at: "2026-09-02T12:00:00Z",
                    decided_at: null,
                  },
                ],
                passes: [],
                quota: { used: 0, limit: 20 },
              }
            : [],
      });
    });
    renderUi(<MemoryProposalRegion kinds={["brief_confirm"]} />);

    fireEvent.click(await screen.findByRole("button", { name: "确认记住" }));
    expect(await screen.findByText("该提议已被处理，已为你刷新列表。")).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// TS-022: evidence applied-context region
// ---------------------------------------------------------------------------

describe("evidence applied-context region (TS-022)", () => {
  const runMemory: MemoryEffective = {
    applied: [
      { id: "rec-1", category: "language_mode", content: "输出语言偏好保持「中英双语」" },
    ],
    conflicts: [
      {
        id: "rec-x",
        category: "language_mode",
        content: "偏好全英文输出",
        value: "english",
        brief_value: "bilingual",
      },
    ],
    budget_skipped: [{ id: "rec-2", category: "pacing_structure" }],
    project_disabled: [],
    injected_chars: 14,
  };

  it("renders applied records, conflicts, and budget skips honestly", async () => {
    mockFetch({
      "/projects/p1/memory": {
        ...PROJECT_MEMORY,
        records: [
          ...PROJECT_MEMORY.records,
          {
            id: "rec-x",
            category: "language_mode",
            content: "偏好全英文输出",
            value: "english",
            brief_version_id: null,
            blueprint_version_id: null,
            generation_run_id: null,
            created_at: "2026-09-02T10:00:00Z",
            project_enabled: true,
          },
          {
            id: "rec-2",
            category: "pacing_structure",
            content: "节奏偏好",
            value: null,
            brief_version_id: null,
            blueprint_version_id: null,
            generation_run_id: null,
            created_at: "2026-09-02T10:00:00Z",
            project_enabled: true,
          },
        ],
      },
    });
    renderUi(<MemoryContextRegion projectId="p1" runMemory={runMemory} />);

    expect(await screen.findByText("教师记忆（本项目）")).toBeVisible();
    expect(screen.getByText("与当前确认版本冲突，已按确认版本执行")).toBeVisible();
    expect(screen.getByText("未注入（超出记忆预算）")).toBeVisible();
    expect(screen.getByText(/当前运行的应用快照（1 条，共 14 字符）/)).toBeVisible();
    expect(screen.getByRole("link", { name: /账号与数据/ })).toHaveAttribute("href", "/account");
  });

  it("offers the project-scoped enable/disable toggle", async () => {
    mockFetch({ "/projects/p1/memory": PROJECT_MEMORY });
    renderUi(<MemoryContextRegion projectId="p1" runMemory={null} />);

    const toggle = await screen.findByLabelText("在本项目停用该记忆");
    expect(toggle).toBeChecked();
    fireEvent.click(toggle);
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/projects/p1/memory/records/rec-1/override"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("explains honestly when a run applied no memory", async () => {
    mockFetch({ "/projects/p1/memory": PROJECT_MEMORY });
    renderUi(
      <MemoryContextRegion
        projectId="p1"
        runMemory={{
          applied: [],
          conflicts: [],
          budget_skipped: [],
          project_disabled: PROJECT_MEMORY.effective.applied as MemoryEffective["project_disabled"],
          injected_chars: 0,
        }}
      />,
    );
    expect(
      await screen.findByText(/本次运行未应用教师记忆（存在被冲突、预算或项目停用跳过的记录，见上方标注）。/),
    ).toBeVisible();
  });
});

// Client error class sanity used above.
expect.extend({
  toBeApiClientError(received: unknown) {
    return {
      pass: received instanceof ApiClientError,
      message: () => "expected ApiClientError",
    };
  },
});
