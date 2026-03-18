// Zustand auth store (§10.2)
// Replaces React Context for auth state management.
// Holds current user, tenant, role, memberships, and auth actions.
import { create } from 'zustand';
import { api } from '../api/client';
import type { MeResponse, Membership, User } from '../types/api';

interface AuthState {
  user: User | null;
  tenantId: string | null;
  role: string;
  memberships: Membership[];
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;

  // Actions
  fetchMe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  switchTenant: (tenantId: string) => Promise<void>;
  reset: () => void;
}

const INITIAL: Pick<AuthState, 'user' | 'tenantId' | 'role' | 'memberships' | 'isLoading' | 'isAuthenticated' | 'error'> = {
  user: null,
  tenantId: null,
  role: 'viewer',
  memberships: [],
  isLoading: true,
  isAuthenticated: false,
  error: null,
};

export const useAuthStore = create<AuthState>((set) => ({
  ...INITIAL,

  fetchMe: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.get<MeResponse>('/auth/me');
      set({
        user: data.user,
        tenantId: data.current_tenant_id,
        role: data.current_role,
        memberships: data.memberships,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      set({ ...INITIAL, isLoading: false });
    }
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.post('/auth/login', { email, password });
      // Re-fetch full profile after login sets the session cookie
      const data = await api.get<MeResponse>('/auth/me');
      set({
        user: data.user,
        tenantId: data.current_tenant_id,
        role: data.current_role,
        memberships: data.memberships,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      set({ isLoading: false, error: err instanceof Error ? err.message : 'Login failed' });
      throw err;
    }
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Proceed even if the server call fails
    }
    set({ ...INITIAL, isLoading: false });
  },

  switchTenant: async (tenantId: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.post('/auth/switch-tenant', { tenant_id: tenantId });
      const data = await api.get<MeResponse>('/auth/me');
      set({
        user: data.user,
        tenantId: data.current_tenant_id,
        role: data.current_role,
        memberships: data.memberships,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      set({ isLoading: false, error: err instanceof Error ? err.message : 'Tenant switch failed' });
      throw err;
    }
  },

  reset: () => set({ ...INITIAL, isLoading: false }),
}));
