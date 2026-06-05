/**
 * Convenience hook on top of `useAuthStore`. Components should prefer this
 * over reading the store directly so the React subscription semantics are
 * consistent.
 */
import { useAuthStore } from '@/stores/authStore';
import type { UserRole } from '@/types/domain';

export function useAuth() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const bootstrapped = useAuthStore((s) => s.bootstrapped);
  const setSession = useAuthStore((s) => s.setSession);
  const clear = useAuthStore((s) => s.clear);

  const bootstrap = useAuthStore((s) => s.bootstrap);

  return {
    token,
    user,
    role: user?.role as UserRole | undefined,
    isAuthenticated: !!token && !!user,
    bootstrapped,
    setSession,
    clear,
    bootstrap,
  };
}
