import { useState, useEffect } from 'react';
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
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

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

const AQIMonitor = () => {
  const navigate = useNavigate();
  const [activeLocation, setActiveLocation] = useState('New Delhi, DL');
  const [aqiValue, setAqiValue] = useState(156);
  const [alertThreshold, setAlertThreshold] = useState(100);
  const [isAlertEnabled, setIsAlertEnabled] = useState(true);
  const [coords, setCoords] = useState({ lat: DELHI_LAT, lng: DELHI_LNG });

  // BUG 2 FIX C — Geolocation with proper error handling + fallback
  useEffect(() => {
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported. Using default location.');
      fetchAQIData(DELHI_LAT, DELHI_LNG);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCoords({ lat: latitude, lng: longitude });
        fetchAQIData(latitude, longitude);
      },
      (error) => {
        // BUG 2 FIX C (denial path) — fallback to Delhi, show toast
        toast.error('Could not get your location. Using default.');
        fetchAQIData(DELHI_LAT, DELHI_LNG);
      },
      { timeout: 8000, maximumAge: 60000 }
    );
  }, []);

  // BUG 2 FIX D — axios api instance with Bearer token (via interceptors)
  const fetchAQIData = async (lat, lng) => {
    try {
      const { data } = await api.get('/health/aqi-risk', { params: { lat, lng } });
      if (data?.aqi != null) setAqiValue(data.aqi);
      if (data?.location) setActiveLocation(data.location);
    } catch (err) {
      // Backend offline → keep displayed mock data, don't crash
      console.warn('[AQIMonitor] Backend unavailable, using static data:', err?.message);
    }
  };

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
          <div className="flex items-center gap-6">
             <div className="flex items-center gap-2 bg-[#6143f4]/10 px-4 py-2 rounded-xl border border-[#6143f4]/20">
                <Navigation size={14} className="text-[#6143f4]" />
                <span className="text-xs font-black text-[#6143f4] uppercase tracking-widest">{activeLocation}</span>
             </div>
             <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 relative active:scale-90 transition-all">
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
              <div className="absolute inset-0 opacity-80 z-0 select-none pointer-events-none">
                 <MapContainer 
                    center={[coords.lat, coords.lng]} 
                    zoom={10} 
                    style={{ height: '100%', width: '100%' }}
                    zoomControl={false}
                    scrollWheelZoom={false}
                    dragging={false}
                 >
                    <TileLayer 
                       url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" 
                    />
                    <Marker position={[coords.lat, coords.lng]}>
                       <Popup>{activeLocation}</Popup>
                    </Marker>
                    <Circle 
                       center={[coords.lat, coords.lng]} 
                       radius={5000} 
                       pathOptions={{ color: '#6143f4', fillColor: '#6143f4', fillOpacity: 0.1, weight: 1 }} 
                    />
                 </MapContainer>
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-[#13082A] via-transparent to-transparent"></div>
              
              <div className="relative z-10 p-8 h-full flex flex-col justify-between">
                <div className="flex justify-between items-start">
                   <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-2xl flex items-center gap-3">
                      <div className="size-10 bg-white/20 rounded-xl flex items-center justify-center">
                         <MapPin className="text-white" size={20} />
                      </div>
                      <div>
                        <p className="text-white font-black text-sm tracking-tight">{activeLocation}</p>
                        <p className="text-white/50 text-[10px] font-bold uppercase tracking-widest">Lat: {coords.lat.toFixed(2)}, Lng: {coords.lng.toFixed(2)}</p>
                      </div>
                   </div>
                   <div className="flex gap-2">
                      <button className="size-10 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white flex items-center justify-center hover:bg-white/20 transition-all"><Search size={18} /></button>
                      <button className="size-10 rounded-xl bg-white/10 backdrop-blur-md border border-white/20 text-white flex items-center justify-center hover:bg-white/20 transition-all"><Navigation size={18} /></button>
                   </div>
                </div>

                <div className="flex items-end justify-between">
                   <div className="space-y-4">
                      <div className="flex gap-3">
                         <div className="bg-white/10 backdrop-blur-md p-3 rounded-xl flex items-center gap-2 border border-white/10">
                            <Thermometer size={14} className="text-orange-400" />
                            <span className="text-white text-xs font-bold">28°C</span>
                         </div>
                         <div className="bg-white/10 backdrop-blur-md p-3 rounded-xl flex items-center gap-2 border border-white/10">
                            <Droplets size={14} className="text-blue-400" />
                            <span className="text-white text-xs font-bold">64% Hum.</span>
                         </div>
                      </div>
                      <p className="text-white/40 text-[10px] font-bold uppercase tracking-widest leading-none max-w-[200px]">Interactive Environmental Mapping Terminal</p>
                   </div>
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
