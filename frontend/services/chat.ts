import { api } from "@/lib/api";
import type { Message, SearchHit } from "@/types";

export const chatApi = {
  send: (
    wsId: string,
    nbId: string,
    convId: string,
    payload: { message: string; agent?: string; retrieve_k?: number },
  ) =>
    api.post<Message>(
      `/workspaces/${wsId}/notebooks/${nbId}/conversations/${convId}`,
      payload,
    ),
};

export const searchApi = {
  search: (
    wsId: string,
    payload: {
      query: string;
      notebook_id?: string;
      document_ids?: string[];
      mode?: "semantic" | "keyword" | "hybrid" | "graph" | "memory";
      limit?: number;
    },
  ) => api.post<{ query: string; mode: string; hits: SearchHit[]; took_ms: number }>(
    `/workspaces/${wsId}/search`,
    payload,
  ),
};
