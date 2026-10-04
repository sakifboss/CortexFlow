"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, StickyNote } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { SlideDeckContent } from "@/types";
import { cn } from "@/lib/utils";

export function SlideDeckRenderer({ content }: { content: SlideDeckContent }) {
  const slides = content.slides ?? [];
  const [idx, setIdx] = useState(0);
  const [showNotes, setShowNotes] = useState(false);

  if (slides.length === 0) {
    return <p className="text-center text-muted-foreground">No slides generated.</p>;
  }

  const slide = slides[idx];
  const isTitle = idx === 0;

  function go(delta: number) {
    setIdx((i) => Math.max(0, Math.min(slides.length - 1, i + delta)));
  }

  return (
    <div className="mx-auto max-w-4xl space-y-3 pb-10">
      {/* Slide canvas — 16:9 */}
      <div className="relative aspect-video w-full overflow-hidden rounded-xl border bg-gradient-to-br from-orange-500/5 to-amber-500/5 shadow-sm">
        <div className="flex h-full flex-col p-10">
          {isTitle ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <h1 className="text-3xl font-bold tracking-tight md:text-4xl">{slide.title || content.title}</h1>
              {(content.subtitle || slide.bullets?.[0]) && (
                <p className="mt-3 text-lg text-muted-foreground">
                  {content.subtitle || slide.bullets?.[0]}
                </p>
              )}
            </div>
          ) : (
            <>
              <h2 className="mb-6 border-b pb-3 text-2xl font-bold tracking-tight">
                {slide.title}
              </h2>
              <ul className="space-y-3">
                {slide.bullets?.map((b, i) => (
                  <li key={i} className="flex gap-3 text-lg">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-orange-500" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
        <div className="absolute bottom-3 right-4 text-xs text-muted-foreground">
          {idx + 1} / {slides.length}
        </div>
      </div>

      {/* Speaker notes */}
      {slide.notes && (
        <div>
          <button
            onClick={() => setShowNotes((s) => !s)}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            <StickyNote className="h-3.5 w-3.5" />
            {showNotes ? "Hide" : "Show"} speaker notes
          </button>
          {showNotes && (
            <p className="mt-2 rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
              {slide.notes}
            </p>
          )}
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={() => go(-1)} disabled={idx === 0}>
          <ChevronLeft className="h-4 w-4" /> Prev
        </Button>
        <div className="flex flex-wrap justify-center gap-1.5">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === idx ? "w-6 bg-orange-500" : "w-1.5 bg-muted-foreground/30",
              )}
            />
          ))}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => go(1)}
          disabled={idx === slides.length - 1}
        >
          Next <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
