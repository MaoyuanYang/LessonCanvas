import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DeckPanel } from "../components/deck-panel";

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

function notFoundResponse(what: string) {
  return {
    ok: false,
    status: 404,
    json: async () => ({
      error: { code: "NOT_FOUND", message: `${what} not found`, correlation_id: null },
    }),
  };
}

function deckSnapshotFixture(status: string, overrides: Record<string, unknown> = {}) {
  const complete = status === "complete";
  return {
    run_id: "deck-run-1",
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
        id: "deck-1",
        lesson_index: 1,
        status: "complete",
        language_mode: "中英双语",
        slide_count: 8,
        failure_reason: null,
        retry_count: 0,
        download_url: "/slide-decks/1/download",
      },
      {
        id: "deck-2",
        lesson_index: 2,
        status: complete ? "complete" : "failed",
        language_mode: "中英双语",
        slide_count: complete ? 9 : null,
        failure_reason: complete ? null : "too many slides: 17 > 16",
        retry_count: 1,
        download_url: complete ? "/slide-decks/2/download" : null,
      },
      {
        id: "deck-3",
        lesson_index: 3,
        status: complete ? "complete" : "pending",
        language_mode: "中英双语",
        slide_count: complete ? 8 : null,
        failure_reason: null,
        retry_count: 0,
        download_url: complete ? "/slide-decks/3/download" : null,
      },
    ],
    ...overrides,
  };
}

function planSnapshotFixture(status: string) {
  return {
    run_id: "plan-run-1",
    status,
    brief_version: 1,
    blueprint_version: 1,
    language_mode: "中英双语",
    model_calls: 6,
    model_call_cap: 20,
    complete_count: status === "complete" ? 3 : 1,
    total_count: 3,
    artifacts: [],
  };
}

describe("DeckPanel", () => {
  it("names the lesson-plan prerequisite when no plan run exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/decks/generation")) {
          return Promise.resolve(notFoundResponse("deck generation run"));
        }
        return Promise.resolve(notFoundResponse("generation run"));
      }),
    );
    renderUi(<DeckPanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText(/需要先确认单元蓝图并生成全部教案/)).toBeVisible();
    expect(screen.getByRole("button", { name: "前往「教案生成」" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "开始生成课件" })).toBeNull();
    vi.unstubAllGlobals();
  });

  it("names the incomplete-plan prerequisite when plans are not finished", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/decks/generation")) {
          return Promise.resolve(notFoundResponse("deck generation run"));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("partial_failure")));
      }),
    );
    renderUi(<DeckPanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText(/教案任务尚未全部完成/)).toBeVisible();
    expect(screen.getByRole("button", { name: "前往「教案生成」" })).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("shows the start surface with bound versions when plans are complete", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/decks/generation")) {
          return Promise.resolve(notFoundResponse("deck generation run"));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
      }),
    );
    renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText("开始生成课件")).toBeVisible();
    expect(screen.getByText(/绑定版本：教学简报 v1 · 单元蓝图 v1/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("renders generating progress with per-lesson deck states and structure summary", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation((url: string) => {
        if (url.includes("/decks/generation/events")) {
          return Promise.resolve(
            new Response("", { status: 200, headers: { "content-type": "text/event-stream" } }),
          );
        }
        if (url.includes("/decks/generation")) {
          return Promise.resolve(jsonResponse(deckSnapshotFixture("generating")));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
      });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText(/模型调用 2\/20/, {}, { timeout: 5000 })).toBeVisible();
    expect(screen.getByText("第 1 课")).toBeVisible();
    expect(screen.getByText("共 8 页")).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("shows the complete outcome with per-lesson slide counts and downloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(deckSnapshotFixture("complete"))),
    );
    renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText(/全部 3 课课件已生成/)).toBeVisible();
    expect(screen.getAllByText("下载 PPTX").length).toBe(3);
    expect(screen.getAllByText(/共 \d+ 页/).length).toBe(3);
    vi.unstubAllGlobals();
  });

  it("shows partial failure reasons and a scoped deck resume action", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation((url: string) => {
        if (url.includes("/decks/generation/resume")) {
          return Promise.resolve(jsonResponse({ status: "queued" }));
        }
        return Promise.resolve(jsonResponse(deckSnapshotFixture("partial_failure")));
      });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText(/部分课程失败/)).toBeVisible();
    expect(screen.getByText(/原因：too many slides/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "恢复未完成课件" }));
    expect(screen.getByText("恢复课件生成")).toBeVisible();
    expect(screen.getByText(/已完成课件不会重跑/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "确认恢复" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/decks/generation/resume"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    vi.unstubAllGlobals();
  });

  it("shows the capped and superseded banners with deck wording", async () => {
    const dispatch = (status: string) =>
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/decks/generation")) {
          return Promise.resolve(jsonResponse(deckSnapshotFixture(status)));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
      });
    vi.stubGlobal("fetch", dispatch("capped_failure"));
    const { unmount } = renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText(/已达本任务模型调用上限/)).toBeVisible();
    expect(screen.getByText(/已完成课件仍可下载/)).toBeVisible();
    unmount();

    vi.stubGlobal("fetch", dispatch("superseded"));
    renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText(/已被更新的已确认版本取代/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("hides start/resume deck actions on small screens with a desktop-required notice", async () => {
    matchMediaMatches = false;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(deckSnapshotFixture("partial_failure"))),
    );
    renderUi(<DeckPanel projectId="p1" />);
    expect(await screen.findByText(/部分课程失败/)).toBeVisible();
    expect(screen.getByText(/恢复失败课件/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "恢复未完成课件" })).toBeNull();
    vi.unstubAllGlobals();
  });
});
