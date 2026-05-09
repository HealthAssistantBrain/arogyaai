import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { getAuthenticatedHomeRoute } from "../../router/authRedirects";

export default function GuestGuard() {
  const authState = useAuthStore();
  const { isAuthenticated, isHydrated, isHydratingAuth, authBootstrapStatus, lastHydrationError } = authState;
  const location = useLocation();
  const hasToken = !!authState.token;
  const hasAuthUser = !!authState.user?.id;
  const isSignedIn = isAuthenticated && hasAuthUser;

  if (!isHydrated || isHydratingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
        Restoring your session...
      </div>
    );
  }

  if (hasToken && isAuthenticated && !hasAuthUser) {
    if (authBootstrapStatus === 'degraded' || lastHydrationError) {
      console.warn('[GuestGuard] auth degraded without synchronized user; allowing guest route', { path: location.pathname });
      return <Outlet />;
    }

    console.debug('[GuestGuard] token present; waiting for /users/me', { path: location.pathname });
    return (
      <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
        Loading your clinical workspace...
      </div>
    );
  }

  if (isSignedIn && ["/login", "/signup"].includes(location.pathname)) {
    return <Navigate to={getAuthenticatedHomeRoute(authState)} replace />;
  }

  return <Outlet />;
}

