/**
 * Token storage + refresh helper.
 *
 * Tokens live in localStorage (client-only). SSR routes guard via middleware
 * that checks for the presence of an access token cookie mirrored on login.
 */
import { api } from "./api";

const ACCESS_KEY = "cf_access_token";
const REFRESH_KEY = "cf_refresh_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  // Mirror to cookie so middleware can guard SSR routes
  document.cookie = `${ACCESS_KEY}=${access}; path=/; max-age=${60 * 60 * 24 * 14}; SameSite=Lax`;
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  document.cookie = `${ACCESS_KEY}=; path=/; max-age=0`;
}

let refreshing: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  if (refreshing) return refreshing;

  refreshing = (async () => {
    try {
      const res = await api.post<{ access_token: string }>("/auth/refresh", {
        refresh_token: refresh,
      });
      if (typeof window !== "undefined") {
        localStorage.setItem(ACCESS_KEY, res.access_token);
        document.cookie = `${ACCESS_KEY}=${res.access_token}; path=/; max-age=${60 * 60 * 24 * 14}; SameSite=Lax`;
      }
      return res.access_token;
    } catch {
      clearTokens();
      return null;
    } finally {
      refreshing = null;
    }
  })();

  return refreshing;
}
