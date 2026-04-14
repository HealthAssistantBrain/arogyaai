import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Activity,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Bell,
  Brain,
  FolderOpen,
  Lightbulb,
  LayoutDashboard,
  Rocket,
  Search,
  ShieldCheck,
  Smartphone,
  User,
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { useAuthStore } from '../store/authStore';
import { useInsightsData } from '../hooks/useInsightsData';
import { openCommandPalette } from '../components/CommandPalette';

const containerVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
};

const riskStyles = {
  diabetes: {
    ring: 'border-[#009CDE]/20',
    fill: 'bg-[#009CDE]',
    badge: 'bg-[#009CDE]/10 text-[#009CDE]',
  },
  hypertension: {
    ring: 'border-[#6043F4]/20',
    fill: 'bg-[#6043F4]',
    badge: 'bg-[#6043F4]/10 text-[#6043F4]',
  },
  cad: {
    ring: 'border-[#13082A]/15',
    fill: 'bg-[#13082A]',
    badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  },
};

const levelStyles = {
  LOW: 'bg-green-100 text-green-600 dark:bg-green-500/10 dark:text-green-400',
  MODERATE: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
  HIGH: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300',
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-300',
};

const fmtDateTime = (value) => {
  if (!value) return 'No data available';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No data available';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
};

const initialsFromName = (value) =>
  String(value || 'ArogyaAI')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('') || 'AI';

const mapRiskToCategory = (riskKey) => {
  switch (riskKey) {
    case 'diabetes':
      return 'metabolic';
    case 'hypertension':
    case 'cad':
      return 'cardiovascular';
    default:
      return 'all';
  }
};

const AIInsights = () => {
  const navigate = useNavigate();
  const profileLoading = useAuthStore((state) => state.profileLoading);
  const user = useAuthStore((state) => state.user);
  const profile = useAuthStore((state) => state.profile);
  const { loading, error, data, status, cards, drivers, analysis, recommendations, lastUpdated, confidence, dataPoints } = useInsightsData();
  const [selectedCategory, setSelectedCategory] = useState('all');

  const displayName = profile?.full_name || user?.full_name || 'Your profile';
  const avatarUrl = profile?.avatar_url || user?.avatar_url || null;
  const avatarInitials = useMemo(() => initialsFromName(displayName), [displayName]);
  const filteredCards = useMemo(() => {
    if (selectedCategory === 'all') {
      return cards;
    }

    return cards.filter((card) => mapRiskToCategory(card.key) === selectedCategory);
  }, [cards, selectedCategory]);
  const isInsufficientData = status === 'insufficient_data';

  useEffect(() => {
    console.log('FILTER:', selectedCategory);
    console.log('API DATA:', data);
  }, [data, selectedCategory]);

  const topCards = filteredCards.slice(0, 3);
  const hasRiskCards = !isInsufficientData && topCards.length > 0;
  const hasDrivers = !isInsufficientData && drivers.length > 0;
  const hasRecommendations = !isInsufficientData && recommendations.length > 0;
  const hasAnalysis = !isInsufficientData && Boolean(analysis?.trim());

  if (profileLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#EAEAEA] dark:bg-[#13082A] text-sm font-bold text-slate-500">
        Loading live insights...
      </div>
    );
  }

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-[#13082A] dark:text-slate-100 min-h-screen font-display antialiased leading-normal">
      <div className="flex h-screen overflow-hidden">
        <main className="flex-1 flex flex-col overflow-y-auto bg-mesh custom-scrollbar">
          <header className="h-16 bg-white dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-8 shrink-0 sticky top-0 z-30 backdrop-blur-md">
            <div className="max-w-md w-full">
              <div className="relative group">
                <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6043F4] transition-colors" size={18} />
                <input
                  className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-[#6043F4]/20 text-sm font-medium transition-all outline-none"
                  placeholder="Search analytics or records..."
                  type="text"
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors"
                type="button"
                onClick={() => navigate(ROUTES.NOTIFICATIONS)}
              >
                <Bell size={20} />
              </button>
              <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-800 mx-2" />
              <div className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity" onClick={() => navigate(ROUTES.PROFILE)}>
                <div className="text-right hidden sm:block">
                  <p className="text-xs font-bold text-[#13082A] dark:text-white leading-none">{displayName}</p>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-1">Live profile</p>
                </div>
                {avatarUrl ? (
                  <img className="size-10 rounded-full border-2 border-[#6043F4]/20 p-0.5 object-cover" src={avatarUrl} alt={displayName} />
                ) : (
                  <div className="size-10 rounded-full border-2 border-[#6043F4]/20 p-0.5 flex items-center justify-center bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-white font-bold">
                    {avatarInitials}
                  </div>
                )}
              </div>
            </div>
          </header>

          <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
              <div>
                <h2 className="text-3xl font-bold text-[#13082A] dark:text-white leading-none tracking-tight">AI Health Insights</h2>
                <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">
                  {isInsufficientData ? 'Not enough data to generate insights yet.' : (
                    <>
                      Last comprehensive analysis performed: <span className="text-[#6043F4] font-semibold">{fmtDateTime(lastUpdated)}</span>
                    </>
                  )}
                </p>
              </div>
              {!isInsufficientData ? (
                <div className="bg-[#6043F4]/10 dark:bg-[#6043F4]/5 px-4 py-2 rounded-lg flex items-center gap-2 border border-[#6043F4]/20">
                  <ShieldCheck size={16} className="text-[#6043F4]" />
                  <span className="text-xs font-bold text-[#6043F4]">
                    {confidence.toFixed(1)}% confidence based on {dataPoints} data points
                  </span>
                </div>
              ) : null}
            </div>

            {isInsufficientData ? (
              <motion.div
                variants={itemVariants}
                initial="initial"
                animate="animate"
                className="rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/80 dark:bg-slate-900/40 p-10 text-center shadow-sm"
              >
                <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-2xl bg-[#6043F4]/10 text-[#6043F4]">
                  <ShieldCheck size={28} />
                </div>
                <h3 className="text-xl font-bold text-[#13082A] dark:text-white">Not enough data to generate insights yet</h3>
                <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-500 dark:text-slate-400">
                  The insights engine will stay empty until the required inputs and a validated model are available.
                </p>
              </motion.div>
            ) : (
              <div className="flex flex-wrap gap-2 p-1 bg-slate-200/50 dark:bg-white/5 w-fit rounded-xl backdrop-blur-sm">
                {[
                  { label: 'All', value: 'all' },
                  { label: 'Cardiovascular', value: 'cardiovascular' },
                  { label: 'Metabolic', value: 'metabolic' },
                  { label: 'Neurological', value: 'neurological' },
                  { label: 'Respiratory', value: 'respiratory' },
                  { label: 'Environmental', value: 'environmental' },
                ].map((tab) => (
                  <button
                    key={tab.label}
                    onClick={() => setSelectedCategory(tab.value)}
                    className={`px-6 py-2 rounded-lg text-sm font-bold transition-all duration-300 ${
                      selectedCategory === tab.value
                        ? 'bg-white dark:bg-[#6043F4] text-[#6043F4] dark:text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:bg-white/50 dark:hover:bg-white/5'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            )}

            {!isInsufficientData ? (
              <>
            {error ? (
              <div className="rounded-2xl border border-amber-300/40 bg-amber-50 dark:bg-amber-500/10 px-5 py-4 text-sm text-amber-900 dark:text-amber-100">
                {error}
              </div>
            ) : null}

            {hasRiskCards ? (
              <motion.div variants={containerVariants} initial="initial" animate="animate" className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {topCards.map((risk) => {
                  const theme = riskStyles[risk.key] || riskStyles.cad;
                  const levelClass = levelStyles[risk.riskLevel] || levelStyles.LOW;
                  const trendIcon = risk.deltaFromNeutral >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />;

                  return (
                    <motion.div
                      key={risk.key}
                      variants={itemVariants}
                      className={`bg-white dark:bg-slate-900/50 p-6 rounded-xl border shadow-sm hover:border-[#6043F4]/20 transition-all cursor-pointer group ${theme.ring}`}
                    >
                      <div className="flex justify-between items-start mb-4">
                        <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">{risk.title}</p>
                        <span className={`${levelClass} text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider`}>
                          {risk.status}
                        </span>
                      </div>
                      <div className="flex items-baseline gap-2 mb-4">
                        <span className="text-3xl font-bold text-[#13082A] dark:text-white">{risk.value.toFixed(1)}%</span>
                        <span className={`text-xs font-bold flex items-center gap-0.5 ${risk.deltaFromNeutral >= 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                          {trendIcon}
                          {risk.trend}
                        </span>
                      </div>
                      <div className="h-10 w-full bg-gradient-to-r from-[#009CDE]/10 to-[#6043F4]/10 rounded flex items-center px-1">
                        <div className="h-1 w-full bg-slate-200 dark:bg-slate-800 rounded-full relative overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${risk.progress}%` }}
                            transition={{ duration: 1, ease: 'easeOut' }}
                            className={`h-full ${theme.fill} rounded-full`}
                          />
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            ) : (
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 p-6 text-sm font-medium text-slate-500 dark:text-slate-400 shadow-sm">
                No data available
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                    <div className="flex items-center gap-1.5">
                      <span className="size-2 bg-[#009CDE] rounded-full" /> Decreasing Risk
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="size-2 bg-[#6043F4] rounded-full" /> Increasing Risk
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  {hasDrivers ? (
                    drivers.map((driver, index) => (
                      <div key={driver.key || driver.label} className="relative group/bar">
                        <div className="flex justify-between mb-1 text-sm font-bold tracking-tight">
                          <span className="text-slate-700 dark:text-slate-300">{driver.label}</span>
                          <span className={driver.direction === 'increasing' ? 'text-[#6043F4]' : 'text-[#009CDE]'}>{driver.impact}</span>
                        </div>
                        <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full flex justify-center items-center relative overflow-hidden shadow-inner">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: driver.barWidth }}
                            transition={{ duration: 1, delay: index * 0.08 }}
                            className={`absolute ${driver.direction === 'increasing' ? 'left-1/2 rounded-r-full' : 'right-1/2 rounded-l-full'} h-full ${
                              driver.direction === 'increasing' ? 'bg-[#6043F4]' : 'bg-[#009CDE]'
                            } shadow-sm`}
                          />
                          <div className="absolute left-1/2 top-0 h-full w-[1px] bg-slate-300 dark:bg-slate-700 z-10" />
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No data available</p>
                  )}
                </div>
              </motion.div>

              <div className="space-y-6">
                <motion.div
                  variants={itemVariants}
                  initial="initial"
                  animate="animate"
                  className="bg-[#6043F4] p-8 rounded-xl text-white shadow-xl shadow-[#6043F4]/20 relative overflow-hidden group"
                >
                  <div className="relative z-10">
                    <Lightbulb size={40} className="mb-4 text-white hover:rotate-12 transition-transform duration-500" />
                    <h3 className="text-lg font-bold mb-3 tracking-tight">Deep Analysis</h3>
                    {hasAnalysis ? (
                      <p className="text-sm leading-relaxed text-white/80 font-medium">{analysis}</p>
                    ) : (
                      <p className="text-sm leading-relaxed text-white/80 font-medium">No insights available</p>
                    )}
                  </div>
                  <div className="absolute -bottom-10 -right-10 size-40 bg-white/10 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-1000" />
                </motion.div>

                <motion.div
                  variants={itemVariants}
                  className="bg-white dark:bg-slate-900/50 p-6 rounded-xl border border-slate-100 dark:border-white/5 shadow-sm"
                >
                  <h4 className="font-bold mb-4 flex items-center gap-2 dark:text-white">
                    <Rocket size={18} className="text-[#6043F4]" />
                    Top Recommendations
                  </h4>
                  <div className="space-y-4">
                    {hasRecommendations ? (
                      recommendations.map((item) => (
                        <div key={`${item.title}-${item.category}`} className="flex gap-3 group">
                          <div className="size-2 bg-[#009CDE] rounded-full mt-1.5 shrink-0 group-hover:scale-125 transition-transform" />
                          <div>
                            <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-relaxed">{item.title}</p>
                            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-medium">{item.detail}</p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-slate-500 dark:text-slate-400">No insights available</p>
                    )}
                  </div>
                </motion.div>
              </div>
            </div>

              </>
            ) : null}

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
                  <p className="text-slate-600 dark:text-slate-400 font-semibold text-sm">Use the AI Simulator to see how lifestyle changes would shift future health scores.</p>
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
