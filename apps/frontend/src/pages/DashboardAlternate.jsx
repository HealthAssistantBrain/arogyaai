import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, 
  BarChart2, 
  Users, 
  Watch, 
  Sparkles, 
  Settings, 
  Search, 
  Bell, 
  MessageSquare, 
  TrendingUp, 
  Activity, 
  Heart, 
  Droplets, 
  Zap, 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  PlusCircle, 
  Clock, 
  Flame, 
  BrainCircuit,
  ChevronRight,
  ShieldCheck,
  Smartphone,
  ClipboardList,
  LineChart as LineChartIcon,
  Stethoscope,
  Microscope,
  IterationCcw
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { ROUTES } from '../router/routes';

// Mock Data
const metabolicTrendData = [
  { name: 'Week 1', value: 220 },
  { name: 'Week 2', value: 210 },
  { name: 'Week 3', value: 250 },
  { name: 'Week 4', value: 180 },
  { name: 'Week 5', value: 100 },
  { name: 'Week 6', value: 140 },
  { name: 'Week 7', value: 100 },
  { name: 'Week 8', value: 60 },
  { name: 'Week 9', value: 80 },
  { name: 'Week 10', value: 50 },
];

const sleepScoreData = [
  { name: 'Quality', value: 82 },
  { name: 'Remaining', value: 18 },
];

const DashboardAlternate = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('Dashboard');

  const metrics = [
    { label: 'Heart Rate Var. (HRV)', value: '64', unit: 'ms', trend: '+12%', trendColor: 'text-green-600', trendBg: 'bg-green-100', stroke: '#6043F4', data: [35, 10, 30, 15, 25, 5, 20] },
    { label: 'Oxygen Sat. (SpO2)', value: '98', unit: '%', trend: '-1%', trendColor: 'text-red-500', trendBg: 'bg-red-100', stroke: '#009CDE', data: [20, 15, 22, 18, 20, 19, 21] },
    { label: 'Resting HR (RHR)', value: '58', unit: 'bpm', trend: '-3%', trendColor: 'text-green-600', trendBg: 'bg-green-100', stroke: '#6043F4', data: [30, 35, 15, 20, 25, 22, 28] },
    { label: 'Blood Glucose', value: '92', unit: 'mg/dL', trend: '+2%', trendColor: 'text-green-600', trendBg: 'bg-green-100', stroke: '#009CDE', data: [25, 10, 30, 15, 22, 25, 18] },
  ];

  const sidebarLinks = [
    { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
    { icon: BarChart2, label: 'Analytics', path: ROUTES.DASHBOARD_ALT },
    { icon: Users, label: 'Patients', path: '/patients' },
    { icon: Watch, label: 'Wearables', path: ROUTES.DEVICES },
    { icon: Sparkles, label: 'AI Insights', path: ROUTES.INSIGHTS },
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
    <div className="bg-[#EAEAEA] dark:bg-[#131022] text-[#13082A] dark:text-slate-100 min-h-screen font-display antialiased leading-normal">
      <div className="flex h-screen overflow-hidden">
        
        {/* Sidebar Navigation - Matched Stitch */}


        <main className="flex-1 flex flex-col overflow-hidden relative">
          
          {/* Top Header Navbar - Matched Stitch */}
          <header className="h-20 bg-white/50 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-8 shrink-0 backdrop-blur-md z-30">
            <div className="w-96">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6043F4] transition-colors" size={18} />
                <input 
                  className="w-full bg-slate-100/50 dark:bg-slate-800 border-none rounded-xl pl-10 pr-4 py-2 focus:ring-2 focus:ring-[#6043F4]/20 text-sm font-medium transition-all outline-none" 
                  placeholder="Search biometrics, patients, or alerts..." 
                  type="text"
                />
              </div>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <button className="size-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors relative">
                  <Bell size={20} className="text-slate-600 dark:text-slate-400" />
                  <span className="absolute top-2.5 right-2.5 size-2 bg-red-500 rounded-full border-2 border-white dark:border-slate-900 shadow-sm"></span>
                </button>
                <button className="size-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                  <MessageSquare size={20} className="text-slate-600 dark:text-slate-400" />
                </button>
              </div>
              <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-800"></div>
              
              <div className="flex items-center gap-3">
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-bold leading-none">Dr. Elena Kostic</p>
                  <p className="text-[10px] text-slate-500 font-medium mt-1 uppercase tracking-widest">Head of Cardiology</p>
                </div>
                <div className="size-10 rounded-full bg-[#6043F4]/20 overflow-hidden border-2 border-white dark:border-slate-700 shadow-sm">
                  <img 
                    className="w-full h-full object-cover" 
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuAFvQx4D6Pg2Vup_aFO8U62tnxOuNdrKQQmb5f1tT4GYlWHxaJx67XDwQZRYXKeotUnWQmwOAQXw16X9A8s9NqHgUtnNM8Y30BpyDuqj_mTUyU_pc_boJSOO9iDoAiEzsChzgSc85o18ysKdCylmw1q75ulSCmMB61VbjMtSFgpSh4qVLfEnjTHaXLyl321Jut1N44NOVHrMKh8IFUXtV-chqs_gFsvzl0F9BVcHsi_qnmkmoTsYAYOEcPO0AUaG_jlBAK51UPnNWGW" 
                    alt="Elena Kostic Profile" 
                  />
                </div>
              </div>
            </div>
          </header>

          {/* Main Context Area - Matched Stitch Layout */}
          <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar relative z-10">
            
            {/* Row 1: Key Metrics Matrix */}
            <motion.div 
              variants={containerVariants}
              initial="initial"
              animate="animate"
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
            >
              {metrics.map((m) => (
                <motion.div 
                  key={m.label} 
                  variants={itemVariants}
                  className="bg-white/70 dark:bg-slate-900/70 backdrop-blur-md p-5 rounded-xl border border-white/30 dark:border-white/5 cursor-pointer hover:shadow-md transition-all group"
                >
                  <div className="flex justify-between items-start mb-4">
                    <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">{m.label}</p>
                    <span className={`${m.trendColor} ${m.trendBg} dark:bg-white/5 text-[10px] font-bold px-2 py-0.5 rounded-full border border-current/10`}>{m.trend}</span>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <h3 className="text-2xl font-bold dark:text-white leading-none">{m.value} <span className="text-sm font-normal text-slate-400 ml-0.5">{m.unit}</span></h3>
                    </div>
                    <div className="h-10 w-24">
                       <ResponsiveContainer width="100%" height="100%">
                         <LineChart data={m.data.map((v, i) => ({ value: v }))}>
                           <Line 
                             type="monotone" 
                             dataKey="value" 
                             stroke={m.stroke} 
                             strokeWidth={2} 
                             dot={false} 
                             animationDuration={1500}
                           />
                         </LineChart>
                       </ResponsiveContainer>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* Row 2: Charts & AI Intelligence Feed */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Metabolic Trend Card */}
              <motion.div 
                variants={itemVariants}
                className="lg:col-span-2 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md rounded-xl p-6 flex flex-col shadow-sm border border-white/30 dark:border-white/5"
              >
                <div className="flex justify-between items-center mb-8">
                  <div>
                    <h2 className="text-lg font-bold dark:text-white">Metabolic Trend</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Aggregate efficiency score over 30 days</p>
                  </div>
                  <div className="flex gap-2">
                    {['7D', '30D', '90D'].map(period => (
                      <button 
                        key={period}
                        className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                          period === '30D' 
                          ? 'bg-[#6043F4] text-white shadow-md' 
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
                        }`}
                      >
                        {period}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="flex-1 min-h-[300px] w-full mt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metabolicTrendData} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="metaGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#6043F4" stopOpacity={0.3}/>
                          <stop offset="100%" stopColor="#009CDE" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stopColor="#6043F4" />
                          <stop offset="100%" stopColor="#009CDE" />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.03)" />
                      <Tooltip 
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.1)', fontWeight: 'bold' }}
                        itemStyle={{ color: '#6043F4' }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="value" 
                        stroke="url(#lineGradient)" 
                        strokeWidth={4}
                        fillOpacity={1} 
                        fill="url(#metaGradient)" 
                        animationDuration={2500}
                        strokeLinecap="round"
                      />
                      <XAxis 
                        dataKey="name" 
                        axisLine={false} 
                        tickLine={false} 
                        tick={{ fontSize: 10, fontWeight: 'bold', fill: '#94a3b8' }} 
                        dy={15}
                        hide={true}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                  {/* Custom X Axis labels to match Stitch exactly */}
                  <div className="flex justify-between mt-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest px-2">
                    <span>Week 1</span>
                    <span>Week 2</span>
                    <span>Week 3</span>
                    <span>Week 4</span>
                  </div>
                </div>
              </motion.div>

              {/* Side Panel: AI Insights & Alerts */}
              <div className="space-y-6">
                {/* AI Insights Card */}
                <motion.div 
                  variants={itemVariants}
                  className="bg-white/70 dark:bg-slate-900/70 backdrop-blur-md rounded-xl p-6 bg-gradient-to-br from-[#6043F4]/5 to-transparent border border-white/30 dark:border-white/5 shadow-sm"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkles size={18} className="text-[#6043F4]" />
                    <h2 className="font-bold text-sm uppercase tracking-wider dark:text-white">AI Insights</h2>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="bg-white/60 dark:bg-slate-800/60 p-4 rounded-xl border border-white/40 dark:border-white/5">
                      <p className="text-sm leading-relaxed font-medium text-slate-700 dark:text-slate-300">
                        Significant <span className="text-[#6043F4] font-bold">HRV upward shift</span> detected during sleep cycles. This correlates with reduced cortisol marker levels.
                      </p>
                      <p className="text-[11px] text-slate-500 mt-2 font-semibold italic">Reliability: 94.2%</p>
                    </div>
                    <div className="bg-white/60 dark:bg-slate-800/60 p-4 rounded-xl border border-white/40 dark:border-white/5">
                      <p className="text-sm leading-relaxed font-medium text-slate-700 dark:text-slate-300">
                        Glucose variability is <span className="text-[#009CDE] font-bold">stabilizing</span> after recent dietary adjustments. Suggesting continued intermittent fasting protocol.
                      </p>
                    </div>
                    <button className="w-full py-2 bg-[#13082A] dark:bg-slate-100 text-white dark:text-[#13082A] rounded-lg text-xs font-bold hover:opacity-90 transition-all">View Deep Analysis</button>
                  </div>
                </motion.div>

                {/* Recent Alerts Feed */}
                <motion.div variants={itemVariants} className="bg-white/70 dark:bg-slate-900/70 backdrop-blur-md rounded-xl p-6 border border-white/30 dark:border-white/5 shadow-sm">
                  <h2 className="font-bold text-sm uppercase tracking-wider mb-4 flex justify-between items-center dark:text-white">
                    Recent Alerts
                    <span className="text-[10px] bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400 px-2 py-1 rounded-full font-bold">2 Critical</span>
                  </h2>
                  <div className="space-y-3">
                    <div className="flex gap-3 items-start p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border-l-4 border-red-500">
                      <AlertTriangle className="text-red-500 text-sm mt-0.5 shrink-0" size={16} />
                      <div>
                        <p className="text-xs font-bold text-red-900 dark:text-red-100">SpO2 Drop</p>
                        <p className="text-[11px] text-red-700/80 dark:text-red-400/80 leading-snug">Sustained drop below 92% detected during last sync.</p>
                      </div>
                    </div>
                    <div className="flex gap-3 items-start p-3 rounded-lg bg-orange-50 dark:bg-orange-500/10 border-l-4 border-orange-500">
                      <AlertCircle className="text-orange-500 text-sm mt-0.5 shrink-0" size={16} />
                      <div>
                        <p className="text-xs font-bold text-orange-900 dark:text-orange-100">Sync Interrupted</p>
                        <p className="text-[11px] text-orange-700/80 dark:text-orange-400/80 leading-snug">Continuous glucose monitor (CGM) signal lost.</p>
                      </div>
                    </div>
                    <div className="flex gap-3 items-start p-3 rounded-lg bg-blue-50 dark:bg-blue-500/10 border-l-4 border-blue-500">
                      <Info className="text-blue-500 text-sm mt-0.5 shrink-0" size={16} />
                      <div>
                        <p className="text-xs font-bold text-blue-900 dark:text-blue-100">Protocol Update</p>
                        <p className="text-[11px] text-blue-700/80 dark:text-blue-400/80 leading-snug">Daily exercise target reached. HRV recovery recommended.</p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>

            {/* Row 3: Wearable & Specialized Widgets */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-10">
              
              {/* Wearable Summary Dashboard */}
              <motion.div variants={itemVariants} className="bg-white/70 dark:bg-slate-900/70 backdrop-blur-md rounded-xl p-6 border border-white/30 dark:border-white/5 shadow-sm">
                <h2 className="font-bold text-sm uppercase tracking-wider mb-6 dark:text-white">Wearable Summary</h2>
                <div className="space-y-5">
                  <div className="flex items-center justify-between group cursor-pointer hover:translate-x-1 transition-transform">
                    <div className="flex items-center gap-4">
                      <div className="size-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 shadow-inner">
                        <Watch size={20} />
                      </div>
                      <div>
                        <p className="text-sm font-bold dark:text-white">Oura Ring Gen 3</p>
                        <p className="text-[11px] text-green-500 font-bold uppercase tracking-widest">Active • Synced</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Zap size={14} fill="currentColor" />
                      <span className="text-xs font-bold">84%</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between group cursor-pointer hover:translate-x-1 transition-transform">
                    <div className="flex items-center gap-4">
                      <div className="size-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 shadow-inner">
                        <Heart size={20} />
                      </div>
                      <div>
                        <p className="text-sm font-bold dark:text-white">Dexcom G6</p>
                        <p className="text-[11px] text-orange-500 font-bold uppercase tracking-widest">Signal Low</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 text-red-500">
                      <AlertTriangle size={14} />
                      <span className="text-xs font-bold">12%</span>
                    </div>
                  </div>
                  <button className="w-full mt-2 py-3 border-2 border-dashed border-slate-300 dark:border-slate-800 rounded-xl text-slate-400 text-xs font-bold hover:border-[#6043F4] hover:text-[#6043F4] hover:bg-[#6043F4]/5 transition-all flex items-center justify-center gap-2 active:scale-[0.98]">
                    <PlusCircle size={16} />
                    Connect Device
                  </button>
                </div>
              </motion.div>

              {/* Sleep Score Gauge Widget */}
              <motion.div variants={itemVariants} className="bg-white/70 dark:bg-slate-900/70 backdrop-blur-md rounded-xl p-6 border border-white/30 dark:border-white/5 shadow-sm relative flex flex-col items-center">
                <h2 className="font-bold text-sm uppercase tracking-wider mb-6 w-full dark:text-white">Sleep Performance</h2>
                <div className="relative size-40 flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={sleepScoreData}
                        cx="50%"
                        cy="50%"
                        innerRadius={65}
                        outerRadius={80}
                        paddingAngle={0}
                        dataKey="value"
                        startAngle={90}
                        endAngle={-270}
                        stroke="none"
                      >
                        <Cell fill="#6043F4" />
                        <Cell fill="rgba(0,0,0,0.05)" />
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-3xl font-black text-[#13082A] dark:text-white">82</span>
                    <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest mt-1">Score</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-6 w-full">
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg shadow-inner">
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">REM Sleep</p>
                    <p className="text-sm font-bold dark:text-white mt-1">1h 42m</p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg shadow-inner">
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Deep Sleep</p>
                    <p className="text-sm font-bold dark:text-white mt-1">2h 15m</p>
                  </div>
                </div>
              </motion.div>

              {/* Specialized Recent Activity Log */}
              <motion.div variants={itemVariants} className="bg-white/70 dark:bg-slate-900/70 backdrop-blur-md rounded-xl p-6 overflow-hidden relative border border-white/30 dark:border-white/5 shadow-sm">
                <h2 className="font-bold text-sm uppercase tracking-wider mb-6 dark:text-white">Recent Activity</h2>
                <div className="space-y-4">
                  {[
                    { title: 'High Intensity Workout', meta: '640 kcal burned • 45 mins', color: 'bg-[#6043F4]', level: 'h-1/2', bg: 'bg-[#6043F4]/20' },
                    { title: 'Guided Meditation', meta: 'HRV optimization • 15 mins', color: 'bg-[#009CDE]', level: 'h-1/3', bg: 'bg-[#009CDE]/20' },
                    { title: 'Inactivity Period', meta: 'Sedentary alert • 3 hours', color: 'bg-slate-400', level: 'h-3/4', bg: 'bg-slate-200' }
                  ].map((act, i) => (
                    <div key={i} className="flex gap-4 group cursor-pointer">
                      <div className={`w-2 h-10 rounded-full ${act.bg} flex flex-col items-center shrink-0 overflow-hidden`}>
                        <motion.div initial={{ height: 0 }} animate={{ height: act.level.replace('h-', '') }} transition={{ duration: 1.5, delay: 0.5 + (i * 0.2) }} className={`w-full ${act.color} rounded-full`}></motion.div>
                      </div>
                      <div>
                        <p className="text-sm font-bold dark:text-white group-hover:text-[#6043F4] transition-colors">{act.title}</p>
                        <p className="text-[11px] text-slate-500 font-medium mt-0.5">{act.meta}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>
          </div>
        </main>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(96, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(96, 67, 244, 0.2); }
      `}} />
    </div>
  );
};

export default DashboardAlternate;
