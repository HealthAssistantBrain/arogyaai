import { memo } from 'react';
import { motion as Motion } from 'framer-motion';

export type MetricRangeOption = '24h' | '7d';

type MetricRangeToggleProps = {
  value: MetricRangeOption;
  onChange: (next: MetricRangeOption) => void;
  compact?: boolean;
  highlightId?: string;
};

const OPTIONS: MetricRangeOption[] = ['24h', '7d'];

const MetricRangeToggle = ({ value, onChange, compact = false, highlightId = 'default' }: MetricRangeToggleProps) => (
  <div
    className={`relative inline-flex rounded-full border border-white/70 bg-white/55 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.85),0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.08] ${compact ? 'gap-0.5' : 'gap-1'}`}
    role="tablist"
    aria-label="Metric range"
  >
    {OPTIONS.map((option) => {
      const active = option === value;
      return (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`relative z-10 rounded-full px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.18em] transition-colors sm:px-3.5 ${active ? 'text-slate-950 dark:text-white' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'}`}
          role="tab"
          aria-selected={active}
        >
          {active ? (
            <Motion.span
              layoutId={`metric-range-toggle-highlight-${highlightId}`}
              className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-white via-white to-slate-100 shadow-[0_10px_22px_rgba(15,23,42,0.12)] dark:from-white/18 dark:via-white/22 dark:to-white/12"
              transition={{ type: 'spring', stiffness: 420, damping: 34 }}
            />
          ) : null}
          {option}
        </button>
      );
    })}
  </div>
);

export default memo(MetricRangeToggle);
