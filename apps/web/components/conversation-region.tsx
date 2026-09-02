"use client";

import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { getApiToken } from "@/lib/auth";
import { Button } from "@/components/ui";
import type { ConversationKind } from "@/lib/api";
import { ApiClientError, narrate, reask, stopNarration, streamUrl } from "@/lib/api";

interface ConversationRegionProps {
  projectId: string;
  kind: ConversationKind;
  narrateText: string;
  onError?: (message: string) => void;
}

export function ConversationRegion({
  projectId,
  kind,
  narrateText,
  onError,
}: ConversationRegionProps) {
  const [narration, setNarration] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function startStream() {
    const token = await getApiToken();
    setStreaming(true);
    setNarration("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await fetch(streamUrl(projectId, 0, kind), {
        headers: token ? { authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            if (data.t) setNarration((current) => current + data.t);
          }
        }
      }
    } catch {
      // stopped or closed by user
    } finally {
      setStreaming(false);
    }
  }

  const narrateMutation = useMutation({
    mutationFn: async () => narrate(await getApiToken(), projectId, narrateText, kind),
    onSuccess: () => void startStream(),
    onError: (err) =>
      onError?.(err instanceof ApiClientError ? err.message : "叙述失败"),
  });

  const reaskMutation = useMutation({
    mutationFn: async () => reask(await getApiToken(), projectId, narrateText, kind),
    onSuccess: () => void startStream(),
    onError: (err) => onError?.(err instanceof ApiClientError ? err.message : "重问失败"),
  });

  const stopMutation = useMutation({
    mutationFn: async () => stopNarration(await getApiToken(), projectId, kind),
    onSuccess: () => abortRef.current?.abort(),
  });

  useEffect(() => () => abortRef.current?.abort(), []);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          onClick={() => narrateMutation.mutate()}
          disabled={narrateMutation.isPending || streaming}
        >
          生成叙述
        </Button>
        {streaming ? (
          <Button variant="quiet" onClick={() => stopMutation.mutate()}>
            停止
          </Button>
        ) : narration ? (
          <Button variant="quiet" onClick={() => reaskMutation.mutate()}>
            重新提问
          </Button>
        ) : null}
      </div>
      {narration ? (
        <p
          aria-live="polite"
          className="rounded border border-line bg-paper p-4 text-sm text-ink"
        >
          {narration}
        </p>
      ) : null}
    </div>
  );
}
