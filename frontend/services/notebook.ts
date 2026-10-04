import { api } from "@/lib/api";
import type { Conversation, Message, Notebook } from "@/types";

const base = (wsId: string) => `/workspaces/${wsId}/notebooks`;

export const notebookApi = {
  list: (wsId: string) => api.get<Notebook[]>(base(wsId)),
  create: (wsId: string, payload: { title: string; description?: string; emoji?: string }) =>
    api.post<Notebook>(base(wsId), payload),
  get: (wsId: string, id: string) => api.get<Notebook>(`${base(wsId)}/${id}`),
  update: (wsId: string, id: string, patch: Partial<Notebook>) =>
    api.patch<Notebook>(`${base(wsId)}/${id}`, patch),
  delete: (wsId: string, id: string) => api.delete<void>(`${base(wsId)}/${id}`),

  conversations: (wsId: string, notebookId: string) =>
    api.get<Conversation[]>(`${base(wsId)}/${notebookId}/conversations`),
  createConversation: (
    wsId: string,
    notebookId: string,
    payload: { title?: string; agent?: string },
  ) => api.post<Conversation>(`${base(wsId)}/${notebookId}/conversations`, payload),
  messages: (wsId: string, notebookId: string, conversationId: string) =>
    api.get<Message[]>(
      `${base(wsId)}/${notebookId}/conversations/${conversationId}/messages`,
    ),
};
