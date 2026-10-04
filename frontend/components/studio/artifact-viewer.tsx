"use client";

import { AlertCircle, Loader2, RefreshCw, X } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArtifactRenderer } from "./artifact-renderer";
import { KIND_META } from "./artifact-catalog";
import { useArtifact, useRegenerateArtifact } from "@/hooks/use-artifacts";
import { cn } from "@/lib/utils";

interface Props {
  workspaceId: string;
  notebookId: string;
  artifactId: string | null;
  onClose: () => void;
}

export function ArtifactViewer({ workspaceId, notebookId, artifactId, onClose }: Props) {
  const { data: artifact, isLoading } = useArtifact(workspaceId, notebookId, artifactId);
  const regen = useRegenerateArtifact(workspaceId, notebookId);

  return (
    <Dialog open={!!artifactId} onOpenChange={(o: boolean) => !o && onClose()}>
      <DialogContent className="flex h-[88vh] max-w-5xl flex-col gap-0 overflow-hidden p-0">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-5 py-3">
          <div className="flex min-w-0 items-center gap-2">
            {artifact && (
              <div
                className={cn(
                  "grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br text-white",
                  KIND_META[artifact.kind]?.gradient,
                )}
              >
                {(() => {
                  const Icon = KIND_META[artifact.kind]?.icon;
                  return Icon ? <Icon className="h-4 w-4" /> : null;
                })()}
              </div>
            )}
            <div className="min-w-0">
              <h2 className="truncate font-semibold">{artifact?.title ?? "Artifact"}</h2>
              {artifact?.citations && artifact.citations.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Grounded in {artifact.citations.length} source
                  {artifact.citations.length > 1 ? "s" : ""}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1">
            {artifact && artifact.status !== "generating" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => regen.mutate(artifact.id)}
                disabled={regen.isPending}
              >
                <RefreshCw className={cn("h-3.5 w-3.5", regen.isPending && "animate-spin")} />
                Regenerate
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading || !artifact ? (
            <div className="grid h-full place-items-center text-sm text-muted-foreground">
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading…
              </span>
            </div>
          ) : artifact.status === "failed" ? (
            <div className="mx-auto max-w-md rounded-xl border border-destructive/40 bg-destructive/5 p-6 text-center">
              <AlertCircle className="mx-auto h-8 w-8 text-destructive" />
              <h3 className="mt-2 font-semibold">Generation failed</h3>
              <p className="mt-1 text-sm text-muted-foreground">{artifact.error}</p>
              <Button
                className="mt-4"
                variant="outline"
                onClick={() => regen.mutate(artifact.id)}
                disabled={regen.isPending}
              >
                <RefreshCw className="h-4 w-4" /> Try again
              </Button>
            </div>
          ) : (
            <ArtifactRenderer artifact={artifact} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
