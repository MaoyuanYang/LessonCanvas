import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BriefPanel } from "../components/brief-panel";
import { DiscoveryPanel } from "../components/discovery-panel";
import { SourcesPanel } from "../components/sources-panel";

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

const BRIEF_MISSING = {
  draft_revision: 1,
  fields: {
    unit_theme: { value: "环保", grounding: "teacher-stated", unresolved: false },
    lesson_count: { value: null, grounding: null, unresolved: true },
  },
  confirmed_version: null,
  confirmed_fields: null,
};

const BRIEF_COMPLETE = {
  ...BRIEF_MISSING,
  fields: {
    unit_theme: { value: "环保", grounding: "teacher-stated", unresolved: false },
    lesson_count: { value: "6", grounding: "teacher-stated", unresolved: false },
  },
};

describe("BriefPanel", () => {
  it("marks unresolved fields and gates confirmation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(jsonResponse(BRIEF_MISSING)));
    renderUi(<BriefPanel projectId="p1" />);
    expect(await screen.findByText("待补充")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认简报" })).toBeDisabled();
  });

  it("enables confirmation when all fields present", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(jsonResponse(BRIEF_COMPLETE)));
    renderUi(<BriefPanel projectId="p1" />);
    const badges = await screen.findAllByText("教师陈述");
    expect(badges.length).toBe(2);
    expect(screen.getByRole("button", { name: "确认简报" })).toBeEnabled();
  });

  it("shows stale banner on version conflict", async () => {
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(jsonResponse(BRIEF_COMPLETE))
      .mockReturnValueOnce(
        jsonResponse(
          { error: { code: "STALE_VERSION", message: "stale", correlation_id: null, details: {} } },
          409,
        ),
      )
      .mockReturnValue(jsonResponse(BRIEF_COMPLETE));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<BriefPanel projectId="p1" />);
    await screen.findAllByText("教师陈述");
    await act(async () => {
      screen.getByRole("button", { name: "保存修订" }).click();
    });
    expect(await screen.findByText(/存在更新的草稿修订/)).toBeInTheDocument();
  });
});

describe("DiscoveryPanel", () => {
  it("renders questions and submits answers", async () => {
    const status = {
      run_id: "r1",
      status: "questioning",
      round_count: 1,
      questions: [{ field: "lesson_count", question: "课时数是多少？" }],
      draft: null,
    };
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(jsonResponse(status))
      .mockReturnValue(jsonResponse({ ...status, questions: [] }));
    vi.stubGlobal("fetch", fetchMock);
    renderUi(<DiscoveryPanel projectId="p1" />);
    expect(await screen.findByText(/课时数是多少？/)).toBeInTheDocument();
    const textarea = screen.getByLabelText(/课时数是多少？/);
    await act(async () => {
      textarea.focus();
    });
    (textarea as HTMLTextAreaElement).value = "6";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    await act(async () => {
      screen.getByRole("button", { name: "提交回答" }).click();
    });
    const answersCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).includes("/discovery/answers") && init?.method === "POST",
    );
    expect(answersCall).toBeTruthy();
  });
});

describe("SourcesPanel", () => {
  it("shows rejection reasons and gates upload on small screens", async () => {
    matchMediaMatches = false;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(
        jsonResponse([
          {
            id: "s1",
            filename: "grades.txt",
            content_type: "text/plain",
            size_bytes: 10,
            status: "rejected",
            rejection_code: "STUDENT_DATA",
            rejection_message: "包含学生身份信息",
            rights_acknowledged: true,
            created_at: "2026-08-24T00:00:00Z",
            updated_at: "2026-08-24T00:00:00Z",
          },
        ]),
      ),
    );
    renderUi(<SourcesPanel projectId="p1" />);
    expect(await screen.findByText("包含学生身份信息")).toBeInTheDocument();
    expect(screen.getByText(/需要在桌面端/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "上传" })).toBeNull();
  });
});
