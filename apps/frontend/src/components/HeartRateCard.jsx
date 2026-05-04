import { useEffect, useState } from 'react';
import { Activity, RefreshCcw } from 'lucide-react';

import HeartRateChart from './charts/HeartRateChart';
import useHealthStore from '../store/healthStore';
import { safeArray } from '../utils/safeData';

const isToday = (timestamp, now = new Date()) => {
  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) return false;

  return (
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  );
};

const normalizeToTodayTimeline = (data, now = new Date()) => {
  const currentHour = now.getHours();
  const hourlyValues = {};
  const hourlyAnomalies = {};

  safeArray(data).forEach((item) => {
    if (!item?.timestamp) return;

    const timestamp = new Date(item.timestamp);
    const value = Number(item.value);

    if (Number.isNaN(timestamp.getTime()) || !Number.isFinite(value)) return;

    const hour = timestamp.getHours();

    hourlyValues[hour] = value;
    hourlyAnomalies[hour] = Boolean(item.is_anomaly);
  });

  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    value: hour > currentHour ? null : hourlyValues[hour] ?? null,
    is_anomaly: hour <= currentHour && hourlyValues[hour] !== undefined
      ? hourlyAnomalies[hour] || hourlyValues[hour] < 60 || hourlyValues[hour] > 100
      : false,
    isFuture: hour > currentHour,
  }));
};

const HeartRateCard = () => {
  const [now, setNow] = useState(() => new Date());
  const metrics = useHealthStore((s) => s.metrics);
  const loading = useHealthStore((s) => s.metricsLoading);
  const error = useHealthStore((s) => s.metricsError);
  const fetchHealthMetrics = useHealthStore((s) => s.fetchHealthMetrics);

  const heartRateMetric = metrics?.metrics?.heart_rate ?? metrics?.cards?.find((metric) => metric.key === 'heart_rate') ?? null;
  const heartRateData = safeArray(heartRateMetric?.series);
  const todayData = heartRateData.filter((item) => isToday(item?.timestamp, now));
  const latestReading = todayData.length > 0
    ? todayData[todayData.length - 1]
    : (heartRateMetric?.value !== null && heartRateMetric?.value !== undefined
      ? { value: heartRateMetric.value, timestamp: heartRateMetric.lastUpdated }
      : null);
  const chartData = normalizeToTodayTimeline(todayData, now);
  const currentDayKey = now.toDateString();
  const emptyMessage = 'Waiting for sync';

  useEffect(() => {
    const interval = window.setInterval(() => {
      setNow(new Date());
    }, 60_000);

    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const currentTime = new Date();
    const nextMidnight = new Date(currentTime);
    nextMidnight.setHours(24, 0, 0, 0);

    const timeout = window.setTimeout(() => {
      setNow(new Date());
    }, nextMidnight.getTime() - currentTime.getTime());

    return () => window.clearTimeout(timeout);
  }, [currentDayKey]);

  return (
    <section className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-[24px] font-black tracking-tight text-[#13082a] dark:text-white">
            Heart Rate
          </h2>
          <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-slate-500 dark:text-slate-400">
            Live wearable readings from the health metrics pipeline, refreshed automatically for near-real-time monitoring.
          </p>
        </div>

        <button
          onClick={() => void fetchHealthMetrics({ force: true })}
          className="inline-flex items-center gap-2 rounded-xl bg-[#6143f4] px-4 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc]"
        >
          <RefreshCcw size={16} />
          Refresh
        </button>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-5 dark:border-white/10 dark:bg-[#131022]">
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Latest BPM</p>
          <div className="mt-5 flex items-end gap-3">
            <span className="text-[48px] font-black leading-none tracking-tight text-[#13082a] dark:text-white">
              {latestReading?.value ?? '--'}
            </span>
            <span className="mb-1 text-[13px] font-bold uppercase tracking-[0.18em] text-slate-400">BPM</span>
          </div>
          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white bg-white px-4 py-3 dark:border-white/10 dark:bg-white/5">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-rose-500/10 text-rose-500">
              <Activity size={18} />
            </div>
            <div>
              <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-400">Reading time</p>
              <p className="mt-1 text-[14px] font-semibold text-[#13082a] dark:text-white">
                {latestReading?.timestamp ? new Date(latestReading.timestamp).toLocaleString() : 'Waiting for heart rate data'}
              </p>
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] font-medium text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
              {error}
            </div>
          )}

        </div>

        <div className="rounded-[1.5rem] border border-slate-200/70 bg-white p-5 dark:border-white/10 dark:bg-[#131022]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Trend</p>
              <h3 className="mt-2 text-[20px] font-black tracking-tight text-[#13082a] dark:text-white">
                Hourly heart rate
              </h3>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 dark:bg-white/5 dark:text-slate-300">
              24h Window
            </span>
          </div>

          <div className="mt-5 min-h-[220px]">
            {loading ? (
              <div className="flex h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-200 text-[13px] font-semibold text-slate-400 dark:border-white/10 dark:text-slate-500">
                Syncing latest Google Fit heart rate...
              </div>
            ) : (
              <>
                <HeartRateChart data={chartData} height={220} />
                {todayData.length === 0 && (
                  <p className="mt-3 text-center text-[13px] font-semibold text-slate-400 dark:text-slate-500">
                    {error || emptyMessage}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeartRateCard;
