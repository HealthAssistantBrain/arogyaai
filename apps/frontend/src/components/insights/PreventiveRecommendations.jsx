import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Brain,
  HeartPulse,
  Moon,
  Pill,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Utensils,
  Zap,
} from 'lucide-react';

const itemVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
};

const riskToneStyles = {
  green: {
    border: 'border-emerald-200/70 dark:border-emerald-500/20',
    badge: 'bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300',
    bar: 'bg-emerald-500',
  },
  yellow: {
    border: 'border-amber-200/80 dark:border-amber-500/20',
    badge: 'bg-amber-500/10 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
    bar: 'bg-amber-500',
  },
  red: {
    border: 'border-rose-200/80 dark:border-rose-500/20',
    badge: 'bg-rose-500/10 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
    bar: 'bg-rose-500',
  },
  slate: {
    border: 'border-slate-200/80 dark:border-white/10',
    badge: 'bg-slate-200 text-slate-700 dark:bg-slate-700/60 dark:text-slate-200',
    bar: 'bg-slate-400',
  },
};

const categoryConfig = {
  lifestyle: {
    title: 'Lifestyle',
    icon: Sparkles,
    iconClass: 'text-[#6143f4]',
  },
  diet: {
    title: 'Diet',
    icon: Utensils,
    iconClass: 'text-[#009cde]',
  },
  fitness: {
    title: 'Fitness',
    icon: Activity,
    iconClass: 'text-orange-500',
  },
  sleep: {
    title: 'Sleep',
    icon: Moon,
    iconClass: 'text-indigo-500',
  },
};

const priorityStyles = {
  high: 'bg-rose-500/10 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300',
  medium: 'bg-amber-500/10 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  low: 'bg-slate-200 text-slate-700 dark:bg-slate-700/60 dark:text-slate-200',
};

const formatUpdatedAt = (value) => {
  if (!value) {
    return 'Waiting for backend refresh';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'Waiting for backend refresh';
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

const formatMetricValue = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '--';
  }
  const fixed = numeric % 1 === 0 ? numeric.toFixed(0) : numeric.toFixed(1);
  return fixed.endsWith('.0') ? fixed.slice(0, -2) : fixed;
};

const EmptyInsight = ({ title = 'Insufficient data for this insight' }) => (
  <div className="rounded-3xl border border-dashed border-slate-300 bg-white/90 p-8 text-center shadow-sm dark:border-slate-700 dark:bg-[#1a1433]">
    <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-300">
      <AlertTriangle size={24} />
    </div>
    <p className="mt-4 text-sm font-bold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
      {title}
    </p>
  </div>
);

const PreventiveRecommendations = ({ data, error, onRetry }) => {
  const {
    riskCards = [],
    summary = '',
    factors = [],
    outcome = {},
    possibleConditions = [],
    symptoms = [],
    groupedRecommendations = {},
    sources = [],
    metricInsights = [],
    lastUpdated = null,
    hasAnyData = false,
  } = data || {};

  const visibleRecommendationSections = Object.entries(categoryConfig)
    .map(([key, config]) => ({
      key,
      config,
      items: groupedRecommendations?.[key] ?? [],
    }))
    .filter((section) => section.items.length > 0);

  return (
    <motion.div
      variants={itemVariants}
      initial="initial"
      animate="animate"
      className="space-y-8"
    >
      <section className="relative overflow-hidden rounded-[32px] border border-white/60 bg-gradient-to-br from-[#13082a] via-[#1a1433] to-[#0f172a] p-8 text-white shadow-2xl shadow-[#13082a]/10 lg:p-10">
        <div className="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-4xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.2em] text-white/80">
              <Brain size={14} />
              Live ML + SHAP + RAG
            </span>
            <h1 className="mt-5 text-4xl font-black uppercase tracking-tight lg:text-5xl">
              AI Health Insights
            </h1>
            <p className="mt-4 max-w-3xl text-base font-medium leading-relaxed text-white/75 lg:text-lg">
              {outcome?.headline || summary || 'Insufficient data for this insight'}
            </p>
            {summary ? (
              <p className="mt-4 max-w-3xl text-sm font-medium leading-relaxed text-white/60">
                {summary}
              </p>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">Risk Cards</p>
              <p className="mt-2 text-xl font-black">{riskCards.length || 0}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">SHAP Factors</p>
              <p className="mt-2 text-xl font-black">{factors.length || 0}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">Clinical Outlook</p>
              <p className="mt-2 text-sm font-black uppercase tracking-[0.12em] text-white/85">
                {outcome?.severity || 'pending'}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">Last Updated</p>
              <p className="mt-2 text-sm font-black uppercase tracking-[0.12em] text-white/85">
                {formatUpdatedAt(lastUpdated)}
              </p>
            </div>
          </div>
        </div>

        <div className="absolute -right-16 -top-16 size-72 rounded-full bg-[#6143f4]/20 blur-3xl" />
        <div className="absolute -bottom-24 left-1/3 size-72 rounded-full bg-[#009cde]/20 blur-3xl" />
      </section>

      {error ? (
        <div className="flex flex-col gap-4 rounded-3xl border border-amber-300/70 bg-amber-50 p-5 text-sm font-medium text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-100 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 shrink-0 text-amber-600 dark:text-amber-300" size={18} />
            <p>{error}</p>
          </div>
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white"
          >
            <RefreshCcw size={14} />
            Retry
          </button>
        </div>
      ) : null}

      {!hasAnyData ? (
        <EmptyInsight />
      ) : (
        <>
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <ShieldCheck className="text-[#6143f4]" size={22} />
              <h2 className="text-2xl font-black tracking-tight dark:text-white">Multi-Condition Risk Analysis</h2>
            </div>

            {riskCards.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {riskCards.map((risk) => {
                  const tone = riskToneStyles[risk.tone] || riskToneStyles.slate;
                  return (
                    <article
                      key={risk.id}
                      className={`rounded-3xl border bg-white p-6 shadow-sm dark:bg-[#1a1433] ${tone.border}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="text-sm font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                            {risk.title}
                          </p>
                          <p className="mt-4 text-4xl font-black text-[#13082a] dark:text-white">
                            {Number.isFinite(Number(risk.percent)) ? `${Number(risk.percent).toFixed(1)}%` : '--'}
                          </p>
                        </div>
                        <span className={`inline-flex rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${tone.badge}`}>
                          {risk.label}
                        </span>
                      </div>

                      <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className={`h-full rounded-full ${tone.bar}`}
                          style={{ width: `${Math.max(6, Number(risk.percent) || 0)}%` }}
                        />
                      </div>

                      {risk.summary ? (
                        <p className="mt-4 text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                          {risk.summary}
                        </p>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            ) : (
              <EmptyInsight />
            )}
          </section>

          <section className="grid grid-cols-1 gap-8 xl:grid-cols-[1.2fr_0.8fr]">
            <article className="rounded-[28px] border border-slate-200/80 bg-white p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
              <div className="flex items-center gap-3">
                <div className="flex size-11 items-center justify-center rounded-2xl bg-[#6143f4]/10 text-[#6143f4]">
                  <Brain size={22} />
                </div>
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#6143f4]">Deep Analysis</p>
                  <h2 className="mt-1 text-2xl font-black tracking-tight dark:text-white">RAG Explanation</h2>
                </div>
              </div>

              <p className="mt-6 text-base font-medium leading-relaxed text-slate-600 dark:text-slate-300">
                {summary || 'Insufficient data for this insight'}
              </p>

              {sources.length > 0 ? (
                <div className="mt-6 flex flex-wrap gap-2">
                  {sources.slice(0, 4).map((source) => (
                    <span
                      key={source.id}
                      className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300"
                    >
                      {source.source}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>

            <article className="rounded-[28px] border border-slate-200/80 bg-white p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
              <div className="flex items-center gap-3">
                <div className="flex size-11 items-center justify-center rounded-2xl bg-[#009cde]/10 text-[#009cde]">
                  <HeartPulse size={22} />
                </div>
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#009cde]">Live Biometrics</p>
                  <h2 className="mt-1 text-2xl font-black tracking-tight dark:text-white">Health Metrics</h2>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-4">
                {metricInsights.map((metric) => (
                  <div
                    key={metric.key}
                    className="rounded-2xl border border-slate-100 bg-slate-50/80 p-5 dark:border-white/5 dark:bg-white/[0.03]"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">
                          {metric.label}
                        </p>
                        <p className="mt-3 text-3xl font-black text-[#13082a] dark:text-white">
                          {formatMetricValue(metric.value)}
                          {metric.value !== null ? (
                            <span className="ml-2 text-sm font-bold text-slate-400 dark:text-slate-500">
                              {metric.unit}
                            </span>
                          ) : null}
                        </p>
                      </div>
                      <Zap size={18} className="shrink-0 text-slate-300 dark:text-slate-600" />
                    </div>
                    <p className="mt-4 text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                      {metric.assessment}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          </section>

          <section className="grid grid-cols-1 gap-8 xl:grid-cols-2">
            <article className="rounded-[28px] border border-slate-200/80 bg-white p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
              <div className="flex items-center gap-3">
                <div className="flex size-11 items-center justify-center rounded-2xl bg-[#13082a]/5 text-[#13082a] dark:bg-white/5 dark:text-white">
                  <Pill size={22} />
                </div>
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">Possible Conditions</p>
                  <h2 className="mt-1 text-2xl font-black tracking-tight dark:text-white">Condition Signals</h2>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                {possibleConditions.length > 0 ? (
                  possibleConditions.map((condition) => (
                    <span
                      key={condition}
                      className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-200"
                    >
                      {condition}
                    </span>
                  ))
                ) : (
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    No clear condition signal available from the current explanation payload.
                  </p>
                )}
              </div>
            </article>

            <article className="rounded-[28px] border border-slate-200/80 bg-white p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
              <div className="flex items-center gap-3">
                <div className="flex size-11 items-center justify-center rounded-2xl bg-[#009cde]/10 text-[#009cde]">
                  <Stethoscope size={22} />
                </div>
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">Symptoms</p>
                  <h2 className="mt-1 text-2xl font-black tracking-tight dark:text-white">Likely Manifestations</h2>
                </div>
              </div>

              <div className="mt-8 flex flex-wrap gap-3">
                {symptoms.length > 0 ? (
                  symptoms.map((symptom) => (
                    <span
                      key={symptom}
                      className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-200"
                    >
                      {symptom}
                    </span>
                  ))
                ) : (
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    No symptom inference is available from the current explanation payload.
                  </p>
                )}
              </div>
            </article>
          </section>

          <section className="rounded-[28px] border border-slate-200/80 bg-white p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-[#13082a]/5 text-[#13082a] dark:bg-white/5 dark:text-white">
                <Brain size={22} />
              </div>
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">SHAP Insights</p>
                <h2 className="mt-1 text-2xl font-black tracking-tight dark:text-white">Top Contributing Factors</h2>
              </div>
            </div>

            <div className="mt-8 space-y-5">
              {factors.length > 0 ? (
                factors.map((factor) => {
                  const increasingRisk = factor.direction === 'increase';
                  return (
                    <div key={factor.id} className="rounded-2xl border border-slate-100 bg-slate-50/80 p-5 dark:border-white/5 dark:bg-white/[0.03]">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-lg font-black tracking-tight text-[#13082a] dark:text-white">
                            {factor.summary}
                          </p>
                          {factor.description ? (
                            <p className="mt-2 text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                              {factor.description}
                            </p>
                          ) : null}
                        </div>
                        <span
                          className={`inline-flex w-fit rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${
                            increasingRisk
                              ? 'bg-rose-500/10 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300'
                              : 'bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
                          }`}
                        >
                          {increasingRisk ? 'Increase' : 'Decrease'}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <EmptyInsight />
              )}
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-[#6143f4]/10 text-[#6143f4]">
                <Sparkles size={22} />
              </div>
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-[#6143f4]">Action Plan</p>
                <h2 className="mt-1 text-2xl font-black tracking-tight dark:text-white">Recommendations</h2>
              </div>
            </div>

            {visibleRecommendationSections.length > 0 ? (
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                {visibleRecommendationSections.map(({ key, config, items }) => {
                  const Icon = config.icon;
                  return (
                    <article
                      key={key}
                      className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/5 dark:bg-[#1a1433]"
                    >
                      <div className="mb-6 flex items-center gap-3">
                        <div className={`flex size-11 items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/5 ${config.iconClass}`}>
                          <Icon size={22} />
                        </div>
                        <h3 className="text-xl font-black tracking-tight dark:text-white">{config.title}</h3>
                      </div>

                      <div className="space-y-4">
                        {items.map((recommendation) => (
                          <div
                            key={recommendation.id}
                            className="rounded-2xl border border-slate-100 bg-slate-50/80 p-5 dark:border-white/5 dark:bg-white/[0.03]"
                          >
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                              <div>
                                <h4 className="text-lg font-black tracking-tight text-[#13082a] dark:text-white">
                                  {recommendation.title}
                                </h4>
                                <p className="mt-3 text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                                  {recommendation.description}
                                </p>
                              </div>
                              <span
                                className={`inline-flex w-fit rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${priorityStyles[recommendation.priority] || priorityStyles.medium}`}
                              >
                                {recommendation.priority}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <EmptyInsight />
            )}
          </section>
        </>
      )}
    </motion.div>
  );
};

export default PreventiveRecommendations;
