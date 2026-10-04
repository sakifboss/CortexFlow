"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { cn } from "@/lib/utils";
import type { CitationRef } from "@/types";

interface MarkdownProps {
  content: string;
  citations?: CitationRef[] | null;
  onCitationClick?: (cite: CitationRef) => void;
}

/**
 * Renders markdown and transforms [n] citation markers into clickable chips
 * that surface the source snippet in a popover/panel.
 */
export function Markdown({ content, citations, onCitationClick }: MarkdownProps) {
  const citeMap = new Map<number, CitationRef>();
  (citations ?? []).forEach((c) => citeMap.set(c.id, c));

  // Tokenize to inject citation chips while preserving markdown structure
  const parts = content.split(/(\[\d+\])/g);

  return (
    <div className="prose-cortexflow max-w-none">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (m) {
          const id = Number(m[1]);
          const cite = citeMap.get(id);
          if (!cite) return null; // drop ungrounded markers
          return (
            <button
              key={i}
              className="cite-chip"
              onClick={() => onCitationClick?.(cite)}
              title={`${cite.document_title}${cite.page ? ` · p.${cite.page}` : ""}`}
            >
              {id}
            </button>
          );
        }
        return (
          <ReactMarkdown
            key={i}
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
          >
            {part}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
