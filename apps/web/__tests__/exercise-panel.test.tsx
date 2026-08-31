import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExercisePanel } from "../components/exercise-panel";

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

function exerciseSnapshotFixture(status: string, overrides: Record<string, unknown> = {}) {
  const complete = status === "complete";
  return {
    run_id: "exercise-run-1",
    status,
    brief_version: 1,
    blueprint_version: 1,
    language_mode: "中英双语",
    difficulty: "consolidation",
    model_calls: complete ? 6 : 2,
    model_call_cap: 20,
    complete_count: complete ? 3 : 1,
    total_count: 3,
    artifacts: [
      {
        id: "ex-1",
        lesson_index: 1,
        status: "complete",
        language_mode: "中英双语",
        category_count: 4,
        item_count: 9,
        failure_reason: null,
        retry_count: 0,
        exercise_download_url: "/exercises/1/download?file=exercise",
        answer_download_url: "/exercises/1/download?file=answer",
      },
      {
        id: "ex-2",
        lesson_index: 2,
        status: complete ? "complete" : "failed",
        language_mode: "中英双语",
        category_count: complete ? 4 : null,
        item_count: complete ? 8 : null,
        failure_reason: complete ? null : "empty answer entries: [2]",
        retry_count: 1,
        exercise_download_url: complete ? "/exercises/2/download?file=exercise" : null,
        answer_download_url: complete ? "/exercises/2/download?file=answer" : null,
      },
      {
        id: "ex-3",
        lesson_index: 3,
        status: complete ? "complete" : "pending",
        language_mode: "中英双语",
        category_count: complete ? 3 : null,
        item_count: complete ? 7 : null,
        failure_reason: null,
        retry_count: 0,
        exercise_download_url: complete ? "/exercises/3/download?file=exercise" : null,
        answer_download_url: complete ? "/exercises/3/download?file=answer" : null,
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

describe("ExercisePanel", () => {
  it("names the lesson-plan prerequisite when no plan run exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/exercises/generation")) {
          return Promise.resolve(notFoundResponse("exercise generation run"));
        }
        return Promise.resolve(notFoundResponse("generation run"));
      }),
    );
    renderUi(<ExercisePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText(/需要先确认单元蓝图并生成全部教案/)).toBeVisible();
    expect(screen.getByRole("button", { name: "前往「教案生成」" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "开始生成练习与答案" })).toBeNull();
    vi.unstubAllGlobals();
  });

  it("names the incomplete-plan prerequisite when plans are not finished", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/exercises/generation")) {
          return Promise.resolve(notFoundResponse("exercise generation run"));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("partial_failure")));
      }),
    );
    renderUi(<ExercisePanel projectId="p1" onNavigate={() => {}} />);
    expect(await screen.findByText(/教案任务尚未全部完成/)).toBeVisible();
    expect(screen.getByRole("button", { name: "前往「教案生成」" })).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("shows the start surface with bound versions and a required tier group without default", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/exercises/generation")) {
          return Promise.resolve(notFoundResponse("exercise generation run"));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
      }),
    );
    renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText("开始生成练习与答案")).toBeVisible();
    expect(screen.getByText(/绑定版本：教学简报 v1 · 单元蓝图 v1/)).toBeVisible();
    const legend = screen.getByText("难度档位（必选）");
    expect(legend).toBeVisible();
    const radios = screen
      .getAllByRole("radio")
      .filter((radio) => (radio as HTMLInputElement).name === "exercise-difficulty");
    expect(radios.length).toBe(3);
    expect(radios.every((radio) => (radio as HTMLInputElement).checked === false)).toBe(true);
    expect(screen.getByText("基础")).toBeVisible();
    expect(screen.getByText("巩固")).toBeVisible();
    expect(screen.getByText("进阶")).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("blocks submit without a tier and posts the chosen difficulty on start", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/exercises/generation/start")) {
        return Promise.resolve(jsonResponse(exerciseSnapshotFixture("queued")));
      }
      if (url.includes("/exercises/generation")) {
        return Promise.resolve(notFoundResponse("exercise generation run"));
      }
      return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<ExercisePanel projectId="p1" />);

    const startButton = await screen.findByText("开始生成练习与答案");
    fireEvent.click(startButton);
    expect(await screen.findByText(/请先选择难度档位/)).toBeVisible();

    fireEvent.click(screen.getByLabelText(/基础/));
    fireEvent.click(startButton);
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/exercises/generation/start"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ difficulty: "foundation" }),
        }),
      ),
    );
    vi.unstubAllGlobals();
  });

  it("renders generating progress with per-lesson pair states and pair summary", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/exercises/generation/events")) {
        return Promise.resolve(
          new Response("", { status: 200, headers: { "content-type": "text/event-stream" } }),
        );
      }
      if (url.includes("/exercises/generation")) {
        return Promise.resolve(jsonResponse(exerciseSnapshotFixture("generating")));
      }
      return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText(/模型调用 2\/20/, {}, { timeout: 5000 })).toBeVisible();
    expect(screen.getByText(/难度档位：巩固/)).toBeVisible();
    expect(screen.getByText("第 1 课")).toBeVisible();
    expect(screen.getByText("共 9 题 · 4 类")).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("shows the complete outcome with dual downloads and recorded tier", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(exerciseSnapshotFixture("complete"))),
    );
    renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText(/全部 3 课练习已生成/)).toBeVisible();
    expect(screen.getAllByRole("button", { name: "下载练习 DOCX" }).length).toBe(3);
    expect(screen.getAllByRole("button", { name: "下载答案 DOCX" }).length).toBe(3);
    expect(screen.getAllByText(/共 \d+ 题 · \d+ 类/).length).toBe(3);
    expect(screen.getByText(/难度档位：巩固/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("shows partial failure reasons and a scoped exercise resume action", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/exercises/generation/resume")) {
        return Promise.resolve(jsonResponse({ status: "queued" }));
      }
      return Promise.resolve(jsonResponse(exerciseSnapshotFixture("partial_failure")));
    });
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText(/部分课程失败/)).toBeVisible();
    expect(screen.getByText(/原因：empty answer entries/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "恢复未完成练习" }));
    expect(screen.getByText("恢复练习与答案生成")).toBeVisible();
    expect(screen.getByText(/已完成配对不会重跑/)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "确认恢复" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/exercises/generation/resume"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    vi.unstubAllGlobals();
  });

  it("shows the capped and superseded banners with exercise wording", async () => {
    const dispatch = (status: string) =>
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/exercises/generation")) {
          return Promise.resolve(jsonResponse(exerciseSnapshotFixture(status)));
        }
        return Promise.resolve(jsonResponse(planSnapshotFixture("complete")));
      });
    vi.stubGlobal("fetch", dispatch("capped_failure"));
    const { unmount } = renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText(/已达本任务模型调用上限/)).toBeVisible();
    expect(screen.getByText(/已完成练习仍可下载/)).toBeVisible();
    unmount();

    vi.stubGlobal("fetch", dispatch("superseded"));
    renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText(/已被更新的已确认版本取代/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it("hides start/resume exercise actions on small screens with a desktop-required notice", async () => {
    matchMediaMatches = false;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(exerciseSnapshotFixture("partial_failure"))),
    );
    renderUi(<ExercisePanel projectId="p1" />);
    expect(await screen.findByText(/部分课程失败/)).toBeVisible();
    expect(screen.getByText(/恢复失败练习/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "恢复未完成练习" })).toBeNull();
    vi.unstubAllGlobals();
  });
});
