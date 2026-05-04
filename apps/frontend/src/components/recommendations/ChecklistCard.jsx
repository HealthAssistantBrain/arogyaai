import { useMemo, useState } from 'react';
import { CheckCircle2, Circle } from 'lucide-react';
import { PriorityTag } from './RecommendationSection';

const ChecklistCard = ({ title, items = [] }) => {
  const [checked, setChecked] = useState({});
  const completedCount = useMemo(
    () => items.filter((item) => checked[item.id]).length,
    [checked, items]
  );
  const progress = items.length ? Math.round((completedCount / items.length) * 100) : 0;

  const toggle = (id) => {
    setChecked((current) => ({ ...current, [id]: !current[id] }));
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-black uppercase tracking-[0.14em] text-slate-500 dark:text-text-muted">{title}</h3>
          <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-text-muted">{completedCount} of {items.length} completed</p>
        </div>
        <span className="text-2xl font-black text-slate-950 dark:text-text-primary">{progress}%</span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-card">
        <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress}%` }} />
      </div>

      <div className="mt-5 space-y-3">
        {items.map((item) => {
          const isChecked = Boolean(checked[item.id]);
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => toggle(item.id)}
              className="flex w-full items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-slate-300 dark:border-stroke dark:bg-background/20 dark:hover:border-stroke"
            >
              {isChecked ? (
                <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-500" size={20} />
              ) : (
                <Circle className="mt-0.5 shrink-0 text-text-muted" size={20} />
              )}
              <span className="min-w-0 flex-1">
                <span className={`block text-sm font-semibold leading-relaxed ${isChecked ? 'text-text-muted line-through' : 'text-slate-800 dark:text-slate-100'}`}>
                  {item.text}
                </span>
                {item.rationale ? (
                  <span className="mt-1 block text-xs font-medium leading-relaxed text-slate-500 dark:text-text-muted">{item.rationale}</span>
                ) : null}
              </span>
              <PriorityTag priority={item.priority} />
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ChecklistCard;

