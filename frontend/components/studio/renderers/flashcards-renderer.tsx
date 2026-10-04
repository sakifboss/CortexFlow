"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Lightbulb, RotateCw, Shuffle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { FlashcardsContent } from "@/types";
import { cn } from "@/lib/utils";

export function FlashcardsRenderer({ content }: { content: FlashcardsContent }) {
  const [order, setOrder] = useState<number[]>(() =>
    (content.cards ?? []).map((_, i) => i),
  );
  const [pos, setPos] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [showHint, setShowHint] = useState(false);

  const cards = content.cards ?? [];
  if (cards.length === 0) {
    return <p className="text-center text-muted-foreground">No cards generated.</p>;
  }

  const card = cards[order[pos]];

  function go(delta: number) {
    setFlipped(false);
    setShowHint(false);
    setPos((p) => (p + delta + cards.length) % cards.length);
  }

  function shuffle() {
    const shuffled = [...order].sort(() => Math.random() - 0.5);
    setOrder(shuffled);
    setPos(0);
    setFlipped(false);
    setShowHint(false);
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-4 pb-10">
      <div className="flex w-full items-center justify-between">
        <h1 className="text-xl font-bold">{content.title}</h1>
        <Button size="sm" variant="ghost" onClick={shuffle}>
          <Shuffle className="h-3.5 w-3.5" /> Shuffle
        </Button>
      </div>

      {/* Card */}
      <button
        onClick={() => setFlipped((f) => !f)}
        className="group relative h-72 w-full [perspective:1600px]"
      >
        <div
          className={cn(
            "relative h-full w-full rounded-2xl border shadow-sm transition-transform duration-500 [transform-style:preserve-3d]",
            flipped && "[transform:rotateY(180deg)]",
          )}
        >
          {/* Front */}
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 rounded-2xl bg-gradient-to-br from-teal-500/10 to-emerald-500/10 p-8 [backface-visibility:hidden]">
            <span className="absolute left-4 top-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Question
            </span>
            <p className="text-center text-lg font-medium">{card.front}</p>
            <span className="absolute bottom-3 flex items-center gap-1 text-xs text-muted-foreground opacity-0 transition group-hover:opacity-100">
              <RotateCw className="h-3 w-3" /> Click to flip
            </span>
          </div>
          {/* Back */}
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-2xl border bg-card p-8 [backface-visibility:hidden] [transform:rotateY(180deg)]">
            <span className="absolute left-4 top-3 text-xs font-medium uppercase tracking-wide text-emerald-600">
              Answer
            </span>
            <p className="text-center">{card.back}</p>
          </div>
        </div>
      </button>

      {/* Hint */}
      {card.hint ? (
        <div className="min-h-[1.5rem] text-center text-sm">
          {showHint ? (
            <span className="inline-flex items-center gap-1 text-amber-600">
              <Lightbulb className="h-3.5 w-3.5" /> {card.hint}
            </span>
          ) : (
            <button
              onClick={() => setShowHint(true)}
              className="text-muted-foreground underline-offset-2 hover:underline"
            >
              Show hint
            </button>
          )}
        </div>
      ) : (
        <div className="min-h-[1.5rem]" />
      )}

      {/* Nav */}
      <div className="flex w-full items-center justify-between">
        <Button variant="outline" size="icon" onClick={() => go(-1)}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium tabular-nums">
            {pos + 1} / {cards.length}
          </span>
        </div>
        <Button variant="outline" size="icon" onClick={() => go(1)}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Progress dots */}
      <div className="flex flex-wrap justify-center gap-1">
        {cards.map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              i === pos ? "bg-primary" : "bg-muted-foreground/30",
            )}
          />
        ))}
      </div>
    </div>
  );
}
