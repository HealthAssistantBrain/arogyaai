import { create } from 'zustand'
import { persist, devtools } from 'zustand/middleware'
import { isSystemLocked } from '../lib/systemLock'

// ── Patch 7: isHydrated prevents guard decisions before Zustand hydrates from localStorage
// ── Patch 4: role field added for future role-based access control (no UI impact)
// ── Bug Fix: logout() must NOT wipe onboarding state. onboardingDone / onboardingStep
//    are user-level persistent data, not session data. They survive across login cycles.

export const useAuthStore = create(
  devtools(
    persist(
      (set, get) => ({
        // Trace state for debugging
        logOnboardingState: () => console.log("ONBOARDING STATE:", get()),
        user: null,
        token: null,
        refreshToken: null,      // ← Added for session revocation
        isAuthenticated: false,
        isEmailVerified: false,
        onboardingStep: 1,       // onboarding starts at step 1
        onboardingDone: false,
        role: 'user',  // ← 'user' | 'doctor' | 'admin' (Patch 4)
        isHydrated: false,   // ← set to true after persist rehydration (Patch 7)
        isHydratingAuth: false,   // ← network fetching lock

        setUser: (user) =>
          set({ user, isAuthenticated: true }, false, 'setUser'),

        setToken: (token) => {
          // ── SECTION 5: TOKEN VALIDATION ──
          if (!token || typeof token !== 'string' || token.trim() === '') {
            // Invalid token → nullify
            set({ token: null }, false, 'setToken')
            return
          }
          set({ token }, false, 'setToken')
        },

        setRefreshToken: (refreshToken) => {
          set({ refreshToken }, false, 'setRefreshToken')
        },

        setEmailVerified: () =>
          set({ isEmailVerified: true }, false, 'setEmailVerified'),

        setOnboardingStatus: (data) => {
          const onboardingDone = data?.onboardingDone ?? data?.is_onboarding_done ?? false
          const rawStep = data?.onboardingStep ?? data?.onboarding_step ?? 1
          const normalizedStep = Number.isFinite(Number(rawStep)) ? Number(rawStep) : 1
          const onboardingStep = onboardingDone
            ? 6
            : (normalizedStep >= 1 && normalizedStep <= 5 ? normalizedStep : 1)
          // #region agent log (setOnboardingStatus normalization)
          fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H9', location: 'src/store/authStore.js:setOnboardingStatus', message: 'setOnboardingStatus normalized payload', data: { raw_onboardingDone: data?.onboardingDone ?? data?.is_onboarding_done, raw_onboardingStep: data?.onboardingStep ?? data?.onboarding_step, onboardingDone, onboardingStep }, timestamp: Date.now() }) }).catch(() => { });
          // #endregion
          set({ onboardingDone, onboardingStep }, false, 'setOnboardingStatus')
        },

        setOnboardingStep: (step) => {
          // ── SECTION 4: FINALIZE ONBOARDING LOCK ──
          // Once onboardingDone is true, freeze onboarding state.
          // Ignore ANY state updates attempting to modify onboarding step backwards.
          if (get().onboardingDone === true) return;

          const requestedStep = Number.isFinite(Number(step)) ? Number(step) : 1
          const safeStep = requestedStep >= 1 && requestedStep <= 6 ? requestedStep : 1

          // PREVENT BACKWARD DOWNGRADES: if they are editing a previous step,
          // do not overwrite their max progress.
          const maxStep = Math.max(get().onboardingStep || 1, safeStep);

          fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H9', location: 'src/store/authStore.js:setOnboardingStep', message: 'setOnboardingStep requested/clamped', data: { requestedStep, safeStep, maxStep, currentOnboardingDone: get().onboardingDone, currentPath: window?.location?.pathname }, timestamp: Date.now() }) }).catch(() => { });

          set({ onboardingStep: maxStep }, false, 'setOnboardingStep')
        },

        setHydrated: () =>
          set({ isHydrated: true }, false, 'setHydrated'),

        // ── CRITICAL ────────────────────────────────────────────────────────
        // completeOnboarding MUST be called BEFORE navigate()
        // in OnboardingCompletion.jsx — if navigate() fires first
        // the OnboardingGuard reads onboardingDone=false and
        // redirects back to the last step creating an infinite loop
        // ────────────────────────────────────────────────────────────────────
        completeOnboarding: async () => {
          try {
            const token = get().token;
            // Persist to backend so reload doesn't trigger recursion
            await fetch('http://localhost:8000/api/v1/users/me', {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({ is_onboarding_done: true, onboarding_step: 6 })
            });

            set(
              { onboardingDone: true, onboardingStep: 6 },
              false,
              'completeOnboarding'
            );
          } catch (err) {
            console.error("Failed to persist onboarding completion:", err);
            // Fallback: update local state anyway
            set({ onboardingDone: true, onboardingStep: 6 });
          }
        },

        // ── Auth Hydration Logic ───────────────────────────────────────────
        // Called by GlobalStateValidator to sync JWT token with true DB state.
        // Accepts an optional tokenOverride so callers like Signup can set the
        // token and start hydration in ONE atomic Zustand update, preventing the
        // brief "ghost token" state (token set, isAuthenticated still false) that
        // guards detect as invalid and incorrectly call logout().
        // ────────────────────────────────────────────────────────────────────
        hydrateAuth: async (tokenOverride = null) => {
          const token = tokenOverride !== null ? tokenOverride : get().token

          if (!token) {
            set({ isHydrated: true, isHydratingAuth: false })
            return
          }

          // Atomic: if an explicit token was passed, set it together with
          // isHydratingAuth=true so guards never see the ghost-token state.
          if (tokenOverride !== null) {
            set({ token: tokenOverride, isHydratingAuth: true }, false, 'hydrateAuth_start')
          } else {
            set({ isHydratingAuth: true })
          }

          try {
            // Hit the newly scaffolded backend /api/v1/users/me endpoint
            const res = await fetch('http://localhost:8000/api/v1/users/me', {
              headers: { Authorization: `Bearer ${token}` },
              credentials: 'include'
            })

            if (!res.ok) throw new Error('Token rejected by server')

            const envelope = await res.json()
            const dbUser = envelope.data

            const normalizedOnboardingDone = dbUser?.is_onboarding_done ?? false
            const stepFromServerRaw = dbUser?.onboarding_step ?? dbUser?.onboardingStep
            const stepFromServer = Number.isFinite(Number(stepFromServerRaw))
              ? Number(stepFromServerRaw)
              : null
            const persistedStepRaw = get().onboardingStep
            const persistedStep = Number.isFinite(Number(persistedStepRaw))
              ? Number(persistedStepRaw)
              : null
            // Incomplete onboarding must stay inside steps 1..5; never hydrate as step 6.
            const fallbackIncompleteStep =
              persistedStep !== null && persistedStep >= 1 && persistedStep <= 5
                ? persistedStep
                : 1
            const normalizedOnboardingStep = normalizedOnboardingDone
              ? 6
              : (
                stepFromServer !== null && stepFromServer >= 1 && stepFromServer <= 5
                  ? stepFromServer
                  : fallbackIncompleteStep
              )

            // #region agent log (authStore hydrateAuth normalization)
            fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H3', location: 'src/store/authStore.js:hydrateAuth', message: 'hydrateAuth received user + normalized onboarding fields', data: { has_is_onboarding_done: dbUser?.is_onboarding_done !== undefined, raw_is_onboarding_done: dbUser?.is_onboarding_done, normalizedOnboardingDone, has_onboarding_step: dbUser?.onboarding_step !== undefined, raw_onboarding_step: dbUser?.onboarding_step, persistedStep, normalizedOnboardingStep }, timestamp: Date.now() }) }).catch(() => { });
            // #endregion

            // Sync Zustand precisely to the Postgres reality
            set({
              user: dbUser,
              isAuthenticated: true,
              isEmailVerified: dbUser.is_email_verified ?? true, // Fallback if backend doesn't implement yet
              onboardingDone: normalizedOnboardingDone,
              // Only modify onboardingStep if onboarding is legitimately incomplete
              onboardingStep: normalizedOnboardingDone ? 6 : normalizedOnboardingStep,
              isHydrated: true,
              isHydratingAuth: false
            }, false, 'hydrateAuth_SUCCESS')

            // #region agent log (authStore final state snapshot)
            const s = get();
            fetch('http://127.0.0.1:7242/ingest/b5e6953e-01ca-4b76-858d-bfd42af56294', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'fcf4a1' }, body: JSON.stringify({ sessionId: 'fcf4a1', runId: 'post-fix', hypothesisId: 'H3', location: 'src/store/authStore.js:hydrateAuth', message: 'AUTH STATE (post-hydrateAuth_SUCCESS)', data: { isAuthenticated: s.isAuthenticated, isEmailVerified: s.isEmailVerified, onboardingDone: s.onboardingDone, onboardingStep: s.onboardingStep, isHydrated: s.isHydrated, isHydratingAuth: s.isHydratingAuth }, timestamp: Date.now() }) }).catch(() => { });
            // #endregion

          } catch (err) {
            console.error('[Zustand] Auth Hydration Failed:', err)
            // ── Determine whether this was a hard auth rejection or a transient error
            const isHardReject = err?.message === 'Token rejected by server'

            if (isHardReject) {
              // 401/403: token is dead → wipe everything, user must re-login
              set(
                {
                  user: null, token: null, refreshToken: null,
                  isAuthenticated: false, isEmailVerified: false,
                  onboardingStep: 1, onboardingDone: false, role: 'user',
                  isHydrated: true, isHydratingAuth: false,
                },
                false, 'hydrateAuth_HARD_FAIL'
              )
              localStorage.removeItem('arogyaai-auth')
            } else {
              // Transient failure (backend 500, network down, etc.).
              // Keep the token: don't log the user out for a temporary error.
              // Set isAuthenticated=true to unblock guards so the user reaches onboarding.
              // The next page reload will re-run hydrateAuth and sync correctly.
              const existingToken = get().token
              set(
                {
                  isAuthenticated: !!existingToken, // true if we still have a token
                  isHydrated: true,
                  isHydratingAuth: false,
                },
                false, 'hydrateAuth_TRANSIENT_FAIL'
              )
            }
          }
        },

        // ── Logout Fix ──────────────────────────────────────────────────
        // requirements: Call POST /api/v1/auth/logout with refresh_token, clear store,
        // remove localStorage key "arogyaai-auth", redirect to "/".
        // ─────────────────────────────────────────────────────────────────
        logout: async () => {
          const { refreshToken } = get()

          try {
            if (refreshToken) {
              await fetch('http://localhost:8000/api/v1/auth/logout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
              })
            }
          } catch (err) {
            console.error('[authStore] Logout request failed:', err)
            // Continue with local logout regardless of backend success
          }

          // 1. Wipe all Zustand state back to absolute zero (No stale state remains)
          set(
            {
              user: null,
              token: null,
              refreshToken: null,
              isAuthenticated: false,
              isEmailVerified: false,
              onboardingStep: 1,
              onboardingDone: false,
              role: 'user',
              isHydrated: true,
              isHydratingAuth: false,
            },
            false,
            'logout'
          )

          // 2. Nuke the Zustand persist localStorage key entirely
          localStorage.removeItem('arogyaai-auth')
          sessionStorage.clear()

          // 3. Redirect user to "/" (landing page)
          window.location.href = '/'
        },

        // ── HARD RESET ────────────────────────────────────────────────────────────────
        // Called by: DELETE /users/me, and 401 auto-logout interceptor.
        // Scenario: User deleted their account or token was completely invalidated.
        // Unlike logout(), hardReset() destroys EVERYTHING including onboarding state.
        // Reason: A deleted account (or stolen token invalidation) is not a returning-user scenario.
        // ────────────────────────────────────────────────────────────────────
        hardReset: () => {
          // 1. Wipe all Zustand state back to absolute zero
          set(
            {
              user: null,
              token: null,
              refreshToken: null,
              isAuthenticated: false,
              isEmailVerified: false,
              onboardingStep: 1,
              onboardingDone: false,
              role: 'user',
              isHydrated: true,  // Keep true so routing doesn't infinite-loop
              isHydratingAuth: false,
            },
            false,
            'hardReset'
          )
          // 2. Nuke the Zustand persist localStorage key entirely
          localStorage.removeItem('arogyaai-auth')
          sessionStorage.clear()
        }
      }),
      {
        name: 'arogyaai-auth',                   // ← exact key — must match this
        onRehydrateStorage: () => (state) => {
          // ── Patch 7 + Race-Fix ──────────────────────────────────────────────
          // PROBLEM: Previously, setHydrated() set isHydrated=true without setting
          // isHydratingAuth=true. Guards would unblock on the FIRST render and
          // route on stale localStorage state before hydrateAuth() ran.
          //
          // FIX: If a token is present, atomically set BOTH flags so guards are
          // blocked from the very first render. hydrateAuth() then runs immediately
          // (not after a render cycle via useEffect) and clears the lock when done.
          // ─────────────────────────────────────────────────────────────────────
          if (!state) return;

          const token = state.token;
          if (token) {
            // Token exists → server sync needed → lock guards immediately
            state.isHydrated = true;
            state.isHydratingAuth = true;
            // Call hydrateAuth synchronously (it is async internally)
            // This fires BEFORE any React renders, preventing the stale-state window.
            state.hydrateAuth();
          } else {
            // No token → no server sync needed → unlock guards directly
            state.setHydrated();
          }
        },
        // ── persisted fields ──
        partialize: (state) => ({
          token: state.token,
          refreshToken: state.refreshToken,
          user: state.user,
          isAuthenticated: state.isAuthenticated,
          isEmailVerified: state.isEmailVerified,
          onboardingDone: state.onboardingDone,
          onboardingStep: state.onboardingStep,
          role: state.role,
        }),
      }
    )
  )
)
