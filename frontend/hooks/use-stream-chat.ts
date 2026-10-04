"use client";

import { useCallback, useRef, useState } from "react";
import { getToken } from "@/lib/auth";
import type { CitationRef, ChatStreamEvent } from "@/types";

interface StreamState {
  isStreaming: boolean;
  partial: string;
  citations: CitationRef[];
  sources: string[];
  tookMs: number | null;
  error: string | null;
}

/**
 * Streams an assistant response via SSE from the chat endpoint.
 * Returns imperative `send` plus live state for the UI.
 */
export function useStreamChat() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    partial: "",
    citations: [],
    sources: [],
    tookMs: null,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (
      wsId: string,
      nbId: string,
      convId: string,
      message: string,
      onDone?: (text: string, citations: CitationRef[]) => void,
    ) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState({
        isStreaming: true,
        partial: "",
        citations: [],
        sources: [],
        tookMs: null,
        error: null,
      });

      const base = process.env.NEXT_PUBLIC_API_URL ?? "";
      const url = `${base}/api/v1/workspaces/${wsId}/notebooks/${nbId}/conversations/${convId}/stream`;

      try {
        const res = await fetch(url, {
          method: "POST",
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken() ?? ""}`,
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ message, stream: true }),
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let full = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          buffer = events.pop() ?? "";

          for (const raw of events) {
            const line = raw.replace(/^data: /, "").trim();
            if (!line) continue;
            let evt: ChatStreamEvent;
            try {
              evt = JSON.parse(line);
            } catch {
              continue;
            }
            if (evt.event === "delta") {
              full += evt.data;
              setState((s) => ({ ...s, partial: full }));
            } else if (evt.event === "sources") {
              setState((s) => ({ ...s, sources: evt.data }));
            } else if (evt.event === "done") {
              const citations: CitationRef[] = evt.data.citations ?? [];
              setState((s) => ({ ...s, citations, tookMs: evt.data.took_ms }));
              onDone?.(full, citations);
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setState((s) => ({ ...s, error: err.message ?? "Stream failed" }));
        }
      } finally {
        setState((s) => ({ ...s, isStreaming: false }));
      }
    },
    [],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return { ...state, send, stop };
}
