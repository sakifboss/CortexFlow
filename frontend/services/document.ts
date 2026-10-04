import { api } from "@/lib/api";
import type { SourceDocument } from "@/types";

const base = (wsId: string, nbId: string) =>
  `/workspaces/${wsId}/notebooks/${nbId}/documents`;

export const documentApi = {
  list: (wsId: string, nbId: string) => api.get<SourceDocument[]>(base(wsId, nbId)),
  upload: (wsId: string, nbId: string, file: File) =>
    api.upload<SourceDocument>(base(wsId, nbId), file),
  get: (wsId: string, nbId: string, id: string) =>
    api.get<SourceDocument>(`${base(wsId, nbId)}/${id}`),
  rename: (wsId: string, nbId: string, id: string, title: string) =>
    api.patch<SourceDocument>(`${base(wsId, nbId)}/${id}`, { title }),
  delete: (wsId: string, nbId: string, id: string) =>
    api.delete<void>(`${base(wsId, nbId)}/${id}`),
  reingest: (wsId: string, nbId: string, id: string) =>
    api.post<SourceDocument>(`${base(wsId, nbId)}/${id}/reingest`),
  downloadUrl: (wsId: string, nbId: string, id: string) =>
    api.get<{ url: string; mime_type: string }>(`${base(wsId, nbId)}/${id}/download-url`),
};
