import { useEffect, useMemo, useRef } from 'react';
import {
    Activity,
    AlertTriangle,
    Brain,
    Dumbbell,
    Moon,
    RefreshCcw,
    Sparkles,
    Utensils,
    Wind,
} from 'lucide-react';
import useHealthStore from '../store/healthStore';
import useDashboardStore from '../store/dashboardStore';
import ClinicalInsightCard from '../components/clinical/ClinicalInsightCard';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const CATEGORY_CONFIG = {
    lifestyle: {
        title: 'Lifestyle Improvements',
        icon: Sparkles,
        iconClass: 'text-[#6143f4]',
        panelClass: 'border-[#6143f4]/10 bg-white dark:bg-[#1a1433]',
    },
    diet: {
        title: 'Dietary Optimization',
        icon: Utensils,
        iconClass: 'text-[#009cde]',
        panelClass: 'border-[#009cde]/10 bg-white dark:bg-[#1a1433]',
    },
    fitness: {
        title: 'Fitness & Activity',
        icon: Dumbbell,
        iconClass: 'text-orange-500',
        panelClass: 'border-orange-500/10 bg-white dark:bg-[#1a1433]',
    },
    sleep: {
        title: 'Sleep Optimization',
        icon: Moon,
        iconClass: 'text-indigo-500',
        panelClass: 'border-indigo-500/10 bg-white dark:bg-[#1a1433]',
    },
    environment: {
        title: 'Environmental Risk',
        icon: Wind,
        iconClass: 'text-emerald-500',
        panelClass: 'border-emerald-500/10 bg-white dark:bg-[#1a1433]',
    },
};

const PRIORITY_STYLES = {
    high: 'bg-red-500/10 text-red-600 dark:bg-red-500/15 dark:text-red-300 ring-1 ring-red-500/20',
    medium: 'bg-amber-500/10 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300 ring-1 ring-amber-500/20',
    low: 'bg-slate-200 text-slate-700 dark:bg-slate-700/60 dark:text-slate-200 ring-1 ring-slate-300/60 dark:ring-slate-600',
};

const formatMetricValue = (metric) => {
    const value = Number(metric?.value);
    if (!Number.isFinite(value)) {
        return '--';
    }

    const precision = Number.isFinite(Number(metric?.precision)) ? Number(metric.precision) : 0;
    const fixed = value.toFixed(precision);
    return fixed.endsWith('.0') ? fixed.slice(0, -2) : fixed;
};

const formatUpdatedAt = (value) => {
    if (!value) return 'Waiting for new data';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return 'Waiting for new data';
    }

    return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    });
};

const formatImpact = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return '0.000';
    }

    return `${numeric >= 0 ? '+' : '-'}${Math.abs(numeric).toFixed(3)}`;
};

const RecommendationSkeleton = () => (
    <div className="space-y-10">
        <div className="rounded-[28px] border border-slate-200/80 bg-white/90 p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
            <div className="h-4 w-32 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
            <div className="mt-5 h-12 w-3/4 animate-pulse rounded-2xl bg-slate-200 dark:bg-white/10" />
            <div className="mt-4 h-4 w-full animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
            <div className="mt-3 h-4 w-5/6 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {[0, 1, 2].map((index) => (
                <div
                    key={index}
                    className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-sm dark:border-white/5 dark:bg-[#1a1433]"
                >
                    <div className="h-4 w-20 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                    <div className="mt-4 h-10 w-24 animate-pulse rounded-2xl bg-slate-200 dark:bg-white/10" />
                    <div className="mt-4 h-3 w-28 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                </div>
            ))}
        </div>

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
            {[0, 1, 2, 3].map((index) => (
                <div
                    key={index}
                    className="rounded-3xl border border-slate-200/80 bg-white/90 p-6 shadow-sm dark:border-white/5 dark:bg-[#1a1433]"
                >
                    <div className="h-5 w-44 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                    <div className="mt-6 space-y-4">
                        {[0, 1].map((line) => (
                            <div
                                key={line}
                                className="rounded-2xl border border-slate-100 bg-slate-50/70 p-5 dark:border-white/5 dark:bg-white/[0.03]"
                            >
                                <div className="h-4 w-32 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                                <div className="mt-4 h-3 w-full animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                                <div className="mt-3 h-3 w-4/5 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    </div>
);

const PreventiveRecommendations = () => {
    const explanation = useHealthStore((state) => state.explanation);
    const recommendations = useHealthStore((state) => state.recommendations);
    const loading = useHealthStore((state) => state.loading);
    const error = useHealthStore((state) => state.error);
    const metrics = useHealthStore((state) => state.metrics);
    const metricsLoading = useHealthStore((state) => state.metricsLoading);
    const fetchExplanation = useHealthStore((state) => state.fetchExplanation);
    const fetchHealthMetrics = useHealthStore((state) => state.fetchHealthMetrics);

    const fetchDashboardData = useDashboardStore((state) => state.fetchDashboardData);
    const dashboardIsFetching = useDashboardStore((state) => state.isFetching);
    const dashboardUpdatedAt = useDashboardStore((state) => state.dashboardUpdatedAt);
    const dashboardHydrated = useDashboardStore((state) => state.hasHydratedCache);
    const predictionId = useDashboardStore((state) => state.prediction?.data?.prediction_id ?? null);

    const refreshKeyRef = useRef(null);
    const hasExplanationSnapshot = Boolean(explanation);
    const showSkeleton = !hasExplanationSnapshot && (loading || metricsLoading || dashboardIsFetching || !dashboardHydrated);
    const showRefreshOverlay = useSmartFetchOverlay(
        loading || metricsLoading || dashboardIsFetching,
        hasExplanationSnapshot,
        { exitDelayMs: 200 }
    );

    useEffect(() => {
        const silent = hasExplanationSnapshot;
        const loadPage = async () => {
            try {
                await Promise.all([
                    fetchDashboardData({ silent }),
                    fetchHealthMetrics({ silent }),
                    fetchExplanation({ silent, predictionId }),
                ]);
            } catch (loadError) {
                console.error('Failed to load recommendations page:', loadError);
            }
        };

        void loadPage();
    }, [fetchDashboardData, fetchHealthMetrics, fetchExplanation, hasExplanationSnapshot, predictionId]);

    useEffect(() => {
        if (!dashboardUpdatedAt) {
            return;
        }

        const refreshKey = `${predictionId ?? 'latest'}:${dashboardUpdatedAt}`;
        if (refreshKeyRef.current === refreshKey) {
            return;
        }

        refreshKeyRef.current = refreshKey;
        void Promise.all([
            fetchHealthMetrics({ force: true, silent: true }),
            fetchExplanation({ force: true, silent: true, predictionId }),
        ]);
    }, [dashboardUpdatedAt, fetchExplanation, fetchHealthMetrics, predictionId]);

    const groupedRecommendations = useMemo(() => {
        const grouped = recommendations.reduce((acc, recommendation) => {
            const category = CATEGORY_CONFIG[recommendation.category] ? recommendation.category : 'lifestyle';
            if (!acc[category]) {
                acc[category] = [];
            }
            acc[category].push(recommendation);
            return acc;
        }, {});

        return Object.entries(CATEGORY_CONFIG)
            .map(([key, config]) => ({
                key,
                config,
                items: grouped[key] ?? [],
            }))
            .filter((section) => section.items.length > 0);
    }, [recommendations]);

    const metricCards = useMemo(() => metrics?.cards ?? [], [metrics]);
    const factors = useMemo(() => explanation?.factors ?? [], [explanation]);
    const clinicalCards = useMemo(() => explanation?.clinicalCards ?? [], [explanation]);
    const strongestFactorMagnitude = useMemo(
        () => Math.max(...factors.map((factor) => Math.abs(Number(factor.impact) || 0)), 0.001),
        [factors]
    );

    const handleRetry = () => {
        void Promise.all([
            fetchDashboardData({ force: true }),
            fetchHealthMetrics({ force: true }),
            fetchExplanation({ force: true, predictionId }),
        ]);
    };

    if (showSkeleton) {
        return (
            <div className="min-h-screen bg-[#f6f5f8] px-6 py-8 text-[#13082a] dark:bg-[#131022] dark:text-slate-100 lg:px-8">
                <div className="mx-auto max-w-7xl">
                    <RecommendationSkeleton />
                </div>
            </div>
        );
    }

    if (!hasExplanationSnapshot && error) {
        return (
            <div className="min-h-screen bg-[#f6f5f8] px-6 py-8 text-[#13082a] dark:bg-[#131022] dark:text-slate-100 lg:px-8">
                <div className="mx-auto flex max-w-3xl flex-col items-center rounded-[32px] border border-red-200 bg-white p-10 text-center shadow-sm dark:border-red-500/20 dark:bg-[#1a1433]">
                    <div className="flex size-16 items-center justify-center rounded-2xl bg-red-500/10 text-red-500">
                        <AlertTriangle size={28} />
                    </div>
                    <h2 className="mt-6 text-3xl font-black tracking-tight">Unable to load personalized recommendations</h2>
                    <p className="mt-3 max-w-xl text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                        {error}
                    </p>
                    <button
                        onClick={handleRetry}
                        className="mt-8 inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-5 py-3 text-sm font-black uppercase tracking-[0.2em] text-white transition-transform hover:scale-[1.02]"
                    >
                        <RefreshCcw size={16} />
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="relative min-h-screen bg-[#f6f5f8] text-[#13082a] dark:bg-[#131022] dark:text-slate-100">
            {showRefreshOverlay ? <SmartLoadingOverlay label="Refreshing recommendations" /> : null}

            <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
                <div className="space-y-10">
                    <section className="relative overflow-hidden rounded-[32px] border border-white/60 bg-gradient-to-br from-[#13082a] via-[#1a1433] to-[#0f172a] p-8 text-white shadow-2xl shadow-[#13082a]/10 lg:p-10">
                        <div className="relative z-10 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
                            <div className="max-w-4xl">
                                <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.2em] text-white/80">
                                    <Brain size={14} />
                                    Live AI Output
                                </span>
                                <h1 className="mt-5 text-4xl font-black uppercase tracking-tight lg:text-5xl">
                                    Personalized Health Recommendations
                                </h1>
                                <p className="mt-4 max-w-3xl text-base font-medium leading-relaxed text-white/75 lg:text-lg">
                                    {explanation?.summary || 'Personalized recommendations update as new SHAP factors and health metrics arrive.'}
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                                <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">Risk Level</p>
                                    <p className="mt-2 text-xl font-black">{explanation?.riskLevel || 'Pending'}</p>
                                </div>
                                <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">Risk Score</p>
                                    <p className="mt-2 text-xl font-black">
                                        {Number.isFinite(Number(explanation?.riskPercent))
                                            ? `${Number(explanation.riskPercent).toFixed(1)}%`
                                            : '--'}
                                    </p>
                                </div>
                                <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">Last Updated</p>
                                    <p className="mt-2 text-sm font-black uppercase tracking-[0.16em] text-white/85">
                                        {formatUpdatedAt(metrics?.lastUpdated ?? dashboardUpdatedAt)}
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
                                onClick={handleRetry}
                                className="inline-flex items-center gap-2 rounded-2xl bg-amber-500 px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white"
                            >
                                <RefreshCcw size={14} />
                                Retry
                            </button>
                        </div>
                    ) : null}

                    {clinicalCards.length > 0 ? (
                        <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                            {clinicalCards.slice(0, 4).map((card, index) => (
                                <ClinicalInsightCard
                                    key={`${card.condition}-${card.icdCode}-${index}`}
                                    card={card}
                                    fallback={{
                                        summary: explanation?.summary,
                                        recommendations,
                                        sources: explanation?.sources,
                                    }}
                                />
                            ))}
                        </section>
                    ) : null}

                    <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        {metricCards.map((metric) => (
                            <div
                                key={metric.key}
                                className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-white/5 dark:bg-[#1a1433]"
                            >
                                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">
                                    {metric.label}
                                </p>
                                <div className="mt-4 flex items-end gap-2">
                                    <span className="text-3xl font-black text-[#13082a] dark:text-white">
                                        {formatMetricValue(metric)}
                                    </span>
                                    <span className="pb-1 text-sm font-bold text-slate-400 dark:text-slate-500">
                                        {metric.unit || ''}
                                    </span>
                                </div>
                                <p className="mt-4 text-sm font-medium text-slate-500 dark:text-slate-400">
                                    {metric.caption || metric.emptyMessage || 'Waiting for new health data.'}
                                </p>
                            </div>
                        ))}
                    </section>

                    <section className="grid grid-cols-1 gap-8 xl:grid-cols-2">
                        {groupedRecommendations.length > 0 ? (
                            groupedRecommendations.map(({ key, config, items }) => {
                                const Icon = config.icon;
                                return (
                                    <div
                                        key={key}
                                        className={`rounded-[28px] border p-6 shadow-sm ${config.panelClass}`}
                                    >
                                        <div className="mb-6 flex items-center gap-3">
                                            <div className={`flex size-11 items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/5 ${config.iconClass}`}>
                                                <Icon size={22} />
                                            </div>
                                            <h2 className="text-xl font-black uppercase tracking-tight">{config.title}</h2>
                                        </div>

                                        <div className="space-y-4">
                                            {items.map((recommendation) => (
                                                <article
                                                    key={recommendation.id}
                                                    className="rounded-2xl border border-slate-100 bg-slate-50/80 p-5 transition-transform duration-300 hover:-translate-y-1 hover:shadow-lg dark:border-white/5 dark:bg-white/[0.03]"
                                                >
                                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                                        <div>
                                                            <h3 className="text-lg font-black tracking-tight text-[#13082a] dark:text-white">
                                                                {recommendation.title}
                                                            </h3>
                                                            <p className="mt-3 text-sm font-medium leading-relaxed text-slate-600 dark:text-slate-400">
                                                                {recommendation.description}
                                                            </p>
                                                        </div>
                                                        <span
                                                            className={`inline-flex w-fit items-center rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${PRIORITY_STYLES[recommendation.priority] || PRIORITY_STYLES.medium}`}
                                                        >
                                                            {recommendation.priority}
                                                        </span>
                                                    </div>
                                                </article>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })
                        ) : (
                            <div className="xl:col-span-2 rounded-[28px] border border-dashed border-slate-300 bg-white/90 p-10 text-center shadow-sm dark:border-slate-700 dark:bg-[#1a1433]">
                                <div className="mx-auto flex size-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-300">
                                    <Activity size={28} />
                                </div>
                                <h2 className="mt-6 text-2xl font-black tracking-tight">No recommendations yet</h2>
                                <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-500 dark:text-slate-400">
                                    No personalized recommendations available yet. Connect more data sources.
                                </p>
                            </div>
                        )}
                    </section>

                    <section className="rounded-[28px] border border-slate-200/80 bg-white p-8 shadow-sm dark:border-white/5 dark:bg-[#1a1433]">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                            <div>
                                <span className="inline-flex items-center gap-2 rounded-full bg-[#6143f4]/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.2em] text-[#6143f4]">
                                    <Brain size={14} />
                                    SHAP Drivers
                                </span>
                                <h2 className="mt-4 text-2xl font-black tracking-tight">Why the model generated these recommendations</h2>
                                <p className="mt-2 text-sm font-medium text-slate-500 dark:text-slate-400">
                                    These live factors come from the latest explanation payload and update whenever the backend prediction changes.
                                </p>
                            </div>
                        </div>

                        <div className="mt-8 space-y-5">
                            {factors.length > 0 ? (
                                factors.map((factor) => {
                                    const numericImpact = Number(factor.impact) || 0;
                                    const width = `${Math.max(
                                        8,
                                        Math.round((Math.abs(numericImpact) / strongestFactorMagnitude) * 100)
                                    )}%`;
                                    const increasingRisk = numericImpact >= 0;

                                    return (
                                        <div key={`${factor.featureName}-${factor.title}`} className="space-y-2">
                                            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                                                <div>
                                                    <p className="font-black text-[#13082a] dark:text-white">{factor.title}</p>
                                                    {factor.description ? (
                                                        <p className="mt-1 text-sm font-medium text-slate-500 dark:text-slate-400">
                                                            {factor.description}
                                                        </p>
                                                    ) : null}
                                                </div>
                                                <span
                                                    className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${
                                                        increasingRisk
                                                            ? 'bg-red-500/10 text-red-600 dark:bg-red-500/15 dark:text-red-300'
                                                            : 'bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
                                                    }`}
                                                >
                                                    {increasingRisk ? 'Raises Risk' : 'Lowers Risk'}
                                                    {formatImpact(numericImpact)}
                                                </span>
                                            </div>

                                            <div className="relative h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                                                <div
                                                    className={`absolute top-0 h-full rounded-full ${
                                                        increasingRisk ? 'left-0 bg-red-500' : 'right-0 bg-emerald-500'
                                                    }`}
                                                    style={{ width }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 p-6 text-center dark:border-slate-700 dark:bg-white/[0.03]">
                                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                                        SHAP factor data has not arrived yet. The page will refresh automatically once the prediction service publishes a new explanation.
                                    </p>
                                </div>
                            )}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default PreventiveRecommendations;
