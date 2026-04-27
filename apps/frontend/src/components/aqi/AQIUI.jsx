import React from 'react';
import {
    Plus,
    Minus,
    MapPin,
    Navigation,
    Search,
    Clock,
    AlertTriangle,
    Wind,
    CheckCircle2,
    Zap,
    Rocket,
    Activity
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
import { motion, AnimatePresence } from 'framer-motion';

// Note: Using Material Symbols for some icons as per design, but substituting with Lucide where appropriate.
// The design uses "material-symbols-outlined". I'll use Lucide-react for consistency with the existing system.

const AQIUI = ({
    data,
    loading,
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
    searchContainerRef,
    isAlertEnabled,
    setIsAlertEnabled,
    alertThreshold,
    aqiTrendData,
    navigate // For links
}) => {

    const getAqiConfig = (val) => {
        if (val <= 50) return { label: 'Good', color: 'text-green-500', bg: 'bg-green-500', iconColor: 'text-accent-green', desc: 'Air quality is satisfactory, and air pollution poses little or no risk.', action: 'Safe for outdoor exercise' };
        if (val <= 100) return { label: 'Moderate', color: 'text-yellow-500', bg: 'bg-yellow-500', iconColor: 'text-accent-yellow', desc: 'Air quality is acceptable. Sensitive groups should reduce exertion.', action: 'Reduce prolonged outdoor exertion' };
        if (val <= 150) return { label: 'Unhealthy (S)', color: 'text-orange-500', bg: 'bg-orange-500', iconColor: 'text-orange-500', desc: 'Members of sensitive groups may experience health effects.', action: 'Limit outdoor exertion for sensitive groups' };
        if (val <= 200) return { label: 'Unhealthy', color: 'text-red-500', bg: 'bg-red-500', iconColor: 'text-accent-red', desc: 'Everyone may begin to experience health effects.', action: 'Avoid outdoor exercise. Keep windows closed.' };
        if (val <= 300) return { label: 'Very Unhealthy', color: 'text-purple-500', bg: 'bg-purple-500', iconColor: 'text-purple-500', desc: 'Health alert: everyone may experience more serious health effects.', action: 'Remain indoors. Use air purifiers.' };
        return { label: 'Hazardous', color: 'text-red-900', bg: 'bg-red-900', iconColor: 'text-red-900', desc: 'Health warnings of emergency conditions.', action: 'Strictly indoors. Seek medical advice if symptomatic.' };
    };

    const aqiValue = data?.aqi || 0;
    const aqiConfig = getAqiConfig(aqiValue);
    const osmMapEmbedUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${(coords.lng - 0.12).toFixed(6)}%2C${(coords.lat - 0.12).toFixed(6)}%2C${(coords.lng + 0.12).toFixed(6)}%2C${(coords.lat + 0.12).toFixed(6)}&layer=mapnik&marker=${coords.lat}%2C${coords.lng}`;

    return (
        <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-[#EAEAEA] dark:bg-[#13082A] text-slate-900 dark:text-slate-100 font-display transition-colors">
            {/* Header Section */}
            <div className="max-w-4xl">
                <h1 className="text-4xl font-black text-background-dark dark:text-white tracking-tight">Air Quality Risk Monitor</h1>
                <p className="mt-2 text-slate-500 dark:text-slate-400 text-lg leading-relaxed">
                    Precision monitoring of environmental pollutants. Our AI analyzes real-time atmospheric data to predict and mitigate respiratory risks for vulnerable patients.
                </p>
            </div>

            {/* Hero Section: Map & Widgets */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 h-auto">
                {/* Interactive Map */}
                <div className="xl:col-span-8 relative h-[500px] bg-white dark:bg-slate-900 rounded-3xl overflow-hidden shadow-sm border border-slate-200 dark:border-slate-800">
                    <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ background: 'radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.2) 0%, rgba(251, 191, 36, 0.2) 30%, rgba(239, 68, 68, 0.1) 60%)' }}></div>

                    <iframe
                        title="OpenStreetMap AQI Location"
                        src={osmMapEmbedUrl}
                        className="h-full w-full border-0 opacity-95"
                        loading="lazy"
                        referrerPolicy="no-referrer-when-downgrade"
                    />

                    {/* Map Controls */}
                    <div className="absolute top-4 right-4 flex flex-col gap-2">
                        <button className="bg-white dark:bg-slate-800 p-2 rounded-lg shadow-md text-slate-600 dark:text-slate-300 hover:text-[#6143f4] transition-colors"><Plus size={20} /></button>
                        <button className="bg-white dark:bg-slate-800 p-2 rounded-lg shadow-md text-slate-600 dark:text-slate-300 hover:text-[#6143f4] transition-colors"><Minus size={20} /></button>
                        <button onClick={onLocationClick} className="bg-white dark:bg-slate-800 p-2 rounded-lg shadow-md text-slate-600 dark:text-slate-300 hover:text-[#6143f4] mt-2 transition-colors"><Navigation size={20} className={loading ? 'animate-pulse' : ''} /></button>
                    </div>

                    {/* Map Markers (Visual indicators only for now) */}
                    <div className="absolute top-1/4 left-1/3 group cursor-pointer pointer-events-none">
                        <div className="size-4 bg-[#10B981] rounded-full shadow-[0_0_20px_rgba(16,185,129,0.8)] animate-pulse"></div>
                    </div>
                    <div className="absolute top-1/2 left-1/2 group cursor-pointer pointer-events-none">
                        <div className="size-6 bg-[#FBBF24] rounded-full shadow-[0_0_20px_rgba(251,191,36,0.8)] border-4 border-white"></div>
                    </div>

                    {/* Map Legend */}
                    <div className="absolute bottom-4 left-4 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md p-4 rounded-2xl border border-white/50 dark:border-white/10">
                        <p className="text-[10px] font-bold text-slate-600 dark:text-slate-400 uppercase mb-2">AQI Legend</p>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-1.5"><div className="size-2 rounded-full bg-[#10B981]"></div><span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Good</span></div>
                            <div className="flex items-center gap-1.5"><div className="size-2 rounded-full bg-[#FBBF24]"></div><span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Mod</span></div>
                            <div className="flex items-center gap-1.5"><div className="size-2 rounded-full bg-orange-500"></div><span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Unhealthy</span></div>
                            <div className="flex items-center gap-1.5"><div className="size-2 rounded-full bg-[#EF4444]"></div><span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">Hazard</span></div>
                        </div>
                    </div>
                </div>

                {/* Sidebar Widgets */}
                <div className="xl:col-span-4 space-y-6">
                    {/* Location Selector */}
                    <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800">
                        <h3 className="text-sm font-bold text-background-dark dark:text-white mb-4">Location</h3>
                        <div className="space-y-3">
                            <div ref={searchContainerRef} className="relative">
                                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                                <input
                                    className="w-full bg-slate-50 dark:bg-slate-800 border-slate-100 dark:border-slate-700 rounded-xl py-2.5 pl-9 text-sm font-medium focus:ring-2 focus:ring-[#6143f4]/20 outline-none"
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => {
                                        setSearchQuery(e.target.value);
                                        onSearchOpen(true);
                                    }}
                                    onFocus={() => onSearchOpen(true)}
                                    placeholder="Mumbai, Maharashtra"
                                />
                                <AnimatePresence>
                                    {isSearchOpen && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -8 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -8 }}
                                            className="absolute left-0 right-0 top-14 z-50 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#13082A] p-2 shadow-2xl backdrop-blur-xl"
                                        >
                                            <div className="max-h-64 overflow-y-auto rounded-xl">
                                                {isSearching ? (
                                                    <div className="px-4 py-3 text-xs font-bold uppercase tracking-widest text-slate-400">
                                                        Searching cities...
                                                    </div>
                                                ) : searchQuery.trim().length < 2 ? (
                                                    <div className="px-4 py-3 text-xs font-bold uppercase tracking-widest text-slate-400">
                                                        Type at least 2 letters
                                                    </div>
                                                ) : searchSuggestions.length === 0 ? (
                                                    <div className="px-4 py-3 text-xs font-bold uppercase tracking-widest text-slate-400">
                                                        No matching city found
                                                    </div>
                                                ) : (
                                                    searchSuggestions.map((suggestion, index) => (
                                                        <button
                                                            key={`${suggestion.label}-${suggestion.lat}-${suggestion.lng}`}
                                                            type="button"
                                                            onMouseEnter={() => setHighlightedIndex(index)}
                                                            onClick={() => submitCitySearch(suggestion)}
                                                            className={`flex w-full items-start gap-3 px-4 py-2.5 text-left rounded-lg transition-all ${highlightedIndex === index ? 'bg-[#6143f4]/10 text-[#6143f4]' : 'hover:bg-slate-50 dark:hover:bg-white/5'
                                                                }`}
                                                        >
                                                            <MapPin size={14} className="mt-0.5 shrink-0" />
                                                            <div>
                                                                <p className="text-sm font-bold">{suggestion.name}</p>
                                                                <p className="text-[10px] font-semibold uppercase tracking-wide opacity-60">
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
                                onClick={onLocationClick}
                                className="w-full flex items-center justify-center gap-2 py-2.5 text-[#6143f4] bg-[#6143f4]/5 hover:bg-[#6143f4]/10 rounded-xl text-sm font-bold transition-all"
                            >
                                <Navigation size={14} />
                                Use Current Location
                            </button>
                        </div>
                    </div>

                    {/* AQI Status Card */}
                    <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 relative overflow-hidden">
                        <div className={`absolute top-0 right-0 w-32 h-32 ${aqiConfig.bg} opacity-5 rounded-full -mr-16 -mt-16`}></div>
                        <div className="flex items-start justify-between">
                            <div>
                                <p className="text-sm font-bold text-slate-500">AQI Index</p>
                                <div className="flex items-baseline gap-1 mt-1">
                                    <span className="text-6xl font-black text-background-dark dark:text-white tracking-tighter">
                                        {loading ? "..." : aqiValue}
                                    </span>
                                    {!loading && <span className={`text-sm font-bold ${aqiConfig.color}`}>{aqiConfig.label}</span>}
                                </div>
                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mt-4 flex items-center gap-1">
                                    <Clock size={12} />
                                    Updated 5 mins ago
                                </p>
                            </div>
                            <div className={`size-16 rounded-full border-8 ${loading ? 'border-slate-100' : 'border-' + aqiConfig.bg.split('-')[1] + '-500/20'} flex items-center justify-center`}>
                                <div className={`size-8 rounded-full ${loading ? 'bg-slate-200 animate-pulse' : aqiConfig.bg}`}></div>
                            </div>
                        </div>
                    </div>

                    {/* AI Health Impact Notice */}
                    <div className="bg-background-dark dark:bg-slate-900 p-6 rounded-3xl shadow-xl text-white border border-white/5">
                        <h3 className="text-sm font-bold uppercase tracking-widest text-[#6143f4] mb-6">AI Health Assessment</h3>
                        <div className="space-y-6">
                            <div className="flex gap-4">
                                <div className="size-10 rounded-xl bg-[#FBBF24]/20 flex items-center justify-center shrink-0">
                                    <AlertTriangle className="text-[#FBBF24]" size={20} />
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-white leading-tight">Respiratory Alert</p>
                                    <p className="text-xs text-slate-400 mt-1">Elevated particulate matter (PM2.5) may cause irritation for asthmatic patients.</p>
                                </div>
                            </div>
                            <div className="h-px bg-slate-800"></div>
                            <div>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Preventive Advice</p>
                                <div className="grid grid-cols-1 gap-2">
                                    <div className="flex items-center gap-3 bg-white/5 p-3 rounded-xl">
                                        <Activity className="text-[#6143f4]" size={16} />
                                        <span className="text-xs font-medium">Wear N95 Mask outdoors</span>
                                    </div>
                                    <div className="flex items-center gap-3 bg-white/5 p-3 rounded-xl">
                                        <Activity className="text-[#6143f4]" size={16} />
                                        <span className="text-xs font-medium">Avoid outdoor exercise</span>
                                    </div>
                                    <div className="flex items-center gap-3 bg-white/5 p-3 rounded-xl">
                                        <Activity className="text-[#6143f4]" size={16} />
                                        <span className="text-xs font-medium">Keep air purifiers at 50%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Section: Historical Trends */}
            <div className="bg-white dark:bg-slate-900 p-8 rounded-[2rem] shadow-sm border border-slate-200 dark:border-slate-800">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                    <div>
                        <h3 className="text-xl font-bold text-background-dark dark:text-white">7-Day AQI History</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Historical trend of atmospheric pollutants for {location}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button className="px-4 py-2 text-xs font-bold bg-[#6143f4] text-white rounded-lg">PM2.5</button>
                        <button className="px-4 py-2 text-xs font-bold bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">O3</button>
                        <button className="px-4 py-2 text-xs font-bold bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">NO2</button>
                    </div>
                </div>

                {/* Improved Responsive Chart */}
                <div className="h-[300px] w-full mt-4">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={aqiTrendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6143f4" stopOpacity={0.2} />
                                    <stop offset="95%" stopColor="#6143f4" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148, 163, 184, 0.1)" />
                            <XAxis
                                dataKey="day"
                                axisLine={false}
                                tickLine={false}
                                tick={{ fontSize: 10, fontWeight: 'bold', fill: '#94a3b8' }}
                                dy={10}
                            />
                            <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fontSize: 10, fontWeight: 'bold', fill: '#94a3b8' }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1e293b',
                                    border: 'none',
                                    borderRadius: '12px',
                                    color: '#fff',
                                    fontSize: '12px',
                                    fontWeight: 'bold'
                                }}
                            />
                            <Area
                                type="monotone"
                                dataKey="aqi"
                                stroke="#6143f4"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#chartGradient)"
                                animationDuration={2000}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Additional Design Elements from MCP */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pb-12">
                {/* Personal Health Risk Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gradient-to-r from-[#6143f4] to-[#009CDE] rounded-3xl p-1 shadow-2xl overflow-hidden"
                >
                    <div className="bg-white dark:bg-[#1a1433] rounded-[1.4rem] p-8 space-y-6">
                        <div className="inline-flex items-center gap-2 bg-[#6143f4]/10 px-3 py-1.5 rounded-full border border-[#6143f4]/20">
                            <AlertTriangle size={12} className="text-[#6143f4]" />
                            <span className="text-[#6143f4] text-[10px] font-black uppercase tracking-[0.2em]">Clinical Risk Escalation</span>
                        </div>
                        <h2 className="text-2xl font-black tracking-tighter leading-tight italic uppercase">Personal Health <span className="text-[#6143f4]">Impact</span></h2>
                        <p className="text-slate-500 dark:text-slate-400 font-medium text-sm leading-relaxed">
                            High particulate matter concentrations in your current location are elevating your <span className="text-[#6143f4] font-black underline decoration-2 underline-offset-4 decoration-[#6143f4]/20">Respiratory Risk Modifier by +8.4%</span>.
                        </p>
                        <div className="flex gap-3 pt-2">
                            <button
                                onClick={() => navigate('/recommendations')}
                                className="bg-[#6143f4] text-white px-6 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest shadow-lg shadow-[#6143f4]/30 hover:scale-105 transition-all"
                            >
                                View Actions
                            </button>
                        </div>
                    </div>
                </motion.div>

                {/* Alerts Config Card */}
                <div className="bg-white dark:bg-slate-900 p-8 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div className={`size-14 rounded-2xl flex items-center justify-center transition-all ${isAlertEnabled ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/30' : 'bg-slate-100 text-slate-400'}`}>
                            <Zap size={24} className={isAlertEnabled ? 'animate-bounce' : ''} />
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
            </div>
        </div>
    );
};

export default AQIUI;
