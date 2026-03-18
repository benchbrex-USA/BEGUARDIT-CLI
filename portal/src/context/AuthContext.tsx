// Auth context — deprecated shim, delegates to Zustand authStore.
// Kept for backward compatibility; prefer importing useAuthStore directly.
import { useAuthStore } from '../stores/authStore';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // No-op wrapper — Zustand stores don't need providers
  return <>{children}</>;
}

export function useAuth() {
  const store = useAuthStore();
  return {
    user: store.user,
    tenantId: store.tenantId,
    role: store.role,
    memberships: store.memberships,
    isLoading: store.isLoading,
    isAuthenticated: store.isAuthenticated,
    login: store.login,
    logout: store.logout,
  };
}
