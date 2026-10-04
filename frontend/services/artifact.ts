import { api } from "@/lib/api";
import type {
  Artifact,
  ArtifactKind,
  ArtifactSummary,
  GenerateArtifactInput,
  KindInfo,
} from "@/types";

const base = (wsId: string, nbId: string) =>
  `/workspaces/${wsId}/notebooks/${nbId}/artifacts`;

export const artifactApi = {
  kinds: (wsId: string, nbId: string) => api.get<KindInfo[]>(`${base(wsId, nbId)}/kinds`),

  list: (wsId: string, nbId: string, kind?: ArtifactKind) =>
    api.get<ArtifactSummary[]>(base(wsId, nbId), { params: { kind } }),

  get: (wsId: string, nbId: string, id: string) =>
    api.get<Artifact>(`${base(wsId, nbId)}/${id}`),

  generate: (wsId: string, nbId: string, payload: GenerateArtifactInput) =>
    api.post<Artifact>(base(wsId, nbId), payload),

  update: (
    wsId: string,
    nbId: string,
    id: string,
    patch: { title?: string; content?: Record<string, unknown> },
  ) => api.patch<Artifact>(`${base(wsId, nbId)}/${id}`, patch),

  regenerate: (wsId: string, nbId: string, id: string) =>
    api.post<Artifact>(`${base(wsId, nbId)}/${id}/regenerate`),

  remove: (wsId: string, nbId: string, id: string) =>
    api.delete<void>(`${base(wsId, nbId)}/${id}`),
};
