import { create }            from 'zustand'
import { persist, devtools } from 'zustand/middleware'

// ── Patch 7: isHydrated prevents guard decisions before Zustand hydrates from localStorage
// ── Patch 4: role field added for future role-based access control (no UI impact)
// ── Bug Fix: logout() must NOT wipe onboarding state. onboardingDone / onboardingStep
//    are user-level persistent data, not session data. They survive across login cycles.

export const useAuthStore = create(
  devtools(
    persist(
      (set, get) => ({
        user:              null,
        token:             null,
        isAuthenticated:   false,
        isEmailVerified:   false,
        onboardingStep:    0,       // ← number 0 — NOT string '0'
        onboardingDone:    false,
        role:              'user',  // ← 'user' | 'doctor' | 'admin' (Patch 4)
        isHydrated:        false,   // ← set to true after persist rehydration (Patch 7)
        isHydratingAuth:   false,   // ← network fetching lock

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

        setEmailVerified: () =>
          set({ isEmailVerified: true }, false, 'setEmailVerified'),

        setOnboardingStep: (step) => {
          // ── SECTION 4: FINALIZE ONBOARDING LOCK ──
          // Once onboardingDone is true, freeze onboarding state.
          // Ignore ANY state updates attempting to modify onboarding step backwards.
          if (get().onboardingDone === true) return;
          
          set({ onboardingStep: step }, false, 'setOnboardingStep')
        },

        setHydrated: () =>
          set({ isHydrated: true }, false, 'setHydrated'),

        // ── CRITICAL ────────────────────────────────────────────────────────
        // completeOnboarding MUST be called BEFORE navigate()
        // in OnboardingCompletion.jsx — if navigate() fires first
        // the OnboardingGuard reads onboardingDone=false and
        // redirects back to the last step creating an infinite loop
        // ────────────────────────────────────────────────────────────────────
        completeOnboarding: () =>
          set(
            { onboardingDone: true, onboardingStep: 6 },
            false,
            'completeOnboarding'
          ),

        // ── Auth Hydration Logic ───────────────────────────────────────────
        // Called by GlobalStateValidator to sync JWT token with true DB state
        // ────────────────────────────────────────────────────────────────────
        hydrateAuth: async () => {
          const { token } = get()
          
          if (!token) {
            set({ isHydrated: true, isHydratingAuth: false })
            return
          }

          set({ isHydratingAuth: true })
          try {
            // Hit the newly scaffolded backend /users/me endpoint
            const res = await fetch('http://localhost:8000/users/me', {
              headers: { Authorization: `Bearer ${token}` }
            })

            if (!res.ok) throw new Error('Token rejected by server')
            
            const dbUser = await res.json()
            
            // Sync Zustand precisely to the Postgres reality
            set({
              user: dbUser,
              isAuthenticated: true,
              isEmailVerified: dbUser.is_email_verified ?? true, // Fallback if backend doesn't implement yet
              onboardingDone: dbUser.is_onboarding_done,
              // Only modify onboardingStep if onboarding is legitimately incomplete
              onboardingStep: dbUser.is_onboarding_done ? 6 : get().onboardingStep,
              isHydrated: true,
              isHydratingAuth: false
            }, false, 'hydrateAuth_SUCCESS')
            
          } catch (err) {
            console.error('[Zustand] Auth Hydration Failed:', err)
            // Invalid DB state or rejected token → Wipe session but persist hydrated=true to unblock routing
            get().logout()
            set({ isHydrated: true, isHydratingAuth: false }, false, 'hydrateAuth_FAIL')
          }
        },

        // ── Bug Fix (Step 1): logout ONLY clears session data.
        // onboardingDone, onboardingStep, isEmailVerified are USER-LEVEL state
        // and MUST be preserved across logout/login cycles so returning users
        // skip onboarding and go straight to /dashboard.
        // DO NOT call localStorage.removeItem() — Zustand persist will rehydrate
        // the remaining onboarding fields correctly on next login.
        logout: () => {
          // Preserve onboarding + email verification state before clearing session
          const { onboardingDone, onboardingStep, isEmailVerified } = get()

          set(
            {
              // ── Session fields cleared ──────────────────────
              user:            null,
              token:           null,
              isAuthenticated: false,
              role:            'user',
              // ── User-level fields PRESERVED ─────────────────
              onboardingDone:   onboardingDone,
              onboardingStep:   onboardingStep,
              isEmailVerified:  isEmailVerified,
            },
            false,
            'logout'
          )
          // Only clear volatile session keys — NOT the full persist store
          sessionStorage.clear()
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
              user:             null,
              token:            null,
              isAuthenticated:  false,
              isEmailVerified:  false,
              onboardingStep:   0,
              onboardingDone:   false,
              role:             'user',
              isHydrated:       true,  // Keep true so routing doesn't infinite-loop
              isHydratingAuth:  false,
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
          // ── Patch 7: signal hydration complete so guards can safely run
          if (state) state.setHydrated()
        },
        // ── Step 2: Explicitly declare which fields are persisted.
        // This ensures onboardingDone / onboardingStep / isEmailVerified
        // survive page refreshes and logout/login cycles permanently.
        partialize: (state) => ({
          token:            state.token,
          user:             state.user,
          isAuthenticated:  state.isAuthenticated,
          isEmailVerified:  state.isEmailVerified,
          onboardingDone:   state.onboardingDone,
          onboardingStep:   state.onboardingStep,
          role:             state.role,
        }),
      }
    )
  )
)
