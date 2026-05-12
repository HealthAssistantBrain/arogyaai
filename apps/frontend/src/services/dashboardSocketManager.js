import { getApiRootUrl } from '../lib/apiBaseUrl';

const DASHBOARD_WS_ROOT = getApiRootUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
)
  .replace(/localhost/g, '127.0.0.1')
  .replace(/^https:/i, 'wss:')
  .replace(/^http:/i, 'ws:');

const PING_INTERVAL_MS = 25_000;
const SOCKET_STALE_MS = 70_000;
const RECONNECT_SCHEDULE_MS = [1_000, 2_000, 5_000, 10_000, 30_000];

let activeSession = null;
let activeSocket = null;
let reconnectTimer = null;
let pingTimer = null;
let staleTimer = null;
let reconnectAttempt = 0;
let lastSocketActivityAt = 0;
let visibilityListenerBound = false;
const subscribers = new Set();

const isBrowser = () => typeof window !== 'undefined' && typeof document !== 'undefined';
const isVisible = () => !isBrowser() || document.visibilityState === 'visible';

const emit = (event) => {
  subscribers.forEach((listener) => {
    try {
      listener(event);
    } catch (error) {
      console.warn('[dashboardSocket] subscriber failed', error);
    }
  });
};

const clearReconnectTimer = () => {
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
};

const clearPingTimer = () => {
  if (pingTimer) {
    window.clearInterval(pingTimer);
    pingTimer = null;
  }
};

const clearStaleTimer = () => {
  if (staleTimer) {
    window.clearInterval(staleTimer);
    staleTimer = null;
  }
};

const markSocketActivity = () => {
  lastSocketActivityAt = Date.now();
};

const closeActiveSocket = (reason = 'reset') => {
  clearPingTimer();
  clearStaleTimer();
  if (!activeSocket) return;

  const socket = activeSocket;
  activeSocket = null;
  socket.onopen = null;
  socket.onmessage = null;
  socket.onerror = null;
  socket.onclose = null;

  if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
    socket.close(1000, reason);
  }
};

const buildSocketUrl = ({ userId, token }) =>
  `${DASHBOARD_WS_ROOT}/ws/dashboard/${userId}?token=${encodeURIComponent(token)}`;

const startPingLoop = () => {
  clearPingTimer();
  clearStaleTimer();
  markSocketActivity();
  pingTimer = window.setInterval(() => {
    if (activeSocket?.readyState === WebSocket.OPEN) {
      activeSocket.send('ping');
    }
  }, PING_INTERVAL_MS);
  staleTimer = window.setInterval(() => {
    if (!activeSocket || activeSocket.readyState !== WebSocket.OPEN) {
      return;
    }
    if ((Date.now() - lastSocketActivityAt) <= SOCKET_STALE_MS) {
      return;
    }
    emit({ type: 'stale', age: Date.now() - lastSocketActivityAt });
    closeActiveSocket('stale_socket');
    scheduleReconnect('stale_socket');
  }, PING_INTERVAL_MS);
};

const scheduleReconnect = (reason = 'retry') => {
  if (!isBrowser() || !activeSession || reconnectTimer || !isVisible()) {
    return;
  }

  const delay = RECONNECT_SCHEDULE_MS[Math.min(reconnectAttempt, RECONNECT_SCHEDULE_MS.length - 1)];
  reconnectAttempt += 1;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectDashboardSocket();
  }, delay);

  emit({ type: 'reconnecting', reason, delay });
};

export const connectDashboardSocket = () => {
  if (!isBrowser() || !activeSession || !activeSession.userId || !activeSession.token) {
    emit({ type: 'skipped', reason: 'missing_session' });
    return;
  }

  if (!isVisible()) {
    scheduleReconnect('document_hidden');
    return;
  }

  if (activeSocket && (activeSocket.readyState === WebSocket.OPEN || activeSocket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  clearReconnectTimer();
  closeActiveSocket('reconnect');

  const socket = new WebSocket(buildSocketUrl(activeSession));
  activeSocket = socket;
  emit({ type: 'connecting' });

  socket.onopen = () => {
    reconnectAttempt = 0;
    markSocketActivity();
    emit({ type: 'open' });
    startPingLoop();
  };

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      markSocketActivity();
      if (payload?.type === 'dashboard.pong') {
        emit({ type: 'heartbeat' });
        return;
      }
      emit({ type: 'message', payload });
    } catch (error) {
      console.warn('[dashboardSocket] invalid payload ignored', error);
    }
  };

  socket.onerror = () => {
    emit({ type: 'error' });
  };

  socket.onclose = (event) => {
    clearPingTimer();
    clearStaleTimer();
    if (activeSocket === socket) {
      activeSocket = null;
    }
    emit({ type: 'close', code: event.code, reason: event.reason });

    if (activeSession) {
      scheduleReconnect(event.reason || 'socket_closed');
    }
  };
};

export const setDashboardSocketSession = ({ userId = null, token = null, enabled = true } = {}) => {
  const nextSession = enabled && userId && token
    ? { userId, token, sessionKey: `${userId}:${token}` }
    : null;

  if (nextSession?.sessionKey === activeSession?.sessionKey) {
    emit({ type: 'session_unchanged' });
    if (!activeSocket && enabled) {
      connectDashboardSocket();
    }
    return;
  }

  clearReconnectTimer();
  reconnectAttempt = 0;
  activeSession = nextSession;

  if (!activeSession) {
    closeActiveSocket('session_cleared');
    emit({ type: 'idle' });
    return;
  }

  emit({ type: 'session_changed' });
  connectDashboardSocket();
};

export const subscribeDashboardSocket = (listener) => {
  subscribers.add(listener);
  return () => {
    subscribers.delete(listener);
  };
};

if (isBrowser() && !visibilityListenerBound) {
  visibilityListenerBound = true;
  document.addEventListener('visibilitychange', () => {
    if (!activeSession) return;
    if (document.visibilityState === 'visible') {
      connectDashboardSocket();
      return;
    }

    clearReconnectTimer();
  });
}
