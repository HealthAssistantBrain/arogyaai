import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore, selectAuthRoutingState } from "../../store/authStore";
import { useShallow } from 'zustand/shallow';
import { logOrchestration } from "../../lib/orchestrationDebug";
import { getAuthLifecycle, getAuthenticatedHomeRoute } from "../../router/authRedirects";

export default function GuestGuard() {
  const authState = useAuthStore(useShallow(selectAuthRoutingState));
  const { isHydrated, hasBootstrappedAuth } = authState;
  const location = useLocation();
  const lifecycle = getAuthLifecycle(authState);

  if (lifecycle.phase === 'hydrating' || !isHydrated || !hasBootstrappedAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
        Restoring your session...
      </div>
    );
  }

  if (lifecycle.phase !== 'idle') {
    logOrchestration('route', 'guest_guard.redirect', {
      from: location.pathname,
      to: getAuthenticatedHomeRoute(authState),
      phase: lifecycle.phase,
    });
    return <Navigate to={getAuthenticatedHomeRoute(authState)} replace />;
  }

  return <Outlet />;
}

