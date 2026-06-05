/**
 * Auth guard. Renders the children only when:
 * - the bootstrap has run, AND
 * - there is a valid user (i.e. ``/api/auth/me`` returned 200).
 *
 * Otherwise navigates to ``/login`` (preserving the original location via
 * the ``next`` query param so the user lands where they were going).
 */
import { type ReactNode, useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export function RequireAuth({ children }: { children?: ReactNode }) {
  const { isAuthenticated, bootstrapped, bootstrap } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (!bootstrapped) {
      void bootstrap();
    }
  }, [bootstrapped, bootstrap]);

  if (!bootstrapped) {
    return (
      <div className="flex items-center justify-center h-screen bg-surface text-ink-muted">
        <div className="text-body-md">Loading…</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  return <>{children ?? <Outlet />}</>;
}
