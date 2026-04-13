import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { requestBrowserNotificationPermission } from '../services/browserNotifications';

const AUTH_ROUTES = ['/login', '/signup', '/forgot-password', '/reset-password'];
let hasRequestedBrowserNotificationPermission = false;

const BrowserNotificationBootstrap = () => {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const hasRequestedPermission = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      return;
    }

    const onAuthFlowRoute = AUTH_ROUTES.some((path) => location.pathname.startsWith(path));
    const shouldPrompt = isHydrated && Notification.permission === 'default' && (isAuthenticated || onAuthFlowRoute);

    if (!shouldPrompt || hasRequestedPermission.current || hasRequestedBrowserNotificationPermission) {
      return;
    }

    hasRequestedPermission.current = true;
    hasRequestedBrowserNotificationPermission = true;
    void requestBrowserNotificationPermission().catch(() => {});
  }, [isAuthenticated, isHydrated, location.pathname]);

  return null;
};

export default BrowserNotificationBootstrap;
