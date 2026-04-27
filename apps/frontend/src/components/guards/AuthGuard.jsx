import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { getProtectedRouteRedirect } from "../../router/authRedirects";
import { ROUTES } from "../../router/routes";

export default function AuthGuard() {
  const authState = useAuthStore();
  const { isAuthenticated, isHydrated, isHydratingAuth } = authState;
  const location = useLocation();
  const hasAuthUser = !!authState.user?.id;

  if (!isHydrated || isHydratingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f5f8] dark:bg-[#0B0819] text-sm font-bold text-slate-500">
        Restoring your session...
      </div>
    );
  }

  if (!isAuthenticated || !hasAuthUser) {
    return <Navigate to={ROUTES.HOME} replace />;
  }

  const redirect = getProtectedRouteRedirect(location.pathname, authState);
  if (redirect && redirect !== location.pathname) {
    return <Navigate to={redirect} replace />;
  }

  return <Outlet />;
}
