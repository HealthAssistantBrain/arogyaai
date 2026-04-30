import { apiClient } from '../lib/apiClient';
import {
  registerBrowserNotificationServiceWorker,
  requestBrowserNotificationPermission,
} from './browserNotifications';

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const normalized = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(normalized);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

function describeBrowser() {
  const userAgent = navigator.userAgent || '';
  if (userAgent.includes('Edg/')) return 'Edge';
  if (userAgent.includes('Chrome/')) return 'Chrome';
  if (userAgent.includes('Firefox/')) return 'Firefox';
  if (userAgent.includes('Safari/')) return 'Safari';
  return 'Browser';
}

function currentPlatform() {
  const platform = navigator.userAgentData?.platform || navigator.platform || 'web';
  return String(platform).toLowerCase();
}

function currentDeviceName() {
  return `${describeBrowser()} on ${navigator.userAgentData?.platform || navigator.platform || 'Web'}`;
}

export async function ensurePushSubscription() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Push notifications are not supported in this browser.');
  }

  const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
  if (!vapidPublicKey) {
    throw new Error('Push notifications are not configured for this environment.');
  }

  const permission = await requestBrowserNotificationPermission();
  if (permission !== 'granted') {
    throw new Error('Push notification permission was not granted.');
  }

  await registerBrowserNotificationServiceWorker();
  const registration = await navigator.serviceWorker.ready;

  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    });
  }

  await apiClient.post('/devices/push-subscriptions', {
    subscription: subscription.toJSON(),
    platform: currentPlatform(),
    device_name: currentDeviceName(),
  });

  return subscription;
}

export async function removeCurrentPushSubscription() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
    return false;
  }

  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    return false;
  }

  await apiClient.delete('/devices/push-subscriptions/current', {
    data: { endpoint: subscription.endpoint },
  });
  await subscription.unsubscribe();
  return true;
}
