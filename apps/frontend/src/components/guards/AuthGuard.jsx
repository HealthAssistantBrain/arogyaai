import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

export default function AuthGuard() {
  const { isAuthenticated, isHydrated, onboardingDone } = useAuthStore();

  if (!isHydrated) return null;

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (!onboardingDone) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Outlet />;
}
