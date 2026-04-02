import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Brain, 
  Activity, 
  TrendingUp, 
  Lightbulb, 
  Zap, 
  Rocket, 
  ArrowRight, 
  ShieldCheck, 
  Search, 
  Bell, 
  Menu,
  ChevronRight,
  User,
  LayoutDashboard,
  FolderOpen,
  Video,
  Smartphone,
  Settings,
  ArrowDown,
  ArrowUp
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const AIInsights = () => {
  const navigate = useNavigate();

  const riskFactors = [
    { label: 'Type 2 Diabetes Risk', value: '12%', status: 'Low', statusColor: 'bg-green-100 text-green-600', trend: '- 2.4%', trendIcon: <ArrowDown size={12} />, trendColor: 'text-green-500', progress: 30, color: 'bg-[#009CDE]' },
    { label: 'Hypertension Risk', value: '45%', status: 'Medium', statusColor: 'bg-amber-100 text-amber-600', trend: '+ 5.1%', trendIcon: <ArrowUp size={12} />, trendColor: 'text-amber-500', progress: 65, color: 'bg-[#6043F4]' },
    { label: 'Coronary Artery Disease', value: '08%', status: 'Low', statusColor: 'bg-green-100 text-green-600', trend: 'Stable', trendIcon: null, trendColor: 'text-green-500', progress: 15, color: 'bg-[#009CDE]' },
  ];

  const riskDrivers = [
    { label: 'High LDL Cholesterol', impact: '+12.4%', color: 'bg-[#6043F4]', width: '33%', side: 'right' },
    { label: 'Daily Physical Activity', impact: '-8.2%', color: 'bg-[#009CDE]', width: '25%', side: 'left' },
    { label: 'Systolic Blood Pressure', impact: '+6.8%', color: 'bg-[#6043F4]', width: '18%', side: 'right' },
    { label: 'Genetic Predisposition', impact: '+4.1%', color: 'bg-[#6043F4]', width: '10%', side: 'right' },
    { label: 'Sleep Consistency', impact: '-3.5%', color: 'bg-[#009CDE]', width: '8%', side: 'left' },
  ];

  const sidebarLinks = [
    { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
    { icon: FolderOpen, label: 'Health Records', path:ROUTES.REPORTS },
    { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, active: true },
    { icon: Video, label: 'Telemedicine', path: ROUTES.CONSULTATION },
    { icon: Smartphone, label: 'Simulator', path: ROUTES.SIMULATOR },
  ];

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } }
  };

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-[#13082A] dark:text-slate-100 min-h-screen font-display antialiased leading-normal">
      <div className="flex h-screen overflow-hidden">
        
        {/* Sidebar Navigation - Matched Stitch */}


        {/* Main Content Area */}
        <main className="flex-1 flex flex-col overflow-y-auto bg-mesh custom-scrollbar">
          
          {/* Top Header Navbar - Matched Stitch */}
          <header className="h-16 bg-white dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-8 shrink-0 sticky top-0 z-30 backdrop-blur-md">
            <div className="max-w-md w-full">
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6043F4] transition-colors" size={18} />
                <input 
                  className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-[#6043F4]/20 text-sm font-medium transition-all outline-none" 
                  placeholder="Search analytics or records..." 
                  type="text"
                />
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors">
                <Bell size={20} />
              </button>
              <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-800 mx-2"></div>
              <div className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity" onClick={() => navigate(ROUTES.PROFILE)}>
                <div className="text-right hidden sm:block">
                  <p className="text-xs font-bold text-[#13082A] dark:text-white leading-none">Dr. Sarah Chen</p>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-1">Premium Member</p>
                </div>
                <img 
                  className="size-10 rounded-full border-2 border-[#6043F4]/20 p-0.5 object-cover" 
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuAGSbHTjjvEwoBWvqsZ9a8VimL5ajWP-M9Ffa6V18M48YoDe1PZcfqEs4rm1sTUIHmM0loXRFn1Gnd-wmz26jECwpReUKAb57ZJfTsoUPOUC5xXWR2NezWDFBQImUtEgsOAHYPldVSSIdTvGrrBA5Km_mH900BB9Ox9Ybk8KDNBxr4bYsACf5Zcq5g-joV39Hhmn_SdsdcN3qd41HtpnM4aHpNfGpIc0QfmJpMUqvAAQnlzQXC7-ZBIuIUgbAWwM95FGxBHwCB7JI34" 
                  alt="Dr. Sarah Chen" 
                />
              </div>
            </div>
          </header>

          <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
            {/* Page Header - Matched Stitch */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
              <div>
                <h2 className="text-3xl font-bold text-[#13082A] dark:text-white leading-none tracking-tight">AI Health Insights</h2>
                <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">
                  Last comprehensive analysis performed: <span className="text-[#6043F4] font-semibold">Oct 24, 2023 at 10:45 AM</span>
                </p>
              </div>
              <div className="bg-[#6043F4]/10 dark:bg-[#6043F4]/5 px-4 py-2 rounded-lg flex items-center gap-2 border border-[#6043F4]/20">
                <ShieldCheck size={16} className="text-[#6043F4]" />
                <span className="text-xs font-bold text-[#6043F4]">96.4% confidence based on 42 data points</span>
              </div>
            </div>

            {/* Category Tabs - Matched Stitch */}
            <div className="flex flex-wrap gap-2 p-1 bg-slate-200/50 dark:bg-white/5 w-fit rounded-xl backdrop-blur-sm">
              {['All', 'Cardiovascular', 'Metabolic', 'Neurological', 'Respiratory', 'Environmental'].map((tab, i) => (
                <button 
                  key={tab}
                  onClick={() => tab === 'Environmental' ? navigate(ROUTES.AQI_MONITOR) : null}
                  className={`px-6 py-2 rounded-lg text-sm font-bold transition-all duration-300 ${
                    i === 0 
                    ? 'bg-white dark:bg-[#6043F4] text-[#6043F4] dark:text-white shadow-sm' 
                    : 'text-slate-600 dark:text-slate-400 hover:bg-white/50 dark:hover:bg-white/5'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Risk Score Cards - Matched Stitch */}
            <motion.div 
              variants={containerVariants}
              initial="initial"
              animate="animate"
              className="grid grid-cols-1 md:grid-cols-3 gap-6"
            >
              {riskFactors.map((risk) => (
                <motion.div 
                  key={risk.label} 
                  variants={itemVariants}
                  className="bg-white dark:bg-slate-900/50 p-6 rounded-xl border border-white dark:border-white/5 shadow-sm hover:border-[#6043F4]/20 transition-all cursor-pointer group"
                >
                  <div className="flex justify-between items-start mb-4">
                    <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">{risk.label}</p>
                    <span className={`${risk.statusColor} text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider`}>{risk.status}</span>
                  </div>
                  <div className="flex items-baseline gap-2 mb-4">
                    <span className="text-3xl font-bold text-[#13082A] dark:text-white">{risk.value}</span>
                    <span className={`${risk.trendColor} text-xs font-bold flex items-center gap-0.5`}>
                      {risk.trendIcon}
                      {risk.trend}
                    </span>
                  </div>
                  <div className="h-10 w-full bg-gradient-to-r from-[#009CDE]/10 to-[#6043F4]/10 rounded flex items-center px-1">
                    <div className="h-1 w-full bg-slate-200 dark:bg-slate-800 rounded-full relative overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${risk.progress}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className={`h-full ${risk.color} rounded-full`} 
                      ></motion.div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* Main Visualization Section - Matched Stitch */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* SHAP Factor Chart */}
              <motion.div 
                variants={itemVariants}
                initial="initial"
                animate="animate"
                className="lg:col-span-2 bg-white dark:bg-slate-900/50 p-8 rounded-xl border border-white dark:border-white/5 shadow-sm"
              >
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                  <div>
                    <h3 className="text-lg font-bold text-[#13082A] dark:text-white">Risk Drivers (SHAP Impact)</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Biometric factors influencing your current risk score</p>
                  </div>
                  <div className="flex gap-4 text-[10px] font-bold uppercase tracking-wider">
                    <div className="flex items-center gap-1.5"><span className="size-2 bg-[#009CDE] rounded-full"></span> Decreasing Risk</div>
                    <div className="flex items-center gap-1.5"><span className="size-2 bg-[#6043F4] rounded-full"></span> Increasing Risk</div>
                  </div>
                </div>
                
                <div className="space-y-6">
                  {riskDrivers.map((driver, i) => (
                    <div key={driver.label} className="relative group/bar">
                      <div className="flex justify-between mb-1 text-sm font-bold tracking-tight">
                        <span className="text-slate-700 dark:text-slate-300">{driver.label}</span>
                        <span className={driver.side === 'right' ? 'text-[#6043F4]' : 'text-[#009CDE]'}>{driver.impact}</span>
                      </div>
                      <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full flex justify-center items-center relative overflow-hidden shadow-inner">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: driver.width }}
                          transition={{ duration: 1, delay: i * 0.1 }}
                          className={`absolute ${driver.side === 'right' ? 'left-1/2 rounded-r-full' : 'right-1/2 rounded-l-full'} h-full ${driver.color} shadow-sm`} 
                        ></motion.div>
                        <div className="absolute left-1/2 top-0 h-full w-[1px] bg-slate-300 dark:bg-slate-700 z-10"></div>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* AI Explanation & Recommendations */}
              <div className="space-y-6">
                {/* Deep Analysis Card - Matched Stitch */}
                <motion.div 
                  variants={itemVariants}
                  initial="initial"
                  animate="animate"
                  className="bg-[#6043F4] p-8 rounded-xl text-white shadow-xl shadow-[#6043F4]/20 relative overflow-hidden group"
                >
                  <div className="relative z-10">
                    <Lightbulb size={40} className="mb-4 text-white hover:rotate-12 transition-transform duration-500" />
                    <h3 className="text-lg font-bold mb-3 tracking-tight">Deep Analysis</h3>
                    <p className="text-sm leading-relaxed text-white/80 font-medium">
                      Our AI detected that your <span className="font-bold text-white">LDL Cholesterol levels</span> are the primary driver of the increased Hypertension risk. While your <span className="font-bold text-white">active lifestyle</span> acts as a significant buffer, reducing risk by 8.2%, focus on dietary adjustments could lower overall risk by an additional 15% in 3 months.
                    </p>
                  </div>
                  <div className="absolute -bottom-10 -right-10 size-40 bg-white/10 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-1000"></div>
                </motion.div>

                {/* Recommendations List - Matched Stitch */}
                <motion.div 
                  variants={itemVariants}
                  className="bg-white dark:bg-slate-900/50 p-6 rounded-xl border border-slate-100 dark:border-white/5 shadow-sm"
                >
                  <h4 className="font-bold mb-4 flex items-center gap-2 dark:text-white">
                    <Rocket size={18} className="text-[#6043F4]" />
                    Top Recommendations
                  </h4>
                  <div className="space-y-4">
                    {[
                      'Increase daily potassium intake to balance sodium levels.',
                      'Consider a 24-hour BP monitor for more granular cardiovascular data.'
                    ].map((rec, i) => (
                      <div key={i} className="flex gap-3 group">
                        <div className="size-2 bg-[#009CDE] rounded-full mt-1.5 shrink-0 group-hover:scale-125 transition-transform"></div>
                        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-semibold group-hover:text-[#6043F4] transition-colors">{rec}</p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </div>

            {/* Simulator CTA Card - Matched Stitch */}
            <motion.div 
              variants={itemVariants}
              className="bg-[#009CDE]/10 dark:bg-[#009CDE]/5 border border-[#009CDE]/20 dark:border-[#009CDE]/10 p-8 rounded-xl flex flex-col md:flex-row items-center justify-between gap-6 relative overflow-hidden group"
            >
              <div className="flex items-center gap-6 text-center md:text-left z-10">
                <div className="size-16 bg-[#009CDE]/20 rounded-2xl flex items-center justify-center text-[#009CDE] shadow-inner group-hover:rotate-6 transition-transform duration-500">
                  <Activity size={36} strokeWidth={2.5} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#13082A] dark:text-white tracking-tight">What if you changed your habits?</h3>
                  <p className="text-slate-600 dark:text-slate-400 font-semibold text-sm">Use our AI Simulator to see how specific lifestyle changes impact your future health scores.</p>
                </div>
              </div>
              <button 
                onClick={() => navigate(ROUTES.SIMULATOR)}
                className="bg-[#009CDE] text-white px-8 py-3 rounded-xl font-bold hover:shadow-xl hover:shadow-[#009CDE]/30 active:scale-95 transition-all flex items-center gap-2 whitespace-nowrap z-10 shadow-lg"
              >
                Simulate Lifestyle Changes
                <ArrowRight size={18} />
              </button>
              <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                <Brain size={120} />
              </div>
            </motion.div>
          </div>
        </main>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(96, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(96, 67, 244, 0.2); }
        .bg-mesh {
          background-image: 
            radial-gradient(at 0% 0%, rgba(96, 67, 244, 0.02) 0px, transparent 55%),
            radial-gradient(at 100% 100%, rgba(0, 156, 222, 0.02) 0px, transparent 55%);
        }
      `}} />
    </div>
  );
};

export default AIInsights;
