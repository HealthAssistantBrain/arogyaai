import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { ROUTES } from '../../router/routes';

export default function SafeNavigate({ to, replace, state }) {
  const [isLooping, setIsLooping] = useState(false);

  useEffect(() => {
    try {
      // Create a unique key for tracking specific path redirects
      const trackerKey = `redirect_tracker_${to}`;

      // Get count
      const raw = sessionStorage.getItem(trackerKey);
      const count = raw ? Number.parseInt(raw, 10) : 0;

      if (count > 5) {
        // Loop detected!
        console.error(`[ROUTER SECURE] Infinite loop detected targeting: ${to}. Navigation aborted.`);
        setIsLooping(true);
      } else {
        // Increment count
        sessionStorage.setItem(trackerKey, (count + 1).toString());

        // Setup a decay/clear timer. If the user legitimately hits this route later, we don't want to block it forever.
        // A loop happens instantaneously. If 1 second passes, it wasn't a loop.
        setTimeout(() => {
          sessionStorage.removeItem(trackerKey);
        }, 1000);
      }
    } catch (e) {
      // In case sessionStorage is blocked, ignore gracefully
      console.warn('[ROUTER SECURE] Non-critical state failure in SafeNavigate', e);
    }
  }, [to]);

  if (isLooping) {
    // Break the loop and drop them at a safe fallback page
    return <Navigate to={ROUTES.SERVER_ERROR} replace />;
  }

  // Safe to navigate
  return <Navigate to={to} replace={replace} state={state} />;
}
