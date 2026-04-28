import React from 'react';
import 'leaflet/dist/leaflet.css';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  LoaderCircle,
  MapPin,
  Navigation,
  Search,
  Wind,
  Zap,
} from 'lucide-react';
import { MapContainer, TileLayer, CircleMarker, useMap } from 'react-leaflet';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AnimatePresence, motion } from 'framer-motion';

const METRIC_META = {
  pm25: { label: 'PM2.5', unit: 'ug/m3', color: '#7C3AED', description: 'Fine particulate matter' },
  o3: { label: 'O3', unit: 'ug/m3', color: '#0EA5E9', description: 'Ground-level ozone' },
  no2: { label: 'NO2', unit: 'ug/m3', color: '#F97316', description: 'Nitrogen dioxide' },
};

const DEFAULT_COORDS = { lat: 28.6139, lng: 77.209 };

const formatTimeAgo = (timestamp) => {
  if (!timestamp) {
    return 'Awaiting live AQI feed';
  }

  const diffMs = Date.now() - new Date(timestamp).getTime();
  const diffMinutes = Math.max(0, Math.round(diffMs / 60000));

  if (diffMinutes < 1) {
    return 'Updated just now';
  }

  if (diffMinutes < 60) {
    return `Updated ${diffMinutes} min ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  return `Updated ${diffHours} hr ago`;
};

const getAqiConfig = (value, hasData) => {
  if (!hasData || value <= 0) {
    return {
      label: 'No Data',
      accent: '#64748B',
      soft: '#E2E8F0',
      glow: 'rgba(100, 116, 139, 0.22)',
      description: 'Live AQI data is temporarily unavailable for this location.',
      action: 'Try another location or refresh current location.',
    };
  }

  if (value <= 50) {
    return {
      label: 'Good',
      accent: '#16A34A',
      soft: '#DCFCE7',
      glow: 'rgba(22, 163, 74, 0.22)',
      description: 'Air quality is satisfactory and outdoor exposure risk is low.',
      action: 'Normal outdoor activity is generally safe.',
    };
  }

  if (value <= 100) {
    return {
      label: 'Moderate',
      accent: '#CA8A04',
      soft: '#FEF3C7',
      glow: 'rgba(202, 138, 4, 0.22)',
      description: 'Sensitive groups should reduce long outdoor exposure.',
      action: 'Keep an eye on symptoms if you have respiratory sensitivity.',
    };
  }

  if (value <= 150) {
    return {
      label: 'Unhealthy (Sensitive)',
      accent: '#EA580C',
      soft: '#FFEDD5',
      glow: 'rgba(234, 88, 12, 0.22)',
      description: 'Sensitive groups may experience breathing discomfort.',
      action: 'Limit strenuous outdoor activity for vulnerable patients.',
    };
  }

  if (value <= 200) {
    return {
      label: 'Unhealthy',
      accent: '#DC2626',
      soft: '#FEE2E2',
      glow: 'rgba(220, 38, 38, 0.22)',
      description: 'Most people can begin to feel health effects at this level.',
      action: 'Reduce outdoor exposure and keep indoor air clean.',
    };
  }

  return {
    label: 'Very High Risk',
    accent: '#7F1D1D',
    soft: '#FECACA',
    glow: 'rgba(127, 29, 29, 0.26)',
    description: 'Air quality is very unhealthy and can trigger acute symptoms.',
    action: 'Stay indoors and follow clinical precautions immediately.',
  };
};

const MapViewportController = ({ coords }) => {
  const map = useMap();

  React.useEffect(() => {
    if (coords?.lat && coords?.lng) {
      map.setView([coords.lat, coords.lng], 10, { animate: true });
    }
  }, [coords, map]);

  return null;
};

const AQIUI = ({
  data,
  historyData,
  loading,
  error,
  location,
  coords,
  onLocationClick,
  onSearchOpen,
  isSearchOpen,
  searchQuery,
  setSearchQuery,
  searchSuggestions,
  isSearching,
  highlightedIndex,
  setHighlightedIndex,
  submitCitySearch,
  onSearchKeyDown,
  searchContainerRef,
  isAlertEnabled,
  setIsAlertEnabled,
  alertThreshold,
  selectedMetric,
  onMetricChange,
  navigate,
}) => {
  const activeCoords = coords || DEFAULT_COORDS;
  const activeMetric = METRIC_META[selectedMetric] || METRIC_META.pm25;
  const hasCurrentData = Boolean(data && (data.aqi > 0 || data.pm25 > 0 || data.o3 > 0 || data.no2 > 0) && !data.isFallback);
  const hasHistoryData = Array.isArray(historyData) && historyData.some((entry) => Number(entry[selectedMetric]) > 0);
  const aqiValue = Number(data?.aqi || 0);
  const aqiConfig = getAqiConfig(aqiValue, hasCurrentData);

  return (
    <div className="w-full overflow-x-hidden bg-[#EAEAEA] px-4 py-6 text-[#13082A] transition-colors sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="max-w-4xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/80 px-4 py-1.5 text-[11px] font-black uppercase tracking-[0.24em] text-[#6143F4] shadow-sm backdrop-blur">
            <Wind size={14} />
            AQI Intelligence
          </div>
          <h1 className="text-3xl font-black tracking-tight text-[#13082A] sm:text-4xl">
            Air Quality Risk Monitor
          </h1>
          <p className="mt-3 max-w-3xl text-sm font-medium leading-7 text-slate-700 sm:text-base">
            Live pollution monitoring with location-aware AQI, historical pollutant trends, and patient-safe environmental guidance.
          </p>
        </header>

        <section className="relative grid gap-6 xl:grid-cols-12">
          <div className="relative z-0 min-w-0 xl:col-span-8">
            <div className="map-wrapper relative z-0 isolate overflow-hidden rounded-[32px] border border-slate-200/80 bg-white shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <div
                className="pointer-events-none absolute inset-x-0 top-0 h-32"
                style={{ background: `linear-gradient(180deg, ${aqiConfig.glow} 0%, rgba(255,255,255,0) 100%)` }}
              />
              <div className="absolute left-5 top-5 z-10 flex flex-wrap items-center gap-3">
                <div className="rounded-2xl border border-white/90 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Tracked Location</p>
                  <p className="mt-1 text-sm font-bold text-slate-900">{location || 'Current region'}</p>
                  <p className="mt-1 text-xs font-medium text-slate-600">
                    {activeCoords.lat.toFixed(4)}, {activeCoords.lng.toFixed(4)}
                  </p>
                </div>
              </div>
              <div className="absolute right-5 top-5 z-10">
                <button
                  type="button"
                  onClick={onLocationClick}
                  className="inline-flex items-center gap-2 rounded-2xl border border-white/80 bg-white/95 px-4 py-3 text-sm font-bold text-[#13082A] shadow-lg transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#6143F4]"
                  aria-label="Use current location"
                >
                  {loading ? <LoaderCircle size={16} className="animate-spin text-[#6143F4]" /> : <Navigation size={16} className="text-[#6143F4]" />}
                  Current location
                </button>
              </div>

              <div className="relative z-0 h-[520px] w-full overflow-hidden">
                <MapContainer
                  center={[activeCoords.lat, activeCoords.lng]}
                  zoom={10}
                  scrollWheelZoom
                  className="relative z-0 h-full w-full"
                  zoomControl
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <MapViewportController coords={activeCoords} />
                  <CircleMarker
                    center={[activeCoords.lat, activeCoords.lng]}
                    radius={18}
                    pathOptions={{
                      color: aqiConfig.accent,
                      fillColor: aqiConfig.accent,
                      fillOpacity: 0.35,
                      weight: 3,
                    }}
                  />
                </MapContainer>
              </div>

              <div className="absolute bottom-5 left-5 z-10 rounded-2xl border border-white/80 bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">AQI Status</p>
                <div className="mt-2 flex items-center gap-3">
                  <span
                    className="inline-flex size-3 rounded-full"
                    style={{ backgroundColor: aqiConfig.accent, boxShadow: `0 0 0 6px ${aqiConfig.glow}` }}
                  />
                  <span className="text-sm font-bold text-slate-900">{aqiConfig.label}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="relative z-20 flex min-w-0 flex-col gap-6 xl:col-span-4">
            <div className="relative z-20 rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Location Search</p>
              <div ref={searchContainerRef} className="relative z-20 mt-4">
                <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(event) => {
                    setSearchQuery(event.target.value);
                    onSearchOpen(true);
                  }}
                  onFocus={() => onSearchOpen(true)}
                  onKeyDown={onSearchKeyDown}
                  placeholder="Search city or region"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-11 pr-4 text-sm font-medium text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#6143F4] focus:bg-white focus:ring-4 focus:ring-[#6143F4]/10"
                  aria-label="Search location"
                />

                <AnimatePresence>
                  {isSearchOpen ? (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="absolute left-0 right-0 top-[4.25rem] z-30 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl"
                    >
                      <div className="max-h-72 overflow-y-auto p-2">
                        {isSearching ? (
                          <div className="flex items-center gap-2 px-4 py-3 text-sm font-semibold text-slate-600">
                            <LoaderCircle size={16} className="animate-spin text-[#6143F4]" />
                            Searching locations...
                          </div>
                        ) : searchQuery.trim().length < 2 ? (
                          <div className="px-4 py-3 text-sm font-semibold text-slate-500">
                            Type at least 2 letters to search.
                          </div>
                        ) : searchSuggestions.length === 0 ? (
                          <div className="px-4 py-3 text-sm font-semibold text-slate-500">
                            No matching location found.
                          </div>
                        ) : (
                          searchSuggestions.map((suggestion, index) => (
                            <button
                              key={`${suggestion.label}-${suggestion.lat}-${suggestion.lng}`}
                              type="button"
                              onMouseEnter={() => setHighlightedIndex(index)}
                              onClick={() => submitCitySearch(suggestion)}
                              className={`flex w-full items-start gap-3 rounded-2xl px-4 py-3 text-left transition ${
                                highlightedIndex === index ? 'bg-[#6143F4]/10 text-[#13082A]' : 'text-slate-700 hover:bg-slate-50'
                              }`}
                            >
                              <MapPin size={16} className="mt-0.5 shrink-0 text-[#6143F4]" />
                              <div>
                                <p className="text-sm font-bold">{suggestion.name}</p>
                                <p className="text-xs font-medium text-slate-500">
                                  {suggestion.state || suggestion.country}
                                </p>
                              </div>
                            </button>
                          ))
                        )}
                      </div>
                    </motion.div>
                  ) : null}
                </AnimatePresence>
              </div>

              <button
                type="button"
                onClick={onLocationClick}
                className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[#6143F4] px-4 py-3 text-sm font-bold text-white transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#6143F4] focus-visible:ring-offset-2"
              >
                <Navigation size={16} />
                Use Current Location
              </button>
            </div>

            <div className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">AQI Index</p>
                  <div className="mt-3 flex items-end gap-3">
                    <span className="text-6xl font-black tracking-tight text-[#13082A]">
                      {loading ? '...' : aqiValue}
                    </span>
                    <span
                      className="rounded-full px-3 py-1 text-xs font-black uppercase tracking-[0.18em]"
                      style={{ backgroundColor: aqiConfig.soft, color: aqiConfig.accent }}
                    >
                      {aqiConfig.label}
                    </span>
                  </div>
                  <p className="mt-4 flex items-center gap-2 text-xs font-semibold text-slate-600">
                    <Clock size={14} />
                    {formatTimeAgo(data?.lastUpdated)}
                  </p>
                </div>
                <div
                  className="flex size-20 items-center justify-center rounded-[28px] border"
                  style={{ borderColor: aqiConfig.glow, backgroundColor: aqiConfig.soft }}
                >
                  <div
                    className="size-8 rounded-full"
                    style={{ backgroundColor: aqiConfig.accent, boxShadow: `0 0 0 12px ${aqiConfig.glow}` }}
                  />
                </div>
              </div>

              <p className="mt-6 text-sm font-medium leading-7 text-slate-700">{aqiConfig.description}</p>

              <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
                {['pm25', 'o3', 'no2'].map((metricKey) => (
                  <div key={metricKey} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 transition hover:border-slate-300 hover:bg-white">
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
                      {METRIC_META[metricKey].label}
                    </p>
                    <p className="mt-2 text-xl font-black text-[#13082A]">
                      {Number(data?.[metricKey] || 0).toFixed(1)}
                    </p>
                    <p className="text-[11px] font-semibold text-slate-500">{METRIC_META[metricKey].unit}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[32px] border border-slate-200/80 bg-white p-6 shadow-[0_18px_60px_rgba(15,23,42,0.08)] sm:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">7-Day Trend</p>
              <h2 className="mt-2 text-2xl font-black tracking-tight text-[#13082A]">
                Pollution history for {location}
              </h2>
              <p className="mt-2 text-sm font-medium text-slate-600">
                Switch between pollutants to review how exposure changes with location.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {Object.entries(METRIC_META).map(([metricKey, meta]) => {
                const isActive = selectedMetric === metricKey;
                return (
                  <button
                    key={metricKey}
                    type="button"
                    onClick={() => onMetricChange(metricKey)}
                    className={`rounded-2xl px-4 py-2 text-sm font-bold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#6143F4] ${
                      isActive ? 'text-white shadow-lg' : 'border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'
                    }`}
                    style={isActive ? { backgroundColor: meta.color } : undefined}
                  >
                    {meta.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-[1.6fr_0.9fr]">
            <div className="h-[340px] rounded-[28px] border border-slate-100 bg-slate-50/70 p-4 sm:p-6">
              {hasHistoryData ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historyData} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="aqiMetricGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={activeMetric.color} stopOpacity={0.28} />
                        <stop offset="95%" stopColor={activeMetric.color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="rgba(148, 163, 184, 0.18)" strokeDasharray="3 3" />
                    <XAxis
                      dataKey="day"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#64748B', fontSize: 12, fontWeight: 700 }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#64748B', fontSize: 12, fontWeight: 700 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0F172A',
                        border: 'none',
                        borderRadius: '16px',
                        color: '#F8FAFC',
                        boxShadow: '0 18px 50px rgba(15, 23, 42, 0.28)',
                      }}
                      formatter={(value) => [`${Number(value).toFixed(1)} ${activeMetric.unit}`, activeMetric.label]}
                    />
                    <Area
                      type="monotone"
                      dataKey={selectedMetric}
                      stroke={activeMetric.color}
                      strokeWidth={3}
                      fill="url(#aqiMetricGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <Activity size={28} className="text-slate-400" />
                  <p className="mt-4 text-base font-bold text-slate-700">No live history available</p>
                  <p className="mt-2 max-w-sm text-sm font-medium leading-6 text-slate-500">
                    Historical AQI data for {activeMetric.label} will appear here after a successful API response.
                  </p>
                </div>
              )}
            </div>

            <div className="space-y-4">
              <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
                <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Selected metric</p>
                <p className="mt-3 text-2xl font-black text-[#13082A]">{activeMetric.label}</p>
                <p className="mt-2 text-sm font-medium leading-6 text-slate-600">{activeMetric.description}</p>
              </div>

              <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
                <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Current reading</p>
                <p className="mt-3 text-3xl font-black text-[#13082A]">
                  {Number(data?.[selectedMetric] || 0).toFixed(1)}
                  <span className="ml-2 text-sm font-semibold text-slate-500">{activeMetric.unit}</span>
                </p>
                <p className="mt-3 text-sm font-medium leading-6 text-slate-600">
                  Latest measured concentration for {activeMetric.label} near {location}.
                </p>
              </div>

              <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-slate-50 p-5">
                <div className="flex w-full max-w-full flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">AQI Breach Alerts</p>
                    <p className="mt-2 text-sm font-medium leading-6 text-slate-600">
                      Notify the user when AQI crosses {alertThreshold}.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsAlertEnabled(!isAlertEnabled)}
                    aria-pressed={isAlertEnabled}
                    className={`relative ml-0 h-8 w-16 shrink-0 self-start overflow-hidden rounded-full transition sm:ml-4 ${isAlertEnabled ? 'bg-[#6143F4]' : 'bg-slate-300'}`}
                  >
                    <motion.span
                      animate={{ x: isAlertEnabled ? 32 : 0 }}
                      transition={{ type: 'spring', stiffness: 320, damping: 24 }}
                      className="absolute left-1 top-1 inline-flex size-6 rounded-full bg-white shadow-md"
                    />
                  </button>
                </div>
                <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-600">
                  <Zap size={16} className={isAlertEnabled ? 'text-[#6143F4]' : 'text-slate-400'} />
                  {isAlertEnabled ? 'Alerts are enabled' : 'Alerts are disabled'}
                </div>
              </div>
            </div>
          </div>

          {error ? (
            <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
              AQI service warning: {error}
            </div>
          ) : null}
        </section>

        <section className="grid gap-6 pb-6 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            className="overflow-hidden rounded-[30px] bg-gradient-to-r from-[#6143F4] to-[#009CDE] p-[1px] shadow-[0_18px_60px_rgba(96,67,244,0.22)]"
          >
            <div className="rounded-[29px] bg-white p-7">
              <div className="inline-flex items-center gap-2 rounded-full bg-[#6143F4]/10 px-3 py-1.5 text-[11px] font-black uppercase tracking-[0.18em] text-[#6143F4]">
                <AlertTriangle size={14} />
                Clinical Risk Escalation
              </div>
              <h3 className="mt-5 text-2xl font-black tracking-tight text-[#13082A]">
                Personal Health Impact
              </h3>
              <p className="mt-3 text-sm font-medium leading-7 text-slate-700">
                AQI conditions are currently influencing respiratory exposure risk. This module is now ready to feed live pollutant signals into downstream ML risk scoring.
              </p>
              <button
                type="button"
                onClick={() => navigate('/recommendations')}
                className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-[#6143F4] px-5 py-3 text-sm font-bold text-white transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#6143F4] focus-visible:ring-offset-2"
              >
                <Activity size={16} />
                View Actions
              </button>
            </div>
          </motion.div>

          <div className="rounded-[30px] border border-slate-200/80 bg-white p-7 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <div className="flex items-center gap-4">
              <div className="flex size-14 items-center justify-center rounded-[24px] bg-[#ECF2FF] text-[#6143F4]">
                <Wind size={24} />
              </div>
              <div>
                <p className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Module status</p>
                <p className="mt-1 text-xl font-black text-[#13082A]">
                  {hasCurrentData ? 'Live AQI synchronized' : 'Fallback mode active'}
                </p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="flex items-start gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-green-600" />
                <p className="text-sm font-medium leading-6 text-slate-700">
                  Location search, current-location detection, and chart toggles are bound to the same AQI state.
                </p>
              </div>
              <div className="flex items-start gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-green-600" />
                <p className="text-sm font-medium leading-6 text-slate-700">
                  Map position and 7-day pollutant history refresh whenever the tracked location changes.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default AQIUI;
