import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Sparkles,
  Activity,
  History,
  FlaskConical,
  FileText,
  Moon,
  Watch,
  Settings,
  Bell,
  Plus,
  Search,
  TrendingUp,
  Heart,
  Flame,
  Footprints,
  Droplets,
  Utensils,
  CloudLightning,
  AlertCircle,
  AlertTriangle,
  RotateCcw,
  Eye,
  CheckCircle2,
  ChevronRight,
  Info,
  BarChart2,
  Stethoscope,
  Microscope,
  Zap,
  CheckCircle,
  ClipboardList,
  Wind
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { ROUTES } from '../router/routes';
import useDashboardStore from '../store/dashboardStore';
import { useAuthStore } from '../store/authStore';


const Dashboard = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('Dashboard');

  // ── Store ─────────────────────────────────────────────────────────────────
  const { healthScore, history, prediction, profile, alerts, googleFit,
    loading, error, fetchDashboardData } = useDashboardStore();
  const authUser = useAuthStore((s) => s.user);

  useEffect(() => { fetchDashboardData(); }, [fetchDashboardData]);

  // ── Per-module data + status ──────────────────────────────────────────────
  // Each store key is now a slice: { data, status, source, last_updated }
  const hsData = healthScore?.data;
  const hiData = history?.data;
  const predData = prediction?.data;
  const profData = profile?.data;
  const alertsData = alerts?.data?.alerts ?? [];
  const gfData = googleFit?.data;

  // Status: 'ready' | 'processing' | 'fallback'
  const hsStatus = healthScore?.status ?? 'fallback';
  const hiStatus = history?.status ?? 'fallback';
  const predStatus = prediction?.status ?? 'fallback';
  const isShimmer = (status) => status === 'processing';  // dim + animate
  const isFallback = (status) => status === 'fallback';    // show subtle badge

  // ── Derived display values ────────────────────────────────────────────────
  const score = hsData?.score ?? 75;
  const scoreLabel = hsData?.label ?? '…';
  const riskScoreData = [
    { name: 'Score', value: score },
    { name: 'Remaining', value: 100 - score },
  ];
  const hrvData = hiData?.hrv ?? [];
  const sleepData = hiData?.sleep ?? [];
  const avgBpm = hiData?.hrv_average_bpm ?? '—';
  const avgSleep = hiData?.sleep_average_hours ?? '—';
  const displayName = profData?.full_name ?? authUser?.full_name ?? 'User';
  const bioAgeDelta = predData?.biological_age_delta ?? '—';
  const metabolicRate = predData?.metabolic_rate ?? '—';
  const trajectilePercentile = predData?.trajectory_percentile ?? '—';
  const predRecs = predData?.recommendations ?? [];

  const gfSteps = (gfData?.connected && gfData?.stats?.latest_day?.steps !== undefined) ? gfData.stats.latest_day.steps : 8432;
  const gfDistance = (gfSteps * 0.00073529).toFixed(1);
  const gfCalories = Math.round(gfSteps * 0.050759);
  const gfProgress = Math.min((gfSteps / 10000) * 100, 100).toFixed(2);

  const sidebarLinks = [
    { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
    { icon: Sparkles, label: 'AI Insights', path: ROUTES.INSIGHTS },
    { icon: TrendingUp, label: 'Disease Simulator', path: ROUTES.SIMULATOR },
    { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE },
    { icon: Microscope, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
    { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS },
    { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP },
    { icon: Watch, label: 'Device Manager', path: ROUTES.DEVICES },
  ];

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.05 } }
  };

  const itemVariants = {
    initial: { opacity: 0, scale: 0.98, y: 10 },
    animate: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } }
  };

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] font-display text-[#13082A] dark:text-slate-100 min-h-screen flex antialiased">

      {/* Left Sidebar - Matched Stitch */}


      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">

        {/* Top Header Navbar - Matched Stitch */}
        <header className="h-20 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative w-full max-w-md group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
              <input
                className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-[#6143f4] text-sm font-medium"
                placeholder="Search health records, insights, or labs..."
                type="text"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-500 bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full relative transition-colors">
              <Bell size={20} />
              <span className="absolute top-2.5 right-2.5 size-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-slate-900"></span>
            </button>
            <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-2"></div>
            <button className="flex items-center gap-2 bg-[#6143f4] text-white px-4 py-2 rounded-xl text-sm font-bold shadow-lg shadow-[#6143f4]/20 hover:shadow-xl transition-all active:scale-95">
              <Plus size={16} strokeWidth={3} />
              Sync Data
            </button>
          </div>
        </header>

        {/* Dashboard Content Container */}
        <motion.div
          variants={containerVariants}
          initial="initial"
          animate="animate"
          className="p-8 space-y-8 max-w-7xl mx-auto w-full"
        >
          {/* Error Banner — Added Post-Audit */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 rounded-r-xl flex items-center gap-4 group"
              >
                <AlertCircle className="text-red-500 shrink-0" size={24} />
                <div className="flex-1 min-w-0">
                  <p className="text-red-900 dark:text-red-200 font-bold text-sm">Dashboard Data Sync Issue</p>
                  <p className="text-red-700 dark:text-red-400/80 text-xs font-medium truncate">{error}</p>
                </div>
                <button
                  onClick={() => fetchDashboardData()}
                  className="bg-red-500 text-white px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest hover:bg-red-600 transition-colors"
                >
                  Retry Now
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Section 1: Hero Stats Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Health Risk Gauge - Matched Stitch */}
            <motion.div variants={itemVariants} className="lg:col-span-1 bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col items-center justify-center text-center relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <BarChart2 size={120} className="text-[#6143f4]" />
              </div>
              <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-8">Health Risk Score</h3>

              <div className="relative size-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskScoreData}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={88}
                      startAngle={225}
                      endAngle={-45}
                      paddingAngle={0}
                      dataKey="value"
                      stroke="none"
                    >
                      <Cell fill="#6143f4" strokeLinecap="round" />
                      <Cell fill="rgba(0,0,0,0.05)" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-5xl font-black text-[#13082A] dark:text-white leading-none">84</span>
                  <span className="text-slate-400 font-bold text-sm tracking-tight mt-1">Optimal</span>
                </div>
              </div>

              <p className="mt-8 text-slate-500 font-medium text-sm">
                Your risk factor has decreased by <span className="text-green-500 font-bold px-1.5 py-0.5 bg-green-50 dark:bg-green-500/10 rounded-lg">4.2%</span> since last month.
              </p>
            </motion.div>

            {/* Environmental Risk Card - NEW Additive Link */}
            <motion.div
              variants={itemVariants}
              onClick={() => navigate(ROUTES.AQI_MONITOR)}
              className="lg:col-span-1 bg-gradient-to-br from-[#13082A] to-[#1a1433] p-8 rounded-xl shadow-xl border border-white/5 flex flex-col items-center justify-center text-center relative overflow-hidden group cursor-pointer hover:scale-[1.02] transition-all"
            >
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <Wind size={120} className="text-white" />
              </div>
              <h3 className="text-white/40 font-bold text-[10px] uppercase tracking-[0.3em] mb-8 italic">Environmental Risk</h3>
              <div className="size-32 bg-white/5 rounded-full flex items-center justify-center relative shadow-inner">
                <Wind size={48} className="text-[#6143f4] animate-pulse" />
                <div className="absolute -bottom-2 bg-[#6143f4] text-white text-[10px] font-black px-3 py-1 rounded-full shadow-lg">156 AQI</div>
              </div>
              <p className="mt-8 text-white/60 font-medium text-xs leading-relaxed">
                Atmospheric particulates are <span className="text-[#6143f4] font-black underline">elevated</span>. High priority risk modifier detected.
              </p>
              <div className="mt-6 flex items-center gap-2 text-[#6143f4] font-black text-[10px] uppercase tracking-widest">
                Check Risk Node <ChevronRight size={14} />
              </div>
            </motion.div>

            {/* HRV Chart */}
            <motion.div variants={itemVariants} className="lg:col-span-2 bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col group">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-1">Heart Rate Variability</h3>
                  <p className="text-3xl font-black text-[#13082A] dark:text-white">{avgBpm} <span className="text-sm font-medium text-slate-400 ml-1">bpm average</span></p>
                </div>
                <div className="flex gap-2">
                  <span className="px-3 py-1 bg-[#6143f4]/10 text-[#6143f4] rounded-full text-[10px] font-black uppercase tracking-widest border border-[#6143f4]/20">Live</span>
                  <span className="px-3 py-1 bg-slate-50 dark:bg-slate-800 text-slate-500 rounded-full text-[10px] font-black uppercase tracking-widest border border-slate-100 dark:border-slate-700">24h</span>
                </div>
              </div>

              <div className="flex-1 min-h-[180px] w-full mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={hrvData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="hrvGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6143f4" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#6143f4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.03)" />
                    <Tooltip
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.05)', fontWeight: 'bold' }}
                      itemStyle={{ color: '#6143f4' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#6143f4"
                      strokeWidth={3}
                      fillOpacity={1}
                      fill="url(#hrvGradient)"
                      animationDuration={2000}
                    />
                    <XAxis
                      dataKey="time"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 9, fontWeight: 'bold', fill: '#94a3b8' }}
                      dy={10}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          </div>

          {/* Section 2: AI Prediction */}
          <motion.div variants={itemVariants} className="relative overflow-hidden rounded-xl p-8 bg-gradient-to-br from-[#6143f4] via-[#6143f4]/90 to-[#009CDE] shadow-xl group border border-white/10">
            <div className="absolute inset-0 opacity-15 pointer-events-none mix-blend-overlay">
              <div className="absolute top-0 left-0 w-full h-full" style={{ backgroundImage: "url('https://www.transparenttextures.com/patterns/carbon-fibre.png')" }}></div>
            </div>
            <div className="relative z-10 flex flex-col lg:flex-row gap-8 items-center">
              <div className="flex-1">
                <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-md px-4 py-1.5 rounded-full mb-6 border border-white/30">
                  <Sparkles size={14} className="text-white" fill="currentColor" />
                  <span className="text-white text-[10px] font-black uppercase tracking-[0.2em]">Predictive Engine v2.4</span>
                </div>
                <h2 className="text-3xl font-black text-white mb-4 tracking-tight">5-Year Health Trajectory</h2>
                <p className="text-white/80 text-lg leading-relaxed max-w-2xl font-medium">
                  Based on your metabolic markers, your cardiovascular health is projected to remain in the{' '}
                  <span className="text-white font-black underline decoration-white/40 decoration-2 underline-offset-4">{trajectilePercentile}th percentile</span>.
                  {predRecs[0] && <> {predRecs[0]}.</>}
                </p>
                <div className="mt-8 flex flex-wrap gap-4">
                  <button className="bg-white text-[#6143f4] px-6 py-3 rounded-xl font-bold text-sm shadow-xl hover:scale-105 transition-all active:scale-95">Detailed Simulation</button>
                  <button className="bg-[#6143f4]/30 backdrop-blur-md text-white border border-white/30 px-6 py-3 rounded-xl font-bold text-sm hover:bg-[#6143f4]/40 transition-all active:scale-95">View Metabolic Data</button>
                </div>
              </div>

              <div className="w-full lg:w-72 bg-white/10 backdrop-blur-xl rounded-xl border border-white/20 p-6 shadow-2xl">
                <h4 className="text-white font-black text-[10px] uppercase tracking-[0.3em] mb-8 flex items-center gap-2">
                  <TrendingUp size={14} /> Vital Forecast
                </h4>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-white/70 text-xs font-bold">Biological Age</span>
                      <span className="text-white font-black text-xl tracking-tight">{bioAgeDelta}</span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: '75%' }} transition={{ duration: 1.5, delay: 0.5 }} className="h-full bg-white rounded-full shadow-lg shadow-white/20"></motion.div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-end">
                      <span className="text-white/70 text-xs font-bold">Metabolic Rate</span>
                      <span className="text-white font-black text-xl tracking-tight">{metabolicRate}</span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: '85%' }} transition={{ duration: 1.5, delay: 0.7 }} className="h-full bg-white rounded-full shadow-lg shadow-white/20"></motion.div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Section 3: Secondary Stats Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Sleep Quality */}
            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
              <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-4">Sleep Quality</h3>
              <div className="flex items-end gap-2 mb-8">
                <span className="text-3xl font-black text-[#13082A] dark:text-white">{avgSleep}</span>
                <span className="text-slate-400 font-medium mb-1.5">hrs avg</span>
              </div>
              <div className="h-32 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sleepData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.03)" />
                    <XAxis
                      dataKey="day"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 9, fontWeight: 'bold', fill: '#94a3b8' }}
                    />
                    <Tooltip cursor={{ fill: 'rgba(0,0,0,0.02)' }} />
                    <Bar
                      dataKey="hours"
                      fill="#6143f4"
                      radius={[4, 4, 4, 4]}
                      barSize={16}
                      animationDuration={1500}
                    >
                      {sleepData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 5 ? '#009CDE' : '#6143f4'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Daily Steps Progress - Matched Stitch */}
            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
              <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-4">Daily Steps</h3>
              <div className="flex items-end gap-2 mb-8">
                <span className="text-3xl font-black text-[#13082A] dark:text-white">{gfSteps.toLocaleString()}</span>
                <span className="text-slate-400 font-medium mb-1.5">/ 10,000</span>
              </div>
              <div className="space-y-6">
                <div className="h-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner border border-white dark:border-slate-700">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${gfProgress}%` }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className="h-full bg-gradient-to-r from-[#6143f4] to-[#009CDE] rounded-full"
                  ></motion.div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700 group hover:bg-[#6143f4]/5 hover:border-[#6143f4]/20 transition-all">
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none mb-2">Distance</p>
                    <p className="text-xl font-black text-[#13082A] dark:text-white">{gfDistance} <span className="text-xs font-bold text-slate-400 ml-1">km</span></p>
                  </div>
                  <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700 group hover:bg-[#6143f4]/5 hover:border-[#6143f4]/20 transition-all">
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none mb-2">Calories</p>
                    <p className="text-xl font-black text-[#13082A] dark:text-white">{gfCalories} <span className="text-xs font-bold text-slate-400 ml-1">kcal</span></p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Daily Health Summary - Matched Stitch */}
            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col">
              <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-6">Health Summary</h3>
              <div className="space-y-5 flex-1 overflow-y-auto custom-scrollbar">
                {[
                  { icon: Droplets, color: 'text-blue-500', bg: 'bg-blue-100 dark:bg-blue-900/20', title: 'Hydration Level', desc: 'You are 1.2L behind your daily goal. Drink up!' },
                  { icon: Utensils, color: 'text-orange-500', bg: 'bg-orange-100 dark:bg-orange-900/20', title: 'Caloric Intake', desc: 'Breakfast was high in protein, good for recovery.' },
                  { icon: Activity, color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900/20', title: 'Stress Levels', desc: 'Cortisol levels are steady. Perfect focus window.' }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 group">
                    <div className={`${item.bg} ${item.color} size-10 shrink-0 rounded-full flex items-center justify-center transition-transform group-hover:scale-110 shadow-sm border border-white dark:border-slate-700`}>
                      <item.icon size={18} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-[#13082A] dark:text-white tracking-tight">{item.title}</p>
                      <p className="text-xs text-slate-500 leading-relaxed font-medium mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Section 4: Critical Alerts & Recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">

            {/* Alerts Panel — dynamic from backend */}
            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border-l-4 border-red-500 border-slate-100 dark:border-slate-800 relative overflow-hidden group">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-red-500 font-black text-xs uppercase tracking-[0.3em] flex items-center gap-2">
                  <AlertCircle size={16} fill="currentColor" /> Critical Updates
                </h3>
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                  {alertsData.length > 0 ? `${alertsData.length} Active Alert${alertsData.length > 1 ? 's' : ''}` : 'No Active Alerts'}
                </span>
              </div>
              <div className="space-y-4">
                {alertsData.length === 0 ? (
                  <div className="flex items-center gap-3 text-slate-400 text-sm font-medium py-4">
                    <CheckCircle size={18} className="text-green-400" />
                    All health indicators are within normal range.
                  </div>
                ) : alertsData.map((alert, i) => (
                  <div key={i} className={`p-5 rounded-xl border flex items-start gap-4 transition-all cursor-pointer ${alert.severity === 'critical'
                    ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-500/20 hover:bg-red-50/80'
                    : 'bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800 hover:bg-slate-100'
                    }`}>
                    <AlertTriangle className={`mt-0.5 shrink-0 ${alert.severity === 'critical' ? 'text-red-500' : 'text-slate-500'}`} size={20} />
                    <div>
                      <p className={`text-sm font-bold ${alert.severity === 'critical' ? 'text-red-900 dark:text-red-200' : 'text-[#13082A] dark:text-white'}`}>{alert.title}</p>
                      <p className={`text-xs mt-1 font-medium leading-relaxed ${alert.severity === 'critical' ? 'text-red-700 dark:text-red-400/80' : 'text-slate-500'}`}>{alert.message}</p>
                      {alert.action_label && (
                        <button className="mt-3 text-xs font-bold underline text-red-600 hover:text-red-700 decoration-2">{alert.action_label}</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Recommended Tests - Matched Stitch */}
            <motion.div variants={itemVariants} className="bg-white dark:bg-slate-900 p-8 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
              <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-8">Recommended Tests</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { icon: Microscope, title: 'CBC with Differential', date: 'Due in 14 days', badge: 'Annual', color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/10' },
                  { icon: Heart, title: '24-Hr Holter Monitor', date: 'Schedule ASAP', badge: 'Priority', color: 'text-[#009CDE]', bg: 'bg-[#009CDE]/10', urgent: true },
                  { icon: Zap, title: 'HbA1c Blood Test', date: 'Due in 3 months', badge: 'Routine', color: 'text-[#6143f4]', bg: 'bg-[#6143f4]/10' },
                  { icon: Eye, title: 'Retinal Imaging', date: 'Due in 45 days', badge: 'Vision', color: 'text-[#009CDE]', bg: 'bg-[#009CDE]/10' }
                ].map((test, i) => (
                  <div key={i} className="p-4 border border-slate-100 dark:border-slate-800 rounded-xl hover:border-[#6143f4]/30 transition-all cursor-pointer group hover:shadow-lg hover:shadow-black/5 bg-white dark:bg-slate-900">
                    <div className="flex items-center justify-between mb-3">
                      <div className={`${test.bg} ${test.color} p-2 rounded-lg transition-transform group-hover:scale-110 shadow-sm border border-white dark:border-slate-800`}>
                        <test.icon size={18} />
                      </div>
                      <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-full ${test.urgent ? 'bg-[#009CDE] text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'}`}>{test.badge}</span>
                    </div>
                    <p className="text-sm font-bold text-[#13082A] dark:text-white leading-tight truncate">{test.title}</p>
                    <p className="text-xs text-slate-500 font-medium mt-1 uppercase tracking-wider">{test.date}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </motion.div>

        <footer className="py-8 px-10 text-center text-slate-400 dark:text-slate-600 text-[10px] font-bold uppercase tracking-[0.3em] mt-auto border-t border-slate-100 dark:border-slate-800 bg-white/40 dark:bg-slate-900/40 backdrop-blur-sm relative z-20">
          © 2024 ArogyaAI Neural Systems • Clinical Grade Intelligence • HIPAA Certified
        </footer>
      </main>

      <style dangerouslySetInnerHTML={{
        __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #6143f422; border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #6143f444; }
      `}} />
    </div >
  );
};

export default Dashboard;
