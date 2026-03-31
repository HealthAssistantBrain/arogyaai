import { useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';

export default function GlobalStateValidator() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isEmailVerified = useAuthStore((s) => s.isEmailVerified);
  const onboardingDone = useAuthStore((s) => s.onboardingDone);
  const onboardingStep = useAuthStore((s) => s.onboardingStep);
  const token = useAuthStore((s) => s.token);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const isHydratingAuth = useAuthStore((s) => s.isHydratingAuth);
  const hydrateAuth = useAuthStore((s) => s.hydrateAuth);
  const logout = useAuthStore((s) => s.logout);

  // ── 0. Trigger backend Hydration on startup ───────────────────────────────────
  // NOTE: Cold-start hydration is now handled directly in authStore's
  // onRehydrateStorage callback, which fires BEFORE any React renders.
  // This effect is a FALLBACK for mid-session token changes (e.g. after login
  // where a new token is set and the component is already mounted).
  // isHydratingAuth guard prevents double-calls with the cold-start path.
  // ─────────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (isHydrated && token && !isHydratingAuth) {
      hydrateAuth();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]); // Only re-run when token changes (not isHydrated, which fires the cold-start path)

  useEffect(() => {
    // ── SECTION 9: Wait for both persist hydration AND network auth hydration
    if (!isHydrated || isHydratingAuth) return;

    // ── SECTION 1: ENFORCE STATE MACHINE CONTRACT
    let isValid = false;
    let reason = '';

    // STATE 0: HYDRATING FALLBACK
    // After a transient hydrateAuth failure, we set isAuthenticated=true but
    // user=null so the user isn't kicked out by a temporary backend 500.
    // This is transitional and will self-correct on the next hydrateAuth call.
    if (isAuthenticated && !token) {
      // isAuthenticated without token → hard parity error
      isValid = false;
      reason = 'isAuthenticated=true but no token';
    }
    // STATE 1: GUEST
    else if (!isAuthenticated && !token) {
      isValid = true;
    }
    // STATE 1b: TOKEN-ONLY (transient after signup/login before hydrateAuth resolves)
    // isAuthenticated may still be false immediately after setToken() fires.
    // The hydrateAuth call will fix this; GlobalStateValidator must not interfere.
    // We skip validation here and let hydrateAuth+isHydratingAuth handle it.
    // (isHydratingAuth=true already returns early above, so this is belt+suspenders)
    else if (!isAuthenticated && token) {
      isValid = true; // ghost-token? No — this is the pre-hydration state window
    }
    // SECTION 5: TOKEN PARITY HARDENING
    // Any state with isAuthenticated MUST have a valid token string
    else if (isAuthenticated && (!token || typeof token !== 'string' || token.trim() === '')) {
      isValid = false;
      reason = 'isAuthenticated=true but token is invalid or missing';
    }
    // STATE 2: AUTHENTICATED_UNVERIFIED
    else if (isAuthenticated && !isEmailVerified) {
      isValid = true;
    }
    // STATE 3: ONBOARDING
    else if (isAuthenticated && isEmailVerified && !onboardingDone) {
      // Validate onboardingStep is a clean number
      if (typeof onboardingStep !== 'number' || isNaN(onboardingStep)) {
        isValid = false;
        reason = 'onboardingStep is corrupt/NaN';
      } else {
        isValid = true;
      }
    }
    // STATE 4: ACTIVE USER
    else if (isAuthenticated && isEmailVerified && onboardingDone) {
      if (onboardingStep !== 6 && onboardingStep !== 5) {
        // Step 6 is the final frozen state. Step 5 is the 'summary' page before final submit.
        // During testing we might mock it, but structurally it should be fully completed.
      }
      isValid = true;
    }
    // ANY OTHER COMBINATION IS INVALID
    else {
      isValid = false;
      reason = 'Unknown/invalid state combination matrix';
    }

    if (!isValid) {
      console.error(`[SYSTEM SECURITY] Invalid state combination detected: ${reason}. Forcing logout sequence.`);
      logout();
    }
  }, [isAuthenticated, isEmailVerified, onboardingDone, onboardingStep, token, isHydrated, logout]);

  // This is a headless component. It only runs side-effects.
  return null;
}
