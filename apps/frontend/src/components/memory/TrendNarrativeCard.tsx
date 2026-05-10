type TrendNarrative = {
  metric: string;
  narrative: string;
  trend: 'improving' | 'worsening' | 'stable';
  period: string;
};

const TREND_STYLES = {
  improving: {
    color: 'text-emerald-600 dark:text-emerald-300',
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    icon: '↗',
    border: 'border-emerald-200 dark:border-emerald-500/20',
  },
  worsening: {
    color: 'text-red-600 dark:text-red-300',
    bg: 'bg-red-50 dark:bg-red-500/10',
    icon: '↘',
    border: 'border-red-200 dark:border-red-500/20',
  },
  stable: {
    color: 'text-sky-600 dark:text-sky-300',
    bg: 'bg-sky-50 dark:bg-sky-500/10',
    icon: '→',
    border: 'border-sky-200 dark:border-sky-500/20',
  },
};

export function TrendNarrativeCard({ trend }: { trend: TrendNarrative }) {
  const style = TREND_STYLES[trend.trend] || TREND_STYLES.stable;

  return (
    <div className={`rounded-2xl border ${style.border} ${style.bg} px-4 py-4`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-[10px] font-black uppercase tracking-[0.22em] text-text-muted">{trend.metric}</span>
        <span className={`text-sm font-black ${style.color}`}>
          {style.icon} {trend.trend}
        </span>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-text-primary">{trend.narrative}</p>
      <p className="mt-2 text-[11px] font-semibold text-slate-400 dark:text-text-muted">{trend.period}</p>
    </div>
  );
}
