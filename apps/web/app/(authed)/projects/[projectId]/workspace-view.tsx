"use client";

import { useState } from "react";
import { BlueprintPanel } from "@/components/blueprint-panel";
import { BriefPanel } from "@/components/brief-panel";
import { DiscoveryPanel } from "@/components/discovery-panel";
import { SourcesPanel } from "@/components/sources-panel";

type Tab = "sources" | "discovery" | "brief" | "blueprint";

const TAB_LABELS: Record<Tab, string> = {
  sources: "来源",
  discovery: "需求访谈",
  brief: "教学简报",
  blueprint: "单元蓝图",
};

export default function WorkspaceView({ projectId }: { projectId: string }) {
  const [tab, setTab] = useState<Tab>("sources");

  return (
    <section aria-label="单元备课工作区">
      <nav aria-label="工作区导航" className="mb-6 flex gap-2 border-b border-line">
        {(Object.keys(TAB_LABELS) as Tab[]).map((key) => (
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
      {tab === "sources" ? <SourcesPanel projectId={projectId} /> : null}
      {tab === "discovery" ? <DiscoveryPanel projectId={projectId} /> : null}
      {tab === "brief" ? <BriefPanel projectId={projectId} /> : null}
      {tab === "blueprint" ? <BlueprintPanel projectId={projectId} /> : null}
    </section>
  );
}
