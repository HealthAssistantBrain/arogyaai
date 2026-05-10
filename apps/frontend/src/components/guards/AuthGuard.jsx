import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore, selectAuthRoutingState } from "../../store/authStore";
import { useShallow } from 'zustand/shallow';
import { logOrchestration } from "../../lib/orchestrationDebug";
import { getAuthLifecycle, getProtectedRouteRedirect } from "../../router/authRedirects";
import { ROUTES } from "../../router/routes";

export default function AuthGuard() {
  const authState = useAuthStore(useShallow(selectAuthRoutingState));
  const { isAuthenticated, isHydrated, hasBootstrappedAuth } = authState;
  const location = useLocation();
  const lifecycle = getAuthLifecycle(authState);

  if (lifecycle.phase === 'hydrating' || !isHydrated || !hasBootstrappedAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
        Restoring your session...
      </div>
    );
  }

  if (lifecycle.phase === 'idle' || !isAuthenticated) {
    logOrchestration('route', 'auth_guard.redirect_home', { path: location.pathname });
    return <Navigate to={ROUTES.HOME} replace />;
  }

  if (!lifecycle.stable) {
    logOrchestration('route', 'auth_guard.awaiting_stable_state', {
      path: location.pathname,
      phase: lifecycle.phase,
    });
    return <Outlet />;
  }

  const redirect = getProtectedRouteRedirect(location.pathname, authState);
  if (redirect && redirect !== location.pathname) {
    logOrchestration('route', 'auth_guard.redirect', {
      from: location.pathname,
      to: redirect,
      phase: lifecycle.phase,
    }, 'info');
    return <Navigate to={redirect} replace />;
  }

  logOrchestration('route', 'auth_guard.allow', {
    path: location.pathname,
    phase: lifecycle.phase,
  });
  return <Outlet />;
}

