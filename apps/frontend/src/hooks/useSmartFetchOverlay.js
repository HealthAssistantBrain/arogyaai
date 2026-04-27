import { useEffect, useState } from 'react';

const DEFAULT_EXIT_DELAY_MS = 200;

export const useSmartFetchOverlay = (
  isFetching,
  hasCachedData,
  { exitDelayMs = DEFAULT_EXIT_DELAY_MS } = {}
) => {
  const [showOverlay, setShowOverlay] = useState(Boolean(isFetching && hasCachedData));

  useEffect(() => {
    if (!hasCachedData) {
      setShowOverlay(false);
      return undefined;
    }

    if (isFetching) {
      setShowOverlay(true);
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setShowOverlay(false);
    }, exitDelayMs);

    return () => window.clearTimeout(timeoutId);
  }, [exitDelayMs, hasCachedData, isFetching]);

  return showOverlay;
};

export default useSmartFetchOverlay;
