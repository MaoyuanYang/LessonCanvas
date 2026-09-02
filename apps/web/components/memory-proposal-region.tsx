"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getApiToken } from "@/lib/auth";
import { Alert, Button } from "@/components/ui";
import { MemoryProposalCard } from "@/components/memory-shared";
import {
  getMemoryOverview,
  retryMemoryPass,
  type MemoryOverview,
} from "@/lib/api";

/**
 * F013 U2: the "记忆提议" region hosted by the panels whose trigger events
 * fired (brief panel, blueprint panel, and the artifact-run panels). One
 * shared component serves every host; decisions invalidate the shared
 * workspace query.
 */
export function MemoryProposalRegion({
  kinds,
  readOnly = false,
}: {
  kinds: readonly string[];
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const overviewQuery = useQuery({
    queryKey: ["memory-overview"],
    queryFn: async () => getMemoryOverview(await getApiToken()),
    // Poll lightly so proposal cards and the badge appear after
    // asynchronous passes settle (F013 D3 best-effort triggers).
    refetchInterval: 4000,
  });

  const retryMutation = useMutation({
    mutationFn: async (passId: string) => retryMemoryPass(await getApiToken(), passId),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["memory-overview"] }),
  });

  if (overviewQuery.isLoading || readOnly) return null;

  const overview: MemoryOverview | undefined = overviewQuery.data;
  if (!overview) return null;

  const pending = (overview.proposals ?? []).filter(
    (proposal) =>
      proposal.status === "pending" &&
      (proposal.trigger_kind ? kinds.includes(proposal.trigger_kind) : false),
  );
  const failedPasses = (overview.passes ?? []).filter(
    (row) => row.status === "failed" && kinds.includes(row.trigger_kind),
  );
  const generating = (overview.passes ?? []).some(
    (row) =>
      (row.status === "scheduled" || row.status === "running") &&
      kinds.includes(row.trigger_kind),
  );
  if (!pending.length && !failedPasses.length && !generating) return null;

  return (
    <section
      aria-labelledby={`memory-proposal-heading-${kinds.join("-")}`}
      className="rounded border border-accent/40 bg-accent/5 p-4"
    >
      <h3
        id={`memory-proposal-heading-${kinds.join("-")}`}
        className="text-sm font-semibold text-ink"
      >
        记忆提议
      </h3>
      <p className="mt-1 text-xs text-ink-secondary">
        以下偏好由 Agent 从你已确认的内容中提出；仅在你确认后才会记住并用于后续备课，任何时候可在「账号与数据」中管理或删除。
      </p>

      {generating ? <p className="mt-2 text-sm text-ink-secondary">提案生成中…</p> : null}

      {failedPasses.map((row) => (
        <div key={row.id} className="mt-2">
          <Alert tone="warning">记忆提案生成失败，不影响当前流程。</Alert>
          <Button
            variant="secondary"
            className="mt-2"
            disabled={retryMutation.isPending}
            onClick={() => retryMutation.mutate(row.id)}
          >
            {retryMutation.isPending ? "重试中…" : "重试生成"}
          </Button>
        </div>
      ))}

      {pending.length ? (
        <ul className="mt-3 space-y-3">
          {pending.map((proposal) => (
            <MemoryProposalCard key={proposal.id} proposal={proposal} />
          ))}
        </ul>
      ) : null}
    </section>
  );
}
