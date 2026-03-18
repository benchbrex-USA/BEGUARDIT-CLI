// API client — typed fetch wrapper for BeGuardit backend
// In development: proxied via Vite (/api → localhost:8000)
// In production: talks to the API over HTTPS at the configured origin
import type { ApiError } from '../types/api';

function resolveBaseUrl(): string {
  // VITE_API_BASE_URL overrides everything (set in .env.production)
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // In production builds, default to same-origin HTTPS
  if (import.meta.env.PROD) {
    return `${window.location.origin}/api/v1`;
  }
  // Dev: rely on Vite proxy
  return '/api/v1';
}

const BASE = resolveBaseUrl();

/** Read the csrf_token cookie set by the API on login/register. */
function getCsrfToken(): string | undefined {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrf_token='));
  return match ? decodeURIComponent(match.split('=')[1]) : undefined;
}

/** HTTP methods that require a CSRF token header. */
const CSRF_METHODS = new Set(['POST', 'PATCH', 'DELETE']);

class ApiClient {
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {};

    // Only set Content-Type for JSON requests (skip for FormData/multipart)
    if (!(init?.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    // Attach CSRF token for state-changing requests
    const method = (init?.method ?? 'GET').toUpperCase();
    if (CSRF_METHODS.has(method)) {
      const csrf = getCsrfToken();
      if (csrf) {
        headers['X-CSRF-Token'] = csrf;
      }
    }

    const res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      headers: { ...headers, ...init?.headers },
      ...init,
    });

    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as ApiError | null;
      const message = body?.error?.message || `HTTP ${res.status}`;
      const err = new Error(message) as Error & { status: number; code: string };
      err.status = res.status;
      err.code = body?.error?.code || 'UNKNOWN';
      throw err;
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  get<T>(path: string) {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: 'DELETE' });
  }

  upload<T>(path: string, formData: FormData) {
    return this.request<T>(path, {
      method: 'POST',
      body: formData,
    });
  }
}

export const api = new ApiClient();
