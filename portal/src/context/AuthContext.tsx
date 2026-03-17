// Auth context — provides current user, tenant, and auth actions
import { createContext, useContext, useCallback, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchMe, login as loginApi, logout as logoutApi, queryKeys } from '../api/queries';
import type { MeResponse } from '../types/api';

interface AuthState {
  user: MeResponse['user'] | null;
  tenantId: string | null;
  role: string;
  memberships: MeResponse['memberships'];
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.me,
    queryFn: fetchMe,
    retry: false,
    staleTime: 5 * 60_000,
  });

  const login = useCallback(async (email: string, password: string) => {
    await loginApi(email, password);
    await qc.invalidateQueries({ queryKey: queryKeys.me });
  }, [qc]);

  const logout = useCallback(async () => {
    await logoutApi();
    qc.clear();
  }, [qc]);

  const value: AuthState = {
    user: data?.user ?? null,
    tenantId: data?.current_tenant_id ?? null,
    role: data?.current_role ?? 'viewer',
    memberships: data?.memberships ?? [],
    isLoading,
    isAuthenticated: !!data?.user && !isError,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
