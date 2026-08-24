import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectsView from "../app/(authed)/projects/projects-view";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
  useUser: () => ({ isSignedIn: true }),
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

function renderView(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal("fetch", fetchMock);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectsView />
    </QueryClientProvider>,
  );
}

function projectsResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

describe("ProjectsView", () => {
  it("shows empty state when the teacher has no projects", async () => {
    renderView(vi.fn().mockReturnValue(projectsResponse([])));
    expect(await screen.findByText("还没有备课项目")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建备课项目" })).toBeInTheDocument();
  });

  it("lists owned projects with status", async () => {
    const fetchMock = vi.fn().mockReturnValue(
      projectsResponse([
        {
          id: "p1",
          name: "外研社必修一 Unit 3",
          unit_hints: null,
          status: "active",
          created_at: "2026-08-24T00:00:00Z",
          updated_at: "2026-08-24T00:00:00Z",
        },
      ]),
    );
    renderView(fetchMock);
    expect(await screen.findByText("外研社必修一 Unit 3")).toBeInTheDocument();
    expect(screen.getByText("进行中")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects"),
      expect.objectContaining({ method: "GET" }),
    );
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.authorization).toBe("Bearer test-token");
  });

  it("shows a named error with retry for quota failures", async () => {
    renderView(
      vi.fn().mockReturnValue(
        projectsResponse(
          {
            error: {
              code: "QUOTA_EXCEEDED",
              message: "limit",
              correlation_id: "corr-1",
              details: {},
            },
          },
          429,
        ),
      ),
    );
    expect(await screen.findByText(/已达到项目数量上限/)).toBeInTheDocument();
    expect(screen.getByText("参考编号：corr-1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });

  it("gates structured actions behind the desktop boundary", async () => {
    matchMediaMatches = false;
    renderView(vi.fn().mockReturnValue(projectsResponse([])));
    expect(await screen.findByText(/需要在桌面端（宽度不小于 1024px）完成/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新建备课项目" })).toBeNull();
  });

  it("creates a project and refreshes the list", async () => {
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(projectsResponse([]))
      .mockReturnValueOnce(
        projectsResponse({
          id: "p2",
          name: "新项目",
          unit_hints: null,
          status: "active",
          created_at: "2026-08-24T00:00:00Z",
          updated_at: "2026-08-24T00:00:00Z",
        }),
      )
      .mockReturnValue(
        projectsResponse([
          {
            id: "p2",
            name: "新项目",
            unit_hints: null,
            status: "active",
            created_at: "2026-08-24T00:00:00Z",
            updated_at: "2026-08-24T00:00:00Z",
          },
        ]),
      );
    renderView(fetchMock);
    await screen.findByText("还没有备课项目");

    await act(async () => {
      screen.getByRole("button", { name: "新建备课项目" }).click();
    });
    const input = await screen.findByLabelText(/项目名称/);
    await act(async () => {
      input.focus();
    });
    const form = screen.getByRole("button", { name: "创建项目" }).closest("form");
    await act(async () => {
      const field = screen.getByLabelText(/项目名称/);
      (field as HTMLInputElement).value = "新项目";
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    expect(await screen.findByText("新项目")).toBeInTheDocument();
    const createCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/projects") && init.method === "POST",
    );
    expect(createCall).toBeTruthy();
  });
});
