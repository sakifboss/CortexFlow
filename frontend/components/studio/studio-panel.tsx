"use client";

import { useState } from "react";
import { AlertCircle, Clock, Loader2, MoreVertical, Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { KIND_META } from "./artifact-catalog";
import { GenerateDialog } from "./generate-dialog";
import { ArtifactViewer } from "./artifact-viewer";
import {
  useArtifactKinds,
  useArtifacts,
  useDeleteArtifact,
} from "@/hooks/use-artifacts";
import type { Artifact, ArtifactSummary, KindInfo } from "@/types";
import { cn, timeAgo } from "@/lib/utils";

export function StudioPanel({
  workspaceId,
  notebookId,
}: {
  workspaceId: string;
  notebookId: string;
}) {
  const { data: kinds, isLoading: kindsLoading } = useArtifactKinds(workspaceId, notebookId);
  const { data: artifacts, isLoading: listLoading } = useArtifacts(workspaceId, notebookId);
  const del = useDeleteArtifact(workspaceId, notebookId);

  const [genKind, setGenKind] = useState<KindInfo | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-6">
      {/* Create grid */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <h2 className="font-semibold">Studio</h2>
          <span className="text-sm text-muted-foreground">
            — generate grounded artifacts from your sources
          </span>
        </div>

        {kindsLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl border bg-muted/40" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {(kinds ?? []).map((k: KindInfo) => {
              const meta = KIND_META[k.kind];
              const Icon = meta.icon;
              return (
                <button
                  key={k.kind}
                  onClick={() => setGenKind(k)}
                  className="group flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition hover:border-primary/40 hover:shadow-md"
                >
                  <div
                    className={cn(
                      "grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br text-white shadow-sm transition group-hover:scale-105",
                      meta.gradient,
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold">{k.label}</div>
                    <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                      {k.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* Generated artifacts */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
          Generated ({artifacts?.length ?? 0})
        </h3>

        {listLoading ? (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : !artifacts || artifacts.length === 0 ? (
          <div className="rounded-xl border border-dashed p-10 text-center">
            <Sparkles className="mx-auto h-7 w-7 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">
              No artifacts yet. Pick a type above to generate your first one.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {artifacts.map((a: ArtifactSummary) => (
              <ArtifactRow
                key={a.id}
                artifact={a}
                onOpen={() => setOpenId(a.id)}
                onDelete={() => del.mutate(a.id)}
              />
            ))}
          </div>
        )}
      </section>

      <GenerateDialog
        workspaceId={workspaceId}
        notebookId={notebookId}
        kind={genKind}
        onClose={() => setGenKind(null)}
        onGenerated={(a: Artifact) => {
          setGenKind(null);
          if (a.status === "ready") setOpenId(a.id);
        }}
      />

      <ArtifactViewer
        workspaceId={workspaceId}
        notebookId={notebookId}
        artifactId={openId}
        onClose={() => setOpenId(null)}
      />
    </div>
  );
}

function ArtifactRow({
  artifact,
  onOpen,
  onDelete,
}: {
  artifact: ArtifactSummary;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const meta = KIND_META[artifact.kind];
  const Icon = meta.icon;
  const failed = artifact.status === "failed";

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border p-3 transition hover:bg-muted/40",
        !failed && "cursor-pointer",
      )}
      onClick={() => !failed && onOpen()}
    >
      <div
        className={cn(
          "grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-gradient-to-br text-white",
          meta.gradient,
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">{artifact.title}</span>
          {failed && (
            <Badge variant="destructive" className="shrink-0 gap-1">
              <AlertCircle className="h-3 w-3" /> failed
            </Badge>
          )}
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="capitalize">{artifact.kind.replace(/_/g, " ")}</span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" /> {timeAgo(artifact.created_at)}
          </span>
        </div>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild onClick={(e: React.MouseEvent) => e.stopPropagation()}>
          <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
