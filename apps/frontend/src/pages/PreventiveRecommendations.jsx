import { useEffect, useMemo, useRef, useState } from 'react';
import {
    Activity,
    AlertTriangle,
    CalendarCheck,
    ClipboardList,
    HeartPulse,
    Moon,
    RefreshCcw,
    ShieldAlert,
    Stethoscope,
    Utensils,
} from 'lucide-react';
import useHealthStore from '../store/healthStore';
import useDashboardStore from '../store/dashboardStore';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';
import RecommendationSection, { ActionItem, PriorityTag } from '../components/recommendations/RecommendationSection';
import ActionTimeline from '../components/recommendations/ActionTimeline';
import MonitoringCard from '../components/recommendations/MonitoringCard';

const RISK_CLASSES = {
    HIGH: 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/25 dark:bg-red-500/10 dark:text-red-200',
    MEDIUM: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/25 dark:bg-amber-500/10 dark:text-amber-200',
    LOW: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/25 dark:bg-emerald-500/10 dark:text-emerald-200',
};

const formatUpdatedAt = (value) => {
    if (!value) return 'Waiting for data';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Waiting for data';

    return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    });
};

const formatConfidence = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '--';
    return `${Math.round((numeric > 1 ? numeric / 100 : numeric) * 100)}%`;
};

const metricLabel = (metric) => {
    if (!metric) return '--';
    if (typeof metric.value === 'string' && metric.value.trim()) {
        return `${metric.value}${metric.unit ? ` ${metric.unit}` : ''}`;
    }
    const value = Number(metric.value);
    if (!Number.isFinite(value)) return '--';
    const formatted = value.toFixed(Number(metric.precision ?? 0));
    return `${formatted.endsWith('.0') ? formatted.slice(0, -2) : formatted}${metric.unit ? ` ${metric.unit}` : ''}`;
};

const RecommendationSkeleton = () => (
    <div className="space-y-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 dark:border-stroke dark:bg-[#171923]">
            <div className="h-4 w-36 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
            <div className="mt-5 h-10 w-3/4 animate-pulse rounded-xl bg-slate-200 dark:bg-white/10" />
            <div className="mt-4 h-4 w-full animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
            <div className="mt-3 h-4 w-5/6 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
        </div>
        {[0, 1, 2, 3].map((item) => (
            <div key={item} className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-stroke dark:bg-[#171923]">
                <div className="h-5 w-52 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
                <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-white/10" />
                    <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-white/10" />
                </div>
            </div>
        ))}
    </div>
);

const EmptyPlan = ({ error, onRetry }) => (
    <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm dark:border-stroke dark:bg-[#171923]">
        <div className="mx-auto flex size-14 items-center justify-center rounded-xl bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-200">
            <AlertTriangle size={26} />
        </div>
        <h2 className="mt-6 text-2xl font-black tracking-tight text-slate-950 dark:text-text-primary">No prevention plan available yet</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm font-medium leading-relaxed text-slate-600 dark:text-text-muted">
            {error || 'Run a fresh prediction or connect recent wearable and lab data to generate a structured prevention plan.'}
        </p>
        <button
            onClick={onRetry}
            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-background px-5 py-3 text-sm font-black uppercase tracking-[0.14em] text-text-primary transition hover:bg-card dark:bg-white dark:text-slate-950"
        >
            <RefreshCcw size={16} />
            Refresh
        </button>
    </div>
);

const PlanTabs = ({ plans, selectedIndex, onSelect }) => {
    if (plans.length <= 1) return null;

    return (
        <div className="flex gap-2 overflow-x-auto pb-1">
            {plans.map((plan, index) => (
                <button
                    key={`${plan.conditionKey}-${index}`}
                    type="button"
                    onClick={() => onSelect(index)}
                    className={`h-11 shrink-0 rounded-xl border px-4 text-sm font-black transition ${
                        index === selectedIndex
                            ? 'border-slate-950 bg-background text-text-primary dark:border-white dark:bg-white dark:text-slate-950'
                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-stroke dark:bg-white/[0.03] dark:text-text-primary'
                    }`}
                >
                    {plan.condition}
                </button>
            ))}
        </div>
    );
};

const SourceStrip = ({ plan }) => {
    const sources = plan.sources ?? [];
    const generatedFrom = plan.generatedFrom ?? {};
    const dataSources = [
        generatedFrom.ml ? 'ML risk' : null,
        generatedFrom.wearables ? 'Wearables' : null,
        generatedFrom.labs ? 'Labs' : null,
        generatedFrom.symptoms ? 'Symptoms' : null,
    ].filter(Boolean);

    return (
        <div className="flex flex-wrap gap-2">
            {dataSources.map((item) => (
                <span key={item} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-black text-slate-600 dark:border-stroke dark:bg-white/[0.04] dark:text-text-secondary">
                    {item}
                </span>
            ))}
            {sources.slice(0, 3).map((source, index) => (
                <span key={`${source.title}-${index}`} className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-black text-blue-700 dark:border-blue-500/25 dark:bg-blue-500/10 dark:text-blue-200">
                    {source.title || source.source || 'Medical reference'}
                </span>
            ))}
        </div>
    );
};

const PreventiveRecommendations = () => {
    const explanation = useHealthStore((state) => state.explanation);
    const recommendationPlans = useHealthStore((state) => state.recommendationPlans);
    const recommendationPlan = useHealthStore((state) => state.recommendationPlan);
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

    const [selectedPlanIndex, setSelectedPlanIndex] = useState(0);
    const refreshKeyRef = useRef(null);
    const plans = useMemo(
        () => (recommendationPlans?.length ? recommendationPlans : (recommendationPlan ? [recommendationPlan] : [])),
        [recommendationPlan, recommendationPlans]
    );
    const activePlan = plans[Math.min(selectedPlanIndex, Math.max(plans.length - 1, 0))] ?? null;
    const hasPlan = Boolean(activePlan);
    const hasExplanationSnapshot = Boolean(explanation);
    const showSkeleton = !hasExplanationSnapshot && !hasPlan && (loading || metricsLoading || dashboardIsFetching || !dashboardHydrated);
    const showRefreshOverlay = useSmartFetchOverlay(
        loading || metricsLoading || dashboardIsFetching,
        hasExplanationSnapshot || hasPlan,
        { exitDelayMs: 200 }
    );

    useEffect(() => {
        const silent = hasExplanationSnapshot || hasPlan;
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
    }, [fetchDashboardData, fetchHealthMetrics, fetchExplanation, hasExplanationSnapshot, hasPlan, predictionId]);

    useEffect(() => {
        if (!dashboardUpdatedAt) return;

        const refreshKey = `${predictionId ?? 'latest'}:${dashboardUpdatedAt}`;
        if (refreshKeyRef.current === refreshKey) return;

        refreshKeyRef.current = refreshKey;
        void Promise.all([
            fetchHealthMetrics({ force: true, silent: true }),
            fetchExplanation({ force: true, silent: true, predictionId }),
        ]);
    }, [dashboardUpdatedAt, fetchExplanation, fetchHealthMetrics, predictionId]);

    useEffect(() => {
        if (selectedPlanIndex >= plans.length) {
            setSelectedPlanIndex(0);
        }
    }, [plans.length, selectedPlanIndex]);

    const metricCards = useMemo(() => metrics?.cards ?? [], [metrics]);
    const snapshotMetrics = useMemo(() => {
        const wanted = ['steps', 'heart_rate', 'sleep', 'blood_pressure'];
        return wanted
            .map((key) => metricCards.find((metric) => metric.key === key))
            .filter(Boolean)
            .slice(0, 4);
    }, [metricCards]);

    const handleRetry = () => {
        void Promise.all([
            fetchDashboardData({ force: true }),
            fetchHealthMetrics({ force: true }),
            fetchExplanation({ force: true, predictionId }),
        ]);
    };

    if (showSkeleton) {
        return (
            <div className="min-h-screen bg-slate-100 px-6 py-8 text-slate-950 dark:bg-[#10131a] dark:text-slate-100 lg:px-8">
                <div className="mx-auto max-w-7xl">
                    <RecommendationSkeleton />
                </div>
            </div>
        );
    }

    return (
        <div className="relative min-h-screen bg-slate-100 text-slate-950 dark:bg-[#10131a] dark:text-slate-100">
            {showRefreshOverlay ? <SmartLoadingOverlay label="Refreshing prevention plan" /> : null}

            <div className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
                {!hasPlan ? (
                    <EmptyPlan error={error} onRetry={handleRetry} />
                ) : (
                    <div className="space-y-6">
                        <PlanTabs plans={plans} selectedIndex={selectedPlanIndex} onSelect={setSelectedPlanIndex} />

                        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-stroke dark:bg-[#171923] lg:p-8">
                            <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                                <div className="max-w-4xl">
                                    <div className="flex flex-wrap items-center gap-3">
                                        <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-black uppercase tracking-[0.14em] text-slate-600 dark:border-stroke dark:bg-white/[0.04] dark:text-text-secondary">
                                            <HeartPulse size={14} />
                                            Prevention plan
                                        </span>
                                        <span className={`rounded-full border px-3 py-1.5 text-xs font-black uppercase tracking-[0.14em] ${RISK_CLASSES[activePlan.riskLevel] || RISK_CLASSES.MEDIUM}`}>
                                            {activePlan.riskLevel} risk
                                        </span>
                                        {activePlan.badgeLabel ? (
                                            <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-black uppercase tracking-[0.14em] text-sky-700 dark:border-sky-500/25 dark:bg-sky-500/10 dark:text-sky-200">
                                                {activePlan.badgeLabel}
                                            </span>
                                        ) : null}
                                        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-black uppercase tracking-[0.14em] text-slate-600 dark:border-stroke dark:bg-white/[0.04] dark:text-text-secondary">
                                            Confidence {formatConfidence(activePlan.confidence)}
                                        </span>
                                    </div>
                                    <h1 className="mt-5 text-3xl font-black tracking-tight text-slate-950 dark:text-text-primary lg:text-5xl">
                                        {activePlan.condition}
                                    </h1>
                                    <p className="mt-4 max-w-3xl text-base font-semibold leading-relaxed text-slate-600 dark:text-text-secondary">
                                        {activePlan.summary}
                                    </p>
                                </div>

                                <div className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-4 xl:w-[420px] xl:grid-cols-2">
                                    {snapshotMetrics.map((metric) => (
                                        <div key={metric.key} className="min-h-[92px] rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-white/[0.03]">
                                            <p className="truncate text-[10px] font-black uppercase tracking-[0.14em] text-slate-500 dark:text-text-muted">{metric.label}</p>
                                            <p className="mt-3 text-lg font-black text-slate-950 dark:text-text-primary">{metricLabel(metric)}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="mt-6 flex flex-col gap-4 border-t border-slate-200 pt-5 dark:border-stroke lg:flex-row lg:items-center lg:justify-between">
                                <SourceStrip plan={activePlan} />
                                <p className="text-xs font-black uppercase tracking-[0.14em] text-text-muted">
                                    Updated {formatUpdatedAt(metrics?.lastUpdated ?? dashboardUpdatedAt)}
                                </p>
                            </div>
                        </section>

                        {error ? (
                            <div className="flex flex-col gap-4 rounded-2xl border border-amber-300/70 bg-amber-50 p-5 text-sm font-semibold text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-100 sm:flex-row sm:items-center sm:justify-between">
                                <div className="flex items-start gap-3">
                                    <AlertTriangle className="mt-0.5 shrink-0" size={18} />
                                    <p>{error}</p>
                                </div>
                                <button
                                    onClick={handleRetry}
                                    className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-amber-500 px-4 text-xs font-black uppercase tracking-[0.14em] text-text-primary"
                                >
                                    <RefreshCcw size={14} />
                                    Retry
                                </button>
                            </div>
                        ) : null}

                        <RecommendationSection title="Immediate precautions" icon={ShieldAlert} tone="red">
                            <ul className="space-y-3">
                                {activePlan.precautions.map((item) => (
                                    <ActionItem key={item.id} item={item} />
                                ))}
                            </ul>
                        </RecommendationSection>

                        <RecommendationSection title="Lifestyle plan" icon={Utensils} tone="emerald">
                            <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                                {[
                                    ['Diet', activePlan.lifestyle.diet, Utensils],
                                    ['Activity', activePlan.lifestyle.activity, Activity],
                                    ['Sleep', activePlan.lifestyle.sleep, Moon],
                                ].map(([title, items, Icon]) => (
                                    <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
                                        <div className="flex items-center gap-3">
                                            <span className="flex size-10 items-center justify-center rounded-xl bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-100">
                                                <Icon size={20} />
                                            </span>
                                            <h3 className="text-base font-black text-slate-950 dark:text-text-primary">{title}</h3>
                                        </div>
                                        <ul className="mt-5 space-y-3">
                                            {items.map((item) => (
                                                <ActionItem key={item.id} item={item} />
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        </RecommendationSection>

                        <RecommendationSection title="Clinical actions" icon={Stethoscope} tone="blue">
                            <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                                <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
                                    <div className="flex items-center gap-3">
                                        <ClipboardList size={20} />
                                        <h3 className="text-base font-black text-slate-950 dark:text-text-primary">Tests</h3>
                                    </div>
                                    <ul className="mt-5 space-y-3">
                                        {activePlan.clinicalActions.tests.map((item) => (
                                            <ActionItem key={item.id} item={item} />
                                        ))}
                                    </ul>
                                </div>

                                <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
                                    <div className="flex items-center gap-3">
                                        <CalendarCheck size={20} />
                                        <h3 className="text-base font-black text-slate-950 dark:text-text-primary">Doctor advice</h3>
                                    </div>
                                    <div className="mt-5">
                                        {activePlan.clinicalActions.doctorVisit ? (
                                            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/20">
                                                <div className="mb-3">
                                                    <PriorityTag priority={activePlan.clinicalActions.doctorVisit.priority} />
                                                </div>
                                                <p className="text-sm font-semibold leading-relaxed text-slate-800 dark:text-slate-100">
                                                    {activePlan.clinicalActions.doctorVisit.text}
                                                </p>
                                            </div>
                                        ) : null}
                                    </div>
                                </div>

                                <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-stroke dark:bg-white/[0.04]">
                                    <div className="flex items-center gap-3">
                                        <ShieldAlert size={20} />
                                        <h3 className="text-base font-black text-slate-950 dark:text-text-primary">Warning signs</h3>
                                    </div>
                                    <ul className="mt-5 space-y-3">
                                        {activePlan.clinicalActions.warningSigns.map((item) => (
                                            <ActionItem key={item.id} item={item} />
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </RecommendationSection>

                        <RecommendationSection title="Action plan" icon={CalendarCheck} tone="amber">
                            <ActionTimeline daily={activePlan.actionPlan.daily} weekly={activePlan.actionPlan.weekly} />
                        </RecommendationSection>

                        <RecommendationSection title="Monitoring" icon={HeartPulse} tone="slate">
                            <MonitoringCard monitoring={activePlan.monitoring} />
                        </RecommendationSection>

                        {activePlan.clinicalBasis || activePlan.generatedFrom?.topDrivers?.length ? (
                            <RecommendationSection title="Why these actions" icon={ClipboardList} tone="blue" defaultOpen={false}>
                                {activePlan.clinicalBasis ? (
                                    <p className="text-sm font-semibold leading-relaxed text-slate-700 dark:text-text-secondary">
                                        {activePlan.clinicalBasis}
                                    </p>
                                ) : null}
                                {activePlan.generatedFrom?.topDrivers?.length ? (
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        {activePlan.generatedFrom.topDrivers.map((driver) => (
                                            <span key={driver} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-black text-slate-600 dark:border-stroke dark:bg-white/[0.04] dark:text-text-secondary">
                                                {driver}
                                            </span>
                                        ))}
                                    </div>
                                ) : null}
                            </RecommendationSection>
                        ) : null}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PreventiveRecommendations;

