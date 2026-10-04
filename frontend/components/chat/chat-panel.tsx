"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Bot,
  Copy,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Markdown } from "./markdown";
import { useStreamChat } from "@/hooks/use-stream-chat";
import { useMessages } from "@/hooks/use-notebooks";
import { notebookApi } from "@/services/notebook";
import { useQueryClient } from "@tanstack/react-query";
import type { CitationRef, Message } from "@/types";
import { cn, timeAgo } from "@/lib/utils";
import { toast } from "sonner";

interface ChatPanelProps {
  workspaceId: string;
  notebookId: string;
  conversationId: string;
}

const SUGGESTIONS = [
  "Summarize the key findings",
  "What are the main arguments?",
  "Compare the methodologies used",
  "What gaps remain in the research?",
];

export function ChatPanel({ workspaceId, notebookId, conversationId }: ChatPanelProps) {
  const qc = useQueryClient();
  const { data: messages, isLoading } = useMessages(workspaceId, notebookId, conversationId);
  const stream = useStreamChat();
  const [input, setInput] = useState("");
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // All citations from the latest assistant message (streamed or persisted)
  const allCitations: CitationRef[] =
    stream.citations.length > 0
      ? stream.citations
      : messages?.filter((m) => m.role === "assistant").at(-1)?.citations ?? [];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, stream.partial]);

  async function onSend(text?: string) {
    const message = (text ?? input).trim();
    if (!message || stream.isStreaming) return;
    setInput("");
    await stream.send(workspaceId, notebookId, conversationId, message, () => {
      // invalidate so server history reloads with the persisted pair
      qc.invalidateQueries({ queryKey: ["messages", workspaceId, notebookId, conversationId] });
    });
  }

  async function onRegenerate() {
    const lastUser = messages?.filter((m) => m.role === "user").at(-1);
    if (lastUser) await onSend(lastUser.content);
  }

  const lastAssistant = messages?.filter((m) => m.role === "assistant").at(-1);

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <ScrollArea className="flex-1" ref={scrollRef as never}>
        <div className="mx-auto max-w-3xl space-y-6 p-6">
          {isLoading && (
            <div className="flex justify-center py-12 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading conversation…
            </div>
          )}

          {(!messages || messages.length === 0) && !stream.isStreaming && (
            <EmptyState onPick={onSend} />
          )}

          {messages?.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              onCitationClick={(c) => setActiveCite(c.id)}
            />
          ))}

          {/* Live streaming assistant message */}
          {stream.isStreaming && (
            <div className="flex gap-3">
              <Avatar role="assistant" />
              <div className="min-w-0 flex-1">
                <Markdown content={stream.partial || "…"} />
                <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" /> {stream.model ?? "thinking"}
                </div>
              </div>
            </div>
          )}

          {stream.error && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" /> {stream.error}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Composer */}
      <div className="border-t bg-card/40 p-4">
        <div className="mx-auto max-w-3xl">
          {lastAssistant && !stream.isStreaming && (
            <div className="mb-2 flex items-center justify-end gap-1">
              <Button variant="ghost" size="sm" onClick={onRegenerate}>
                <RefreshCw className="h-3.5 w-3.5" /> Regenerate
              </Button>
            </div>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onSend();
            }}
            className="relative"
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              placeholder="Ask anything about your sources…"
              rows={3}
              className="min-h-[60px] resize-none pr-24"
            />
            <div className="absolute bottom-2 right-2 flex items-center gap-1">
              {stream.isStreaming ? (
                <Button
                  type="button"
                  size="icon"
                  variant="destructive"
                  onClick={stream.stop}
                  title="Stop"
                >
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button type="submit" size="icon" disabled={!input.trim()} title="Send">
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </div>
          </form>
          <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
            Citations are grounded in your uploaded sources. {stream.tookMs && `Last answer: ${stream.tookMs}ms`}
          </p>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="py-12 text-center">
      <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-white">
        <Sparkles className="h-6 w-6" />
      </div>
      <h3 className="text-lg font-semibold">Ask about your sources</h3>
      <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
        Every answer is grounded with clickable citations to the exact page in your documents.
      </p>
      <div className="mx-auto mt-6 grid max-w-md gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-lg border bg-card px-4 py-2.5 text-left text-sm transition hover:border-primary/40 hover:shadow-sm"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onCitationClick,
}: {
  message: Message;
  onCitationClick: (c: CitationRef) => void;
}) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-3 animate-fade-in", isUser && "flex-row-reverse")}>
      <Avatar role={message.role} />
      <div className={cn("min-w-0 flex-1", isUser && "flex flex-col items-end")}>
        <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">
            {isUser ? "You" : "CortexFlow"}
          </span>
          <span>{timeAgo(message.created_at)}</span>
        </div>
        <div
          className={cn(
            "inline-block max-w-full rounded-2xl px-4 py-2.5",
            isUser ? "bg-primary text-primary-foreground" : "bg-card border",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm">{message.content}</p>
          ) : (
            <Markdown content={message.content} citations={message.citations} onCitationClick={onCitationClick} />
          )}
        </div>
        {!isUser && (
          <div className="mt-1.5 flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { navigator.clipboard.writeText(message.content); toast.success("Copied"); }}>
              <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <ThumbsUp className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7">
              <ThumbsDown className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function Avatar({ role }: { role: string }) {
  if (role === "user") {
    return (
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted">
        <User className="h-4 w-4" />
      </div>
    );
  }
  return (
    <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-white">
      <Bot className="h-4 w-4" />
    </div>
  );
}
