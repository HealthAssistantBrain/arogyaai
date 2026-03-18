import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const LOOP_THRESHOLD = 3;
const LOOP_WINDOW_MS = 2000;
const REDIRECT_THRESHOLD = 5;
const ESCAPE_ROUTE = '/system/error';

interface HistoryEntry {
  path: string;
  ts: number;
  isRedirect: boolean;
}

let routeHistory: HistoryEntry[] = [];
let consecutiveRedirects = 0;
let loopDetectorActive = true;

export function useRouteLoopDetector() {
  const location = useLocation();

  useEffect(() => {
    if (!loopDetectorActive) return;
    if (location.pathname === ESCAPE_ROUTE || location.pathname === '/maintenance') return;

    const now = Date.now();
    const state = location.state as any;
    const isRedirect = !!state?.isGuardRedirect;

    routeHistory.push({ path: location.pathname, ts: now, isRedirect });
    
    // Prune history
    routeHistory = routeHistory.filter((entry) => now - entry.ts < LOOP_WINDOW_MS);

    // Rule 1: Same route visited 3+ times in the window
    const exactRouteHits = routeHistory.filter((entry) => entry.path === location.pathname);
    if (exactRouteHits.length >= LOOP_THRESHOLD) {
      triggerEscape('same_route_loop', location.pathname);
      return;
    }

    // Rule 2: Redirect chain tracking
    if (isRedirect) {
      consecutiveRedirects++;
    } else {
      consecutiveRedirects = 0;
    }

    if (consecutiveRedirects >= REDIRECT_THRESHOLD) {
      triggerEscape('redirect_chain_loop', `${consecutiveRedirects}_consecutive`);
    }
  }, [location.pathname, location.state]);
}

function triggerEscape(reason: string, detail: string) {
  console.error('[LOOP_DETECTOR]', { reason, detail, history: [...routeHistory] });
  loopDetectorActive = false;
  routeHistory = [];
  consecutiveRedirects = 0;

  const store = useAuthStore.getState();
  store.hardReset ? store.hardReset() : store.logout();
  
  window.location.replace(`${ESCAPE_ROUTE}?reason=${reason}&detail=${encodeURIComponent(detail)}`);
  
  setTimeout(() => { loopDetectorActive = true; }, 3000);
}
