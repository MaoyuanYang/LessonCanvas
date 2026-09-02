"use client";

import { useState } from "react";
import { AlignmentPanel } from "@/components/alignment-panel";
import { BlueprintPanel } from "@/components/blueprint-panel";
import { BriefPanel } from "@/components/brief-panel";
import { DeckPanel } from "@/components/deck-panel";
import { DiscoveryPanel } from "@/components/discovery-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import { ExercisePanel } from "@/components/exercise-panel";
import { GenerationPanel } from "@/components/generation-panel";
import { MemoryBadge } from "@/components/memory-badge";
import { SourcesPanel } from "@/components/sources-panel";
import { VersionComparePanel } from "@/components/version-compare-panel";

export type WorkspaceTab =
  | "sources"
  | "discovery"
  | "brief"
  | "blueprint"
  | "generation"
  | "decks"
  | "exercises"
  | "evidence"
  | "versions"
  | "alignment";

const TAB_LABELS: Record<WorkspaceTab, string> = {
  sources: "来源",
  discovery: "需求访谈",
  brief: "教学简报",
  blueprint: "单元蓝图",
  generation: "教案生成",
  decks: "课件生成",
  exercises: "练习与答案",
  evidence: "运行证据",
  versions: "版本对比",
  alignment: "对齐与交付",
};

export default function WorkspaceView({
  projectId,
  readOnly = false,
}: {
  projectId: string;
  readOnly?: boolean;
}) {
  const [tab, setTab] = useState<WorkspaceTab>("sources");

  return (
    <section aria-label="单元备课工作区">
      {!readOnly ? (
        <div className="mb-3 flex justify-end">
          <MemoryBadge onNavigate={setTab} />
        </div>
      ) : null}
      <nav
        aria-label="工作区导航"
        className="mb-6 flex flex-wrap gap-2 border-b border-line"
      >
        {(Object.keys(TAB_LABELS) as WorkspaceTab[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            aria-current={tab === key ? "page" : undefined}
            className={`px-4 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus ${
              tab === key
                ? "border-b-2 border-accent text-accent"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </nav>
      {tab === "sources" ? <SourcesPanel projectId={projectId} readOnly={readOnly} /> : null}
      {tab === "discovery" ? <DiscoveryPanel projectId={projectId} readOnly={readOnly} /> : null}
      {tab === "brief" ? <BriefPanel projectId={projectId} readOnly={readOnly} /> : null}
      {tab === "blueprint" ? <BlueprintPanel projectId={projectId} readOnly={readOnly} /> : null}
      {tab === "generation" ? (
        <GenerationPanel projectId={projectId} onNavigate={setTab} readOnly={readOnly} />
      ) : null}
      {tab === "decks" ? (
        <DeckPanel projectId={projectId} onNavigate={setTab} readOnly={readOnly} />
      ) : null}
      {tab === "exercises" ? (
        <ExercisePanel projectId={projectId} onNavigate={setTab} readOnly={readOnly} />
      ) : null}
      {tab === "evidence" ? (
        <EvidencePanel projectId={projectId} onNavigate={setTab} readOnly={readOnly} />
      ) : null}
      {tab === "versions" ? (
        <VersionComparePanel projectId={projectId} readOnly={readOnly} />
      ) : null}
      {tab === "alignment" ? (
        <AlignmentPanel projectId={projectId} onNavigate={setTab} readOnly={readOnly} />
      ) : null}
    </section>
  );
}
