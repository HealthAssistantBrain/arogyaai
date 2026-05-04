import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { getProtectedRouteRedirect } from "../../router/authRedirects";
import { ROUTES } from "../../router/routes";

export default function AuthGuard() {
  const authState = useAuthStore();
  const { isAuthenticated, isHydrated, isHydratingAuth } = authState;
  const location = useLocation();
  const hasToken = !!authState.token;
  const hasAuthUser = !!authState.user?.id;

  if (!isHydrated || isHydratingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
        Restoring your session...
      </div>
    );
  }

  if (!hasToken || !isAuthenticated) {
    console.debug('[AuthGuard] no token; redirecting to home', { path: location.pathname });
    return <Navigate to={ROUTES.HOME} replace />;
  }

  if (!hasAuthUser) {
    console.debug('[AuthGuard] token present; waiting for /users/me', { path: location.pathname });
    return (
      <div className="flex min-h-screen items-center justify-center bg-background dark:bg-background text-sm font-bold text-slate-500">
        Loading your clinical workspace...
      </div>
    );
  }

  const redirect = getProtectedRouteRedirect(location.pathname, authState);
  if (redirect && redirect !== location.pathname) {
    return <Navigate to={redirect} replace />;
  }

  console.debug('[AuthGuard] route allowed', { path: location.pathname });
  return <Outlet />;
}

