import { Heart, Activity, Link2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import HeartRateChart from './charts/HeartRateChart';
import { ROUTES } from '../router/routes';
import useDashboardStore from '../store/dashboardStore';
import { safeArray } from '../utils/safeData';

const HeartRateCard = () => {
  const navigate = useNavigate();
  const heartRateSlice = useDashboardStore((s) => s.vitals?.['heart_rate:24h']);
  const googleFitSlice = useDashboardStore((s) => s.googleFit);


  const heartRateData = safeArray(heartRateSlice?.data);
  const loading = heartRateSlice?.status === 'processing';
  const error = heartRateSlice?.error ?? null;
  const message = heartRateSlice?.message ?? null;
  const connected = Boolean(googleFitSlice?.data?.connected);
  const heartRateAvailable = googleFitSlice?.data?.data_availability?.heart_rate;
  const missingScopes = Array.isArray(googleFitSlice?.data?.missing_scopes) ? googleFitSlice.data.missing_scopes : [];
  const latestReading = heartRateData.length > 0 ? heartRateData[heartRateData.length - 1] : null;
  const chartData = heartRateData.map((item) => ({
    t: new Date(item.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
    v: item.value,
  }));
  const emptyMessage = connected && heartRateAvailable === false
    ? missingScopes.includes('heart_rate')
      ? 'Heart rate permission is missing. Reconnect Google Fit to grant access.'
      : 'Heart rate data not available.'
    : 'No data yet. Connect your device or wait for sync.';

  return (
    <section className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-[24px] font-black tracking-tight text-[#13082a] dark:text-white">
            Heart  Rate
          </h2>
          <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-slate-500 dark:text-slate-400">
            Hourly heart rate buckets are fetched from Google Fit, normalized by the backend, and stored in PostgreSQL before rendering here.
          </p>
        </div>

        {!connected && (
          <button
            onClick={() => navigate(ROUTES.GOOGLE_FIT_SETTINGS)}
            className="inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-4 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc]"
          >
            <Link2 size={16} />
            Connect Google Fit
          </button>
        )}
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

          {!error && message && (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] font-medium text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
              {message}
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
            ) : chartData.length > 0 ? (
              <HeartRateChart data={chartData} height={220} />
            ) : (
              <div className="flex h-[220px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 px-6 text-center dark:border-white/10">
                <Heart size={26} className="text-slate-300 dark:text-slate-600" />
                <p className="mt-4 text-[14px] font-semibold text-slate-500 dark:text-slate-400">
                  No data yet
                </p>
                <p className="mt-2 text-[13px] leading-relaxed text-slate-400 dark:text-slate-500">
                  {error || emptyMessage}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeartRateCard;
