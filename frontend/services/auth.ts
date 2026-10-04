import { api } from "@/lib/api";
import type { TokenPair, User } from "@/types";

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    api.post<TokenPair>("/auth/register", { email, password, full_name }),

  login: (email: string, password: string, mfa_code?: string) =>
    api.post<TokenPair>("/auth/login", { email, password, mfa_code }),

  me: () => api.get<User>("/auth/me"),

  updateMe: (patch: { full_name?: string; avatar_url?: string }) =>
    api.patch<User>("/auth/me", patch),

  requestReset: (email: string) =>
    api.post<{ message: string; dev_token?: string }>("/auth/password-reset/request", { email }),

  confirmReset: (token: string, password: string) =>
    api.post<void>("/auth/password-reset/confirm", { token, password }),

  setupMfa: () => api.get<{ secret: string; provisioning_uri: string }>("/auth/mfa/setup", {}),
  enableMfa: (code: string) => api.post<void>("/auth/mfa/enable", { code }),
  disableMfa: (code: string) => api.post<void>("/auth/mfa/disable", { code }),
};
