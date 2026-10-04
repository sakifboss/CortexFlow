import { api } from "@/lib/api";
import type { Member, Role, Workspace } from "@/types";

export const workspaceApi = {
  list: () => api.get<Workspace[]>("/workspaces"),
  create: (name: string, description?: string) =>
    api.post<Workspace>("/workspaces", { name, description }),
  get: (id: string) => api.get<Workspace>(`/workspaces/${id}`),
  update: (id: string, patch: Partial<Pick<Workspace, "name" | "description" | "settings">>) =>
    api.patch<Workspace>(`/workspaces/${id}`, patch),
  delete: (id: string) => api.delete<void>(`/workspaces/${id}`),

  members: (id: string) => api.get<Member[]>(`/workspaces/${id}/members`),
  addMember: (id: string, email: string, role: Role = "member") =>
    api.post<Member>(`/workspaces/${id}/members`, { email, role }),
  setRole: (id: string, userId: string, role: Role) =>
    api.patch<void>(`/workspaces/${id}/members/${userId}`, { role }),
  removeMember: (id: string, userId: string) =>
    api.delete<void>(`/workspaces/${id}/members/${userId}`),
};
