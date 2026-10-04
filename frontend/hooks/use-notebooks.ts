"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notebookApi } from "@/services/notebook";
import { toast } from "sonner";

export function useNotebooks(wsId: string) {
  return useQuery({
    queryKey: ["notebooks", wsId],
    queryFn: () => notebookApi.list(wsId),
    enabled: !!wsId,
  });
}

export function useCreateNotebook(wsId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: notebookApi.create.bind(null, wsId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notebooks", wsId] });
      toast.success("Notebook created");
    },
  });
}

export function useConversations(wsId: string, notebookId: string) {
  return useQuery({
    queryKey: ["conversations", wsId, notebookId],
    queryFn: () => notebookApi.conversations(wsId, notebookId),
    enabled: !!wsId && !!notebookId,
  });
}

export function useMessages(wsId: string, notebookId: string, conversationId: string | null) {
  return useQuery({
    queryKey: ["messages", wsId, notebookId, conversationId],
    queryFn: () => notebookApi.messages(wsId, notebookId, conversationId!),
    enabled: !!conversationId,
  });
}
