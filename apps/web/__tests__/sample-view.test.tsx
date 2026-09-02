import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SourcesPanel } from "../components/sources-panel";
import { ApiClientError } from "../lib/api";
import SampleView from "../app/(authed)/sample/sample-view";

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

vi.mock("@/app/(authed)/projects/[projectId]/workspace-view", () => ({
  default: ({ projectId, readOnly }: { projectId: string; readOnly?: boolean }) => (
    <div data-testid="workspace-view" data-project-id={projectId} data-read-only={readOnly ? "true" : "false"} />
  ),
}));

const getSampleProject = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getSampleProject: (...args: unknown[]) => getSampleProject(...args) };
});

describe("SampleView", () => {
  it("shows skeleton rows while loading", () => {
    getSampleProject.mockReturnValue(new Promise(() => {}));
    renderUi(<SampleView />);
    expect(screen.getByText("示例项目")).toBeInTheDocument();
    expect(document.querySelector('[aria-hidden="true"] .animate-pulse')).not.toBeNull();
  });

  it("renders read-only notice and workspace with sample project id once loaded", async () => {
    getSampleProject.mockResolvedValue({ project_id: "sample-1", name: "示例" });
    renderUi(<SampleView />);
    expect(await screen.findByText("示例项目为只读演示，不会影响任何任务状态。")).toBeInTheDocument();
    const workspace = screen.getByTestId("workspace-view");
    expect(workspace).toHaveAttribute("data-project-id", "sample-1");
    expect(workspace).toHaveAttribute("data-read-only", "true");
  });

  it("renders sample-missing empty state with retry when sample is NOT_FOUND", async () => {
    getSampleProject.mockRejectedValue(
      new ApiClientError("NOT_FOUND", "sample missing", 404, null, {}),
    );
    renderUi(<SampleView />);
    expect(await screen.findByText("示例项目暂不可用")).toBeInTheDocument();
    expect(screen.getByText(/请稍后重试，或联系部署者重新种入示例/)).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: "重试" });
    await act(async () => {
      retry.click();
    });
    expect(getSampleProject).toHaveBeenCalledTimes(2);
  });

  it("renders an honest error alert for other failures", async () => {
    getSampleProject.mockRejectedValue(
      new ApiClientError("UNEXPECTED", "network unavailable", 0, "corr-1", {}),
    );
    renderUi(<SampleView />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/操作失败（UNEXPECTED）/)).toBeInTheDocument();
    expect(screen.getByText("参考编号：corr-1")).toBeInTheDocument();
  });
});

describe("SourcesPanel readOnly", () => {
  const SOURCES = [
    {
      id: "s1",
      filename: "unit.pdf",
      content_type: "application/pdf",
      size_bytes: 10,
      status: "active",
      rejection_code: null,
      rejection_message: null,
      rights_acknowledged: true,
      created_at: "2026-08-24T00:00:00Z",
      updated_at: "2026-08-24T00:00:00Z",
    },
  ];

  it("hides upload form and delete in readOnly while keeping data rendering", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => SOURCES,
      }),
    );
    renderUi(<SourcesPanel projectId="sample-1" readOnly />);
    expect(await screen.findByText("unit.pdf")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "上传" })).toBeNull();
    expect(screen.queryByRole("button", { name: "删除" })).toBeNull();
  });

  it("keeps the upload form when readOnly is absent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => SOURCES,
      }),
    );
    renderUi(<SourcesPanel projectId="p1" />);
    expect(await screen.findByText("unit.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上传" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除" })).toBeInTheDocument();
  });
});
