"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentApi } from "@/services/document";
import { toast } from "sonner";

export function useDocuments(wsId: string, nbId: string) {
  return useQuery({
    queryKey: ["documents", wsId, nbId],
    queryFn: () => documentApi.list(wsId, nbId),
    enabled: !!wsId && !!nbId,
    refetchInterval: (q) => {
      // Poll while any document is still processing
      const data = q.state.data;
      return data?.some((d) => !["ready", "failed"].includes(d.status)) ? 3000 : false;
    },
  });
}

export function useUploadDocument(wsId: string, nbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => documentApi.upload(wsId, nbId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", wsId, nbId] });
      toast.success("Upload started — parsing in background");
    },
    onError: (e: any) => toast.error(e.message ?? "Upload failed"),
  });
}

export function useDeleteDocument(wsId: string, nbId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentApi.delete(wsId, nbId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", wsId, nbId] }),
  });
}
