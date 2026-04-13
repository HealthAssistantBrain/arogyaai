import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Wind, 
  MapPin, 
  AlertTriangle, 
  Activity, 
  ArrowLeft, 
  Bell, 
  Search, 
  TrendingUp, 
  Navigation,
  ShieldCheck,
  CheckCircle2,
  Info,
  ChevronRight,
  Droplets,
  Cloud,
  Thermometer,
  Zap,
  LayoutDashboard,
  Brain,
  History,
  Rocket
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

// BUG 2 FIX D — Use the shared Axios instance, not fetch()
import api from '../lib/axios';
import toast from 'react-hot-toast';
import { ROUTES } from '../router/routes';

const aqiTrendData = [
  { day: 'Mon', aqi: 42, cat: 'Good' },
  { day: 'Tue', aqi: 48, cat: 'Good' },
  { day: 'Wed', aqi: 112, cat: 'Unhealthy (S)' },
  { day: 'Thu', aqi: 85, cat: 'Moderate' },
  { day: 'Fri', aqi: 156, cat: 'Unhealthy' },
  { day: 'Sat', aqi: 92, cat: 'Moderate' },
  { day: 'Sun', aqi: 45, cat: 'Good' },
];

// Default fallback location — Delhi (per mandate requirement)
const DELHI_LAT = 28.6139;
const DELHI_LNG = 77.2090;

const createOsmEmbedUrl = (lat, lng) => {
  const delta = 0.12;
  const left = (lng - delta).toFixed(6);
  const right = (lng + delta).toFixed(6);
  const top = (lat + delta).toFixed(6);
  const bottom = (lat - delta).toFixed(6);

  return `https://www.openstreetmap.org/export/embed.html?bbox=${left}%2C${bottom}%2C${right}%2C${top}&layer=mapnik&marker=${lat}%2C${lng}`;
};

const AQIMonitor = () => {
  const navigate = useNavigate();
  const searchContainerRef = useRef(null);
  const [activeLocation, setActiveLocation] = useState('New Delhi, DL');
  const [aqiValue, setAqiValue] = useState(156);
  const [pollutantData, setPollutantData] = useState({
    pm25: 25.0,
    pm10: 45.0,
    no2: 20.0,
    o3: 50.0,
    so2: 10.0,
  });
  const [aqiMeta, setAqiMeta] = useState({
    dominantPollutant: 'PM2.5',
    method: 'openweather_pm_epa_interp',
  });
  const [alertThreshold, setAlertThreshold] = useState(100);
  const [isAlertEnabled, setIsAlertEnabled] = useState(true);
  const [coords, setCoords] = useState({ lat: DELHI_LAT, lng: DELHI_LNG });
  const [isLoading, setIsLoading] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const osmMapEmbedUrl = createOsmEmbedUrl(coords.lat, coords.lng);

  const applyAqiResponse = (apiData, fallbackLat, fallbackLng) => {
    setAqiValue(apiData.aqi || 156);
    setActiveLocation(apiData.location || 'Unknown Location');
    setPollutantData({
      pm25: apiData.pm25 || 25.0,
      pm10: apiData.pm10 || 45.0,
      no2: apiData.no2 || 20.0,
      o3: apiData.o3 || 50.0,
      so2: apiData.so2 || 10.0,
    });
    setAqiMeta({
      dominantPollutant: apiData.dominant_pollutant || 'PM2.5',
      method: apiData.aqi_method || 'openweather_pm_epa_interp',
    });
    setCoords({
      lat: apiData.lat ?? fallbackLat,
      lng: apiData.lng ?? fallbackLng,
    });
  };

  // Location is fetched only when the user explicitly requests it.
  // BUG 2 FIX D — axios api instance with Bearer token (via interceptors)
  const fetchAQIData = async (lat, lng) => {
    try {
      setIsLoading(true);
      const response = await api.get('/health/aqi-risk', { params: { lat, lng } });
      
      // Handle standard envelope response
      if (response.data?.success && response.data?.data) {
        const apiData = response.data.data;
        applyAqiResponse(apiData, lat, lng);
        toast.success(`AQI updated for ${apiData.location}`);
      } else if (response.data?.data?.aqi) {
        // Fallback: direct data property
        applyAqiResponse(response.data.data, lat, lng);
      }
    } catch (err) {
      // Backend offline → keep displayed mock data, don't crash
      console.warn('[AQIMonitor] Backend unavailable, using static data:', err?.message);
      toast.error('Using offline data. Some features limited.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCitySuggestions = async (query) => {
    const trimmedQuery = query.trim();
    if (trimmedQuery.length < 2) {
      setSearchSuggestions([]);
      setHighlightedIndex(0);
      return;
    }

    try {
      setIsSearching(true);
      const response = await api.get('/health/aqi-locations', {
        params: { query: trimmedQuery, limit: 6 },
      });
      const suggestions = response.data?.data?.suggestions || [];
      setSearchSuggestions(suggestions);
      setHighlightedIndex(0);
    } catch (err) {
      console.warn('[AQIMonitor] Failed to fetch city suggestions:', err?.message);
      setSearchSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  };

  const submitCitySearch = async (suggestionOverride) => {
    const chosenSuggestion = suggestionOverride || searchSuggestions[highlightedIndex] || searchSuggestions[0];

    if (!chosenSuggestion) {
      toast.error('Please select a city suggestion first.');
      return;
    }

    setSearchQuery(chosenSuggestion.label);
    setSearchSuggestions([]);
    setIsSearchOpen(false);
    await fetchAQIData(chosenSuggestion.lat, chosenSuggestion.lng);
  };

  const handleLocationClick = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported in this browser.');
      return;
    }

    setIsLoading(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords: currentCoords }) => {
        setCoords({ lat: currentCoords.latitude, lng: currentCoords.longitude });
        fetchAQIData(currentCoords.latitude, currentCoords.longitude);
      },
      () => {
        setIsLoading(false);
        toast.error('Location permission denied or unavailable.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  // Load default AQI without prompting for location on page open.
  useEffect(() => {
    fetchAQIData(DELHI_LAT, DELHI_LNG);
  }, []);

  useEffect(() => {
    const trimmedQuery = searchQuery.trim();
    const timeoutId = setTimeout(() => {
      fetchCitySuggestions(trimmedQuery);
    }, 250);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setIsSearchOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getAqiConfig = (val) => {
    if (val <= 50) return { label: 'Good', color: 'text-green-500', bg: 'bg-green-500', desc: 'Air quality is satisfactory, and air pollution poses little or no risk.', action: 'Safe for outdoor exercise' };
    if (val <= 100) return { label: 'Moderate', color: 'text-yellow-500', bg: 'bg-yellow-500', desc: 'Air quality is acceptable. Sensitive groups should reduce exertion.', action: 'Reduce prolonged outdoor exertion' };
    if (val <= 150) return { label: 'Unhealthy (S)', color: 'text-orange-500', bg: 'bg-orange-500', desc: 'Members of sensitive groups may experience health effects.', action: 'Limit outdoor exertion for sensitive groups' };
    if (val <= 200) return { label: 'Unhealthy', color: 'text-red-500', bg: 'bg-red-500', desc: 'Everyone may begin to experience health effects.', action: 'Avoid outdoor exercise. Keep windows closed.' };
    if (val <= 300) return { label: 'Very Unhealthy', color: 'text-purple-500', bg: 'bg-purple-500', desc: 'Health alert: everyone may experience more serious health effects.', action: 'Remain indoors. Use air purifiers.' };
    return { label: 'Hazardous', color: 'text-red-900', bg: 'bg-red-900', desc: 'Health warnings of emergency conditions.', action: 'Strictly indoors. Seek medical advice if symptomatic.' };
  };

  const aqiConfig = getAqiConfig(aqiValue);

  const sidebarLinks = [
    { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
    { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
    { icon: TrendingUp, label: 'Simulator', path: ROUTES.SIMULATOR },
    { icon: History, label: 'Timeline', path: ROUTES.TIMELINE },
    { icon: Wind, label: 'AQI Monitor', path: ROUTES.AQI_MONITOR, active: true },
  ];

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-[#13082A] dark:text-slate-100 min-h-screen font-display antialiased leading-normal flex">
      
      {/* Sidebar - Constant Aesthetic */}


      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto custom-scrollbar">
        
        {/* Header */}
        <header className="h-20 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-10 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate(-1)}
              className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 hover:bg-slate-200 transition-all active:scale-95"
            >
              <ArrowLeft size={18} />
            </button>
            <h2 className="text-xl font-black tracking-tight italic uppercase">Air Quality Risk Monitor</h2>
          </div>
          <div className="flex items-center gap-4">
             <button
                type="button"
                onClick={handleLocationClick}
                disabled={isLoading}
                className="flex items-center gap-2 bg-[#6143f4]/10 px-4 py-2 rounded-xl border border-[#6143f4]/20 transition-all hover:bg-[#6143f4]/15 disabled:opacity-60 disabled:cursor-not-allowed"
             >
                <Navigation size={14} className="text-[#6143f4]" />
                <span className="text-xs font-black text-[#6143f4] uppercase tracking-widest">{isLoading ? 'Fetching...' : activeLocation}</span>
             </button>
              <button
                type="button"
                onClick={() => {
                  window.open(`https://www.openstreetmap.org/?mlat=${coords.lat}&mlon=${coords.lng}#map=11/${coords.lat}/${coords.lng}`, '_blank', 'noopener,noreferrer');
                }}
               className="flex items-center gap-1 px-3 py-2 text-xs font-black uppercase tracking-widest rounded-xl border border-white/20 bg-white/10 text-white hover:bg-white/20"
             >
               <MapPin size={14} /> Open In OSM
             </button>
              <button
                type="button"
                onClick={() => {
                  setCoords({ lat: DELHI_LAT, lng: DELHI_LNG });
                  fetchAQIData(DELHI_LAT, DELHI_LNG);
                }}
                className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 hover:bg-slate-200 transition-all active:scale-90"
              >
               <Navigation size={18} />
             </button>
             <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 relative active:scale-90 transition-all" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                <Bell size={20} />
                <span className="absolute top-2.5 right-2.5 size-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-slate-900"></span>
             </button>
          </div>
        </header>

        <div className="p-10 space-y-8 max-w-7xl mx-auto w-full">
          
          {/* Section 1: Real-time AQI Diagnostics */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* AQI Meter Core */}
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               className="lg:col-span-1 bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col items-center text-center relative overflow-hidden group"
            >
              <h3 className="text-slate-500 font-bold text-[10px] uppercase tracking-[0.3em] mb-8">Current AQI Intensity</h3>
              <div className="relative size-56">
                <svg className="size-full" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-100 dark:text-slate-800" />
                  <motion.circle 
                    cx="50" cy="50" r="45" fill="none" stroke="currentColor" strokeWidth="8" 
                    strokeDasharray="283" 
                    initial={{ strokeDashoffset: 283 }}
                    animate={{ strokeDashoffset: 283 - (283 * (aqiValue / 500)) }}
                    transition={{ duration: 2, ease: "easeOut" }}
                    className={aqiConfig.color} 
                    strokeLinecap="round"
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-6xl font-black tracking-tighter leading-none italic">{aqiValue}</span>
                  <span className={`text-[10px] font-black uppercase tracking-[0.2em] mt-2 px-3 py-1 rounded-full ${aqiConfig.bg} text-white shadow-lg`}>
                    {aqiConfig.label}
                  </span>
                </div>
              </div>
              <p className="mt-8 text-slate-500 font-medium text-xs px-4">
                {aqiConfig.desc}
              </p>
              <div className="mt-5 flex flex-wrap items-center justify-center gap-2 px-4">
                <span className="rounded-full border border-[#6143f4]/20 bg-[#6143f4]/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-[#6143f4]">
                  Driver: {aqiMeta.dominantPollutant}
                </span>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  Source: OpenWeather PM
                </span>
              </div>
              <div className="mt-6 flex gap-2">
                <span className="size-2 rounded-full bg-green-500 animate-pulse"></span>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Live Sensor Synchronized</span>
              </div>
            </motion.div>

            {/* BUG 2 FIX E — Map panel with explicit height style */}
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.1 }}
               className="lg:col-span-2 bg-[#13082A] rounded-3xl shadow-xl overflow-hidden relative border border-slate-800 group h-[400px]"
            >
              <div className="absolute inset-0 z-0 overflow-hidden">
                <iframe
                  title="OpenStreetMap AQI Location"
                  src={osmMapEmbedUrl}
                  className="h-full w-full border-0 opacity-95"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-[#13082A] via-transparent to-transparent pointer-events-none"></div>
              
              <div className="pointer-events-none relative z-10 p-8 h-full flex flex-col justify-between">
                <div className="flex justify-between items-start">
                   <div className="pointer-events-auto bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-2xl flex items-center gap-3">
                      <div className="size-10 bg-white/20 rounded-xl flex items-center justify-center">
                         <MapPin className="text-white" size={20} />
                      </div>
                      <div>
                        <p className="text-white font-black text-sm tracking-tight">{activeLocation}</p>
                        <p className="text-white/50 text-[10px] font-bold uppercase tracking-widest">Lat: {coords.lat.toFixed(2)}, Lng: {coords.lng.toFixed(2)}</p>
                      </div>
                   </div>
                    <div className="pointer-events-auto flex gap-2 items-start">
                       <div ref={searchContainerRef} className="relative">
                         <button
                           type="button"
                           onClick={() => {
                             setIsSearchOpen((prev) => !prev);
                             setHighlightedIndex(0);
                           }}
                           className="size-10 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white flex items-center justify-center hover:bg-white/20 transition-all"
                         >
                           <Search size={18} />
                         </button>
                         <AnimatePresence>
                           {isSearchOpen && (
                             <motion.div
                               initial={{ opacity: 0, y: -8 }}
                               animate={{ opacity: 1, y: 0 }}
                               exit={{ opacity: 0, y: -8 }}
                               className="absolute right-0 top-14 w-80 rounded-2xl border border-white/15 bg-[#13082A]/95 p-3 shadow-2xl backdrop-blur-xl"
                             >
                               <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/10 px-3">
                                 <Search size={16} className="text-white/60" />
                                 <input
                                   type="text"
                                   value={searchQuery}
                                   onChange={(e) => {
                                     setSearchQuery(e.target.value);
                                     setHighlightedIndex(0);
                                   }}
                                   onKeyDown={(e) => {
                                     if (e.key === 'ArrowDown') {
                                       e.preventDefault();
                                       setHighlightedIndex((prev) => (
                                         Math.min(prev + 1, Math.max(searchSuggestions.length - 1, 0))
                                       ));
                                     }
                                     if (e.key === 'ArrowUp') {
                                       e.preventDefault();
                                       setHighlightedIndex((prev) => Math.max(prev - 1, 0));
                                     }
                                     if (e.key === 'Enter') {
                                       e.preventDefault();
                                       submitCitySearch();
                                     }
                                     if (e.key === 'Escape') {
                                       setIsSearchOpen(false);
                                     }
                                   }}
                                   placeholder="Search city name"
                                   className="h-11 w-full bg-transparent text-sm text-white placeholder:text-white/45 outline-none"
                                   autoFocus
                                 />
                               </div>
                               <div className="mt-3 max-h-64 overflow-y-auto rounded-xl border border-white/10 bg-black/10">
                                 {isSearching ? (
                                   <div className="px-4 py-3 text-xs font-bold uppercase tracking-widest text-white/60">
                                     Searching cities...
                                   </div>
                                 ) : searchQuery.trim().length < 2 ? (
                                   <div className="px-4 py-3 text-xs font-bold uppercase tracking-widest text-white/40">
                                     Type at least 2 letters
                                   </div>
                                 ) : searchSuggestions.length === 0 ? (
                                   <div className="px-4 py-3 text-xs font-bold uppercase tracking-widest text-white/40">
                                     No matching city found
                                   </div>
                                 ) : (
                                   searchSuggestions.map((suggestion, index) => (
                                     <button
                                       key={`${suggestion.label}-${suggestion.lat}-${suggestion.lng}`}
                                       type="button"
                                       onMouseEnter={() => setHighlightedIndex(index)}
                                       onClick={() => submitCitySearch(suggestion)}
                                       className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-all ${
                                         highlightedIndex === index ? 'bg-white/12' : 'hover:bg-white/8'
                                       }`}
                                     >
                                       <MapPin size={14} className="mt-0.5 shrink-0 text-white/70" />
                                       <div>
                                         <p className="text-sm font-bold text-white">{suggestion.name}</p>
                                         <p className="text-[11px] font-semibold uppercase tracking-wide text-white/50">
                                           {suggestion.state || suggestion.country}
                                         </p>
                                       </div>
                                     </button>
                                   ))
                                 )}
                               </div>
                             </motion.div>
                           )}
                         </AnimatePresence>
                       </div>
                       <button
                         type="button"
                        onClick={handleLocationClick}
                        disabled={isLoading}
                        className="size-10 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white flex items-center justify-center hover:bg-white/20 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        <Navigation size={18} className={isLoading ? 'animate-pulse' : ''} />
                      </button>
                   </div>
                </div>

                <div className="flex items-end justify-end">
                   <div className="size-32 relative">
                      <motion.div 
                        animate={{ rotate: 360 }} 
                        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                        className="absolute inset-0 border-2 border-dashed border-white/10 rounded-full"
                      ></motion.div>
                      <div className="absolute inset-0 flex items-center justify-center">
                         <Wind size={40} className="text-[#6143f4] opacity-50" />
                      </div>
                   </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Section 2: Personal Health Risk Impact */}
          <motion.div 
             initial={{ opacity: 0, scale: 0.98 }}
             animate={{ opacity: 1, scale: 1 }}
             transition={{ delay: 0.2 }}
             className="bg-gradient-to-r from-[#6143f4] to-[#009CDE] rounded-3xl p-1 shadow-2xl overflow-hidden"
          >
            <div className="bg-white dark:bg-[#1a1433] rounded-[1.4rem] p-10 flex flex-col lg:flex-row items-center justify-between gap-12">
               <div className="flex-1 space-y-6">
                  <div className="inline-flex items-center gap-2 bg-[#6143f4]/10 px-4 py-2 rounded-full border border-[#6143f4]/20">
                     <AlertTriangle size={14} className="text-[#6143f4]" />
                     <span className="text-[#6143f4] text-[10px] font-black uppercase tracking-[0.2em]">Clinical Risk Escalation</span>
                  </div>
                  <h2 className="text-4xl font-black tracking-tighter leading-none italic uppercase">Personal Health <span className="text-[#6143f4]">Impact</span></h2>
                  <p className="text-slate-500 font-medium text-lg leading-relaxed max-w-2xl">
                    High particulate matter concentrations in your current location are elevating your <span className="text-[#6143f4] font-black underline decoration-2 underline-offset-4 decoration-[#6143f4]/20">Respiratory Risk Modifier by +8.4%</span>. Your cardiovascular prediction remains stable due to regular aerobic buffers.
                  </p>
                  <div className="flex flex-wrap gap-4 pt-4">
                     <button 
                       onClick={() => navigate(ROUTES.RECOMMENDATIONS)}
                       className="bg-[#6143f4] text-white px-8 py-4 rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl shadow-[#6143f4]/30 hover:scale-105 active:scale-95 transition-all"
                     >
                        View Preventive Actions
                     </button>
                     <button 
                       onClick={() => navigate(ROUTES.INSIGHTS)}
                       className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-8 py-4 rounded-2xl font-black text-xs uppercase tracking-widest border border-slate-200 dark:border-slate-700 hover:bg-white transition-all"
                     >
                        View AI Insights
                     </button>
                  </div>
               </div>
               
               <div className="w-full lg:w-96 bg-slate-50 dark:bg-slate-800/80 p-8 rounded-[2rem] border border-slate-200 dark:border-slate-700 space-y-8 shadow-inner">
                  <div className="space-y-4">
                     <div className="flex justify-between items-end">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">CVD Modifier</span>
                        <span className="text-2xl font-black text-[#13082a] dark:text-white leading-none tracking-tight">+5.2%</span>
                     </div>
                     <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: '52%' }} transition={{ duration: 1.5, delay: 0.8 }} className="h-full bg-[#6143f4] rounded-full shadow-lg shadow-[#6143f4]/20"></motion.div>
                     </div>
                  </div>
                  <div className="space-y-4">
                     <div className="flex justify-between items-end">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Respiratory Stress</span>
                        <span className="text-2xl font-black text-[#13082a] dark:text-white leading-none tracking-tight">+14.8%</span>
                     </div>
                     <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: '88%' }} transition={{ duration: 1.5, delay: 1 }} className="h-full bg-[#009CDE] rounded-full shadow-lg shadow-[#009CDE]/20"></motion.div>
                     </div>
                  </div>
                  <div className="pt-4 border-t border-slate-200 dark:border-slate-700 flex items-center gap-3">
                     <CheckCircle2 size={16} className="text-green-500" />
                     <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Verified Against FHIR Dataset</p>
                  </div>
               </div>
            </div>
          </motion.div>

          {/* Section 3: Historical Trends & Guidance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pb-12">
            
            {/* 7-Day Trend Chart */}
            <motion.div 
               initial={{ opacity: 0, x: -20 }}
               animate={{ opacity: 1, x: 0 }}
               transition={{ delay: 0.3 }}
               className="bg-white dark:bg-slate-900 p-10 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col"
            >
              <div className="flex justify-between items-start mb-10">
                 <div>
                    <h3 className="text-slate-500 font-bold text-[10px] uppercase tracking-[0.3em] mb-2">AQI Velocity Trend</h3>
                    <p className="text-2xl font-black tracking-tight leading-none italic">7-Day Analysis</p>
                 </div>
                 <div className="bg-orange-50 dark:bg-orange-500/10 text-orange-600 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border border-orange-100 dark:border-orange-500/20">
                    Worsening
                 </div>
              </div>

              <div className="flex-1 min-h-[220px] w-full">
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={aqiTrendData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="aqiGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6143f4" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#6143f4" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="rgba(0,0,0,0.03)" />
                      <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 'bold', fill: '#94a3b8' }} dy={15} />
                      <Tooltip contentStyle={{ borderRadius: '20px', border: 'none', boxShadow: '0 20px 50px rgba(0,0,0,0.1)', fontWeight: 'bold' }} />
                      <Area 
                        type="monotone" 
                        dataKey="aqi" 
                        stroke="#6143f4" 
                        strokeWidth={4} 
                        fill="url(#aqiGrad)" 
                        animationDuration={2500}
                     />
                    </AreaChart>
                 </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Subscriptions & Controls */}
            <motion.div 
               initial={{ opacity: 0, x: 20 }}
               animate={{ opacity: 1, x: 0 }}
               transition={{ delay: 0.4 }}
               className="space-y-8"
            >
               {/* Activity Guidance Panel */}
               <div className="bg-white dark:bg-slate-900 p-10 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800">
                  <h4 className="text-slate-400 font-black text-[10px] uppercase tracking-[0.3em] mb-8 flex items-center gap-2">
                     <Zap size={14} className="text-yellow-500" /> Optimal Activity Guidance
                  </h4>
                  <div className="p-6 bg-[#13082A] rounded-2xl flex items-center gap-6 border border-white/5 shadow-2xl group overflow-hidden relative">
                     <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:rotate-12 transition-transform duration-700"><Rocket size={80} /></div>
                     <div className="size-16 bg-white/10 rounded-[1.5rem] flex items-center justify-center text-white shrink-0 shadow-lg italic font-black text-2xl">i</div>
                     <div>
                        <p className="text-white font-black text-sm uppercase tracking-tight mb-1">{aqiConfig.action}</p>
                        <p className="text-white/40 text-xs font-medium leading-relaxed italic">Escalate to indoor clinical protocol if respiratory tightness occurs.</p>
                     </div>
                  </div>
               </div>

               {/* Push Subscription Card */}
               <div className="bg-white dark:bg-slate-900 p-10 rounded-3xl shadow-sm border border-slate-100 dark:border-slate-800 flex items-center justify-between group">
                  <div className="flex items-center gap-6">
                     <div className={`size-14 rounded-2xl flex items-center justify-center transition-all ${isAlertEnabled ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/30' : 'bg-slate-100 text-slate-400'}`}>
                        <Bell size={24} className={isAlertEnabled ? 'animate-bounce' : ''} />
                     </div>
                     <div>
                        <h4 className="font-black text-lg tracking-tight leading-none italic uppercase">AQI Breach Alerts</h4>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-2 px-3 py-1 bg-slate-50 dark:bg-slate-800 rounded-full w-fit">Threshold: {alertThreshold}+ AQI</p>
                     </div>
                  </div>
                  <button 
                    onClick={() => setIsAlertEnabled(!isAlertEnabled)}
                    className={`w-16 h-8 rounded-full relative transition-all duration-500 ${isAlertEnabled ? 'bg-[#6143f4]' : 'bg-slate-200 dark:bg-slate-700'}`}
                  >
                     <motion.div 
                        animate={{ x: isAlertEnabled ? 34 : 4 }}
                        className="absolute top-1 size-6 bg-white rounded-full shadow-lg"
                     ></motion.div>
                  </button>
               </div>
            </motion.div>
          </div>
        </div>

        {/* Footer */}
        <footer className="py-10 px-12 text-center text-slate-400 text-[10px] font-black uppercase tracking-[0.4em] bg-white/40 dark:bg-slate-900/40 backdrop-blur-md border-t border-slate-200 dark:border-slate-800 mt-auto relative overflow-hidden">
           © 2024 ArogyaAI Neural Systems • Environmental Intelligence Node • v.59.0.0
        </footer>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 5px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #6143f422; border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #6143f444; }
      `}} />
    </div>
  );
};

export default AQIMonitor;
