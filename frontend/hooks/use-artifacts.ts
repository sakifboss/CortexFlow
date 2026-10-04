"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { artifactApi } from "@/services/artifact";
import type { Artifact, GenerateArtifactInput } from "@/types";
import { toast } from "sonner";

const listKey = (wsId: string, nbId: string) => ["artifacts", wsId, nbId];
const oneKey = (wsId: string, nbId: string, id: string) => ["artifact", wsId, nbId, id];

export function useArtifactKinds(wsId: string, nbId: string) {
  return useQuery({
    queryKey: ["artifact-kinds", wsId, nbId],
    queryFn: () => artifactApi.kinds(wsId, nbId),
    enabled: !!wsId && !!nbId,
    staleTime: 1000 * 60 * 60,
  });
}

export function useArtifacts(wsId: string, nbId: string) {
  return useQuery({
    queryKey: listKey(wsId, nbId),
    queryFn: () => artifactApi.list(wsId, nbId),
    enabled: !!wsId && !!nbId,
  });
}

export function useArtifact(wsId: string, nbId: string, id: string | null) {
  return useQuery({
    queryKey: oneKey(wsId, nbId, id ?? ""),
    queryFn: () => artifactApi.get(wsId, nbId, id!),
    enabled: !!wsId && !!nbId && !!id,
  });
}

export function useGenerateArtifact(wsId: string, nbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: GenerateArtifactInput) => artifactApi.generate(wsId, nbId, input),
    onSuccess: (art: Artifact) => {
      qc.invalidateQueries({ queryKey: listKey(wsId, nbId) });
      qc.setQueryData(oneKey(wsId, nbId, art.id), art);
      if (art.status === "failed") {
        toast.error("Generation failed", { description: art.error ?? undefined });
      } else {
        toast.success(`${art.title} is ready`);
      }
    },
    onError: (e: any) => toast.error(e?.message ?? "Generation failed"),
  });
}

export function useRegenerateArtifact(wsId: string, nbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => artifactApi.regenerate(wsId, nbId, id),
    onSuccess: (art: Artifact) => {
      qc.invalidateQueries({ queryKey: listKey(wsId, nbId) });
      qc.setQueryData(oneKey(wsId, nbId, art.id), art);
      toast.success("Regenerated");
    },
  });
}

export function useDeleteArtifact(wsId: string, nbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => artifactApi.remove(wsId, nbId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: listKey(wsId, nbId) });
      toast.success("Deleted");
    },
  });
}
