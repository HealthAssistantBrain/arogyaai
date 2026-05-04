import { Activity, BellRing, Gauge } from 'lucide-react';
import { ActionItem, PriorityTag } from './RecommendationSection';

const MonitoringCard = ({ monitoring }) => {
  const metrics = monitoring?.metrics ?? [];
  const thresholds = monitoring?.thresholds ?? [];
  const frequency = monitoring?.frequency;

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-200">
            <Gauge size={20} />
          </span>
          <h3 className="text-base font-black text-slate-950 dark:text-text-primary">Metrics to watch</h3>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          {metrics.map((item) => (
            <span key={item.id} className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-700 dark:border-stroke dark:bg-white/[0.03] dark:text-text-primary">
              <Activity size={14} />
              {item.text}
              <PriorityTag priority={item.priority} />
            </span>
          ))}
        </div>

        {frequency ? (
          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/20">
            <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500 dark:text-text-muted">Frequency</p>
            <p className="mt-2 text-sm font-semibold leading-relaxed text-slate-800 dark:text-slate-100">{frequency.text}</p>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-200">
            <BellRing size={20} />
          </span>
          <h3 className="text-base font-black text-slate-950 dark:text-text-primary">Thresholds</h3>
        </div>

        <ul className="mt-5 space-y-3">
          {thresholds.map((item) => (
            <ActionItem key={item.id} item={item} />
          ))}
        </ul>
      </div>
    </div>
  );
};

export default MonitoringCard;

