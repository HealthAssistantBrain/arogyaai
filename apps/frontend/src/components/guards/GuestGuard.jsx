import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

export default function GuestGuard() {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (isAuthenticated && location.pathname === "/login") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
