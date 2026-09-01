import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AccountPage from "../app/(authed)/account/page";
import { SourcesPanel } from "../components/sources-panel";
import { ApiClientError, guardrailFeedback } from "../lib/api";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
  useUser: () => ({
    user: { emailAddresses: [{ emailAddress: "teacher@example.com" }] },
  }),
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

function mockFetch(responses: Record<string, unknown>) {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    for (const [prefix, body] of Object.entries(responses)) {
      if (url.includes(prefix)) {
        return Promise.resolve({ ok: true, status: 200, json: async () => body });
      }
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => [] });
  });
}

describe("account guardrails surface", () => {
  it("renders every usage limit with current consumption", async () => {
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [] });
    renderUi(<AccountPage />);

    expect(await screen.findByText("使用与限额")).toBeVisible();
    expect(await screen.findByText("12/240（本窗口）")).toBeVisible();
    expect(screen.getByText("1/2")).toBeVisible(); // concurrent generation runs
    expect(screen.getByText("0/6")).toBeVisible(); // concurrent streams
    expect(screen.getByText("1.0 MB/200.0 MB")).toBeVisible();
    expect(screen.getByText("2/5")).toBeVisible(); // projects
    expect(screen.getByText("4/50")).toBeVisible(); // planning runs
  });

  it("shows the operator-access disclosure including the retained-ledger rule", async () => {
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [] });
    renderUi(<AccountPage />);

    expect(await screen.findByText("隐私与运营访问")).toBeVisible();
    expect(screen.getByText(/没有运营人员账号/)).toBeVisible();
    expect(screen.getByText(/极简安全台账/)).toBeVisible();
    expect(screen.getByText(/托管服务商的管理控制台/)).toBeVisible();
  });

  it("discloses the audit list progressively and lists events", async () => {
    mockFetch({
      "/account/usage": USAGE_BODY,
      "/account/audit": {
        events: [
          { action: "download.lesson_plan", target_type: "lesson_plan", target_id: "a1", created_at: "2026-09-01T10:00:00Z" },
          { action: "project.deleted", target_type: "project", target_id: "p1", created_at: "2026-09-01T09:00:00Z" },
        ],
        next_before: null,
      },
    });
    renderUi(<AccountPage />);

    const toggle = await screen.findByRole("button", { name: "展开审计记录" });
    expect(screen.queryByText("download.lesson_plan")).toBeNull(); // collapsed by default
    fireEvent.click(toggle);
    expect(await screen.findByText("download.lesson_plan")).toBeVisible();
    expect(screen.getByText("project.deleted")).toBeVisible();
  });

  it("defers the audit list below the desktop boundary", async () => {
    matchMediaMatches = false;
    mockFetch({ "/account/usage": USAGE_BODY, "/account/deletion-status": [] });
    renderUi(<AccountPage />);

    expect(await screen.findByText("敏感操作审计")).toBeVisible();
    expect(screen.getAllByText(/需要在桌面端/).length).toBeGreaterThanOrEqual(2); // audit + deletion
    expect(screen.queryByRole("button", { name: "展开审计记录" })).toBeNull();
  });
});

describe("guardrail feedback mapping", () => {
  it("names the rate limit with automatic recovery", () => {
    const error = new ApiClientError(
      "QUOTA_EXCEEDED",
      "request rate limit reached",
      429,
      null,
      { limit: "general", limit_value: 240, retry_after_seconds: 30 },
    );
    const message = guardrailFeedback(error);
    expect(message).toContain("请求速率");
    expect(message).toContain("自动恢复");
  });

  it("names the daily upload volume limit", () => {
    const error = new ApiClientError("QUOTA_EXCEEDED", "limit", 429, null, {
      limit: "upload_daily",
      limit_value: 209715200,
    });
    expect(guardrailFeedback(error)).toContain("每日上传量");
  });

  it("points admission rejection at the active runs", () => {
    const error = new ApiClientError("RUN_ADMISSION", "limit", 409, null, {
      limit: 2,
      active_run_ids: ["r1", "r2"],
    });
    const message = guardrailFeedback(error);
    expect(message).toContain("2 个生成运行进行中");
    expect(message).toContain("最多 2 个");
  });

  it("returns null for non-guardrail errors", () => {
    expect(guardrailFeedback(new Error("boom"))).toBeNull();
    expect(
      guardrailFeedback(new ApiClientError("NOT_FOUND", "x", 404, null, {})),
    ).toBeNull();
  });
});

describe("source delete-failure state", () => {
  it("shows the repairable delete-failed hint", async () => {
    mockFetch({
      "/sources": [
        {
          id: "s1",
          filename: "notes.txt",
          content_type: "text/plain",
          size_bytes: 8,
          status: "delete_failed",
          rejection_code: null,
          rejection_message: null,
          rights_acknowledged: true,
          created_at: "2026-09-01T08:00:00Z",
          updated_at: "2026-09-01T08:05:00Z",
        },
      ],
    });
    renderUi(<SourcesPanel projectId="p1" />);

    expect(await screen.findByText("删除未完成")).toBeVisible();
    expect(screen.getByText(/再次点击「删除」即可修复/)).toBeVisible();
    expect(screen.getByRole("button", { name: "删除" })).toBeEnabled();
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  });
});
