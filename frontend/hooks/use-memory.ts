"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  memoryApi,
  type MemoryLayer,
  type WriteMemoryInput,
} from "@/services/memory";
import { useWorkspaceStore } from "@/stores/workspace-store";

export function useActiveWorkspaceId(): string | null {
  return useWorkspaceStore((s) => s.current?.id ?? null);
}

export function useMemories(layer?: MemoryLayer) {
  const ws = useActiveWorkspaceId();
  return useQuery({
    queryKey: ["memories", ws, layer ?? "all"],
    queryFn: () => memoryApi.list(ws!, layer),
    enabled: !!ws,
  });
}

export function useWriteMemory() {
  const ws = useActiveWorkspaceId();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: WriteMemoryInput) => memoryApi.write(ws!, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories", ws] });
      toast.success("Memory stored");
    },
    onError: () => toast.error("Failed to store memory"),
  });
}

export function useRecall() {
  const ws = useActiveWorkspaceId();
  return useMutation({
    mutationFn: (vars: {
      query: string;
      layers?: MemoryLayer[];
      limit?: number;
      min_importance?: number;
    }) => memoryApi.recall(ws!, vars.query, vars),
  });
}

export function useConsolidate() {
  const ws = useActiveWorkspaceId();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => memoryApi.consolidate(ws!),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["memories", ws] });
      toast.success(
        `Consolidated ${res.memories_scanned} memories → ${res.clusters_created} clusters, ${res.memories_promoted} promoted`,
      );
    },
    onError: () => toast.error("Consolidation failed"),
  });
}

export function useForget() {
  const ws = useActiveWorkspaceId();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { dry_run: boolean; importance_floor?: number }) =>
      memoryApi.forget(ws!, vars),
    onSuccess: (res) => {
      if (!res.dry_run) {
        qc.invalidateQueries({ queryKey: ["memories", ws] });
        toast.success(`Forgot ${res.deleted} decayed memories`);
      }
    },
    onError: () => toast.error("Forget pass failed"),
  });
}

export function useDeleteMemory() {
  const ws = useActiveWorkspaceId();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => memoryApi.delete(ws!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories", ws] });
      toast.success("Memory deleted");
    },
  });
}
