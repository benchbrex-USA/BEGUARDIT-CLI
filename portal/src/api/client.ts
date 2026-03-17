// API client — typed fetch wrapper for BeGuardit backend
// All requests go through the Vite dev proxy (/api → localhost:8000)

import type { ApiError } from '../types/api';

const BASE = '/api/v1';

class ApiClient {
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...init?.headers },
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
    return this.request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
  }

  patch<T>(path: string, body?: unknown) {
    return this.request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined });
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: 'DELETE' });
  }
}

export const api = new ApiClient();
