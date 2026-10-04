"use client";

import type { Artifact } from "@/types";
import { CustomRenderer, ReportRenderer } from "./renderers/text-renderers";
import { DataTableRenderer } from "./renderers/data-table-renderer";
import { FlashcardsRenderer } from "./renderers/flashcards-renderer";
import { QuizRenderer } from "./renderers/quiz-renderer";
import { SlideDeckRenderer } from "./renderers/slide-deck-renderer";
import { AudioOverviewRenderer } from "./renderers/audio-overview-renderer";
import { MindMapRenderer } from "./renderers/mind-map-renderer";
import { InfographicRenderer } from "./renderers/infographic-renderer";

/**
 * Routes a ready artifact to the renderer for its kind. Content shapes are
 * validated server-side against the matching Pydantic model, so each renderer
 * can trust its typed content.
 */
export function ArtifactRenderer({ artifact }: { artifact: Artifact }) {
  const c = artifact.content;
  if (!c) return <p className="text-center text-muted-foreground">No content.</p>;
  const cites = artifact.citations;

  switch (artifact.kind) {
    case "custom":
      return <CustomRenderer content={c as any} citations={cites} />;
    case "report":
      return <ReportRenderer content={c as any} citations={cites} />;
    case "slide_deck":
      return <SlideDeckRenderer content={c as any} />;
    case "audio_overview":
      return <AudioOverviewRenderer content={c as any} />;
    case "mind_map":
      return <MindMapRenderer content={c as any} />;
    case "flashcards":
      return <FlashcardsRenderer content={c as any} />;
    case "quiz":
      return <QuizRenderer content={c as any} />;
    case "infographic":
      return <InfographicRenderer content={c as any} />;
    case "data_table":
      return <DataTableRenderer content={c as any} />;
    default:
      return <pre className="text-xs">{JSON.stringify(c, null, 2)}</pre>;
  }
}
