import { useAuthStore } from '../store/authStore';

export type InitResult = { route: string | null; cause: string } | null;

export async function INIT_RESOLVER(): Promise<InitResult> {
  console.log('INIT START');

  // Ensure persisted auth is loaded before making INIT decisions.
  await (useAuthStore as any).persist?.rehydrate?.();

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

  // ─── Step 3: No token → login ──────────────────────────────────────────────
  if (!token) {
    // #region agent log (INIT no token decision)
    fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H4', location: 'src/router/INIT_RESOLVER.ts:noToken', message: 'INIT no token -> /login', data: { tokenPresent: false }, timestamp: Date.now() }) }).catch(() => { });
    // #endregion
    return { route: '/login', cause: 'No token — guest user' };
  }

  // ─── Step 4: Verify with backend ─────────────────────────────────────────
  const baseUrl = (
    (import.meta as any).env?.VITE_API_BASE_URL ||
    (import.meta as any).env?.VITE_API_URL ||
    'http://localhost:8000'
  ).replace(/\/$/, '');

  try {
    const response = await fetch(`${baseUrl}/api/v1/users/me`, {
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

    // #region agent log (INIT_RESOLVER auth/me payload)
    fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'pre-fix', hypothesisId: 'H2', location: 'src/router/INIT_RESOLVER.ts:authMe', message: 'INIT_RESOLVER /auth/me parsed (onboarding fields presence)', data: { has_is_onboarding_done: data?.is_onboarding_done !== undefined, is_onboarding_done: data?.is_onboarding_done, has_onboarding_step: data?.onboarding_step !== undefined, onboarding_step: data?.onboarding_step }, timestamp: Date.now() }) }).catch(() => { });
    // #endregion

    // Sync Zustand with the fresh server state
    store.setUser(data);
    store.setOnboardingStatus({
      onboardingDone: data?.onboardingDone ?? data?.is_onboarding_done ?? false,
      onboardingStep: data?.onboardingStep ?? data?.onboarding_step ?? 1,
    });

    const isEmailVerified = data?.isEmailVerified ?? data?.is_email_verified ?? false;
    const onboardingDone = data?.onboardingDone ?? data?.is_onboarding_done ?? false;
    const onboardingStepRaw = data?.onboardingStep ?? data?.onboarding_step ?? store.onboardingStep ?? 1;
    const onboardingStep = Number.isFinite(Number(onboardingStepRaw)) ? Number(onboardingStepRaw) : 1;

    // ── PHASE 1: Email verification NOT enforced ──────────────────────────
    // Re-enable in Phase 2:
    // if (isEmailVerified === false) {
    //   return { route: '/email-verification', cause: 'Email unverified' };
    // }
    // ──────────────────────────────────────────────────────────────────────

    // #region agent log (INIT_RESOLVER decision)
    fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H4', location: 'src/router/INIT_RESOLVER.ts:decision', message: 'INIT_RESOLVER global decision inputs', data: { isEmailVerified, onboardingDone, onboardingStep, store_onboardingDone: store.onboardingDone, store_onboardingStep: store.onboardingStep }, timestamp: Date.now() }) }).catch(() => { });
    // #endregion

    if (!onboardingDone) {
      return {
        route: `/onboarding/step-${onboardingStep || 1}`,
        cause: 'Onboarding incomplete',
      };
    }

    // #region agent log (INIT complete -> dashboard)
    fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H4', location: 'src/router/INIT_RESOLVER.ts:done', message: 'INIT onboarded -> /dashboard', data: { is_email_verified: data?.is_email_verified, onboardingDone, onboardingStep }, timestamp: Date.now() }) }).catch(() => { });
    // #endregion
    return { route: '/dashboard', cause: 'Authenticated and fully onboarded' };

  } catch (err: any) {
    console.warn('INIT_RESOLVER network error:', err?.message);
    return { route: '/login', cause: `Network error: ${err?.message}` };
  }
}
