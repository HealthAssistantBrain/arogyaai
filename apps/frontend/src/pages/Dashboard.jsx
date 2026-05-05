import { useCallback, useRef, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion as Motion, AnimatePresence } from 'framer-motion';
import DashboardSkeleton from '../components/skeletons/DashboardSkeleton';
import {
  LayoutDashboard,
  Sparkles,
  Activity,
  History,
  FlaskConical,
  FileText,
  Moon,
  Watch,
  Plus,
  TrendingUp,
  Heart,
  AlertCircle,
  AlertTriangle,
  Info,
  BarChart2,
  Microscope,
  Zap,
  CheckCircle,
  ClipboardList,
} from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { ROUTES } from '../router/routes';
import useDashboardStore from '../store/dashboardStore';
import { useAuthStore } from '../store/authStore';
import useHealthStore from '../store/healthStore';
import HealthSummary from '../components/HealthSummary';
import { fetchConnectedDeviceSummaries, GOOGLE_FIT_PROVIDER } from '../lib/deviceApi';
import { runGoogleFitSyncOnce } from '../lib/googleFitSyncController';
import { getApiRootUrl } from '../lib/apiBaseUrl';
import { safeArray, safeNumber, safeObject, safeText } from '../utils/safeData';
import { useFetchLock } from '../hooks/useFetchLock';
import useDeviceStore from '../store/deviceStore';
import { setGoogleFitConnectionState } from '../lib/googleFitConnectionState';
import FloatingChatbot from '../components/ui/FloatingChatbot';
import AssistantOverlay from '../components/assistant/AssistantOverlay';
import { useAppStore } from '../store/useAppStore';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';
import useGoogleFitAutoSync from '../hooks/useGoogleFitAutoSync';
import MetricGroup from '../components/dashboard/MetricGroup';
import { extractBloodPressureValues, formatBloodPressureReading } from '../lib/healthMetrics';

const DASHBOARD_WS_ROOT = getApiRootUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
)
  .replace(/localhost/g, '127.0.0.1')
  .replace(/^https:/i, 'wss:')
  .replace(/^http:/i, 'ws:');

const TEST_ICON_RULES = [
  { match: ['ecg', 'holter', 'cardio', 'heart'], icon: Heart },
  { match: ['glucose', 'hba1c', 'metabolic'], icon: Zap },
  { match: ['lipid', 'cholesterol'], icon: FlaskConical },
  { match: ['sleep'], icon: Moon },
  { match: ['baseline', 'preventive', 'repeat'], icon: ClipboardList },
];

const getTestIcon = (testName = '') => {
  const normalized = testName.toLowerCase();
  return TEST_ICON_RULES.find((rule) => rule.match.some((token) => normalized.includes(token)))?.icon ?? Microscope;
};

const priorityStyles = {
  high: 'bg-red-500 text-text-primary',
  medium: 'bg-secondary text-white',
  low: 'bg-slate-100 dark:bg-card text-slate-500',
};

const iconStyles = {
  high: 'text-red-500 bg-red-50 dark:bg-red-500/10',
  medium: 'text-secondary bg-secondary/10',
  low: 'text-primary bg-primary/10',
};

const normalizePriority = (priority) => {
  const normalized = String(priority || 'low').toLowerCase();
  return ['high', 'medium', 'low'].includes(normalized) ? normalized : 'low';
};

const metricThemes = {
  bp: {
    accent: '#ef4444',
    chart: '#ef4444',
    tint: 'bg-gradient-to-br from-rose-50/90 via-white/70 to-red-50/70 dark:from-rose-500/10 dark:via-white/[0.04] dark:to-red-500/10',
    gradient: 'bg-gradient-to-br from-rose-100/95 via-white/80 to-pink-100/85 dark:from-rose-500/18 dark:via-white/[0.05] dark:to-pink-500/12',
    glow: 'shadow-[0_18px_70px_rgba(239,68,68,0.22)] ring-1 ring-red-400/30',
  },
  glucose: {
    accent: '#7c3aed',
    chart: '#7c3aed',
    tint: 'bg-gradient-to-br from-violet-50/90 via-white/75 to-fuchsia-50/70 dark:from-violet-500/10 dark:via-white/[0.04] dark:to-fuchsia-500/10',
    gradient: 'bg-gradient-to-br from-violet-100/90 via-white/80 to-fuchsia-100/80 dark:from-violet-500/18 dark:via-white/[0.05] dark:to-fuchsia-500/12',
    glow: 'shadow-[0_18px_70px_rgba(124,58,237,0.2)] ring-1 ring-violet-400/25',
  },
  temp: {
    accent: '#f59e0b',
    chart: '#f59e0b',
    tint: 'bg-gradient-to-br from-amber-50/90 via-white/75 to-orange-50/70 dark:from-amber-500/10 dark:via-white/[0.04] dark:to-orange-500/10',
    gradient: 'bg-gradient-to-br from-amber-100/90 via-white/80 to-orange-100/80 dark:from-amber-500/18 dark:via-white/[0.05] dark:to-orange-500/12',
    glow: 'shadow-[0_18px_70px_rgba(245,158,11,0.2)] ring-1 ring-amber-400/25',
  },
  steps: {
    accent: '#10b981',
    chart: '#10b981',
    tint: 'bg-gradient-to-br from-emerald-50/90 via-white/75 to-lime-50/70 dark:from-emerald-500/10 dark:via-white/[0.04] dark:to-lime-500/10',
    gradient: 'bg-gradient-to-br from-emerald-100/95 via-white/80 to-lime-100/85 dark:from-emerald-500/18 dark:via-white/[0.05] dark:to-lime-500/12',
    glow: 'shadow-[0_18px_70px_rgba(16,185,129,0.2)] ring-1 ring-emerald-400/25',
  },
  heart: {
    accent: '#e11d48',
    chart: '#e11d48',
    tint: 'bg-gradient-to-br from-rose-50/90 via-white/75 to-slate-50/80 dark:from-rose-500/10 dark:via-white/[0.04] dark:to-white/[0.03]',
    gradient: 'bg-gradient-to-br from-rose-100/90 via-white/80 to-slate-100/80 dark:from-rose-500/18 dark:via-white/[0.05] dark:to-white/[0.04]',
    glow: 'shadow-[0_18px_70px_rgba(225,29,72,0.2)] ring-1 ring-rose-400/25',
  },
  oxygen: {
    accent: '#0284c7',
    chart: '#0284c7',
    tint: 'bg-gradient-to-br from-sky-50/90 via-white/75 to-cyan-50/70 dark:from-sky-500/10 dark:via-white/[0.04] dark:to-cyan-500/10',
    gradient: 'bg-gradient-to-br from-sky-100/90 via-white/80 to-cyan-100/80 dark:from-sky-500/18 dark:via-white/[0.05] dark:to-cyan-500/12',
    glow: 'shadow-[0_18px_70px_rgba(2,132,199,0.2)] ring-1 ring-sky-400/25',
  },
  sleep: {
    accent: '#4f46e5',
    chart: '#4f46e5',
    tint: 'bg-gradient-to-br from-indigo-50/90 via-white/75 to-blue-50/70 dark:from-indigo-500/10 dark:via-white/[0.04] dark:to-blue-500/10',
    gradient: 'bg-gradient-to-br from-indigo-100/95 via-white/80 to-blue-100/85 dark:from-indigo-500/18 dark:via-white/[0.05] dark:to-blue-500/12',
    glow: 'shadow-[0_18px_70px_rgba(79,70,229,0.2)] ring-1 ring-indigo-400/25',
  },
  recovery: {
    accent: '#0f766e',
    chart: '#0f766e',
    tint: 'bg-gradient-to-br from-teal-50/90 via-white/75 to-slate-50/80 dark:from-teal-500/10 dark:via-white/[0.04] dark:to-white/[0.03]',
    gradient: 'bg-gradient-to-br from-teal-100/90 via-white/80 to-slate-100/80 dark:from-teal-500/18 dark:via-white/[0.05] dark:to-white/[0.04]',
    glow: 'shadow-[0_18px_70px_rgba(15,118,110,0.2)] ring-1 ring-teal-400/25',
  },
};

const toFiniteNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatMetricNumber = (value, precision = 0) => {
  const parsed = toFiniteNumber(value);
  if (parsed === null) return '--';
  const fixed = parsed.toFixed(precision);
  return fixed.endsWith('.0') ? fixed.slice(0, -2) : fixed;
};

const getMetricStatus = (key, value, raw = {}) => {
  const numeric = toFiniteNumber(value);

  if (key === 'blood_pressure') {
    const systolic = toFiniteNumber(raw.systolic);
    const diastolic = toFiniteNumber(raw.diastolic);
    if (systolic !== null && systolic < 90) return 'low';
    if ((systolic !== null && systolic >= 130) || (diastolic !== null && diastolic >= 80)) return 'high';
    return 'normal';
  }
  if (key === 'glucose') {
    if (numeric === null) return 'normal';
    if (numeric < 70) return 'low';
    if (numeric > 140) return 'high';
    return 'normal';
  }
  if (key === 'temperature') {
    if (numeric === null) return 'normal';
    if (numeric < 36) return 'low';
    if (numeric >= 38) return 'high';
    return 'normal';
  }
  if (key === 'heart_rate' || key === 'rhr') {
    if (numeric === null) return 'normal';
    if (numeric < 55) return 'low';
    if (numeric > 100) return 'high';
    return 'normal';
  }
  if (key === 'spo2') {
    if (numeric === null) return 'normal';
    if (numeric < 94) return 'low';
    return 'normal';
  }
  if (key === 'sleep') {
    if (numeric === null) return 'normal';
    if (numeric < 6) return 'low';
    if (numeric > 10) return 'high';
    return 'normal';
  }
  return 'normal';
};

const getTrend = (series = []) => {
  const values = safeArray(series)
    .map((item) => toFiniteNumber(item?.value ?? item?.systolic))
    .filter((value) => value !== null);

  if (values.length < 2) {
    return { trend: 'flat', trendLabel: 'stable' };
  }

  const delta = values[values.length - 1] - values[0];
  if (Math.abs(delta) < 0.5) {
    return { trend: 'flat', trendLabel: 'stable' };
  }

  return {
    trend: delta > 0 ? 'up' : 'down',
    trendLabel: `${delta > 0 ? '+' : ''}${Math.round(delta)}`,
  };
};

const getMetric = (healthMetrics, key) => safeObject(healthMetrics?.metrics?.[key]);

const formatBloodPressureValue = (bp = {}) => {
  const { systolic, diastolic } = extractBloodPressureValues(bp);
  const displayValue = formatBloodPressureReading(bp);
  console.log('BP FINAL:', { systolic, diastolic, value: displayValue });
  return displayValue;
};

const buildPremiumMetricGroups = (healthMetrics, dashboardData) => {
  const bp = getMetric(healthMetrics, 'blood_pressure');
  const glucose = getMetric(healthMetrics, 'glucose');
  const temperature = getMetric(healthMetrics, 'temperature');
  const steps = getMetric(healthMetrics, 'steps');
  const heartRate = getMetric(healthMetrics, 'heart_rate');
  const spo2 = getMetric(healthMetrics, 'spo2');
  const sleep = getMetric(healthMetrics, 'sleep');
  const rhr = getMetric(healthMetrics, 'rhr');
  const featureSnapshot = safeObject(dashboardData?.prediction?.data?.feature_snapshot);
  const recoveryValue = toFiniteNumber(
    featureSnapshot.hrv ??
    featureSnapshot.avg_hrv ??
    featureSnapshot.recovery_score ??
    featureSnapshot.sleep_efficiency
  );
  const recoveryIsScore = recoveryValue !== null && recoveryValue <= 100 && featureSnapshot.sleep_efficiency !== undefined;
  const stepsValue = toFiniteNumber(steps.value);
  const stepGoal = 10000;
  const stepProgress = stepsValue === null ? 0 : Math.min(100, (stepsValue / stepGoal) * 100);
  const stepSeries = safeArray(steps.series);
  const activeStepDays = stepSeries.slice(-7).map((point) => toFiniteNumber(point?.value) !== null && Number(point.value) > 0);
  const streak = activeStepDays.length === 7 ? activeStepDays : [true, true, true, false, true, true, stepsValue !== null && stepsValue > 0];
  const bpTrend = getTrend(bp.series);
  const stepsTrend = getTrend(steps.series);
  const sleepTrend = getTrend(sleep.series);

  return [
    {
      title: 'Blood / Metabolic',
      hero: {
        key: 'blood_pressure',
        title: 'Blood Pressure',
        value: formatBloodPressureValue(bp),
        unit: 'mmHg',
        status: getMetricStatus('blood_pressure', null, bp),
        trend: bpTrend.trend,
        trendLabel: bpTrend.trendLabel,
        series: safeArray(bp.series),
        Icon: Activity,
        theme: metricThemes.bp,
        mode: 'blood_pressure',
      },
      mini: [
        {
          key: 'glucose',
          title: 'Glucose',
          value: formatMetricNumber(glucose.value, glucose.precision ?? 0),
          unit: glucose.unit ?? 'mg/dL',
          status: getMetricStatus('glucose', glucose.value),
          ...getTrend(glucose.series),
          series: safeArray(glucose.series),
          Icon: Zap,
          theme: metricThemes.glucose,
        },
        {
          key: 'temperature',
          title: 'Body Temperature',
          value: formatMetricNumber(temperature.value, temperature.precision ?? 1),
          unit: temperature.unit === 'celsius' ? '°C' : (temperature.unit ?? '°C'),
          status: getMetricStatus('temperature', temperature.value),
          ...getTrend(temperature.series),
          series: safeArray(temperature.series),
          Icon: FlaskConical,
          theme: metricThemes.temp,
        },
      ],
    },
    {
      title: 'Activity',
      hero: {
        key: 'steps',
        title: 'Steps',
        value: stepsValue === null ? '--' : Math.round(stepsValue).toLocaleString(),
        unit: 'steps',
        status: getMetricStatus('steps', steps.value),
        trend: stepsTrend.trend,
        trendLabel: stepsTrend.trendLabel,
        series: safeArray(steps.series),
        Icon: TrendingUp,
        theme: metricThemes.steps,
        mode: 'steps',
        goal: stepGoal,
        progress: stepProgress,
        streak,
      },
      mini: [
        {
          key: 'heart_rate',
          title: 'Heart Rate',
          value: formatMetricNumber(heartRate.value, heartRate.precision ?? 0),
          unit: heartRate.unit ?? 'BPM',
          status: getMetricStatus('heart_rate', heartRate.value),
          ...getTrend(heartRate.series),
          series: safeArray(heartRate.series),
          Icon: Heart,
          theme: metricThemes.heart,
        },
        {
          key: 'spo2',
          title: 'SpO2',
          value: formatMetricNumber(spo2.value, spo2.precision ?? 1),
          unit: spo2.unit ?? '%',
          status: getMetricStatus('spo2', spo2.value),
          ...getTrend(spo2.series),
          series: safeArray(spo2.series),
          Icon: Watch,
          theme: metricThemes.oxygen,
        },
      ],
    },
    {
      title: 'Recovery',
      hero: {
        key: 'sleep',
        title: 'Sleep',
        value: formatMetricNumber(sleep.value, sleep.precision ?? 1),
        unit: sleep.unit ?? 'hrs',
        status: getMetricStatus('sleep', sleep.value),
        trend: sleepTrend.trend,
        trendLabel: sleepTrend.trendLabel,
        series: safeArray(sleep.series),
        Icon: Moon,
        theme: metricThemes.sleep,
      },
      mini: [
        {
          key: 'rhr',
          title: 'Resting HR',
          value: formatMetricNumber(rhr.value, rhr.precision ?? 0),
          unit: rhr.unit ?? 'BPM',
          status: getMetricStatus('rhr', rhr.value),
          ...getTrend(rhr.series),
          series: safeArray(rhr.series),
          Icon: Heart,
          theme: metricThemes.heart,
        },
        {
          key: 'recovery_hrv',
          title: recoveryIsScore ? 'Recovery' : 'Recovery / HRV',
          value: formatMetricNumber(recoveryValue, recoveryIsScore ? 0 : 1),
          unit: recoveryIsScore ? '%' : 'ms',
          status: recoveryValue !== null && recoveryValue < (recoveryIsScore ? 55 : 35) ? 'low' : 'normal',
          trend: 'flat',
          trendLabel: 'stable',
          series: [],
          Icon: Sparkles,
          theme: metricThemes.recovery,
        },
      ],
    },
  ];
};

const Dashboard = () => {
  const isSyncing = useHealthStore((s) => s.isSyncing);
  const [hasAttemptedDashboardLoad, setHasAttemptedDashboardLoad] = useState(false);
  const { acquireLock, releaseLock } = useFetchLock();
  const syncLockRef = useRef(false);
  const metricsLoadedForUserRef = useRef(null);

  // ── Store ─────────────────────────────────────────────────────────────────
  const { healthScore, alerts,
    isFetching, error, fetchDashboardData } = useDashboardStore();
  const dashboardData = useDashboardStore((s) => s.dashboardData);
  const setDashboardData = useDashboardStore((s) => s.setDashboardData);
  const lastFetchedAt = useDashboardStore((s) => s.lastFetchedAt);
  const cacheOwnerId = useDashboardStore((s) => s.cacheOwnerId);
  const hasHydratedCache = useDashboardStore((s) => s.hasHydratedCache);
  const healthMetrics = useHealthStore((s) => s.metrics);
  const metricsLoading = useHealthStore((s) => s.metricsLoading);
  const fetchHealthMetrics = useHealthStore((s) => s.fetchHealthMetrics);
  const authUser = useAuthStore((s) => s.user);
  const authToken = useAuthStore((s) => s.token || s.accessToken);

  const setDevices = useDeviceStore((s) => s.setDevices);
  const isAssistantOpen = useAppStore((s) => s.isAssistantOpen);
  const closeAssistant = useAppStore((s) => s.closeAssistant);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const isHydratingAuth = useAuthStore((s) => s.isHydratingAuth);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hasAuthUser = !!authUser?.id;
  const authReady = isHydrated && !isHydratingAuth && isAuthenticated && hasAuthUser;
  const authUserId = authUser?.id ?? null;
  useGoogleFitAutoSync({ enabled: authReady });

  const hasDashboardSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
  const shouldBlockOnCacheHydration = !hasHydratedCache && !hasAttemptedDashboardLoad;
  const showSkeleton = !authReady || (!hasDashboardSnapshot && (isFetching || shouldBlockOnCacheHydration));
  const showRefreshOverlay = useSmartFetchOverlay(isFetching, hasDashboardSnapshot, { exitDelayMs: 200 });

  const refreshDashboard = useCallback(async ({ silent = true } = {}) => {
    if (!acquireLock('dashboard_refresh')) return;

    try {
      await fetchDashboardData({ force: true, silent });
    } catch (err) {
      console.error('Refresh dashboard error:', err);
    } finally {
      releaseLock('dashboard_refresh');
    }
  }, [acquireLock, fetchDashboardData, releaseLock]);

  useEffect(() => {
    if (!authReady) return;

    async function fetchDeviceStatus() {
      try {
        const devices = await fetchConnectedDeviceSummaries();
        setDevices(devices);
        const isConnected = Array.isArray(devices) && devices.some(
          (device) => device?.provider === GOOGLE_FIT_PROVIDER && device?.is_connected
        );
        setGoogleFitConnectionState(isConnected);
      } catch (err) {
        console.log('Fetch device status skipped or failed', err);
      }
    }
    fetchDeviceStatus();
  }, [authReady, setDevices]);

  useEffect(() => {
    if (!authReady) return;

    setHasAttemptedDashboardLoad(true);
    void refreshDashboard({ silent: false });
  }, [authReady, refreshDashboard]);

  useEffect(() => {
    if (!authReady) return;

    if (metricsLoadedForUserRef.current === authUserId) return;

    metricsLoadedForUserRef.current = authUserId;
    void fetchHealthMetrics({ force: true, silent: true });
  }, [authReady, authUserId, fetchHealthMetrics]);

  useEffect(() => {
    if (!authReady || !authUserId || !authToken || typeof WebSocket === 'undefined') return undefined;

    const socket = new WebSocket(`${DASHBOARD_WS_ROOT}/ws/dashboard/${authUserId}?token=${encodeURIComponent(authToken)}`);
    const pingTimer = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping');
      }
    }, 25000);

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message?.type === 'dashboard.update' && message?.data) {
          setDashboardData(message.data, { replace: false, source: 'ws' });
          void fetchHealthMetrics({ force: true, silent: true });
        }
      } catch (err) {
        console.warn('Dashboard realtime payload ignored', err);
      }
    };

    return () => {
      window.clearInterval(pingTimer);
      socket.close();
    };
  }, [authReady, authToken, authUserId, fetchHealthMetrics, setDashboardData]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const root = document.documentElement;
    const scrollTarget = document.querySelector('[data-dashboard-scroll]');
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleScroll = () => {
      if (motionQuery.matches) {
        root.style.setProperty('--scroll-offset', '0px');
        return;
      }

      const scrollY = scrollTarget?.scrollTop ?? window.scrollY;
      const offset = Math.min(scrollY * 0.15, 42);
      root.style.setProperty('--scroll-offset', `${offset}px`);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    scrollTarget?.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      scrollTarget?.removeEventListener('scroll', handleScroll);
      root.style.removeProperty('--scroll-offset');
    };
  }, []);

  // ── Sync handler ──────────────────────────────────────────────────────────
  const handleSync = async () => {
    if (syncLockRef.current || isSyncing) return;

    syncLockRef.current = true;
    console.log('SYNC_TRIGGERED');

    try {
      await runGoogleFitSyncOnce({ requireConnected: false });
    } catch (err) {
      console.error('Sync failed', err);
    } finally {
      syncLockRef.current = false;
    }
  };


  // ── Per-module data + status ──────────────────────────────────────────────
  // Each store key is now a slice: { data, status, source, last_updated }
  const hsData = healthScore?.data;
  const alertsData = safeArray(alerts?.data?.alerts);
  const recommendedTests = safeArray(
    dashboardData?.recommended_tests ?? dashboardData?.recommendedTests?.data
  ).map((item) => {
    const raw = safeObject(item);
    const testName = safeText(raw.test_name ?? raw.name ?? raw.title);
    const priority = normalizePriority(raw.priority);
    return {
      testName,
      reason: safeText(raw.reason, 'Recommended from your latest health signals.'),
      priority,
      timeline: safeText(raw.timeline, '1 month'),
      confidence: safeNumber(raw.confidence, 0),
      Icon: getTestIcon(testName),
    };
  }).filter((item) => item.testName);
  const hasDashboardData = hasDashboardSnapshot && Boolean(safeObject(dashboardData) && Object.keys(safeObject(dashboardData)).length > 0);

  // ── Derived display values ────────────────────────────────────────────────
  const score = safeNumber(hsData?.score, 75);
  const scoreLabel = hsData?.label ?? '…';
  const premiumMetricGroups = buildPremiumMetricGroups(healthMetrics, dashboardData);
  const metricsUpdatedAt = healthMetrics?.lastUpdated
    ? new Date(healthMetrics.lastUpdated).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
    : 'Waiting for sync';
  const riskScoreData = [
    { name: 'Score', value: score },
    { name: 'Remaining', value: 100 - score },
  ];

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.05 } }
  };

  const itemVariants = {
    initial: { opacity: 0, scale: 0.98, y: 10 },
    animate: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } }
  };

  if (hasAttemptedDashboardLoad && hasDashboardSnapshot && !isFetching && !error && !hasDashboardData) {
    return (
      <div className="bg-background dark:bg-card font-display text-text-primary dark:text-slate-100 min-h-screen flex items-center justify-center antialiased p-8">
        <div className="w-full max-w-2xl rounded-[2rem] border border-slate-200 bg-white p-8 shadow-xl dark:border-stroke/50 dark:bg-background">
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-primary mb-3">Dashboard Sync</p>
          <h1 className="text-3xl font-black tracking-tight text-text-primary dark:text-text-primary">
            No dashboard data yet
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-500 dark:text-text-muted">
            We did not receive a dashboard bundle for this account. You can retry the fetch or sync your wearable
            data to repopulate the page safely.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => void refreshDashboard({ silent: false })}
              className="rounded-xl bg-primary px-5 py-3 text-xs font-black uppercase tracking-[0.2em] text-white"
            >
              Retry Fetch
            </button>
            <button
              onClick={() => void handleSync()}
              disabled={isSyncing}
              className="rounded-xl bg-slate-100 px-5 py-3 text-xs font-black uppercase tracking-[0.2em] text-slate-700 disabled:cursor-not-allowed disabled:opacity-70 dark:bg-white/5 dark:text-text-secondary"
            >
              {isSyncing ? 'Syncing...' : 'Sync Data'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      {showSkeleton ? (
        <DashboardSkeleton key="skeleton" />
      ) : (
        <Motion.div
          key="dashboard"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="relative isolate overflow-hidden bg-background dark:bg-card font-display text-text-primary dark:text-slate-100 min-h-screen flex antialiased"
        >    
          {showRefreshOverlay ? <SmartLoadingOverlay label="Refreshing dashboard" /> : null}

          <div
            className={`flex-1 min-w-0 transition-[filter,opacity,transform] duration-200 ease-out ${isAssistantOpen ? 'pointer-events-none select-none opacity-30 blur-[1.5px] saturate-75' : ''
              }`}
          >
            {/* Left Sidebar - Matched Stitch */}


            {/* Main Content Area */}
            <main data-dashboard-scroll className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">

              {/* Dashboard Content Container */}
              <Motion.div
                variants={containerVariants}
                initial="initial"
                animate="animate"
                className="p-8 space-y-8 max-w-7xl mx-auto w-full"
              >
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-2">
                  <div>
                    <h2 className="text-3xl font-black text-text-primary dark:text-text-primary tracking-tight">Overview</h2>
                  </div>
                  <button
                    onClick={() => void handleSync()}
                    disabled={isSyncing}
                    className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-xl text-sm font-bold shadow-lg shadow-primary/20 hover:shadow-xl transition-all active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    <Plus size={16} strokeWidth={3} className={isSyncing ? 'animate-spin' : ''} />
                    {isSyncing ? 'Syncing...' : 'Sync Data'}
                  </button>
                </div>
                {/* Error Banner — Added Post-Audit */}
                <AnimatePresence>
                  {error && (
                    <Motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 rounded-r-xl flex items-center gap-4 group"
                    >
                      <AlertCircle className="text-red-500 shrink-0" size={24} />
                      <div className="flex-1 min-w-0">
                        <p className="text-red-900 dark:text-red-200 font-bold text-sm">Dashboard Data Sync Issue</p>
                        <p className="text-red-700 dark:text-red-400/80 text-xs font-medium truncate">{error}</p>
                      </div>
                      <button
                        onClick={() => void refreshDashboard({ silent: true })}
                        className="bg-red-500 text-text-primary px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest hover:bg-red-600 transition-colors"
                      >
                        Retry Now
                      </button>
                    </Motion.div>
                  )}
                </AnimatePresence>

                <Motion.section variants={itemVariants} className="mt-10 mb-10">
                  <div className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/40 p-6 shadow-[0_18px_58px_rgba(15,23,42,0.08)] backdrop-blur-xl dark:border-stroke dark:bg-white/[0.035]">
                    <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent dark:via-white/30" />
                    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.26em] text-primary">
                          Live Health Metrics
                        </p>
                        <h3 className="mt-2 text-[22px] font-black tracking-tight text-text-primary dark:text-text-primary">
                          Premium vitals cockpit
                        </h3>
                      </div>
                      <span className="rounded-full bg-white/75 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 shadow-sm dark:bg-white/10 dark:text-text-secondary">
                        {metricsLoading && !healthMetrics ? 'Syncing' : metricsUpdatedAt}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 gap-8">
                      {premiumMetricGroups.map((group, index) => (
                        <MetricGroup
                          key={group.title}
                          title={group.title}
                          hero={group.hero}
                          mini={group.mini}
                          index={index}
                        />
                      ))}
                    </div>
                  </div>
                </Motion.section>

                {/* Section 3: Secondary Stats Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                  <Motion.div variants={itemVariants} className="bg-white dark:bg-background p-8 rounded-xl shadow-sm border border-slate-100 dark:border-stroke flex flex-col items-center justify-center text-center relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                      <BarChart2 size={120} className="text-primary" />
                    </div>
                    <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-8">Health Risk Score</h3>

                    <div className="relative size-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={riskScoreData}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={88}
                            startAngle={225}
                            endAngle={-45}
                            paddingAngle={0}
                            dataKey="value"
                            stroke="none"
                          >
                            <Cell fill="var(--color-primary)" strokeLinecap="round" />
                            <Cell fill="rgba(0,0,0,0.05)" />
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-5xl font-black text-text-primary dark:text-text-primary leading-none">
                          {Number.isFinite(Number(score)) ? Math.round(Number(score)) : '--'}
                        </span>
                        <span className="text-text-muted font-bold text-sm tracking-tight mt-1">{scoreLabel}</span>
                      </div>
                    </div>

                    <p className="mt-8 text-slate-500 font-medium text-sm">
                      Metrics sync: <span className="font-bold text-primary">{metricsUpdatedAt}</span>
                    </p>
                  </Motion.div>

                  <Motion.div variants={itemVariants}>
                    <HealthSummary />
                  </Motion.div>
                </div>

                {/* Section 4: Critical Alerts & Recommendations */}
                <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-8 items-start pb-12">

                  {/* Alerts Panel — dynamic from backend */}
                  <Motion.div variants={itemVariants} className="bg-white dark:bg-background p-8 rounded-xl shadow-sm border-l-4 border-red-500 border-slate-100 dark:border-stroke relative overflow-hidden group">
                    <div className="flex items-center justify-between mb-8">
                      <h3 className="text-red-500 font-black text-xs uppercase tracking-[0.3em] flex items-center gap-2">
                        <AlertCircle size={16} fill="currentColor" /> Critical Updates
                      </h3>
                      <span className="text-[10px] font-black uppercase tracking-widest text-text-muted">
                        {alertsData.length > 0 ? `${alertsData.length} Active Alert${alertsData.length > 1 ? 's' : ''}` : 'No Active Alerts'}
                      </span>
                    </div>
                    <div className="relative overflow-hidden">
                      <div className="pointer-events-none absolute top-0 left-0 right-0 h-16 bg-gradient-to-b from-white dark:from-slate-900 to-transparent z-10" />
                      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white dark:from-slate-900 to-transparent z-10" />
                      <div
                        className="max-h-[600px] overflow-y-auto pr-2 custom-scrollbar"
                        onScroll={(event) => {
                          if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
                          const offset = Math.min(event.currentTarget.scrollTop * 0.15, 42);
                          document.documentElement.style.setProperty('--scroll-offset', `${offset}px`);
                        }}
                      >
                        <div
                          className="space-y-4 will-change-transform transition-transform duration-300 ease-out"
                          style={{ transform: 'translateY(var(--scroll-offset, 0px))' }}
                        >
                          {alertsData.length === 0 ? (
                            <div className="flex items-center gap-3 text-text-muted text-sm font-medium py-4">
                              <CheckCircle size={18} className="text-green-400" />
                              All health indicators are within normal range.
                            </div>
                          ) : alertsData.map((alert, i) => (
                            <div
                              key={i}
                              className={`alert-fade-up p-5 rounded-xl border flex items-start gap-4 transition-all duration-300 cursor-pointer hover:scale-[1.01] hover:shadow-lg ${alert.severity === 'critical'
                                ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-500/20 hover:bg-red-50/80 hover:shadow-red-900/10'
                                : 'bg-slate-50 dark:bg-card/50 border-slate-100 dark:border-stroke hover:bg-slate-100 hover:shadow-slate-900/10'
                                }`}
                              style={{ animationDelay: `${i * 50}ms` }}
                            >
                              <AlertTriangle className={`mt-0.5 shrink-0 ${alert.severity === 'critical' ? 'text-red-500' : 'text-slate-500'}`} size={20} />
                              <div>
                                <p className={`text-sm font-bold ${alert.severity === 'critical' ? 'text-red-900 dark:text-red-200' : 'text-text-primary dark:text-text-primary'}`}>{alert.title}</p>
                                <p className={`text-xs mt-1 font-medium leading-relaxed ${alert.severity === 'critical' ? 'text-red-700 dark:text-red-400/80' : 'text-slate-500'}`}>{alert.message}</p>
                                {alert.action_label && (
                                  <button className="mt-3 text-xs font-bold underline text-red-600 hover:text-red-700 decoration-2">{alert.action_label}</button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </Motion.div>

                  {/* Recommended Tests - Matched Stitch */}
                  <Motion.div variants={itemVariants} className="sticky top-6 self-start bg-white dark:bg-background p-8 rounded-xl shadow-sm border border-slate-100 dark:border-stroke">
                    <h3 className="text-slate-500 font-bold text-xs uppercase tracking-[0.2em] mb-8">Recommended Tests</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {recommendedTests.length === 0 ? (
                        <div className="md:col-span-2 flex items-center gap-3 rounded-xl border border-dashed border-slate-200 p-4 text-sm font-medium text-text-muted dark:border-stroke dark:text-slate-500">
                          <ClipboardList size={18} />
                          Baseline preventive tests will appear after your next dashboard refresh.
                        </div>
                      ) : recommendedTests.map((test, i) => (
                        <div key={`${test.testName}-${i}`} title={test.reason} className="p-4 border border-slate-100 dark:border-stroke rounded-xl hover:border-primary/30 transition-all cursor-pointer group hover:shadow-lg hover:shadow-black/5 bg-white dark:bg-background">
                          <div className="flex items-center justify-between mb-3">
                            <div className={`${iconStyles[test.priority]} p-2 rounded-lg transition-transform group-hover:scale-110 shadow-sm border border-white dark:border-stroke`}>
                              <test.Icon size={18} />
                            </div>
                            <div className="flex items-center gap-2">
                              <Info size={14} className="text-text-secondary" aria-label={test.reason} />
                              <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-full ${priorityStyles[test.priority]}`}>{test.priority}</span>
                            </div>
                          </div>
                          <p className="text-sm font-bold text-text-primary dark:text-text-primary leading-tight truncate">{test.testName}</p>
                          <p className="text-xs text-slate-500 font-medium mt-1 uppercase tracking-wider">{test.timeline}</p>
                          {test.confidence > 0 ? (
                            <p className="text-[10px] text-text-muted font-black mt-3 uppercase tracking-widest">
                              {Math.round(test.confidence * 100)}% confidence
                            </p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                    <div className="mt-6 rounded-xl border border-slate-100 bg-slate-50/80 p-5 dark:border-stroke dark:bg-white/[0.03]">
                      <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">Why this matters</p>
                      <p className="mt-2 text-sm font-semibold leading-relaxed text-slate-600 dark:text-text-secondary">
                        Recommendations stay pinned beside active alerts so priority follow-ups remain visible while you review changing risk signals.
                      </p>
                    </div>
                  </Motion.div>
                </div>
              </Motion.div>

              <footer className="py-8 px-10 text-center text-text-muted dark:text-slate-600 text-[10px] font-bold uppercase tracking-[0.3em] mt-auto border-t border-slate-100 dark:border-stroke bg-white/40 dark:bg-background/40 backdrop-blur-sm relative z-20">
                © 2024 ArogyaAI Neural Systems • Clinical Grade Intelligence • HIPAA Certified
              </footer>
            </main>
          </div>

          <AnimatePresence mode="wait" initial={false}>
            {isAssistantOpen ? (
              <AssistantOverlay key="assistant-overlay" onClose={closeAssistant} />
            ) : null}
          </AnimatePresence>

          <FloatingChatbot />

          <style dangerouslySetInnerHTML={{
            __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--color-primary)22; border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--color-primary)44; }
        .alert-fade-up {
          animation: alertFadeUp 420ms ease-out both;
        }
        @keyframes alertFadeUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
        </Motion.div>
      )}
    </AnimatePresence>
  );
};

export default Dashboard;
