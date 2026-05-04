import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../lib/axios';
import AQIUI from '../components/aqi/AQIUI';
import AQISkeleton from '../components/skeleton/AQISkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';
import useAqiStore from '../store/aqiStore';

const SEARCH_DEBOUNCE_MS = 300;

const AQIMonitor = () => {
  const navigate = useNavigate();
  const {
    data,
    history,
    activeLocation,
    coords,
    isFetching,
    error,
    lastFetchedAt,
    isAlertEnabled,
    setIsAlertEnabled,
    alertThreshold,
    hasHydratedCache,
    fetchAQIData,
  } = useAqiStore();

  const [selectedMetric, setSelectedMetric] = useState('pm25');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const searchContainerRef = useRef(null);
  const hasInitializedLocationRef = useRef(false);
  const hasAqiSnapshot = Boolean(data) || lastFetchedAt !== null;
  const showSkeleton = !hasAqiSnapshot && (isFetching || !hasHydratedCache);
  const showRefreshOverlay = useSmartFetchOverlay(isFetching, hasAqiSnapshot, { exitDelayMs: 200 });

  const syncLocation = async (lat, lng, label, successMessage = null) => {
    const result = await fetchAQIData(lat, lng, label, { force: true, days: 7 });

    if (!result) {
      toast.error('Failed to synchronize environmental data');
      return null;
    }

    if (successMessage) {
      if (result.isFallback) {
        toast.error('AQI service is unavailable right now');
      } else {
        toast.success(successMessage);
      }
    }

    return result;
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setIsSearchOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!hasHydratedCache || hasInitializedLocationRef.current) {
      return;
    }

    hasInitializedLocationRef.current = true;
    const { coords: initialCoords, activeLocation: initialLocation, lastFetchedAt: cachedAt } = useAqiStore.getState();

    if (!cachedAt) {
      void fetchAQIData(initialCoords.lat, initialCoords.lng, initialLocation, { force: true, days: 7 });
    }

    if (!('geolocation' in navigator)) {
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        void fetchAQIData(
          position.coords.latitude,
          position.coords.longitude,
          'Current Location',
          { force: true, days: 7 }
        );
      },
      () => {
        if (!cachedAt) {
          void fetchAQIData(initialCoords.lat, initialCoords.lng, initialLocation, { force: true, days: 7 });
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000,
      }
    );
  }, [fetchAQIData, hasHydratedCache]);

  useEffect(() => {
    const trimmedQuery = searchQuery.trim();
    if (trimmedQuery.length < 2) {
      setSearchSuggestions([]);
      setHighlightedIndex(0);
      return undefined;
    }

    let isCancelled = false;
    const timer = window.setTimeout(async () => {
      setIsSearching(true);
      try {
        const response = await api.get('/geocode', {
          params: {
            q: trimmedQuery,
            limit: 6,
          },
        });

        if (!isCancelled) {
          const suggestions = response.data?.data?.suggestions ?? [];
          setSearchSuggestions(suggestions);
          setHighlightedIndex(0);
          setIsSearchOpen(true);
        }
      } catch (searchError) {
        if (!isCancelled) {
          console.error('AQI location search failed:', searchError);
          setSearchSuggestions([]);
        }
      } finally {
        if (!isCancelled) {
          setIsSearching(false);
        }
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      isCancelled = true;
      window.clearTimeout(timer);
    };
  }, [searchQuery]);

  const handleLocationClick = () => {
    if (!('geolocation' in navigator)) {
      toast.error('Geolocation is not supported by your browser');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        void syncLocation(
          position.coords.latitude,
          position.coords.longitude,
          'Current Location',
          'AQI updated for your current location'
        );
      },
      () => {
        toast.error('Unable to access your current location');
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000,
      }
    );
  };

  const submitCitySearch = (suggestion) => {
    if (!suggestion) {
      return;
    }

    setSearchQuery(suggestion.label || suggestion.name);
    setIsSearchOpen(false);
    void syncLocation(
      suggestion.lat,
      suggestion.lng,
      suggestion.label || suggestion.name,
      `AQI updated for ${suggestion.name}`
    );
  };

  const handleSearchKeyDown = (event) => {
    if (!isSearchOpen && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
      setIsSearchOpen(true);
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightedIndex((current) => Math.min(current + 1, Math.max(searchSuggestions.length - 1, 0)));
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex((current) => Math.max(current - 1, 0));
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      if (searchSuggestions[highlightedIndex]) {
        submitCitySearch(searchSuggestions[highlightedIndex]);
      }
    }

    if (event.key === 'Escape') {
      setIsSearchOpen(false);
    }
  };

  if (showSkeleton) {
    return <AQISkeleton />;
  }

  return (
    <div className="relative">
      {showRefreshOverlay ? <SmartLoadingOverlay label="Refreshing AQI data" /> : null}
      <AQIUI
        data={data}
        historyData={history}
        loading={isFetching}
        error={error}
        location={activeLocation}
        coords={coords}
        onLocationClick={handleLocationClick}
        onSearchOpen={setIsSearchOpen}
        isSearchOpen={isSearchOpen}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        searchSuggestions={searchSuggestions}
        isSearching={isSearching}
        highlightedIndex={highlightedIndex}
        setHighlightedIndex={setHighlightedIndex}
        submitCitySearch={submitCitySearch}
        onSearchKeyDown={handleSearchKeyDown}
        searchContainerRef={searchContainerRef}
        isAlertEnabled={isAlertEnabled}
        setIsAlertEnabled={setIsAlertEnabled}
        alertThreshold={alertThreshold}
        selectedMetric={selectedMetric}
        onMetricChange={setSelectedMetric}
        navigate={navigate}
      />
    </div>
  );
};

export default AQIMonitor;

