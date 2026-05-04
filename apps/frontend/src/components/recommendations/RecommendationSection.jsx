import { ChevronDown } from 'lucide-react';

const PRIORITY_CLASSES = {
  HIGH: 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/25 dark:bg-red-500/10 dark:text-red-200',
  MEDIUM: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200',
  LOW: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200',
};

export const PriorityTag = ({ priority = 'MEDIUM' }) => {
  const label = String(priority || 'MEDIUM').toUpperCase();

  return (
    <span className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[10px] font-black tracking-[0.14em] ${PRIORITY_CLASSES[label] || PRIORITY_CLASSES.MEDIUM}`}>
      {label}
    </span>
  );
};

export const ActionItem = ({ item }) => (
  <li className="flex gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-stroke dark:bg-white/[0.03]">
    <PriorityTag priority={item.priority} />
    <div className="min-w-0">
      <p className="text-sm font-semibold leading-relaxed text-slate-800 dark:text-slate-100">{item.text}</p>
      {item.rationale ? (
        <p className="mt-1 text-xs font-medium leading-relaxed text-slate-500 dark:text-text-muted">{item.rationale}</p>
      ) : null}
    </div>
  </li>
);

const RecommendationSection = ({ title, icon: Icon, children, defaultOpen = true, tone = 'slate' }) => {
  const toneClass = {
    red: 'text-red-600 bg-red-50 dark:bg-red-500/10 dark:text-red-200',
    amber: 'text-amber-700 bg-amber-50 dark:bg-amber-500/10 dark:text-amber-200',
    emerald: 'text-emerald-700 bg-emerald-50 dark:bg-emerald-500/10 dark:text-emerald-200',
    blue: 'text-blue-700 bg-blue-50 dark:bg-blue-500/10 dark:text-blue-200',
    slate: 'text-slate-700 bg-slate-100 dark:bg-white/10 dark:text-slate-100',
  }[tone] || 'text-slate-700 bg-slate-100 dark:bg-white/10 dark:text-slate-100';

  return (
    <details open={defaultOpen} className="group overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/80 dark:border-stroke dark:bg-white/[0.03]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4">
        <span className="flex min-w-0 items-center gap-3">
          {Icon ? (
            <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${toneClass}`}>
              <Icon size={20} />
            </span>
          ) : null}
          <span className="text-base font-black tracking-tight text-slate-950 dark:text-text-primary">{title}</span>
        </span>
        <ChevronDown className="shrink-0 text-text-muted transition-transform group-open:rotate-180" size={18} />
      </summary>
      <div className="border-t border-slate-200 px-5 py-5 dark:border-stroke">{children}</div>
    </details>
  );
};

export default RecommendationSection;

