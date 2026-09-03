"use client";

import { useState } from "react";
import type { BlueprintCitation } from "@/lib/api";

// F014 U3 (ux-ui.md): the citation chip promoted from the blueprint-panel
// feature-local pattern to one shared component with two documented
// variants — source-chunk citations (expandable: filename, chunk position,
// server-delivered excerpt, hash prefix) and standards citations (static).
// Expansion follows the evidence-panel pattern: a native button with
// aria-expanded, no dialogs, no motion.

function chipLabel(citation: BlueprintCitation): string {
  if (citation.type === "standards") {
    return `课标 ${citation.snapshot_version ?? ""}`.trim();
  }
  const filename = citation.filename ?? "项目来源";
  return citation.chunk_position != null
    ? `来源：${filename} · 第${citation.chunk_position}段`
    : `来源：${filename}`;
}

function CitationChip({ citation }: { citation: BlueprintCitation }) {
  const [expanded, setExpanded] = useState(false);

  if (citation.type !== "source" || !citation.excerpt) {
    return (
      <span className="ml-2 rounded bg-evidence/10 px-1.5 py-0.5 text-xs text-evidence">
        {chipLabel(citation)}
      </span>
    );
  }
  return (
    <span className="ml-2 inline-flex flex-col gap-1">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        className="rounded bg-evidence/10 px-1.5 py-0.5 text-xs text-evidence focus-visible:outline-2 focus-visible:outline-focus"
      >
        {chipLabel(citation)}
      </button>
      {expanded ? (
        <span className="block max-w-xl rounded border border-line bg-paper p-2 text-xs text-ink">
          <span className="block font-medium">
            {citation.filename ?? "项目来源"}
            {citation.chunk_position != null ? ` · 第${citation.chunk_position}段` : ""}
          </span>
          <span className="mt-1 block whitespace-pre-wrap break-words">{citation.excerpt}</span>
          {citation.text_sha256 ? (
            <span className="mt-1 block text-ink-secondary">
              内容哈希：{citation.text_sha256.slice(0, 8)}
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}

export function CitationChipGroup({ citations }: { citations?: BlueprintCitation[] | null }) {
  if (!citations || citations.length === 0) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap items-center gap-1 align-baseline">
      {citations.map((citation, index) => (
        <CitationChip key={`${citation.type}-${citation.source_id ?? citation.section_id ?? index}-${index}`} citation={citation} />
      ))}
    </span>
  );
}
