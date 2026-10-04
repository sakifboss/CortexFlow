"use client";

import { FileText, Quote, X } from "lucide-react";
import type { CitationRef } from "@/types";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CitationPanelProps {
  citations: CitationRef[];
  activeId: number | null;
  onClose?: () => void;
  onOpenSource?: (cite: CitationRef) => void;
}

/**
 * Right-hand source panel listing every citation used in the current answer,
 * with snippet + document + page. Mirrors NotebookLM's source viewer.
 */
export function CitationPanel({ citations, activeId, onClose, onOpenSource }: CitationPanelProps) {
  return (
    <div className="flex h-full w-full flex-col border-l bg-card/40">
      <div className="flex h-11 shrink-0 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Quote className="h-4 w-4 text-primary" />
          Sources ({citations.length})
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
            <X className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-3 p-3">
          {citations.length === 0 && (
            <div className="px-2 py-12 text-center text-xs text-muted-foreground">
              No sources yet. Citations appear after you ask a question.
            </div>
          )}
          {citations.map((c) => (
            <button
              key={c.id}
              onClick={() => onOpenSource?.(c)}
              className={cn(
                "block w-full rounded-lg border p-3 text-left transition hover:border-primary/40 hover:shadow-sm",
                activeId === c.id ? "border-primary bg-primary/5" : "bg-card",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 items-center gap-1.5 text-xs font-medium">
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded bg-primary/15 text-[10px] text-primary">
                    {c.id}
                  </span>
                  <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
                  <span className="truncate">{c.document_title}</span>
                </div>
                {c.page && <Badge variant="secondary" className="shrink-0">p.{c.page}</Badge>}
              </div>
              <p className="mt-2 line-clamp-4 text-xs text-muted-foreground">{c.snippet}</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  {c.section ?? "source"}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  score {(c.score * 100).toFixed(0)}%
                </span>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
