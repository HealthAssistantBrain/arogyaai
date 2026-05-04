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
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { apiClient } from '../lib/apiClient';
import { safeArray } from '../utils/safeData';
import HeartLoader from '../components/ui/HeartLoader';

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
  return safeArray(trend).map(toNumber).filter((value) => Number.isFinite(value));
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

  return 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-text-muted border-slate-200/50';
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

  if (normalized === 'normal') return 'bg-primary';
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
  <div className="bg-background dark:bg-card min-h-screen flex items-center justify-center">
    <div className="flex flex-col items-center gap-4">
      <HeartLoader size={64} />
      <p className="text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">Loading lab results</p>
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
    ? safeArray(labResults)
    : safeArray(labResults).filter((item) => item.category?.toLowerCase() === activeFilter);

  const activeResult = filteredResults[0] ?? labResults[0] ?? null;

  if (loading) return <Loader />;

  return (
    <div className="bg-background dark:bg-card text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">


          <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-background dark:bg-card">
            <div className="max-w-7xl mx-auto space-y-12 pb-12">
              <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <Beaker size={16} className="text-primary" />
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.3em]">Diagnostic Insights</p>
                  </div>
                  <h2 className="text-5xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase leading-none">Lab Test Results</h2>
                  <p className="text-text-muted mt-4 font-bold uppercase tracking-widest text-[11px] opacity-80">View and analyze your latest clinical diagnostic data landscape</p>
                </div>
                <button onClick={() => navigate(ROUTES.UPLOAD)} className="bg-primary hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.25rem] font-black text-[11px] uppercase tracking-[0.25em] flex items-center gap-4 shadow-2xl shadow-primary/30 transition-all active:scale-95 whitespace-nowrap leading-none">
                  <Upload size={18} strokeWidth={3} />
                  Upload New Report
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2.5 p-2 bg-surface rounded-[1.5rem] w-fit border border-slate-100 dark:border-stroke/50 shadow-xl shadow-slate-200/40 dark:shadow-none">
                {FILTERS.map((filter) => (
                  <button
                    key={filter.value}
                    onClick={() => setActiveFilter(filter.value)}
                    className={`px-7 py-3 rounded-[1rem] text-[10px] font-black uppercase tracking-widest transition-all ${activeFilter === filter.value
                      ? 'bg-primary text-white shadow-xl shadow-primary/20 scale-105'
                      : 'text-slate-500 dark:text-text-muted hover:bg-slate-50 dark:hover:bg-white/5'
                      }`}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>

              <section className="bg-white dark:bg-[#1a1433] rounded-[3rem] border border-slate-100 dark:border-stroke/50 overflow-hidden shadow-2xl shadow-slate-200/50 dark:shadow-none">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50/50 dark:bg-white/5 border-b border-slate-200 dark:border-stroke">
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">Parameter / Category</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">Last Result</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-text-muted text-center">Referential Range</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">Status State</th>
                        <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">Trend (6 Month)</th>
                        <th className="px-10 py-7 w-20"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                      {filteredResults.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-10 py-16 text-center">
                            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">
                              {labResults.length === 0
                                ? 'No lab data yet — upload a report to get started'
                                : 'No results in this category'}
                            </p>
                          </td>
                        </tr>
                      ) : (
                        filteredResults.map((item, index) => {
                          const trendSeries = safeArray(item.trend).length
                            ? safeArray(item.trend)
                            : [item.value].filter((value) => Number.isFinite(value));
                          const barClass = getTrendBarClass(item.status);

                          return (
                            <tr key={item.id || index} className="hover:bg-slate-50/70 dark:hover:bg-white/5 transition-all group/row cursor-pointer relative">
                              <td className="px-10 py-7">
                                <div className="flex flex-col">
                                  <span className="font-black text-text-primary dark:text-text-primary uppercase tracking-tight text-lg leading-none">{item.name}</span>
                                  <span className="text-[10px] text-text-muted font-bold uppercase tracking-widest mt-2 flex items-center gap-1 opacity-70 group-hover/row:text-primary transition-colors leading-none">
                                    <span className="size-1 bg-primary rounded-full mr-1"></span>
                                    {item.category}
                                  </span>
                                </div>
                              </td>
                              <td className="px-10 py-7">
                                <span className="text-2xl font-black tracking-tighter text-text-primary dark:text-text-primary leading-none">
                                  {formatValue(item.value)} <span className="text-[11px] font-bold text-text-muted uppercase tracking-widest ml-1">{item.unit}</span>
                                </span>
                              </td>
                              <td className="px-10 py-7 text-center">
                                <span className="text-[10px] font-black text-slate-600 dark:text-text-muted bg-slate-100 dark:bg-white/5 px-5 py-2 rounded-full uppercase tracking-widest border border-slate-200 dark:border-stroke leading-none">
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
                                <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-text-secondary dark:text-slate-600 group-hover/row:bg-primary/10 group-hover/row:text-primary group-hover/row:scale-110 transition-all opacity-0 md:opacity-100 transform translate-x-4 group-hover/row:translate-x-0">
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
                <div className="lg:col-span-12 bg-white dark:bg-[#1a1433] border border-slate-100 dark:border-stroke/50 rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none relative group overflow-hidden flex flex-col justify-between">
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-10">
                      <h3 className="font-black text-text-primary dark:text-text-primary uppercase tracking-widest text-xs leading-none">Historical Trajectory</h3>
                      <button className="text-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:underline transition-all group/btn" type="button" onClick={() => navigate(ROUTES.MEDICAL_REPORTS)}>
                        Full Analytics
                        <ExternalLink size={12} className="group-hover/btn:translate-x-0.5 transition-transform" />
                      </button>
                    </div>

                    <div className="space-y-10">
                      <div>
                        <div className="flex justify-between items-center mb-6">
                          <span className="text-[10px] font-black text-text-muted uppercase tracking-widest leading-none">Selected Parameter</span>
                          <span className="text-[10px] font-black bg-primary/10 text-primary px-4 py-2 rounded-full uppercase tracking-widest border border-primary/10 leading-none">
                            {activeResult?.name || 'Lab Result'}
                          </span>
                        </div>
                        <div className="h-44 w-full bg-slate-50 dark:bg-black/20 rounded-[2rem] flex items-end justify-between px-8 pb-6 border border-slate-100 dark:border-stroke/50 shadow-inner group/chart overflow-hidden">
                          {(safeArray(activeResult?.trend).length
                            ? safeArray(activeResult?.trend)
                            : [activeResult?.value].filter((value) => Number.isFinite(value))).map((h, i, series) => (
                              <div
                                key={`${activeResult?.id || 'active'}-hist-${i}`}
                                className={`w-2.5 rounded-t-full transition-all duration-1000 ${i === series.length - 1 ? 'bg-primary shadow-xl shadow-primary/30' : 'bg-primary/20 group-hover/chart:bg-primary/40'
                                  }`}
                                style={{
                                  height: `${getTrendBarHeight(h, series)}%`,
                                  transitionDelay: `${i * 75}ms`,
                                }}
                              ></div>
                            ))}
                        </div>
                        <div className="flex justify-between mt-5 px-3 text-[10px] text-text-muted font-black uppercase tracking-[0.25em] opacity-80 leading-none">
                          <span>Oldest</span>
                          <span>Recent</span>
                        </div>
                      </div>
                      <div className="pt-8 border-t border-slate-100 dark:border-stroke/50">
                        <p className="text-xs text-slate-500 dark:text-text-muted leading-relaxed italic font-bold opacity-80 max-w-[420px]">
                          {activeResult
                            ? `Latest ${activeResult.name} reading is ${formatValue(activeResult.value)} ${activeResult.unit}. Current status is ${activeResult.status} against ${activeResult.reference_range}.`
                            : 'No historical lab trend is available for the selected filter.'}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="absolute top-0 right-0 size-40 bg-primary opacity-[0.03] blur-3xl -mr-20 -mt-20 group-hover:opacity-[0.06] transition-opacity"></div>
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

