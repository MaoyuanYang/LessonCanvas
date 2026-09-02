"use client";

import { useQuery } from "@tanstack/react-query";
import { getApiToken } from "@/lib/auth";
import { getMemoryOverview } from "@/lib/api";
import type { WorkspaceTab } from "@/app/(authed)/projects/[projectId]/workspace-view";

const KIND_TABS: Record<string, WorkspaceTab> = {
  brief_confirm: "brief",
  blueprint_confirm: "blueprint",
  run_settled: "generation",
};

const TAB_ORDER: WorkspaceTab[] = ["brief", "blueprint", "generation"];

/**
 * F013 U2: persistent workspace badge while any proposal is pending; links
 * to the first panel (in tab order) holding a pending proposal.
 */
export function MemoryBadge({
  onNavigate,
}: {
  onNavigate: (tab: WorkspaceTab) => void;
}) {
  const overviewQuery = useQuery({
    queryKey: ["memory-overview"],
    queryFn: async () => getMemoryOverview(await getApiToken()),
    retry: false,
    // Poll lightly so the badge appears after asynchronous passes settle
    // (F013 D3 best-effort triggers).
    refetchInterval: 4000,
  });

  const pending = (overviewQuery.data?.proposals ?? []).filter(
    (proposal) => proposal.status === "pending",
  );
  if (!pending.length) return null;

  const targetTabs = pending
    .map((proposal) => (proposal.trigger_kind ? KIND_TABS[proposal.trigger_kind] : null))
    .filter((tab): tab is WorkspaceTab => tab !== null);
  const target = TAB_ORDER.find((tab) => targetTabs.includes(tab)) ?? "brief";

  return (
    <button
      type="button"
      onClick={() => onNavigate(target)}
      aria-label={`${pending.length} 条待处理记忆提议，前往查看`}
      className="rounded-full border border-accent/50 bg-accent/10 px-3 py-1 text-xs font-medium text-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
    >
      记忆提议 {pending.length}
    </button>
  );
}
