"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KIND_META } from "./artifact-catalog";
import { useGenerateArtifact } from "@/hooks/use-artifacts";
import type { Artifact, KindInfo } from "@/types";
import { cn } from "@/lib/utils";

interface Props {
  workspaceId: string;
  notebookId: string;
  kind: KindInfo | null;
  onClose: () => void;
  onGenerated: (a: Artifact) => void;
}

export function GenerateDialog({
  workspaceId,
  notebookId,
  kind,
  onClose,
  onGenerated,
}: Props) {
  const [prompt, setPrompt] = useState("");
  const [count, setCount] = useState<number | "">(kind?.default_count ?? "");
  const gen = useGenerateArtifact(workspaceId, notebookId);

  if (!kind) return null;
  const meta = KIND_META[kind.kind];
  const Icon = meta.icon;

  async function onGenerate() {
    const options: Record<string, unknown> = {};
    if (kind!.supports_count && count !== "") options.count = Number(count);
    const art = await gen.mutateAsync({
      kind: kind!.kind,
      prompt: prompt.trim() || undefined,
      options,
    });
    onGenerated(art);
    setPrompt("");
  }

  return (
    <Dialog open={!!kind} onOpenChange={(o: boolean) => !o && !gen.isPending && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div
              className={cn(
                "grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br text-white",
                meta.gradient,
              )}
            >
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle>{kind.label}</DialogTitle>
              <DialogDescription className="mt-0.5">{kind.description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="focus">
              Focus / instruction <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Textarea
              id="focus"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={placeholderFor(kind.kind)}
              rows={3}
              disabled={gen.isPending}
            />
          </div>

          {kind.supports_count && (
            <div className="space-y-1.5">
              <Label htmlFor="count">{kind.count_label ?? "Count"}</Label>
              <Input
                id="count"
                type="number"
                min={1}
                max={50}
                value={count}
                onChange={(e) =>
                  setCount(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="w-28"
                disabled={gen.isPending}
              />
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={gen.isPending}>
            Cancel
          </Button>
          <Button onClick={onGenerate} disabled={gen.isPending}>
            {gen.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Generating…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Generate
              </>
            )}
          </Button>
        </div>

        {gen.isPending && (
          <p className="text-center text-xs text-muted-foreground">
            Grounding in your sources and generating — this can take a moment on local models.
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}

function placeholderFor(kind: string): string {
  const map: Record<string, string> = {
    custom: "e.g. Write a one-page executive brief for a non-technical audience",
    audio_overview: "e.g. Emphasize the practical implications and real-world examples",
    slide_deck: "e.g. Focus on the methodology and results sections",
    mind_map: "e.g. Center on the key concepts and how they relate",
    report: "e.g. Compare the approaches and highlight open questions",
    flashcards: "e.g. Prioritize definitions and formulas",
    quiz: "e.g. Make it exam-style, medium difficulty",
    infographic: "e.g. Pull out the most striking statistics",
    data_table: "e.g. Extract entities with their dates and values",
  };
  return map[kind] ?? "Add an optional focus…";
}
