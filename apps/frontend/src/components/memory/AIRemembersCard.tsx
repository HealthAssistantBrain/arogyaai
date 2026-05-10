import { useEffect, useState } from 'react';
import api from '../../lib/axios';

type MemoryInsight = {
  icon: string;
  label: string;
  value: string;
};

export function AIRemembersCard() {
  const [insights, setInsights] = useState<MemoryInsight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get('/memory/insights')
      .then((response) => {
        if (active) {
          setInsights(Array.isArray(response?.data?.insights) ? response.data.insights : []);
        }
      })
      .catch(() => {
        if (active) setInsights([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="rounded-[1.8rem] border border-primary/10 bg-[radial-gradient(circle_at_top_left,rgba(97,67,244,0.18),transparent_55%),linear-gradient(180deg,rgba(255,255,255,0.96),rgba(245,247,255,0.88))] p-5 shadow-[0_24px_65px_-38px_rgba(97,67,244,0.6)] dark:border-primary/20 dark:bg-[radial-gradient(circle_at_top_left,rgba(97,67,244,0.24),transparent_55%),linear-gradient(180deg,rgba(19,16,34,0.96),rgba(13,10,25,0.92))]">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-2xl bg-primary/10 text-primary dark:bg-primary/15 dark:text-[#c9bfff]">
          🧠
        </div>
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.24em] text-primary">Long-Term Memory</p>
          <h3 className="mt-1 text-lg font-black tracking-tight text-slate-950 dark:text-text-primary">
            Your AI Health Companion Remembers
          </h3>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {loading ? (
          [1, 2, 3].map((item) => (
            <div key={item} className="h-16 animate-pulse rounded-2xl bg-white/70 dark:bg-white/5" />
          ))
        ) : insights.length > 0 ? (
          insights.map((insight) => (
            <div key={`${insight.label}-${insight.value}`} className="rounded-2xl border border-white/70 bg-white/85 px-4 py-3 dark:border-white/10 dark:bg-white/[0.04]">
              <div className="flex items-center gap-3">
                <span className="text-lg">{insight.icon}</span>
                <div className="min-w-0">
                  <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">{insight.label}</p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-700 dark:text-text-primary">{insight.value}</p>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-white/70 px-4 py-5 text-sm font-medium text-slate-500 dark:border-stroke dark:bg-white/[0.04] dark:text-text-secondary">
            Your personalized memory layer will grow as you continue using Arya.
          </div>
        )}
      </div>
    </div>
  );
}
