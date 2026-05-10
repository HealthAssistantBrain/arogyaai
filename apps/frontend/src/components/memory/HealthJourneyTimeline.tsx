import { useEffect, useState } from 'react';
import api from '../../lib/axios';

type TimelineEvent = {
  date: string;
  type: 'symptom' | 'report' | 'recommendation' | 'trend';
  title: string;
  description: string;
  importance: 'critical' | 'high' | 'medium' | 'low';
};

const IMPORTANCE_COLORS = {
  critical: 'border-red-500/70 bg-red-50 dark:bg-red-500/10',
  high: 'border-amber-400/70 bg-amber-50 dark:bg-amber-500/10',
  medium: 'border-sky-400/70 bg-sky-50 dark:bg-sky-500/10',
  low: 'border-slate-200 bg-slate-50 dark:border-stroke dark:bg-background/45',
};

const TYPE_ICONS = {
  symptom: '🩺',
  report: '📋',
  recommendation: '💡',
  trend: '📈',
};

export function HealthJourneyTimeline() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get('/memory/timeline')
      .then((response) => {
        if (active) {
          setEvents(Array.isArray(response?.data?.events) ? response.data.events : []);
        }
      })
      .catch(() => {
        if (active) setEvents([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((item) => (
          <div key={item} className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-white/5" />
        ))}
      </div>
    );
  }

  if (!events.length) {
    return (
      <div className="rounded-[1.8rem] border border-dashed border-slate-200 bg-white/70 px-5 py-10 text-center text-sm font-medium text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
        Your health journey memory will start appearing here as Arya learns from your sessions.
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute left-[1.1rem] top-0 bottom-0 w-px bg-slate-200 dark:bg-stroke" />
      <div className="space-y-4">
        {events.map((event, index) => (
          <div key={`${event.date}-${event.title}-${index}`} className="relative pl-10">
            <div className="absolute left-0 top-5 flex size-9 items-center justify-center rounded-2xl border border-white bg-white shadow-sm dark:border-stroke dark:bg-background/80">
              <span className="text-sm">{TYPE_ICONS[event.type]}</span>
            </div>
            <div className={`rounded-[1.5rem] border-l-4 px-4 py-4 shadow-sm ${IMPORTANCE_COLORS[event.importance] || IMPORTANCE_COLORS.low}`}>
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-text-muted">{event.date}</p>
              <p className="mt-2 text-sm font-black text-slate-900 dark:text-text-primary">{event.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-text-secondary">{event.description || 'No additional detail captured for this memory event.'}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
