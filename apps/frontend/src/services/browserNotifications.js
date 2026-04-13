const DEFAULT_NOTIFICATION_ICON = '/vite.svg';
const DEFAULT_NOTIFICATION_URL = '/notifications';

export const registerBrowserNotificationServiceWorker = async () => {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return null;
  }

  try {
    return await navigator.serviceWorker.register('/sw.js');
  } catch (error) {
    console.warn('[browserNotifications] Service worker registration failed:', error);
    return null;
  }
};

export const requestBrowserNotificationPermission = async () => {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }

  if (Notification.permission === 'default') {
    try {
      return await Notification.requestPermission();
    } catch (error) {
      console.warn('[browserNotifications] Permission request failed:', error);
      return Notification.permission;
    }
  }

  return Notification.permission;
};

export const showBrowserNotification = async ({
  title = 'ArogyaAI',
  body = '',
  icon = DEFAULT_NOTIFICATION_ICON,
  url = DEFAULT_NOTIFICATION_URL,
  data = {},
} = {}) => {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return false;
  }

  if (Notification.permission !== 'granted') {
    return false;
  }

  const payload = {
    title,
    options: {
      body,
      icon,
      badge: icon,
      data: {
        url,
        ...data,
      },
    },
  };

  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.ready;
      if (registration?.active) {
        registration.active.postMessage({
          type: 'AROGYAAI_BROWSER_NOTIFICATION',
          payload,
        });
        return true;
      }
    } catch (error) {
      console.warn('[browserNotifications] Service worker notify failed, falling back to Notification API:', error);
    }
  }

  new Notification(payload.title, payload.options);
  return true;
};
