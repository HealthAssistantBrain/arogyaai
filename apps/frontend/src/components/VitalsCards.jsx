import { memo } from 'react';
import { motion as Motion } from 'framer-motion';
import { Activity } from 'lucide-react';
import HealthMetricCard from './cards/HealthMetricCard';
import { safeArray } from '../utils/safeData';

const containerVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { staggerChildren: 0.08 } },
};

const itemVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
};

const LoadingCard = () => (
  <div className="rounded-[1.5rem] border border-slate-200/80 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
    <div className="h-28 animate-pulse rounded-[1.25rem] bg-slate-100 dark:bg-white/10" />
    <div className="mt-4 h-3 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
    <div className="mt-3 h-8 w-32 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
  </div>
);

const VitalsCards = ({ items = [], loading = false, className = '', emptyMessage = 'Waiting for sync' }) => {
  const metrics = safeArray(items);

  return (
    <Motion.section
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className={className}
      aria-label="Key health vitals"
    >
      {loading ? (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
          {[0, 1, 2].map((index) => (
            <LoadingCard key={`vitals-loading-${index}`} />
          ))}
        </div>
      ) : metrics.length > 0 ? (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
          {metrics.map((metric) => (
            <HealthMetricCard
              key={metric.key}
              metricKey={metric.key}
              label={metric.label}
              value={metric.value}
              rawValue={metric.rawValue ?? metric.systolic ?? metric.value}
              unit={metric.unit}
              icon={metric.icon}
              color={metric.color}
              timestamp={metric.timestamp ?? metric.lastUpdated}
              isRecent={metric.isRecent}
              precision={metric.precision}
              caption={metric.caption}
              series={metric.series}
              variants={itemVariants}
            />
          ))}
        </div>
      ) : (
        <div className="flex min-h-[148px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white p-6 text-center shadow-sm dark:border-white/10 dark:bg-[#131022]">
          <div className="flex size-11 items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-white/5 dark:text-slate-500">
            <Activity size={18} />
          </div>
          <p className="mt-4 text-[14px] font-black tracking-tight text-[#13082a] dark:text-white">
            {emptyMessage}
          </p>
        </div>
      )}
    </Motion.section>
  );
};

export default memo(VitalsCards);
