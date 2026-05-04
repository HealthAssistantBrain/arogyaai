import { useEffect, useState } from 'react';
import { Activity, AlertCircle, FlaskConical, HeartPulse, Moon, Sparkles } from 'lucide-react';
import api from '../lib/axios';
import { safeArray, safeObject, safeText } from '../utils/safeData';

const ICON_RULES = [
  { match: ['sleep', 'recovery', 'rest'], icon: Moon, color: 'text-indigo-500', bg: 'bg-indigo-100 dark:bg-indigo-900/20' },
  { match: ['heart', 'cardio', 'pulse', 'rhr'], icon: HeartPulse, color: 'text-rose-500', bg: 'bg-rose-100 dark:bg-rose-900/20' },
  { match: ['glucose', 'lab', 'metabolic', 'cholesterol', 'lipid'], icon: FlaskConical, color: 'text-violet-500', bg: 'bg-violet-100 dark:bg-violet-900/20' },
];

const DEFAULT_ICON = { icon: Activity, color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900/20' };

const resolveIcon = (title = '') => {
  const normalized = title.toLowerCase();
  return ICON_RULES.find((rule) => rule.match.some((token) => normalized.includes(token))) ?? DEFAULT_ICON;
};

const normalizeInsight = (item, index) => {
  const payload = safeObject(item);
  const title = safeText(payload.title, `Health Insight ${index + 1}`);
  const description = safeText(
    payload.description ?? payload.detail ?? payload.message,
    'Your latest data generated this AI health signal.'
  );
  const recommendation = safeText(payload.recommendation ?? payload.action ?? payload.next_step);

  return {
    title,
    value: safeText(payload.value ?? payload.status, 'Insight'),
    description,
    recommendation,
  };
};

const LoadingState = () => (
  <div className="space-y-5">
    {[0, 1, 2].map((index) => (
      <div key={index} className="flex gap-4">
        <div className="size-10 shrink-0 animate-pulse rounded-full bg-slate-100 dark:bg-white/10" />
        <div className="flex-1">
          <div className="h-4 w-32 animate-pulse rounded-full bg-slate-100 dark:bg-white/10" />
          <div className="mt-3 h-3 w-full animate-pulse rounded-full bg-slate-100 dark:bg-white/10" />
          <div className="mt-2 h-3 w-3/4 animate-pulse rounded-full bg-slate-100 dark:bg-white/10" />
        </div>
      </div>
    ))}
  </div>
);

const HealthSummary = () => {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    const fetchInsights = async () => {
      try {
        const response = await api.get('/health/insights', { signal: controller.signal });
        const payload = response.data?.data ?? response.data ?? {};
        const nextInsights = safeArray(payload.insights)
          .map(normalizeInsight)
          .filter((item) => item.title && item.description);

        setInsights(nextInsights);
        setError(null);
      } catch (err) {
        if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
        setInsights([]);
        setError(err?.response?.data?.detail || err?.message || 'Unable to load health insights.');
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };

    void fetchInsights();

    return () => controller.abort();
  }, []);

  return (
    <div className="bg-white dark:bg-background p-8 rounded-xl shadow-sm border border-slate-100 dark:border-stroke flex flex-col">
      <div className="mb-6 flex items-center justify-between gap-3">
        <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em]">Health Summary</h3>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-primary">
          <Sparkles size={12} />
          AI
        </span>
      </div>

      <div className="space-y-5 flex-1 overflow-y-auto custom-scrollbar">
        {loading ? (
          <LoadingState />
        ) : insights.length > 0 ? (
          insights.map((item, index) => {
            const IconConfig = resolveIcon(item.title);
            const Icon = IconConfig.icon;

            return (
              <div key={`${item.title}-${index}`} className="flex gap-4 group">
                <div className={`${IconConfig.bg} ${IconConfig.color} size-10 shrink-0 rounded-full flex items-center justify-center transition-transform group-hover:scale-110 shadow-sm border border-white dark:border-stroke`}>
                  <Icon size={18} />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-bold text-text-primary dark:text-text-primary tracking-tight">{item.title}</p>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.16em] text-slate-500 dark:bg-white/5 dark:text-text-secondary">
                      {item.value}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed font-medium mt-1">{item.description}</p>
                  {item.recommendation ? (
                    <p className="mt-2 text-[11px] font-black uppercase tracking-[0.14em] text-primary">
                      {item.recommendation}
                    </p>
                  ) : null}
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex min-h-[132px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 px-4 text-center dark:border-stroke">
            <AlertCircle size={22} className="text-text-secondary dark:text-slate-600" />
            <p className="mt-3 text-sm font-bold text-slate-500 dark:text-text-muted">
              Not enough data to generate insights
            </p>
            {error ? (
              <p className="mt-2 text-xs font-medium text-text-muted dark:text-slate-500">{error}</p>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

export default HealthSummary;

