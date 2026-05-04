import { memo } from 'react';
import { motion as Motion } from 'framer-motion';
import MetricHeroCard from './MetricHeroCard';
import MetricMiniCard from './MetricMiniCard';
import type { DashboardMetric } from './MetricMiniCard';

type MetricGroupProps = {
  title: string;
  hero: DashboardMetric;
  mini: DashboardMetric[];
  index?: number;
};

const MetricGroup = ({ title, hero, mini, index = 0 }: MetricGroupProps) => {
  const cards = mini.slice(0, 2);

  return (
    <Motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.08, ease: 'easeOut' }}
      className="rounded-[2rem] border border-white/65 bg-white/35 p-6 shadow-[0_14px_44px_rgba(15,23,42,0.07)] backdrop-blur-xl dark:border-stroke dark:bg-white/[0.035]"
      aria-label={title}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-[12px] font-black uppercase tracking-[0.22em] text-slate-500 dark:text-text-secondary">
          {title}
        </h3>
        <span className="rounded-full bg-white/70 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-text-muted shadow-sm dark:bg-white/10 dark:text-text-muted">
          3 signals
        </span>
      </div>

      <div>
        <MetricHeroCard metric={hero} />
        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2">
          {cards.map((metric) => (
            <MetricMiniCard key={metric.key} metric={metric} />
          ))}
        </div>
      </div>
    </Motion.section>
  );
};

export default memo(MetricGroup);
