import { useAuthStore } from '../store/authStore';

export type InitResult = { route: string | null; cause: string } | null;

export async function INIT_RESOLVER(): Promise<InitResult> {
  console.log('INIT START');

  // ─── Step 1: Wait for Zustand store to rehydrate from localStorage ───────
  await new Promise<void>((resolve) => {
    const state = useAuthStore.getState();
    if (state.isHydrated) {
      resolve();
      return;
    }
    // Subscribe and wait; bail out after 3 s to avoid hanging
    const timer = setTimeout(resolve, 3000);
    const unsub = useAuthStore.subscribe((s) => {
      if (s.isHydrated) {
        clearTimeout(timer);
        unsub();
        resolve();
      }
    });
  });

  // ─── Step 2: Read token from the persisted Zustand store ─────────────────
  // authStore.js persists the token under the key "arogyaai-auth" in
  // localStorage. We read it from the live store (already rehydrated above).
  const store = useAuthStore.getState();
  const token: string | null = store.token ?? null;

  console.log('TOKEN:', token ? `${token.slice(0, 20)}…` : null);

  // ─── Step 3: No token → send to landing / login ───────────────────────────
  if (!token) {
    return { route: null, cause: 'No token — guest user' };
    // Returning null lets the router load normally; guards redirect to /login
  }

  // ─── Step 4: Verify with backend ─────────────────────────────────────────
  const baseUrl = (
    (import.meta as any).env?.VITE_API_BASE_URL ||
    (import.meta as any).env?.VITE_API_URL ||
    'http://localhost:8000'
  ).replace(/\/$/, '');

  try {
    const response = await fetch(`${baseUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(5000),
    });

    console.log('AUTH STATUS:', response.status);

    // ─── 401 / 403: token is dead ──────────────────────────────────────────
    if (response.status === 401 || response.status === 403) {
      store.hardReset ? store.hardReset() : store.logout();
      return { route: '/login', cause: 'Token rejected by server' };
    }

    if (!response.ok) {
      // Non-auth error (500, network, etc.) – don't wipe token, just let
      // the router load and let the individual pages handle the error.
      return { route: null, cause: `Backend error ${response.status}` };
    }

    // ─── 200: token valid ─────────────────────────────────────────────────
    const data = await response.json();
    console.log('AUTH RESPONSE DATA:', data);

    // Sync Zustand with the fresh server state
    store.setUser(data);

    // Email not verified → gate
    if (data.is_email_verified === false) {
      return { route: '/email-verification', cause: 'Email unverified' };
    }

    // Onboarding not done → step gate (non-blocking if endpoint missing)
    if (data.is_onboarding_done === false) {
      return {
        route: `/onboarding/step-${store.onboardingStep || 1}`,
        cause: 'Onboarding incomplete',
      };
    }

    // All clear — let the router load its own routing from here
    return { route: null, cause: 'Authenticated and fully onboarded' };

  } catch (err: any) {
    // Network failure — DON'T clear the token; fall through so the user
    // can still see the cached page and handle errors inline.
    console.warn('INIT_RESOLVER network error:', err?.message);
    return { route: null, cause: `Network error: ${err?.message}` };
  }
}
