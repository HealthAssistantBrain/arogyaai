import { useEffect, useState } from 'react';
import api from '../../lib/axios';

type RecommendationItem = {
  id: string;
  date?: string | null;
  recommendation: string;
  follow_up_needed: boolean;
  status: string;
};

export function RecommendationTracker() {
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get('/memory/recommendations')
      .then((response) => {
        if (active) {
          setItems(Array.isArray(response?.data?.items) ? response.data.items : []);
        }
      })
      .catch(() => {
        if (active) setItems([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-stroke dark:bg-background/45">
      <p className="text-[11px] font-black uppercase tracking-[0.24em] text-text-muted">Recommendation Tracker</p>
      <h3 className="mt-2 text-lg font-black tracking-tight text-slate-950 dark:text-text-primary">Follow-up advice you can revisit</h3>

      <div className="mt-5 space-y-3">
        {loading ? (
          [1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-white/5" />)
        ) : items.length > 0 ? (
          items.map((item) => (
            <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 dark:border-stroke dark:bg-background/60">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[10px] font-black uppercase tracking-[0.22em] text-text-muted">
                  {item.follow_up_needed ? 'Follow-up recommended' : 'Saved advice'}
                </span>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${
                  item.follow_up_needed
                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300'
                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
                }`}>
                  {item.status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-text-primary">{item.recommendation}</p>
              <p className="mt-2 text-[11px] font-semibold text-slate-400 dark:text-text-muted">
                {item.date ? new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recent session'}
              </p>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-5 text-sm font-medium text-slate-500 dark:border-stroke dark:bg-background/60 dark:text-text-secondary">
            Follow-up suggestions will appear here after richer health conversations.
          </div>
        )}
      </div>
    </div>
  );
}
