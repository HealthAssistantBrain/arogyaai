import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/axios';
import toast from 'react-hot-toast';
import AQIUI from '../components/aqi/AQIUI';
import AQISkeleton from '../components/skeleton/AQISkeleton';
import useAqiStore from '../store/aqiStore';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const aqiTrendData = [
  { day: 'Mon', aqi: 42, cat: 'Good' },
  { day: 'Tue', aqi: 48, cat: 'Good' },
  { day: 'Wed', aqi: 112, cat: 'Unhealthy (S)' },
  { day: 'Thu', aqi: 85, cat: 'Moderate' },
  { day: 'Fri', aqi: 156, cat: 'Unhealthy' },
  { day: 'Sat', aqi: 92, cat: 'Moderate' },
  { day: 'Sun', aqi: 45, cat: 'Good' },
];

const AQIMonitor = () => {
  const navigate = useNavigate();
  const {
    data,
    activeLocation,
    coords,
    isFetching,
    lastFetchedAt,
    isAlertEnabled,
    setIsAlertEnabled,
    alertThreshold,
    hasHydratedCache,
    fetchAQIData,
  } = useAqiStore();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const searchContainerRef = useRef(null);
  const hasAqiSnapshot = lastFetchedAt !== null;
  const showSkeleton = !hasAqiSnapshot && (isFetching || !hasHydratedCache);
  const showRefreshOverlay = useSmartFetchOverlay(isFetching, hasAqiSnapshot, { exitDelayMs: 200 });

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
    const { coords: initialCoords, activeLocation: initialLocation } = useAqiStore.getState();
    void fetchAQIData(initialCoords.lat, initialCoords.lng, initialLocation);
  }, [fetchAQIData]);

  const handleLocationClick = () => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(async (position) => {
        const result = await fetchAQIData(position.coords.latitude, position.coords.longitude, "Current Location", { force: true });
        if (result) {
          toast.success('AQI Updated for Current Location');
        } else {
          toast.error('Failed to synchronize environmental data');
        }
      });
    } else {
      toast.error("Geolocation is not supported by your browser");
    }
  };

  const submitCitySearch = (suggestion) => {
    if (suggestion) {
      void fetchAQIData(suggestion.lat, suggestion.lng, suggestion.name, { force: true }).then((result) => {
        if (result) {
          toast.success(`AQI Updated for ${suggestion.name}`);
        } else {
          toast.error('Failed to synchronize environmental data');
        }
      });
      setIsSearchOpen(false);
      setSearchQuery('');
    }
  };

  useEffect(() => {
    if (searchQuery.length > 2) {
      const searchCities = async () => {
        setIsSearching(true);
        try {
          const res = await api.get(`/locations/search?q=${searchQuery}`);
          setSearchSuggestions(res.data || []);
        } catch (err) {
          console.error('Search error:', err);
        } finally {
          setIsSearching(false);
        }
      };
      const debounce = setTimeout(searchCities, 300);
      return () => clearTimeout(debounce);
    } else {
      setSearchSuggestions([]);
    }
  }, [searchQuery]);

  if (showSkeleton) {
    return <AQISkeleton />;
  }

  return (
    <div className="relative">
      {showRefreshOverlay ? <SmartLoadingOverlay label="Refreshing AQI data" /> : null}
      <AQIUI
        data={data}
        loading={false}
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
        searchContainerRef={searchContainerRef}
        isAlertEnabled={isAlertEnabled}
        setIsAlertEnabled={setIsAlertEnabled}
        alertThreshold={alertThreshold}
        aqiTrendData={aqiTrendData}
        navigate={navigate}
      />
    </div>
  );
};

export default AQIMonitor;
