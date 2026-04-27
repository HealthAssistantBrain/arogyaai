import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { getAuthenticatedHomeRoute } from "../../router/authRedirects";

export default function GuestGuard() {
  const authState = useAuthStore();
  const { isAuthenticated, isHydrated, isHydratingAuth } = authState;
  const location = useLocation();
  const hasAuthUser = !!authState.user?.id;
  const isSignedIn = isAuthenticated && hasAuthUser;

  if (!isHydrated || isHydratingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f5f8] dark:bg-[#0B0819] text-sm font-bold text-slate-500">
        Restoring your session...
      </div>
    );
  }

  if (isSignedIn && ["/login", "/signup"].includes(location.pathname)) {
    return <Navigate to={getAuthenticatedHomeRoute(authState)} replace />;
  }

  return <Outlet />;
}
