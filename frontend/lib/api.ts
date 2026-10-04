/**
 * Typed API client.
 *
 * - Reads the JWT from localStorage and attaches it as Bearer token.
 * - On 401, attempts a single token refresh, then retries.
 * - All routes are prefixed with NEXT_PUBLIC_API_URL or proxied via /api.
 */

import { getToken, refreshAccessToken, clearTokens } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
  : "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

interface FetchOpts extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
}

async function request<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const url = buildUrl(path, opts.params);
  const headers = new Headers(opts.headers);

  if (!(opts.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!opts.skipAuth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(url, { ...opts, headers });
  if (res.status === 401 && !opts.skipAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(url, { ...opts, headers });
    }
  }

  if (!res.ok) {
    let body: any = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }
    if (res.status === 401) clearTokens();
    throw new ApiError(
      res.status,
      body?.error?.code ?? "http_error",
      body?.error?.message ?? res.statusText,
      body?.error?.details,
    );
  }

  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

function buildUrl(path: string, params?: FetchOpts["params"]) {
  const url = new URL(
    `${BASE}${path.startsWith("/") ? path : `/${path}`}`,
    typeof window === "undefined" ? "http://localhost" : window.location.origin,
  );
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    });
  }
  return url.toString().replace("http://localhost", "");
}

export const api = {
  get: <T>(path: string, opts?: FetchOpts) => request<T>(path, { ...opts, method: "GET" }),
  post: <T>(path: string, body?: unknown, opts?: FetchOpts) =>
    request<T>(path, { ...opts, method: "POST", body: serialize(body) }),
  patch: <T>(path: string, body?: unknown, opts?: FetchOpts) =>
    request<T>(path, { ...opts, method: "PATCH", body: serialize(body) }),
  put: <T>(path: string, body?: unknown, opts?: FetchOpts) =>
    request<T>(path, { ...opts, method: "PUT", body: serialize(body) }),
  delete: <T>(path: string, opts?: FetchOpts) => request<T>(path, { ...opts, method: "DELETE" }),
  upload: <T>(path: string, file: File, opts?: FetchOpts) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<T>(path, { ...opts, method: "POST", body: fd });
  },
};

function serialize(body?: unknown) {
  if (body === undefined || body instanceof FormData) return body;
  return JSON.stringify(body);
}
