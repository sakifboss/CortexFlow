"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workspaceApi } from "@/services/workspace";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { toast } from "sonner";

export function useWorkspaces() {
  const setList = useWorkspaceStore((s) => s.setList);
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: async () => {
      const list = await workspaceApi.list();
      setList(list);
      return list;
    },
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      workspaceApi.create(name, description),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success("Workspace created");
    },
  });
}
