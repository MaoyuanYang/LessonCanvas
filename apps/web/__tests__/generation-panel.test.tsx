import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GenerationPanel } from "../components/generation-panel";

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

function notFoundResponse() {
  return {
    ok: false,
    status: 404,
    json: async () => ({
      error: { code: "NOT_FOUND", message: "generation run not found", correlation_id: null },
    }),
  };
}

function snapshotFixture(status: string, overrides: Record<string, unknown> = {}) {
  const complete = status === "complete";
  return {
    run_id: "run-1",
    status,
    brief_version: 1,
    blueprint_version: 1,
    language_mode: "中英双语",
    model_calls: complete ? 6 : 2,
    model_call_cap: 20,
    complete_count: complete ? 3 : 1,
    total_count: 3,
    artifacts: [
      {
        id: "art-1",
        lesson_index: 1,
        status: "complete",
        language_mode: "中英双语",
        failure_reason: null,
        retry_count: 0,
        download_url: "/download/1",
      },
      {
        id: "art-2",
        lesson_index: 2,
        status: complete ? "complete" : "failed",
        language_mode: "中英双语",
        failure_reason: complete ? null : "provider unavailable",
        retry_count: 1,
        download_url: complete ? "/download/2" : null,
      },
      {
        id: "art-3",
        lesson_index: 3,
        status: complete ? "complete" : "pending",
        language_mode: "中英双语",
        failure_reason: null,
        retry_count: 0,
        download_url: complete ? "/download/3" : null,
      },
    ],
    ...overrides,
  };
}

describe("GenerationPanel", () => {
  it("renders the start surface with gate message when no run exists", async () => {
    const fetchMock = vi.fn().mockResolvedValue(notFoundResponse());
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText("开始生成")).toBeVisible();
    expect(screen.getByText(/确认单元蓝图后即可开始生成/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("renders queued/generating progress with per-lesson states and cap usage", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(snapshotFixture("generating")))
      .mockResolvedValue(
        new Response("", { status: 200, headers: { "content-type": "text/event-stream" } }),
      );
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText(/模型调用 2\/20/, {}, { timeout: 5000 })).toBeVisible();
    expect(screen.getByText("第 1 课")).toBeVisible();
    expect(screen.getAllByText(/起草中|渲染中|校验中|等待中|已完成|失败/).length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  });

  it("shows the complete outcome with download actions per lesson", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(snapshotFixture("complete")));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText(/全部 3 课教案已生成/)).toBeVisible();
    expect(screen.getAllByText("下载 DOCX").length).toBe(3);
    vi.unstubAllGlobals();
  });

  it("shows partial failure reasons and a scoped resume action", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(snapshotFixture("partial_failure")));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText(/部分课程失败/)).toBeVisible();
    expect(screen.getByText(/原因：provider unavailable/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "恢复未完成课程" }));
    expect(screen.getByText("恢复生成")).toBeVisible();
    expect(screen.getByText(/已完成教案不会重跑/)).toBeVisible();

    const resumeCall = { status: "queued" };
    fetchMock.mockResolvedValueOnce(jsonResponse(resumeCall));
    fireEvent.click(screen.getByRole("button", { name: "确认恢复" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/generation/resume"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    vi.unstubAllGlobals();
  });

  it("shows the capped and superseded banners", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(jsonResponse(snapshotFixture("capped_failure"))),
    );
    const { unmount } = renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText(/已达本任务模型调用上限/)).toBeVisible();
    unmount();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(jsonResponse(snapshotFixture("superseded"))),
    );
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText(/已被更新的已确认版本取代/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("hides start/resume actions on small screens with a desktop-required notice", async () => {
    matchMediaMatches = false;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(snapshotFixture("partial_failure"))));
    renderUi(<GenerationPanel projectId="p1" />);
    expect(await screen.findByText(/部分课程失败/)).toBeVisible();
    expect(screen.getByText(/恢复失败课程/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "恢复未完成课程" })).toBeNull();
    vi.unstubAllGlobals();
  });
});
