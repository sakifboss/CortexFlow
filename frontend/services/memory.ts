import { api } from "@/lib/api";

export type MemoryLayer =
  | "working"
  | "episodic"
  | "semantic"
  | "procedural"
  | "long_term";

export interface Memory {
  id: string;
  layer: MemoryLayer;
  content: string;
  summary: string | null;
  importance: number;
  access_count: number;
  last_accessed_at: string | null;
  decay_rate: number;
  notebook_id: string | null;
  conversation_id: string | null;
  properties: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryHit {
  memory: Memory;
  similarity: number;
  effective_importance: number;
  score: number;
}

export interface RecallResult {
  query: string;
  hits: MemoryHit[];
}

export interface ConsolidateResult {
  clusters_created: number;
  memories_promoted: number;
  memories_scanned: number;
  cluster_ids: string[];
}

export interface ForgetResult {
  candidates: number;
  deleted: number;
  dry_run: boolean;
  freed_ids: string[];
}

export interface WriteMemoryInput {
  content: string;
  layer?: MemoryLayer;
  summary?: string;
  importance?: number;
  notebook_id?: string;
}

const base = (ws: string) => `/workspaces/${ws}/memory`;

export const memoryApi = {
  list: (ws: string, layer?: MemoryLayer, limit = 100) =>
    api.get<Memory[]>(base(ws), {
      params: { layer, limit },
    }),

  write: (ws: string, input: WriteMemoryInput) =>
    api.post<Memory>(base(ws), input),

  recall: (
    ws: string,
    query: string,
    opts?: { layers?: MemoryLayer[]; limit?: number; min_importance?: number },
  ) =>
    api.post<RecallResult>(`${base(ws)}/recall`, {
      query,
      layers: opts?.layers,
      limit: opts?.limit ?? 8,
      min_importance: opts?.min_importance ?? 0,
    }),

  consolidate: (
    ws: string,
    opts?: {
      layer?: MemoryLayer;
      max_cluster_distance?: number;
      promote_threshold?: number;
    },
  ) =>
    api.post<ConsolidateResult>(`${base(ws)}/consolidate`, {
      layer: opts?.layer ?? "episodic",
      max_cluster_distance: opts?.max_cluster_distance ?? 0.35,
      promote_threshold: opts?.promote_threshold ?? 0.7,
    }),

  forget: (
    ws: string,
    opts?: { layer?: MemoryLayer; importance_floor?: number; dry_run?: boolean },
  ) =>
    api.post<ForgetResult>(`${base(ws)}/forget`, {
      layer: opts?.layer,
      importance_floor: opts?.importance_floor ?? 0.15,
      dry_run: opts?.dry_run ?? true,
    }),

  delete: (ws: string, memoryId: string) =>
    api.delete<void>(`${base(ws)}/${memoryId}`),
};
