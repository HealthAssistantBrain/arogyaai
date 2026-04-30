import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  AlertCircle,
  CalendarDays,
  ClipboardPlus,
  Download,
  FileText,
  History,
  Search,
  Sparkles,
  Stethoscope,
  Watch,
} from 'lucide-react';

import MedicalHistoryPanel from '../components/timeline/MedicalHistoryPanel';
import { useFetchLock } from '../hooks/useFetchLock';
import { getApiUrl } from '../lib/apiBaseUrl';
import { safeFetch } from '../lib/safeApi';
import { useAuthStore } from '../store/authStore';
import { safeArray, safeText } from '../utils/safeData';

const API_BASE_URL = getApiUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
);

const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const parseEventDateValue = (value) => {
  if (!value) return null;

  if (typeof value === 'string' && DATE_ONLY_PATTERN.test(value)) {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day, 12, 0, 0, 0);
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const formatEventDate = (value, variant = 'full') => {
  const parsed = parseEventDateValue(value);
  if (!parsed) return 'Unknown Date';

  const hasExplicitTime = typeof value === 'string' && value.includes('T');
  if (variant === 'compact') {
    return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  if (hasExplicitTime) {
    return parsed.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

const compareTimelineYears = (left, right) => {
  if (left === 'Unknown') return 1;
  if (right === 'Unknown') return -1;
  return Number(left) - Number(right);
};

const getSeverityTone = (value) => {
  const normalized = safeText(value).toLowerCase();

  if (!normalized) {
    return 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300';
  }
  if (
    normalized.includes('critical') ||
    normalized.includes('high') ||
    normalized.includes('9/10') ||
    normalized.includes('10/10')
  ) {
    return 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300';
  }
  if (
    normalized.includes('moderate') ||
    normalized.includes('medium') ||
    normalized.includes('5/10') ||
    normalized.includes('6/10') ||
    normalized.includes('7/10') ||
    normalized.includes('8/10')
  ) {
    return 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300';
  }
  return 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300';
};

const decorateTimelineEvent = (event) => {
  let icon = Activity;
  let iconColor = 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300';
  let dotColor = 'bg-slate-400';

  switch (event.type) {
    case 'Alerts':
      icon = AlertCircle;
      iconColor = 'bg-red-100 text-red-600 dark:bg-red-500/10 dark:text-red-300';
      dotColor = 'bg-red-500';
      break;
    case 'Tests':
      icon = Stethoscope;
      iconColor = 'bg-[#6143f4]/10 text-[#6143f4] dark:bg-[#6143f4]/15 dark:text-[#c1b6ff]';
      dotColor = 'bg-[#6143f4]';
      break;
    case 'Reports':
      icon = FileText;
      iconColor = 'bg-amber-100 text-amber-600 dark:bg-amber-500/10 dark:text-amber-300';
      dotColor = 'bg-amber-500';
      break;
    case 'Clinical History':
      icon = ClipboardPlus;
      iconColor = 'bg-[#009cde]/10 text-[#009cde] dark:bg-[#009cde]/15 dark:text-[#8ad6ff]';
      dotColor = 'bg-[#009cde]';
      break;
    case 'Device':
      icon = Watch;
      iconColor = 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300';
      dotColor = 'bg-slate-400';
      break;
    case 'Vitals':
      icon = Activity;
      iconColor = 'bg-[#009cde]/10 text-[#009cde] dark:bg-[#009cde]/15 dark:text-[#8ad6ff]';
      dotColor = 'bg-[#009cde]';
      break;
    default:
      break;
  }

  const eventDateValue = event.event_date || event.timestamp || null;
  const parsedDate = parseEventDateValue(eventDateValue);
  const severity =
    event.severity ||
    safeArray(event.metrics).find((metric) => safeText(metric?.label).toLowerCase() === 'severity')?.value ||
    null;

  return {
    ...event,
    icon,
    iconColor,
    dotColor,
    event_date: eventDateValue,
    date: formatEventDate(eventDateValue, 'full'),
    compactDate: formatEventDate(eventDateValue, 'compact'),
    yearLabel: parsedDate ? String(parsedDate.getFullYear()) : 'Unknown',
    sortTime: parsedDate?.getTime?.() ?? 0,
    severity,
  };
};

function TimelineDetailCard({ event }) {
  if (!event) return null;

  const possibleConditions = safeArray(event.possible_conditions);
  const recommendations = safeArray(event.recommendations);
  const metrics = safeArray(event.metrics);
  const labData = safeArray(event.labData);
  const summaryLines = safeArray(event.metadata?.summary);
  const detailTone = getSeverityTone(event.severity);

  return (
    <motion.div
      initial={{ opacity: 0, y: 22, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 18, scale: 0.98 }}
      className="mt-8 rounded-[2rem] border border-slate-200/80 bg-white/95 p-6 shadow-[0_28px_80px_-42px_rgba(15,23,42,0.35)] backdrop-blur dark:border-slate-800 dark:bg-[#120d24]/92"
    >
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex items-start gap-4">
          <div className={`flex size-12 items-center justify-center rounded-[1.25rem] shadow-inner ${event.iconColor}`}>
            <event.icon size={22} />
          </div>

          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                {event.type}
              </span>
              {event.severity ? (
                <span className={`rounded-full border px-3 py-1 text-xs font-bold ${detailTone}`}>
                  {event.severity}
                </span>
              ) : null}
            </div>

            <h3 className="mt-4 text-2xl font-black tracking-tight text-slate-950 dark:text-white">{event.title}</h3>
            <p className="mt-2 text-sm font-medium text-slate-500 dark:text-slate-400">
              {event.date}
              <span className="mx-2">•</span>
              {event.source}
            </p>
          </div>
        </div>

        <div className="rounded-[1.4rem] border border-[#6143f4]/10 bg-[linear-gradient(180deg,rgba(97,67,244,0.08),rgba(0,156,222,0.06))] px-4 py-3 dark:border-[#6143f4]/20 dark:bg-[linear-gradient(180deg,rgba(97,67,244,0.12),rgba(15,23,42,0.12))]">
          <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#6143f4]">Selected Event</p>
          <p className="mt-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            {event.type === 'Reports' ? 'Historical report review' : 'Clinical timeline detail'}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <div className="space-y-5">
          <div className="rounded-[1.6rem] border border-slate-200/80 bg-slate-50/80 p-5 dark:border-slate-800 dark:bg-slate-900/45">
            <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Event Summary</p>
            <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{event.description}</p>
          </div>

          {event.insights ? (
            <div className="rounded-[1.6rem] border border-[#6143f4]/10 bg-[#6143f4]/5 p-5 dark:border-[#6143f4]/20 dark:bg-[#6143f4]/10">
              <div className="flex items-center gap-2 text-[#6143f4]">
                <Sparkles size={15} />
                <p className="text-[11px] font-black uppercase tracking-[0.24em]">AI Summary</p>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-200">{event.insights}</p>
            </div>
          ) : summaryLines.length > 1 ? (
            <div className="rounded-[1.6rem] border border-[#6143f4]/10 bg-[#6143f4]/5 p-5 dark:border-[#6143f4]/20 dark:bg-[#6143f4]/10">
              <div className="flex items-center gap-2 text-[#6143f4]">
                <Sparkles size={15} />
                <p className="text-[11px] font-black uppercase tracking-[0.24em]">AI Summary</p>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-200">{summaryLines[1]}</p>
            </div>
          ) : null}

          {possibleConditions.length > 0 ? (
            <div className="rounded-[1.6rem] border border-slate-200/80 bg-white/80 p-5 dark:border-slate-800 dark:bg-slate-950/30">
              <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Possible Conditions</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {possibleConditions.map((condition) => (
                  <span
                    key={`${event.id}:${condition}`}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200"
                  >
                    {condition}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {recommendations.length > 0 ? (
            <div className="rounded-[1.6rem] border border-slate-200/80 bg-white/80 p-5 dark:border-slate-800 dark:bg-slate-950/30">
              <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Recommended Next Steps</p>
              <div className="mt-3 space-y-3">
                {recommendations.map((recommendation) => (
                  <div
                    key={`${event.id}:${recommendation}`}
                    className="rounded-[1.1rem] border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-900/55 dark:text-slate-200"
                  >
                    {recommendation}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="space-y-5">
          {metrics.length > 0 ? (
            <div className="rounded-[1.6rem] border border-slate-200/80 bg-white/85 p-5 dark:border-slate-800 dark:bg-slate-950/35">
              <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Event Details</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {metrics.map((metric) => (
                  <div
                    key={`${event.id}:${metric.label}`}
                    className="rounded-[1.1rem] border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-900/60"
                  >
                    <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{metric.label}</p>
                    <p className={`mt-2 text-sm font-bold ${metric.color || 'text-slate-900 dark:text-white'}`}>
                      {metric.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {labData.length > 0 ? (
            <div className="rounded-[1.6rem] border border-slate-200/80 bg-white/85 p-5 dark:border-slate-800 dark:bg-slate-950/35">
              <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Measurements</p>
              <div className="mt-4 grid gap-3">
                {labData.map((lab) => (
                  <div
                    key={`${event.id}:${lab.label}`}
                    className="rounded-[1.1rem] border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/60"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{lab.label}</p>
                        <p className={`mt-2 text-sm font-bold ${lab.valueColor || 'text-slate-900 dark:text-white'}`}>
                          {lab.value}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${lab.progress ?? 50}%` }}
                        transition={{ duration: 0.9, ease: 'easeOut' }}
                        className={`${lab.color || 'bg-[#6143f4]'} h-full rounded-full`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}

const Timeline = () => {
  const profileLoading = useAuthStore((state) => state.profileLoading);
  const [activeFilter, setActiveFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('timeline');
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { acquireLock, releaseLock } = useFetchLock();
  const timelineScrollRef = useRef(null);
  const eventRefs = useRef({});

  const fetchTimeline = useCallback(async () => {
    const currentToken = useAuthStore.getState().token;
    if (!currentToken) {
      setTimelineEvents([]);
      setSelectedEventId(null);
      setLoading(false);
      return;
    }
    if (!acquireLock('timeline_fetch')) return;

    try {
      setLoading(true);
      const json = await safeFetch(`${API_BASE_URL}/health/timeline`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      });

      const mappedEvents = safeArray(json?.data ?? json).map(decorateTimelineEvent);
      setTimelineEvents(mappedEvents);
      setSelectedEventId(mappedEvents.length > 0 ? mappedEvents[mappedEvents.length - 1].id : null);
      setError(null);
    } catch (fetchError) {
      console.error('fetch timeline error:', fetchError);
      setError(fetchError?.message || 'Unable to load timeline.');
    } finally {
      setLoading(false);
      releaseLock('timeline_fetch');
    }
  }, [acquireLock, releaseLock]);

  useEffect(() => {
    let isMounted = true;

    const run = async () => {
      if (!isMounted) return;
      await fetchTimeline();
    };

    run();

    return () => {
      isMounted = false;
    };
  }, [fetchTimeline]);

  const filters = ['All', 'Reports', 'Tests', 'Symptoms', 'Alerts'];

  const cleanedData = timelineEvents.filter((item) => {
    return !(
      item.source === 'wearable' ||
      item.type === 'steps' ||
      item.type === 'heart_rate' ||
      item.type === 'sleep' ||
      item.type === 'Device' ||
      item.type === 'Vitals'
    );
  });

  const filteredEvents = cleanedData.filter((event) => {
    let matchesFilter = true;

    if (activeFilter !== 'All') {
      if (activeFilter === 'Reports') {
        matchesFilter = event.type === 'Reports' || event.category === 'report';
      } else if (activeFilter === 'Tests') {
        matchesFilter = event.type === 'Tests' || event.category === 'hematology';
      } else if (activeFilter === 'Alerts') {
        matchesFilter = event.type === 'Alerts';
      } else if (activeFilter === 'Symptoms') {
        matchesFilter = event.category === 'symptom' || event.type === 'Clinical History' || event.type === 'Symptom';
      } else {
        matchesFilter = false;
      }
    }

    if (!matchesFilter) return false;
    if (!searchQuery.trim()) return true;

    const query = searchQuery.toLowerCase();
    return [
      event.type,
      event.title,
      event.name,
      event.category,
      event.source,
      event.description,
      event.insights,
      ...(safeArray(event.possible_conditions)),
      ...(safeArray(event.metadata?.summary)),
    ].some((value) => safeText(value).toLowerCase().includes(query));
  });

  const visibleEvents = [...filteredEvents].sort((left, right) => left.sortTime - right.sortTime);

  useEffect(() => {
    if (visibleEvents.length === 0) {
      if (selectedEventId !== null) {
        setSelectedEventId(null);
      }
      return;
    }

    const hasSelectedEvent = visibleEvents.some((event) => event.id === selectedEventId);

    if (!selectedEventId || !hasSelectedEvent) {
      setSelectedEventId(visibleEvents[visibleEvents.length - 1].id);
    }
  }, [selectedEventId, visibleEvents]);

  const groupedEventsMap = {};
  visibleEvents.forEach((event) => {
    const yearKey = event.yearLabel || 'Unknown';
    if (!groupedEventsMap[yearKey]) {
      groupedEventsMap[yearKey] = [];
    }
    groupedEventsMap[yearKey].push(event);
  });

  const groupedEvents = Object.entries(groupedEventsMap)
    .sort(([leftYear], [rightYear]) => compareTimelineYears(leftYear, rightYear))
    .map(([year, events]) => ({ year, events }));

  const selectedEvent =
    visibleEvents.find((event) => event.id === selectedEventId) ?? visibleEvents[visibleEvents.length - 1] ?? null;

  const currentYear = String(new Date().getFullYear());
  const firstVisibleEvent = visibleEvents[0] ?? null;
  const lastVisibleEvent = visibleEvents[visibleEvents.length - 1] ?? null;

  const handleSelectEvent = (id) => {
    setSelectedEventId(id);

    const node = eventRefs.current[id];
    if (!node) return;

    window.requestAnimationFrame(() => {
      node.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    });
  };

  if (profileLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f5f8] text-sm font-bold text-slate-500 dark:bg-[#131022]">
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
          <Activity className="mx-auto mb-4 size-8 text-[#6143f4]" />
        </motion.div>
        <span className="ml-3">Loading Timeline...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f6f5f8_0%,#eef4fb_100%)] font-display text-[#13082a] antialiased dark:bg-[linear-gradient(180deg,#131022_0%,#090612_100%)] dark:text-slate-100">
      <main className="mx-auto max-w-[1480px] p-5 sm:p-8">
        <section className="overflow-hidden rounded-[2.25rem] border border-slate-200/80 bg-white/80 shadow-[0_28px_90px_-44px_rgba(15,23,42,0.4)] backdrop-blur dark:border-slate-800 dark:bg-[#110d21]/88">
          <div className="border-b border-slate-200/80 bg-[radial-gradient(circle_at_top_left,rgba(97,67,244,0.12),transparent_45%),radial-gradient(circle_at_top_right,rgba(0,156,222,0.12),transparent_38%)] px-6 py-7 dark:border-slate-800">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-[#6143f4]/10 bg-[#6143f4]/5 px-3 py-1 text-[10px] font-black uppercase tracking-[0.28em] text-[#6143f4]">
                  <Sparkles size={12} />
                  Longitudinal Record
                </div>
                <h1 className="mt-4 text-4xl font-black tracking-tight text-slate-950 dark:text-white">Health Timeline</h1>
                <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                  Review health events in true clinical order, then switch into intake mode when you want to add new medical history.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                  <CalendarDays size={15} className="text-slate-400" />
                  <span>Year-based Clinical View</span>
                </div>
                <button className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-800 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200">
                  <Download size={15} />
                  <span>Export Summary</span>
                </button>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                {filters.map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setActiveFilter(filter)}
                    className={`rounded-full px-5 py-2 text-sm font-bold whitespace-nowrap transition-all ${
                      activeFilter === filter
                        ? 'bg-slate-950 text-white shadow-xl shadow-slate-950/10 dark:bg-white dark:text-slate-950'
                        : 'border border-slate-200 bg-white text-slate-600 hover:border-[#6143f4]/30 hover:text-[#6143f4] dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300'
                    }`}
                  >
                    {filter === 'All' ? 'All Events' : filter}
                  </button>
                ))}
              </div>

              <div className="relative w-full max-w-md">
                <Search size={16} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search complaints, reports, conditions..."
                  className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm text-slate-700 outline-none transition focus:border-[#6143f4] focus:ring-4 focus:ring-[#6143f4]/10 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-100"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-center">
              <div className="inline-flex items-center rounded-full border border-slate-200/80 bg-white/70 p-1 shadow-sm dark:border-slate-700 dark:bg-slate-900/60">
                {[
                  { key: 'timeline', label: 'Health Timeline' },
                  { key: 'intake', label: 'Add Medical History' },
                ].map((mode) => (
                  <button
                    key={mode.key}
                    type="button"
                    onClick={() => setViewMode(mode.key)}
                    className={`rounded-full px-5 py-2.5 text-sm font-bold transition-all ${
                      viewMode === mode.key
                        ? 'bg-[linear-gradient(135deg,#6143f4_0%,#8f67ff_56%,#009cde_100%)] text-white shadow-[0_16px_34px_-18px_rgba(97,67,244,0.8)]'
                        : 'text-slate-500 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
                    }`}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {viewMode === 'timeline' ? (
              <>
                {error ? (
                  <div className="rounded-[1.6rem] border border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                    {error}
                  </div>
                ) : null}

                {visibleEvents.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-[1.8rem] border border-dashed border-slate-200 bg-slate-50/70 py-20 text-slate-400 dark:border-slate-800 dark:bg-slate-900/35">
                    <History size={48} className="mb-4 opacity-20" />
                    <p className="text-lg font-semibold">
                      {cleanedData.length > 0 && searchQuery ? 'No matching results found' : 'No recent health events'}
                    </p>
                    <p className="mt-2 text-sm">
                      {cleanedData.length > 0 && searchQuery
                        ? 'Try a different search term or clear the filter.'
                        : 'Switch to Add Medical History to begin building a longitudinal record.'}
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
                      <div className="rounded-[1.7rem] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.95),rgba(244,247,252,0.92))] p-5 dark:border-slate-800 dark:bg-[linear-gradient(180deg,rgba(17,13,33,0.92),rgba(11,17,30,0.88))]">
                        <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Timeline Window</p>
                        <div className="mt-3 flex flex-wrap items-center gap-3">
                          <p className="text-xl font-black text-slate-950 dark:text-white">
                            {visibleEvents.length} event{visibleEvents.length === 1 ? '' : 's'}
                          </p>
                          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-bold text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                            {firstVisibleEvent?.date} to {lastVisibleEvent?.date}
                          </span>
                        </div>
                        <p className="mt-3 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                          Scroll across the rail to move year by year through reports, alerts, labs, and structured symptom history.
                        </p>
                      </div>

                      <div className="rounded-[1.7rem] border border-[#6143f4]/10 bg-[linear-gradient(180deg,rgba(97,67,244,0.08),rgba(0,156,222,0.05))] p-5 dark:border-[#6143f4]/20 dark:bg-[linear-gradient(180deg,rgba(97,67,244,0.12),rgba(15,23,42,0.12))]">
                        <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#6143f4]">Current Year</p>
                        <p className="mt-3 text-3xl font-black tracking-tight text-slate-950 dark:text-white">{currentYear}</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                          The current year block is highlighted so the most recent clinical context stays easy to spot.
                        </p>
                      </div>
                    </div>

                    <div className="mt-6 rounded-[2rem] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(248,250,255,0.95),rgba(239,244,252,0.92))] p-4 dark:border-slate-800 dark:bg-[linear-gradient(180deg,rgba(16,13,28,0.92),rgba(10,16,28,0.88))]">
                      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 px-2">
                        <div>
                          <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Horizontal Timeline</p>
                          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                            Events are grouped by year and ordered by their real clinical date.
                          </p>
                        </div>
                        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-bold text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                          Snap scroll enabled
                        </span>
                      </div>

                      <div
                        ref={timelineScrollRef}
                        className="overflow-x-auto pb-4"
                        style={{ scrollBehavior: 'smooth', scrollSnapType: 'x mandatory', scrollbarWidth: 'thin' }}
                      >
                        <div className="relative flex min-w-max items-end gap-8 px-3 pb-10 pt-6">
                          <div className="pointer-events-none absolute bottom-4 left-3 right-3 h-px bg-gradient-to-r from-transparent via-slate-300 to-transparent dark:via-slate-600" />

                          {groupedEvents.map(({ year, events }) => {
                            const isCurrentYear = year === currentYear;

                            return (
                              <motion.section
                                key={year}
                                initial={{ opacity: 0.45, scale: 0.96, y: 18 }}
                                whileInView={{ opacity: 1, scale: 1, y: 0 }}
                                viewport={{ root: timelineScrollRef, amount: 0.35 }}
                                transition={{ duration: 0.45, ease: 'easeOut' }}
                                className={`shrink-0 rounded-[1.8rem] border p-5 ${
                                  isCurrentYear
                                    ? 'border-[#6143f4]/20 bg-[linear-gradient(180deg,rgba(97,67,244,0.1),rgba(255,255,255,0.82))] dark:bg-[linear-gradient(180deg,rgba(97,67,244,0.16),rgba(13,18,31,0.86))]'
                                    : 'border-slate-200/80 bg-white/78 dark:border-slate-800 dark:bg-slate-950/28'
                                }`}
                                style={{
                                  minWidth: `${Math.max(320, events.length * 230)}px`,
                                  scrollSnapAlign: 'center',
                                }}
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <div>
                                    <p className={`text-[11px] font-black uppercase tracking-[0.24em] ${isCurrentYear ? 'text-[#6143f4]' : 'text-slate-400'}`}>
                                      {isCurrentYear ? 'Current Year' : 'Timeline Year'}
                                    </p>
                                    <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950 dark:text-white">{year}</h2>
                                  </div>

                                  <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-bold text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
                                    {events.length} event{events.length === 1 ? '' : 's'}
                                  </span>
                                </div>

                                <div className="mt-8 flex items-end gap-6">
                                  {events.map((event) => {
                                    const isSelected = selectedEvent?.id === event.id;

                                    return (
                                      <motion.button
                                        key={event.id}
                                        ref={(node) => {
                                          if (node) {
                                            eventRefs.current[event.id] = node;
                                          } else {
                                            delete eventRefs.current[event.id];
                                          }
                                        }}
                                        type="button"
                                        onClick={() => handleSelectEvent(event.id)}
                                        initial={{ opacity: 0.55, scale: 0.95 }}
                                        whileInView={{ opacity: 1, scale: 1 }}
                                        viewport={{ root: timelineScrollRef, amount: 0.5 }}
                                        transition={{ duration: 0.35, ease: 'easeOut' }}
                                        className="relative flex w-[210px] shrink-0 flex-col items-center pb-10 text-left"
                                      >
                                        <div
                                          className={`w-full rounded-[1.4rem] border p-4 transition-all duration-300 ${
                                            isSelected
                                              ? 'border-[#6143f4]/20 bg-white shadow-[0_22px_44px_-24px_rgba(97,67,244,0.6)] dark:bg-[#15102a]'
                                              : 'border-slate-200 bg-white/85 hover:-translate-y-1 hover:border-[#6143f4]/20 hover:shadow-[0_18px_36px_-26px_rgba(15,23,42,0.45)] dark:border-slate-800 dark:bg-slate-950/55'
                                          }`}
                                        >
                                          <div className="flex items-start gap-3">
                                            <div className={`flex size-10 items-center justify-center rounded-[1rem] shadow-inner ${event.iconColor}`}>
                                              <event.icon size={18} />
                                            </div>
                                            <div className="min-w-0">
                                              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">{event.type}</p>
                                              <h3 className="mt-1 line-clamp-2 text-sm font-black leading-tight text-slate-900 dark:text-white">
                                                {event.title}
                                              </h3>
                                            </div>
                                          </div>

                                          <p className="mt-3 text-xs font-semibold text-slate-500 dark:text-slate-400">{event.compactDate}</p>
                                          <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                                            {event.description}
                                          </p>
                                        </div>

                                        <div className="pointer-events-none absolute bottom-4 left-1/2 h-6 w-px -translate-x-1/2 bg-slate-300 dark:bg-slate-600" />
                                        <span
                                          className={`pointer-events-none absolute bottom-0 left-1/2 size-5 -translate-x-1/2 rounded-full border-4 border-white ${event.dotColor} transition-all dark:border-[#110d21] ${
                                            isSelected ? 'scale-125 shadow-[0_0_0_8px_rgba(97,67,244,0.14)]' : ''
                                          }`}
                                        />
                                      </motion.button>
                                    );
                                  })}
                                </div>
                              </motion.section>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    <AnimatePresence mode="wait">
                      {selectedEvent ? <TimelineDetailCard key={selectedEvent.id} event={selectedEvent} /> : null}
                    </AnimatePresence>
                  </>
                )}
              </>
            ) : (
              <div className="mx-auto max-w-[880px]">
                <MedicalHistoryPanel onTimelineRefresh={fetchTimeline} />
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
};

export default Timeline;
