self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};

  if (type !== 'AROGYAAI_BROWSER_NOTIFICATION' || !payload?.title) {
    return;
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.options?.body || '',
      icon: payload.options?.icon || '/vite.svg',
      badge: payload.options?.badge || '/vite.svg',
      data: {
        url: payload.options?.data?.url || '/notifications',
        ...payload.options?.data,
      },
    })
  );
});

self.addEventListener('push', (event) => {
  let data = {};

  try {
    data = event.data?.json?.() || {};
  } catch {
    data = {};
  }

  const title = data.title || 'ArogyaAI';
  const body = data.body || 'You have a new notification.';
  const icon = data.icon || '/vite.svg';
  const url = data.url || '/notifications';

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon,
      badge: icon,
      data: { url, ...data },
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const targetUrl = event.notification?.data?.url || '/notifications';

  event.waitUntil(
    (async () => {
      const allClients = await clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of allClients) {
        if ('focus' in client) {
          await client.focus();
          if ('navigate' in client) {
            await client.navigate(targetUrl);
          }
          return;
        }
      }

      if (clients.openWindow) {
        await clients.openWindow(targetUrl);
      }
    })()
  );
});
