import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import {
  Search,
  Bell,
  Upload,
  ChevronRight,
  ExternalLink,
  Beaker,
  Loader2,
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { apiClient } from '../lib/apiClient';
import { openCommandPalette } from '../components/CommandPalette';

const FILTERS = [
  { label: 'All', value: 'all' },
  { label: 'Hematology', value: 'hematology' },
  { label: 'Biochemistry', value: 'biochemistry' },
  { label: 'Metabolic', value: 'metabolic' },
  { label: 'Lipid', value: 'lipid' },
  { label: 'Thyroid', value: 'thyroid' },
];

const toText = (value) => (value === null || value === undefined ? '' : String(value).trim());

const toNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const normalizeTrend = (trend) => {
  if (!Array.isArray(trend)) return [];
  return trend.map(toNumber).filter((value) => Number.isFinite(value));
};

const normalizeLabResult = (item, index) => ({
  id: toText(item?.id) || `${toText(item?.name) || 'lab-result'}-${index}`,
  name: toText(item?.name || item?.parameter || 'Lab Test'),
  value: toNumber(item?.value),
  unit: toText(item?.unit),
  reference_range: toText(item?.reference_range || item?.range),
  status: toText(item?.status || 'normal').toLowerCase(),
  category: toText(item?.category || 'other').toLowerCase(),
  trend: normalizeTrend(item?.trend),
});

const normalizeLabResults = (payload) => {
  const items = Array.isArray(payload) ? payload : Array.isArray(payload?.data) ? payload.data : [];
  return items.map(normalizeLabResult).filter((item) => item.name);
};

const formatValue = (value) => {
  if (!Number.isFinite(value)) return '--';
  const fixed = value.toFixed(1);
  return fixed.endsWith('.0') ? fixed.slice(0, -2) : fixed;
};

const getStatusStyles = (status = '') => {
  const normalized = String(status).toLowerCase();

  if (normalized === 'normal') {
    return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200/50';
  }

  if (normalized === 'borderline') {
    return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200/50';
  }

  if (normalized === 'low' || normalized === 'high') {
    return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-200/50';
  }

  return 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-400 border-slate-200/50';
};

const getStatusDot = (status = '') => {
  const normalized = String(status).toLowerCase();

  if (normalized === 'normal') return 'bg-emerald-500';
  if (normalized === 'borderline') return 'bg-amber-500';
  if (normalized === 'low' || normalized === 'high') return 'bg-red-500';
  return 'bg-slate-400';
};

const getTrendBarClass = (status = '') => {
  const normalized = String(status).toLowerCase();

  if (normalized === 'normal') return 'bg-[#6143f4]';
  if (normalized === 'borderline') return 'bg-amber-500';
  if (normalized === 'low' || normalized === 'high') return 'bg-red-500';
  return 'bg-slate-400';
};

const getTrendBarHeight = (value, series = []) => {
  const numbers = series.filter((item) => Number.isFinite(item));
  if (!numbers.length || !Number.isFinite(value)) {
    return 48;
  }

  const min = Math.min(...numbers);
  const max = Math.max(...numbers);
  if (min === max) {
    return 56;
  }

  return 24 + ((value - min) / (max - min)) * 68;
};

const Loader = () => (
  <div className="bg-[#f6f5f8] dark:bg-[#131022] min-h-screen flex items-center justify-center">
    <div className="flex flex-col items-center gap-4">
      <Loader2 size={36} className="animate-spin text-[#6143f4]" />
      <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Loading lab results</p>
    </div>
  </div>
);

const LabResults = () => {
  const navigate = useNavigate();
  const [labResults, setLabResults] = useState([]);
  const [activeFilter, setActiveFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  // Live user data from auth store — updates immediately after login
  const storeUser = useAuthStore((state) => state.user);
  const storeProfile = useAuthStore((state) => state.profile);
  const displayName = storeUser?.full_name || storeProfile?.full_name || storeUser?.email || 'My Account';
  const patientId = storeProfile?.patient_id
    ? `AR-${String(storeProfile.patient_id).slice(-6).toUpperCase()}`
    : storeUser?.id
      ? `AR-${String(storeUser.id).slice(-6).toUpperCase()}`
      : 'AR-XXXXXX';

  useEffect(() => {
    let isMounted = true;

    const fetchLabResults = async () => {
      try {
        const response = await apiClient.get('/lab-results');
        const data = normalizeLabResults(response.data);

        if (isMounted) {
          setLabResults(data);
        }
      } catch (err) {
        console.error('Failed to fetch lab results', err);
        if (isMounted) {
          setLabResults([]);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void fetchLabResults();

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredResults = activeFilter === 'all'
    ? labResults
    : labResults.filter((item) => item.category?.toLowerCase() === activeFilter);

  const activeResult = filteredResults[0] ?? labResults[0] ?? null;

  if (loading) return <Loader />;

  return (
    <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-20 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 z-10">
            <div className="flex-1 max-w-xl">
              <div className="relative group">
                <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                <input className="w-full pl-12 pr-6 py-3 bg-slate-100 dark:bg-white/5 border-none rounded-2xl text-sm font-medium focus:ring-2 focus:ring-[#6143f4]/20 transition-all placeholder:text-slate-400 outline-none" placeholder="Search lab parameters, dates or providers..." type="text" />
              </div>
            </div>
            <div className="flex items-center gap-8">
              <button className="size-11 flex items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/5 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-90 group" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                <Bell size={20} />
                <span className="absolute top-3 right-3 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#131022] group-hover:scale-110 transition-transform"></span>
              </button>
              <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 hidden md:block"></div>
              <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors">{displayName}</p>
                  <p className="text-[9px] text-slate-500 mt-1.5 uppercase tracking-[0.2em] font-black opacity-70">Patient ID: {patientId}</p>
                </div>
                <div className="size-11 rounded-2xl bg-[#6143f4]/10 border-2 border-transparent group-hover:border-[#6143f4] overflow-hidden transition-all shadow-md group-hover:scale-110">
                  <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBSNEjoorIjStYduz4toUoH9taRezR9gUmeBlfZqgLvFpq-7Dpa-im_yfn3lhwmaedZOiCg-PEuJeDdpULcssnht9u6CnykpHhZffrOhUXsuZ9iTanq55ms_jcerh6Lq3TN4Or7exJuJ0BaCCElRYRK3NBThOT8RXKoJqVsW5ZC_1R8GCbXb1IaZTElgrP9NB2hNpAClQTc6gsxVwCZJx56bTPuLyvxxphaTbQKe2pAiZg6dxh0LvCzzUm-NNDqI7e0fgO5Z4StDAON" alt="User Profile" />
                </div>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-[#f6f5f8] dark:bg-[#131022]">
            <div className="max-w-7xl mx-auto space-y-12 pb-12">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <Beaker size={16} className="text-[#6143f4]" />
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.3em]">Diagnostic Insights</p>
                  </div>
                  <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase leading-none">Lab Test Results</h2>
                  <p className="text-slate-400 mt-4 font-bold uppercase tracking-widest text-[11px] opacity-80">View and analyze your latest clinical diagnostic data landscape</p>
                </div>
                <button onClick={() => navigate(ROUTES.UPLOAD)} className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.25rem] font-black text-[11px] uppercase tracking-[0.25em] flex items-center gap-4 shadow-2xl shadow-[#6143f4]/30 transition-all active:scale-95 whitespace-nowrap leading-none">
                  <Upload size={18} strokeWidth={3} />
                  Upload New Report
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2.5 p-2 bg-white dark:bg-white/5 rounded-[1.5rem] w-fit border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/40 dark:shadow-none">
                {FILTERS.map((filter) => (
                  <button
                    key={filter.value}
                    onClick={() => setActiveFilter(filter.value)}
                    className={`px-7 py-3 rounded-[1rem] text-[10px] font-black uppercase tracking-widest transition-all ${activeFilter === filter.value
                      ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20 scale-105'
                      : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5'
                      }`}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>

              <section className="bg-white dark:bg-[#1a1433] rounded-[3rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-2xl shadow-slate-200/50 dark:shadow-none">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50/50 dark:bg-white/5 border-b border-slate-200 dark:border-slate-800">
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Parameter / Category</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Last Result</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 text-center">Referential Range</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Status State</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Trend (6 Month)</th>
                        <th className="px-10 py-7 w-20"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                      {filteredResults.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-10 py-16 text-center">
                            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">
                              {labResults.length === 0
                                ? 'No lab data yet — upload a report to get started'
                                : 'No results in this category'}
                            </p>
                          </td>
                        </tr>
                      ) : (
                        filteredResults.map((item, index) => {
                          const trendSeries = item.trend.length ? item.trend : [item.value].filter((value) => Number.isFinite(value));
                          const barClass = getTrendBarClass(item.status);

                          return (
                            <tr key={item.id || index} className="hover:bg-slate-50/70 dark:hover:bg-white/5 transition-all group/row cursor-pointer relative">
                              <td className="px-10 py-7">
                                <div className="flex flex-col">
                                  <span className="font-black text-[#13082a] dark:text-white uppercase tracking-tight text-lg leading-none">{item.name}</span>
                                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-2 flex items-center gap-1 opacity-70 group-hover/row:text-[#6143f4] transition-colors leading-none">
                                    <span className="size-1 bg-[#6143f4] rounded-full mr-1"></span>
                                    {item.category}
                                  </span>
                                </div>
                              </td>
                              <td className="px-10 py-7">
                                <span className="text-2xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none">
                                  {formatValue(item.value)} <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest ml-1">{item.unit}</span>
                                </span>
                              </td>
                              <td className="px-10 py-7 text-center">
                                <span className="text-[10px] font-black text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-white/5 px-5 py-2 rounded-full uppercase tracking-widest border border-slate-200 dark:border-slate-800 leading-none">
                                  {item.reference_range}
                                </span>
                              </td>
                              <td className="px-10 py-7">
                                <span className={`inline-flex items-center gap-2.5 px-5 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.1em] shadow-sm border border-transparent ${getStatusStyles(item.status)} leading-none`}>
                                  <span className={`size-2 rounded-full ${getStatusDot(item.status)} animate-pulse`}></span>
                                  {item.status}
                                </span>
                              </td>
                              <td className="px-10 py-7">
                                <div className="flex items-end gap-1.5 h-10 w-32">
                                  {trendSeries.map((val, i) => (
                                    <div
                                      key={`${item.id}-trend-${i}`}
                                      className={`w-1.5 rounded-full transition-all duration-700 ease-out group-hover/row:scale-y-125 ${barClass}`}
                                      style={{
                                        height: `${getTrendBarHeight(val, trendSeries)}%`,
                                        opacity: (i + 1) * 0.15 + 0.1,
                                        transitionDelay: `${i * 50}ms`,
                                      }}
                                    ></div>
                                  ))}
                                </div>
                              </td>
                              <td className="px-10 py-7 text-right">
                                <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-300 dark:text-slate-600 group-hover/row:bg-[#6143f4]/10 group-hover/row:text-[#6143f4] group-hover/row:scale-110 transition-all opacity-0 md:opacity-100 transform translate-x-4 group-hover/row:translate-x-0">
                                  <ChevronRight size={20} strokeWidth={3} />
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                <div className="lg:col-span-12 bg-white dark:bg-[#1a1433] border border-slate-100 dark:border-white/5 rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none relative group overflow-hidden flex flex-col justify-between">
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-10">
                      <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-widest text-xs leading-none">Historical Trajectory</h3>
                      <button className="text-[#6143f4] text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:underline transition-all group/btn" type="button" onClick={() => navigate(ROUTES.MEDICAL_REPORTS)}>
                        Full Analytics
                        <ExternalLink size={12} className="group-hover/btn:translate-x-0.5 transition-transform" />
                      </button>
                    </div>

                    <div className="space-y-10">
                      <div>
                        <div className="flex justify-between items-center mb-6">
                          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Selected Parameter</span>
                          <span className="text-[10px] font-black bg-[#6143f4]/10 text-[#6143f4] px-4 py-2 rounded-full uppercase tracking-widest border border-[#6143f4]/10 leading-none">
                            {activeResult?.name || 'Lab Result'}
                          </span>
                        </div>
                        <div className="h-44 w-full bg-slate-50 dark:bg-black/20 rounded-[2rem] flex items-end justify-between px-8 pb-6 border border-slate-100 dark:border-white/5 shadow-inner group/chart overflow-hidden">
                          {(activeResult?.trend.length ? activeResult.trend : [activeResult?.value].filter((value) => Number.isFinite(value))).map((h, i, series) => (
                            <div
                              key={`${activeResult?.id || 'active'}-hist-${i}`}
                              className={`w-2.5 rounded-t-full transition-all duration-1000 ${i === series.length - 1 ? 'bg-[#6143f4] shadow-xl shadow-[#6143f4]/30' : 'bg-[#6143f4]/20 group-hover/chart:bg-[#6143f4]/40'
                                }`}
                              style={{
                                height: `${getTrendBarHeight(h, series)}%`,
                                transitionDelay: `${i * 75}ms`,
                              }}
                            ></div>
                          ))}
                        </div>
                        <div className="flex justify-between mt-5 px-3 text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] opacity-80 leading-none">
                          <span>Oldest</span>
                          <span>Recent</span>
                        </div>
                      </div>
                      <div className="pt-8 border-t border-slate-100 dark:border-white/5">
                        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed italic font-bold opacity-80 max-w-[420px]">
                          {activeResult
                            ? `Latest ${activeResult.name} reading is ${formatValue(activeResult.value)} ${activeResult.unit}. Current status is ${activeResult.status} against ${activeResult.reference_range}.`
                            : 'No historical lab trend is available for the selected filter.'}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="absolute top-0 right-0 size-40 bg-[#6143f4] opacity-[0.03] blur-3xl -mr-20 -mt-20 group-hover:opacity-[0.06] transition-opacity"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
        .leading-none { line-height: 1 !important; }
      `}} />
    </div>
  );
};

export default LabResults;
