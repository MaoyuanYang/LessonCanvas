// F014 TS-021..TS-024 (test-design.md): citation chips, artifact grounding
// states, sources chunk expansion, evidence retrieval rows.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ArtifactProgressList } from "../components/artifact-run";
import { CitationChipGroup } from "../components/citation-chip";
import { EvidencePanel } from "../components/evidence-panel";
import { SourcesPanel } from "../components/sources-panel";
import type { BlueprintCitation } from "../lib/api";

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

const CHUNK_CITATION: BlueprintCitation = {
  type: "source",
  source_id: "src-1",
  filename: "notes.txt",
  chunk_position: 0,
  text_sha256: "a1b2c3d4e5f6".padEnd(64, "0"),
  excerpt: "本单元围绕自然灾害展开阅读与表达训练。",
};

// TS-021: expandable source-chunk chip and static standards chip.

describe("CitationChipGroup (TS-021)", () => {
  it("expands a chunk citation to filename, position, excerpt, and hash prefix", () => {
    renderUi(
      <CitationChipGroup citations={[CHUNK_CITATION]} />,
    );
    const chip = screen.getByRole("button", { name: "来源：notes.txt · 第0段" });
    expect(chip.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(chip);
    expect(chip.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("notes.txt · 第0段")).toBeVisible();
    expect(screen.getByText("本单元围绕自然灾害展开阅读与表达训练。")).toBeVisible();
    expect(screen.getByText("内容哈希：a1b2c3d4")).toBeVisible();
  });

  it("renders the standards variant statically without expansion", () => {
    renderUi(
      <CitationChipGroup
        citations={[{ type: "standards", section_id: "std-05", snapshot_version: "2026-08-24-v1" }]}
      />,
    );
    expect(screen.getByText("课标 2026-08-24-v1")).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
  });
});

// TS-022: per-lesson citations and the honest ungrounded notice.

describe("ArtifactProgressList grounding states (TS-022)", () => {
  it("shows citations for retrieved lessons and the notice for ungrounded ones", () => {
    renderUi(
      <ArtifactProgressList
        completeCount={2}
        totalCount={2}
        artifacts={[
          {
            id: "a-1",
            lesson_index: 1,
            status: "complete",
            failure_reason: null,
            download_url: null,
            citations: [CHUNK_CITATION],
            grounding_state: "retrieved",
          },
          {
            id: "a-2",
            lesson_index: 2,
            status: "complete",
            failure_reason: null,
            download_url: null,
            citations: [],
            grounding_state: "none",
          },
        ]}
      />,
    );
    expect(screen.getByRole("button", { name: "来源：notes.txt · 第0段" })).toBeVisible();
    expect(screen.getByText("无强相关来源语料")).toBeVisible();
  });
});

// TS-023: sources panel chunk expansion with 未嵌入 disclosure.

describe("SourcesPanel chunk view (TS-023)", () => {
  it("expands chunk text and marks failed embeddings with reasons", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/sources")) {
          return Promise.resolve(
            jsonResponse([
              {
                id: "s-1",
                filename: "notes.txt",
                content_type: "text/plain",
                size_bytes: 128,
                status: "ready",
                rejection_code: null,
                rejection_message: null,
                rights_acknowledged: true,
                content_sha256: "feed0000",
                chunks: [
                  {
                    position: 0,
                    text: "第一段：自然灾害阅读素材。",
                    embedding_status: "ok",
                    embedding_error: null,
                    text_sha256: "aa",
                  },
                  {
                    position: 1,
                    text: "第二段：应对策略素材。",
                    embedding_status: "failed",
                    embedding_error: "embedding model unavailable: boom",
                    text_sha256: "bb",
                  },
                ],
                created_at: "2026-09-03T10:00:00+00:00",
                updated_at: "2026-09-03T10:00:00+00:00",
              },
            ]),
          );
        }
        return Promise.resolve(jsonResponse({}));
      }),
    );
    renderUi(<SourcesPanel projectId="p1" />);
    const toggle = await screen.findByRole("button", { name: /查看切块（2 段，1 段未嵌入）/ });
    fireEvent.click(toggle);
    expect(screen.getByText("第一段：自然灾害阅读素材。")).toBeVisible();
    expect(screen.getByText("第二段：应对策略素材。")).toBeVisible();
    expect(screen.getByText("未嵌入")).toBeVisible();
    expect(screen.getByText("原因：embedding model unavailable: boom")).toBeVisible();
    vi.unstubAllGlobals();
  });
});

// TS-024: evidence retrieval rows with summary chips.

describe("EvidencePanel retrieval rows (TS-024)", () => {
  it("shows hit/exclusion/budget chips on the collapsed retrieval row", async () => {
    const inventory = {
      runs: [
        {
          run_id: "run-plan",
          kind: "lesson_plan",
          status: "complete",
          created_at: "2026-09-03T10:00:00+00:00",
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
          cost_usd_estimated: 0.01,
          cost_estimate_complete: true,
          model_latency_ms_total: 12000,
          trace_event_count: 30,
          model_call_count: 6,
          tool_call_count: 12,
          evidence_kinds: ["retrieval.semantic_search"],
          telemetry_gaps: [],
        },
      ],
      next_cursor: null,
    };
    const summary = {
      ...inventory.runs[0],
      updated_at: "2026-09-03T10:05:00+00:00",
      artifacts: [],
      interview_message_count: null,
      superseded_by: null,
      recovery_view: "generation",
      telemetry_gaps: [],
    };
    const events = {
      run_id: "run-plan",
      events: [
        {
          cursor: "c1",
          source: "trace",
          event_type: "retrieval.semantic_search",
          created_at: "2026-09-03T10:00:01+00:00",
          latency_ms: 12,
          prompt_tokens: null,
          completion_tokens: null,
          cost_usd: null,
          model: null,
          lesson_index: 1,
          payload: {
            family: "plans",
            purpose: "corpus",
            query: "自然灾害 应对",
            hits: [{ source_id: "s-1", filename: "notes.txt", position: 0, similarity: 0.81 }],
            hit_count: 1,
            excluded_count: 2,
            excluded_reasons: ["embedding model unavailable: boom"],
            budget_chars: 2000,
            used_chars: 960,
            grounding_state: "retrieved",
          },
        },
      ],
      next_cursor: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url.includes("/run-plan/events")) return Promise.resolve(jsonResponse(events));
        if (url.includes("/evidence/run-plan")) return Promise.resolve(jsonResponse(summary));
        if (url.endsWith("/evidence")) return Promise.resolve(jsonResponse(inventory));
        return Promise.resolve(jsonResponse({ runs: [], next_cursor: null }));
      }),
    );
    renderUi(<EvidencePanel projectId="p1" onNavigate={() => {}} />);
    await screen.findByText("命中 1");
    expect(screen.getAllByText("语义检索").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("排除 2")).toBeVisible();
    expect(screen.getByText("预算 960/2000 字")).toBeVisible();
    vi.unstubAllGlobals();
  });
});
