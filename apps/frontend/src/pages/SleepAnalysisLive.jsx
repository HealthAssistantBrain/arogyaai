import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Bell,
  Calendar,
  History,
  RefreshCw,
  Verified,
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { useAuthStore } from '../store/authStore';
import useSleepStore from '../store/sleepStore';
import SleepStackedChart from '../components/charts/SleepStackedChart';
import { safeArray } from '../utils/safeData';

const STAGE_COLORS = {
  rem: 'var(--color-primary)',
  deep: '#009cde',
  light: '#a5b4fc',
  awake: '#fca5a5',
};

const STAGE_LEVELS = {
  awake: 18,
  rem: 40,
  light: 64,
  deep: 84,
};

const RANGE_OPTIONS = [
  { label: 'Last Night', value: '24h' },
  { label: '7d Trend', value: '7d' },
  { label: '30d Analytics', value: '30d' },
];

const stageCardMeta = [
  { key: 'rem', label: 'REM', goal: '20-25%' },
  { key: 'deep', label: 'Deep', goal: '15-25%' },
  { key: 'light', label: 'Light', goal: '40-55%' },
  { key: 'awake', label: 'Awake', goal: '< 10%' },
];

const insightToneClasses = {
  success: 'border-emerald-500 text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 dark:text-emerald-400',
  warning: 'border-rose-500 text-rose-600 bg-rose-50 dark:bg-rose-500/10 dark:text-rose-400',
  info: 'border-secondary text-secondary bg-secondary/10',
};

const toNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const formatDuration = (hours) => {
  if (!Number.isFinite(Number(hours)) || hours === null || hours === undefined) return '--';
  const totalMinutes = Math.max(0, Math.round(Number(hours) * 60));
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return `${h}h ${String(m).padStart(2, '0')}m`;
};

const formatPercent = (value) => (Number.isFinite(Number(value)) ? `${Math.round(Number(value))}%` : '--');

const formatDateLabel = (summary) => {
  if (summary?.sleep_date_label) return summary.sleep_date_label;
  if (summary?.sleep_date) {
    const date = new Date(summary.sleep_date);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
    }
  }
  return new Date().toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
};

const buildHypnogramPath = (timeline = []) => {
  const points = Array.isArray(timeline) ? timeline : [];
  if (points.length === 0) return 'M 0 60 L 100 60';

  const step = points.length > 1 ? 100 / (points.length - 1) : 100;
  return points
    .map((point, index) => {
      const x = index * step;
      const stage = point?.stage ?? 'light';
      const y = STAGE_LEVELS[stage] ?? STAGE_LEVELS.light;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
};

const SleepAnalysisLive = () => {
  const navigate = useNavigate();
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const {
    summary,
    loading,
    error,
    selectedRange,
    setSelectedRange,
    fetchSleepSummary,
    refreshSleepSummary,
    startSleepPolling,
    stopSleepPolling,
  } = useSleepStore();

  useEffect(() => {
    if (!isHydrated || !isAuthenticated) return undefined;

    void fetchSleepSummary({ range: selectedRange, force: true });
    startSleepPolling();

    return () => {
      stopSleepPolling();
    };
  }, [fetchSleepSummary, isAuthenticated, isHydrated, selectedRange, startSleepPolling, stopSleepPolling]);

  const stages = useMemo(() => {
    const stageValues = summary?.stages ?? {};
    return stageCardMeta.map((stage) => {
      const percent = toNumber(stageValues[stage.key]) ?? 0;
      return {
        ...stage,
        percent,
        color: STAGE_COLORS[stage.key],
      };
    });
  }, [summary?.stages]);

  const sleepScore = toNumber(summary?.sleep_score);
  const recoveryScore = toNumber(summary?.recovery_score);
  const duration = toNumber(summary?.duration);
  const hrv = toNumber(summary?.hrv);
  const rhr = toNumber(summary?.rhr);
  const efficiency = toNumber(summary?.efficiency);
  const sleepDebt = toNumber(summary?.sleep_debt_hours);
  const weeklyData = Array.isArray(summary?.weekly_data) ? summary.weekly_data : [];
  const timelineData = Array.isArray(summary?.timeline_data) ? summary.timeline_data : [];

  const hypnogramPath = useMemo(() => buildHypnogramPath(timelineData), [timelineData]);
  const timelineLabels = useMemo(() => {
    const first = timelineData[0];
    const last = timelineData[timelineData.length - 1];
    const start = first?.timestamp ? new Date(first.timestamp) : null;
    const end = last?.timestamp ? new Date(last.timestamp) : null;
    return {
      start: start && !Number.isNaN(start.getTime()) ? start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '11:00 PM',
      end: end && !Number.isNaN(end.getTime()) ? end.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : '06:30 AM',
    };
  }, [timelineData]);

  const currentInsight = summary?.insights?.[0];
  const circadianLabel = summary?.circadian_phase ?? 'No data';
  const alignmentLabel = summary?.circadian_alignment ?? 'No data available';
  const metricColor = sleepScore !== null && sleepScore >= 85 ? '#00a67e' : sleepScore !== null && sleepScore >= 70 ? '#009cde' : '#ef4444';
  const scoreRingOffset = sleepScore !== null ? 264 - (264 * Math.max(0, Math.min(100, sleepScore))) / 100 : 264;
  const activeRange = selectedRange;

  const handleRangeChange = (range) => {
    setSelectedRange(range);
  };

  const handleRefresh = () => {
    void refreshSleepSummary();
  };

  const sleepScoreLabel =
    sleepScore === null ? 'No data' : sleepScore >= 85 ? 'Optimal' : sleepScore >= 70 ? 'Stable' : 'Needs recovery';

  return (
    <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-background dark:bg-background">


          <div className="p-10 max-w-[1400px] mx-auto w-full">
            {error ? (
              <div className="mb-6 rounded-3xl border border-amber-200 bg-amber-50/80 dark:bg-amber-500/10 dark:border-amber-500/20 px-5 py-4 text-sm text-amber-700 dark:text-amber-300">
                {error}
              </div>
            ) : null}

            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-10">
              <div>
                <h2 className="text-4xl font-black tracking-tighter text-text-primary dark:text-text-primary mb-3 leading-none">Sleep Intelligence</h2>
                <div className="flex items-center gap-4">
                  <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-bold text-[10px] uppercase tracking-widest border ${sleepScore !== null && sleepScore >= 80 ? 'bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-400' : 'bg-slate-50 text-slate-500 border-slate-200 dark:bg-white/5 dark:border-stroke dark:text-text-secondary'}`}>
                    <Verified size={12} />
                    {sleepScoreLabel}
                  </div>
                  <p className="text-slate-500 dark:text-text-muted font-bold text-[13px]">
                    {currentInsight?.detail || 'Your sleep metrics are updating from the live wearable pipeline.'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[10px] font-black text-text-muted uppercase tracking-widest mb-1">ArogyaAI Score</p>
                <p className="text-5xl font-black text-primary leading-none tracking-tighter">{sleepScore !== null ? sleepScore : '--'}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div className="lg:col-span-4 space-y-8">
                <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50 relative h-[380px] flex flex-col">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-bold text-text-primary dark:text-text-primary text-lg">Sleep Score</h3>
                    <div className="text-[10px] font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 px-3 py-1 rounded-full uppercase tracking-widest">
                      {summary ? (summary.empty ? 'No Data' : 'Live Summary') : 'Loading'}
                    </div>
                  </div>
                  <div className="flex-1 relative flex justify-center items-center">
                    <svg className="size-48 -rotate-90" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="42" fill="transparent" stroke="#f1f5f9" strokeWidth="10" className="dark:stroke-slate-800" />
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        fill="transparent"
                        stroke={metricColor}
                        strokeWidth="10"
                        strokeLinecap="round"
                        strokeDasharray="264"
                        strokeDashoffset={scoreRingOffset}
                      />
                    </svg>
                    <div className="absolute flex flex-col items-center justify-center pt-2">
                      <span className="text-5xl font-black text-text-primary dark:text-text-primary tracking-tighter">{sleepScore !== null ? sleepScore : '--'}</span>
                      <span className="text-[9px] font-bold text-text-muted uppercase tracking-widest mt-1">Points</span>
                    </div>
                  </div>
                  <div className="flex flex-row justify-between items-center mt-6 border-t border-slate-100 dark:border-stroke/50 pt-6">
                    <div>
                      <p className="text-[9px] font-bold text-text-muted uppercase tracking-widest mb-1">Efficiency</p>
                      <p className="text-xl font-black text-text-primary dark:text-text-primary">{formatPercent(efficiency)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[9px] font-bold text-text-muted uppercase tracking-widest mb-1">Total Time</p>
                      <p className="text-xl font-black text-text-primary dark:text-text-primary">{formatDuration(duration)}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50 h-[320px] flex flex-col">
                  <h3 className="font-bold text-text-primary dark:text-text-primary text-lg mb-8">Sleep Quality Breakdown</h3>
                  <div className="space-y-6 flex-1 flex flex-col justify-center">
                    {stages.map((stage) => (
                      <div key={stage.label} className="flex items-center gap-4">
                        <div className="w-14 text-xs font-bold text-slate-500 dark:text-text-muted uppercase tracking-widest">{stage.label}</div>
                        <div className="flex-1 h-3 bg-slate-100 dark:bg-card rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(0, Math.min(100, stage.percent))}%`, backgroundColor: stage.color }} />
                        </div>
                        <div className="w-14 text-right text-sm font-black text-text-primary dark:text-text-primary">{formatPercent(stage.percent)}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-bold text-text-primary dark:text-text-primary text-lg">Sleep Debt</h3>
                    <div className="text-[9px] font-bold text-amber-600 bg-amber-50 dark:bg-amber-500/10 px-3 py-1 rounded-full uppercase tracking-widest">Recovery Needed</div>
                  </div>
                  <div className="flex items-center gap-6">
                    <span className="text-4xl font-black text-rose-500 tracking-tighter">
                      {sleepDebt !== null ? `${sleepDebt.toFixed(1)}h` : '--'}
                    </span>
                    <div className="flex-1">
                      <div className="h-3 bg-slate-100 dark:bg-card w-full overflow-hidden mb-3 rounded-full">
                        <div className="h-full bg-rose-500 rounded-full transition-all" style={{ width: `${sleepDebt !== null ? Math.max(10, 100 - Math.min(100, sleepDebt * 18)) : 15}%` }} />
                      </div>
                      <p className="text-xs text-text-muted font-medium italic">
                        {sleepDebt !== null
                          ? `Target ${summary?.target_sleep_hours ?? 8}h. Close the gap by going to bed about ${sleepDebt.toFixed(1)}h earlier.`
                          : 'No sleep debt can be calculated yet.'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="lg:col-span-8 flex flex-col gap-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-[380px]">
                  <div className="bg-gradient-to-br from-primary to-[#4a34c1] rounded-[2rem] p-8 text-text-primary relative shadow-xl shadow-primary/20 flex flex-col justify-between">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-widest text-text-primary/70 mb-2">Restorative Index</p>
                      <h3 className="text-2xl font-bold mb-4">Recovery Score</h3>
                      <p className="text-7xl font-black tracking-tighter mt-4">{recoveryScore !== null ? recoveryScore : '--'}</p>
                    </div>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center text-sm border-b border-stroke pb-3">
                        <span className="text-text-secondary font-medium">HRV (Proxy)</span>
                        <span className="font-bold">{hrv !== null ? `${hrv} ms` : '--'}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm border-b border-stroke pb-3">
                        <span className="text-text-secondary font-medium">RHR</span>
                        <span className="font-bold">{rhr !== null ? `${rhr} bpm` : '--'}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-text-secondary font-medium">Sleep Window</span>
                        <span className="font-bold">{summary?.bedtime && summary?.wake_time ? `${summary.bedtime} - ${summary.wake_time}` : '--'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50 flex flex-col">
                    <h3 className="font-bold text-text-primary dark:text-text-primary text-lg mb-auto">Circadian Phase</h3>
                    <div className="py-12 mb-auto flex flex-col justify-center">
                      <div className="relative h-12 w-full bg-slate-100 dark:bg-card rounded-lg overflow-hidden">
                        <div className="absolute top-0 bottom-0 left-[12%] right-[40%] bg-primary/20" />
                        <div className="absolute top-1.5 bottom-1.5 left-[18%] right-[44%] bg-primary rounded shadow-md transition-all" />
                      </div>
                      <div className="flex justify-between text-[9px] font-bold text-text-muted mt-4 uppercase tracking-widest">
                        <span>10 PM</span>
                        <span>12 AM</span>
                        <span>2 AM</span>
                        <span>4 AM</span>
                        <span>6 AM</span>
                        <span>8 AM</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-600 uppercase tracking-widest mt-auto bg-emerald-50 dark:bg-emerald-500/10 px-3 py-2 w-max rounded-full">
                      <Verified size={14} />
                      {alignmentLabel}
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-500 dark:text-text-muted">{circadianLabel}</p>
                  </div>
                </div>

                <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50 h-[320px] flex flex-col">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="font-bold text-text-primary dark:text-text-primary text-lg">AI Neuro-Insights</h3>
                    <div className="text-[9px] font-bold text-white bg-primary px-3 py-1 rounded-full uppercase tracking-widest">Live Pipeline</div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1">
                    {safeArray(summary?.insights).slice(0, 2).map((insight) => {
                      const toneClass = insightToneClasses[insight?.type] || insightToneClasses.info;
                      return (
                        <div key={insight.title} className={`p-6 bg-slate-50 dark:bg-background border rounded-2xl flex flex-col sm:flex-row gap-5 ${toneClass}`}>
                          <div className="size-12 rounded-2xl flex items-center justify-center shrink-0 bg-white/70 dark:bg-white/5">
                            {insight.type === 'warning' ? <AlertTriangle size={20} /> : <Activity size={20} />}
                          </div>
                          <div>
                            <p className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-2">{insight.title}</p>
                            <p className="text-sm text-text-primary dark:text-text-primary font-medium leading-relaxed">{insight.detail}</p>
                          </div>
                        </div>
                      );
                    })}
                    {safeArray(summary?.insights).length === 0 && (
                      <div className="p-6 bg-slate-50 dark:bg-background border border-slate-100 dark:border-stroke/50 rounded-2xl flex items-center gap-4 md:col-span-2">
                        <div className="size-12 bg-primary/10 rounded-2xl flex items-center justify-center text-primary shrink-0">
                          <Activity size={20} />
                        </div>
                        <div>
                          <p className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-2">Waiting for data</p>
                          <p className="text-sm text-text-primary dark:text-text-primary font-medium leading-relaxed">Sleep insights will appear after the next wearable sync.</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50">
                  <h3 className="font-bold text-text-primary dark:text-text-primary text-lg mb-6">Protocol Recommendations</h3>
                  <div className="space-y-4">
                    {safeArray(summary?.recommendations).slice(0, 2).map((item) => (
                      <div
                        key={item.title}
                        className="p-5 bg-slate-50 dark:bg-background border border-slate-100 dark:border-stroke/50 rounded-2xl flex flex-row items-center justify-between border-l-4 border-l-rose-500"
                      >
                        <div className="flex flex-col">
                          <p className="font-bold text-text-primary dark:text-text-primary mb-1">{item.title}</p>
                          <p className="text-sm text-slate-500">{item.detail}</p>
                        </div>
                        <div className="text-[9px] font-bold text-rose-500 bg-rose-50 dark:bg-rose-500/10 px-3 py-1 rounded-full uppercase tracking-widest shrink-0">
                          {item.priority || 'Medium'}
                        </div>
                      </div>
                    ))}
                    {safeArray(summary?.recommendations).length === 0 && (
                      <div className="p-5 bg-slate-50 dark:bg-background border border-slate-100 dark:border-stroke/50 rounded-2xl text-sm text-slate-500">
                        No recommendations yet. Once data lands, the pipeline will generate practical next steps.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="col-span-1 lg:col-span-12 bg-surface rounded-[2rem] p-8 shadow-sm border border-slate-100 dark:border-stroke/50 mt-2 mb-10">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-10 gap-4">
                  <div>
                    <h3 className="font-bold text-text-primary dark:text-text-primary text-lg">Hypnogram Analysis</h3>
                    <p className="text-xs text-text-muted mt-1 font-medium">Structural view of sleep stages across the night</p>
                  </div>
                  <div className="flex gap-1 border border-slate-100 dark:border-stroke/50 rounded-lg p-1 bg-slate-50 dark:bg-background">
                    {RANGE_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => handleRangeChange(option.value)}
                        className={`px-5 py-2 text-[10px] font-bold rounded shadow-sm uppercase tracking-widest transition-colors ${activeRange === option.value
                            ? 'text-primary bg-surface border border-slate-200 dark:border-stroke/50'
                            : 'text-slate-500 hover:text-slate-700'
                          }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                {activeRange === '24h' ? (
                  <>
                    <div className="h-64 w-full relative">
                      <div className="absolute inset-x-0 top-0 bottom-8 flex flex-col justify-between text-[9px] font-bold text-text-muted uppercase tracking-widest">
                        <div className="border-b border-slate-100 dark:border-stroke/50 pb-2 w-full flex items-center h-4"><span className="w-16">Awake</span></div>
                        <div className="border-b border-slate-100 dark:border-stroke/50 pb-2 w-full flex items-center h-4"><span className="w-16">REM</span></div>
                        <div className="border-b border-slate-100 dark:border-stroke/50 pb-2 w-full flex items-center h-4"><span className="w-16">Light</span></div>
                        <div className="border-b border-slate-100 dark:border-stroke/50 pb-2 w-full flex items-center h-4"><span className="w-16">Deep</span></div>
                      </div>

                      <svg className="absolute inset-x-16 top-2 bottom-8 w-[calc(100%-4rem)] h-[calc(100%-2rem)] overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                        <path d={hypnogramPath} fill="none" stroke="var(--color-primary)" strokeWidth="2.25" strokeLinejoin="round" strokeLinecap="round" />
                      </svg>
                    </div>

                    <div className="flex justify-between items-center text-[9px] font-bold text-text-muted uppercase tracking-widest mt-1 pl-16">
                      <span>{timelineLabels.start}</span>
                      <span>Midnight</span>
                      <span>{timelineLabels.end}</span>
                    </div>

                    <div className="flex justify-center items-center gap-8 mt-10 flex-wrap">
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest"><span className="size-2 rounded-full bg-slate-200"></span> Awake</div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest"><span className="size-2 rounded-full bg-primary"></span> REM</div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest"><span className="size-2 rounded-full bg-[#a5b4fc]"></span> Light Sleep</div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest"><span className="size-2 rounded-full bg-secondary"></span> Deep Sleep</div>
                    </div>
                  </>
                ) : (
                  <div className="space-y-6">
                    <div className="h-[320px]">
                      <SleepStackedChart data={weeklyData} height={320} />
                    </div>
                    <div className="flex items-center justify-between text-xs text-text-muted font-medium">
                      <span>{weeklyData.length} nights plotted from the live database</span>
                      <span>{summary?.range === '30d' ? '30-day analytics' : '7-day trend'}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>

      <style
        dangerouslySetInnerHTML={{
          __html: `
        .fill-1 { font-variation-settings: 'FILL' 1; }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
        .leading-none { line-height: 1 !important; }
      `,
        }}
      />
    </div>
  );
};

export default SleepAnalysisLive;

