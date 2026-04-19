import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  Footprints,
  TrendingUp,
  CalendarDays,
  Flame,
  Link2,
  Unplug,
  Bug,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

import { ROUTES } from '../router/routes';
import {
  disconnectGoogleFit,
  fetchGoogleFitStatus,
  startGoogleFitConnect,
  syncGoogleFit,
} from '../lib/googleFitApi';
import { refreshAfterGoogleFitSync } from '../lib/googleFitRefresh';

const DEFAULT_TIMEZONE = import.meta.env.VITE_GOOGLE_FIT_DEFAULT_TIMEZONE || 'Asia/Kolkata';
const DEFAULT_WINDOW_DAYS = 30;

function formatNumber(value) {
  if (value === null || value === undefined || value === '') {
    return '--';
  }
  return new Intl.NumberFormat('en-IN').format(Number(value));
}

function formatDate(value, timezone = DEFAULT_TIMEZONE) {
  if (!value) return 'No data';
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: timezone,
  }).format(new Date(value));
}

function formatLocalDay(value) {
  if (!value) return 'No data';
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`));
}

function extractApiError(error, fallback) {
  return error?.response?.data?.error || error?.response?.data?.detail || error?.message || fallback;
}

function StatCard({ label, value, helper, icon: Icon, accent }) {
  return (
    <div className="rounded-3xl border border-slate-200/70 dark:border-white/10 bg-white dark:bg-white/[0.03] p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 mb-2">{label}</p>
          <p className="text-[26px] font-black tracking-tight text-[#13082a] dark:text-white">{value}</p>
          <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">{helper}</p>
        </div>
        <div
          className="flex h-12 w-12 items-center justify-center rounded-2xl border"
          style={{ backgroundColor: `${accent}12`, borderColor: `${accent}30`, color: accent }}
        >
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}

const GoogleFitSettings = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [timezone, setTimezone] = useState(DEFAULT_TIMEZONE);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  async function loadStatus(nextTimezone = timezone, { silent = false } = {}) {
    if (!silent) {
      setIsLoading(true);
    }
    setError('');

    try {
      const response = await fetchGoogleFitStatus(nextTimezone);
      setData(response);
      if (response?.timezone) {
        setTimezone(response.timezone);
      }
    } catch (apiError) {
      setError(extractApiError(apiError, 'Unable to load Google Fit status right now.'));
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }

  async function handleSync(showSuccessMessage = true) {
    setIsSyncing(true);
    setError('');

    try {
      const response = await syncGoogleFit({ timezone, days: DEFAULT_WINDOW_DAYS });
      await Promise.all([
        loadStatus(timezone, { silent: true }),
        refreshAfterGoogleFitSync(),
      ]);
      if (showSuccessMessage) {
        const missing = Array.isArray(response?.missing) ? response.missing : [];
        const hasStepData = Array.isArray(response?.stats?.daily_steps) && response.stats.daily_steps.some((item) => Number(item?.steps || 0) >= 0);
        const missingMessage = missing.length > 0 && !hasStepData ? ` Missing: ${missing.join(', ')}.` : '';
        setNotice((response?.message || `Google Fit steps synced for the last ${DEFAULT_WINDOW_DAYS} local days.`) + missingMessage);
      }
    } catch (apiError) {
      setError(extractApiError(apiError, 'Google Fit sync failed.'));
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleConnect() {
    setIsConnecting(true);
    setError('');

    try {
      const response = await startGoogleFitConnect({
        timezone,
        redirectPath: ROUTES.GOOGLE_FIT_SETTINGS,
      });
      window.location.assign(response.auth_url);
    } catch (apiError) {
      setIsConnecting(false);
      setError(extractApiError(apiError, 'Unable to start Google Fit connection.'));
    }
  }

  async function handleDisconnect() {
    setIsDisconnecting(true);
    setError('');

    try {
      await disconnectGoogleFit();
      setData({
        connected: false,
        timezone,
        last_synced_at: null,
        stats: {
          daily_steps: [],
          total_steps: 0,
          average_daily_steps: 0,
          average_steps_on_active_days: 0,
          best_day: null,
          latest_day: null,
          active_day_count: 0,
        },
        raw_json: null,
        google_email: null,
      });
      setNotice('Google Fit disconnected. Existing cached summaries stay available only until the next refresh.');
    } catch (apiError) {
      setError(extractApiError(apiError, 'Unable to disconnect Google Fit.'));
    } finally {
      setIsDisconnecting(false);
    }
  }

  useEffect(() => {
    loadStatus(DEFAULT_TIMEZONE);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const oauthState = searchParams.get('googleFit');
    const message = searchParams.get('message');

    if (!oauthState && !message) {
      return;
    }

    if (oauthState === 'connected') {
      setNotice('Google account connected. Pulling your latest Google Fit steps now.');
      (async () => {
        try {
          await loadStatus(timezone, { silent: true });
          await handleSync(false);
          navigate(ROUTES.DEVICES, { replace: true });
        } catch (syncError) {
          setError(extractApiError(syncError, 'Google Fit sync failed after connection.'));
        }
      })();
    } else if (oauthState === 'error') {
      setError(message || 'Google Fit connection failed.');
    } else if (message) {
      setNotice(message);
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('googleFit');
    nextParams.delete('message');
    setSearchParams(nextParams, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, setSearchParams]);

  const stats = data?.stats || {
    daily_steps: [],
    total_steps: 0,
    average_daily_steps: 0,
    average_steps_on_active_days: 0,
    best_day: null,
    latest_day: null,
    active_day_count: 0,
  };

  return (
    <div className="min-h-screen bg-[#f6f5f8] text-[#13082a] dark:bg-[#0B0819] dark:text-slate-100">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-8 md:px-10">
        

        {(notice || error) && (
          <div
            className={`rounded-2xl border px-4 py-3 text-[13px] font-medium ${
              error
                ? 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300'
            }`}
          >
            {error || notice}
          </div>
        )}

        <section className="grid gap-4 lg:grid-cols-[1.45fr_0.95fr]">
          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Actions</p>
                <h2 className="mt-2 text-[22px] font-black tracking-tight text-[#13082a] dark:text-white">
                  Sync and manage Google Fit
                </h2>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleConnect}
                  disabled={isConnecting}
                  className="inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc] disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Link2 size={16} />
                  {data?.connected ? 'Reconnect Google' : isConnecting ? 'Opening Google...' : 'Connect Google'}
                </button>
                <button
                  onClick={() => handleSync(true)}
                  disabled={!data?.connected || isSyncing}
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-[#13082a] transition hover:border-[#6143f4]/30 hover:text-[#6143f4] disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-white"
                >
                  <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} />
                  {isSyncing ? 'Syncing Steps...' : 'Sync 30 Days'}
                </button>
                <button
                  onClick={handleDisconnect}
                  disabled={!data?.connected || isDisconnecting}
                  className="inline-flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
                >
                  <Unplug size={16} />
                  {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
                </button>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <StatCard
                label="Daily Steps"
                value={formatNumber(stats.latest_day?.steps ?? null)}
                helper={`Latest local day: ${stats.latest_day?.date ? formatLocalDay(stats.latest_day.date) : 'No sync yet'}`}
                icon={Footprints}
                accent="#22c55e"
              />
              <StatCard
                label="Total Steps"
                value={formatNumber(stats.total_steps ?? null)}
                helper={`Total across the last ${DEFAULT_WINDOW_DAYS} local days`}
                icon={TrendingUp}
                accent="#6143f4"
              />
              <StatCard
                label="Average Daily"
                value={formatNumber(stats.average_daily_steps ?? null)}
                helper="Average across every bucket in the synced window"
                icon={CalendarDays}
                accent="#009cde"
              />
              <StatCard
                label="Active-Day Average"
                value={formatNumber(stats.average_steps_on_active_days ?? null)}
                helper={`${formatNumber(stats.active_day_count)} days had more than 0 recorded steps`}
                icon={Flame}
                accent="#f97316"
              />
              <StatCard
                label="Best Day"
                value={formatNumber(stats.best_day?.steps ?? null)}
                helper={stats.best_day?.date ? formatLocalDay(stats.best_day.date) : 'No synced history yet'}
                icon={TrendingUp}
                accent="#eab308"
              />
              <StatCard
                label="Latest Day"
                value={formatNumber(stats.latest_day?.steps ?? null)}
                helper={stats.latest_day?.date ? formatLocalDay(stats.latest_day.date) : 'No synced history yet'}
                icon={CalendarDays}
                accent="#14b8a6"
              />
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Implementation notes</p>
            <ul className="mt-4 space-y-3 text-[13px] leading-relaxed text-slate-600 dark:text-slate-400">
              <li>The server handles OAuth code exchange and token refresh so Google secrets stay server-side.</li>
              <li>Daily buckets are generated from local-midnight boundaries using your configured timezone.</li>
              <li>Fetched daily steps are cached in the existing wearable data model, tied to the Google Fit device record.</li>
              <li>The raw Google aggregate response is preserved for debugging in the panel below.</li>
            </ul>

            <div className="mt-6 rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-4 dark:border-white/10 dark:bg-[#131022]">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 text-amber-500" size={18} />
                <div>
                  <p className="text-[12px] font-black uppercase tracking-[0.14em] text-[#13082a] dark:text-white">
                    Google Fit status
                  </p>
                  <p className="mt-2 text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">
                    Google Fit APIs are being deprecated by Google in favor of Health Connect. This integration keeps
                    your current flow working, but future migration planning is recommended.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Daily buckets</p>
                <h2 className="mt-2 text-[22px] font-black tracking-tight text-[#13082a] dark:text-white">
                  Last {DEFAULT_WINDOW_DAYS} local days
                </h2>
              </div>
              {isLoading && <RefreshCw className="animate-spin text-slate-400" size={18} />}
            </div>

            <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-slate-200/70 dark:border-white/10">
              <div className="grid grid-cols-[1.2fr_0.8fr] bg-slate-50 px-4 py-3 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400 dark:bg-white/5">
                <span>Date</span>
                <span className="text-right">Steps</span>
              </div>
              {stats.daily_steps.length > 0 ? (
                <div className="max-h-[420px] overflow-y-auto">
                  {stats.daily_steps
                    .slice()
                    .reverse()
                    .map((item) => (
                      <div
                        key={item.date}
                        className="grid grid-cols-[1.2fr_0.8fr] border-t border-slate-100 px-4 py-3 text-[13px] dark:border-white/5"
                      >
                        <span className="font-semibold text-[#13082a] dark:text-white">{formatLocalDay(item.date)}</span>
                        <span className="text-right font-black text-[#6143f4]">{formatNumber(item.steps)}</span>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="flex min-h-[220px] flex-col items-center justify-center px-6 py-10 text-center">
                  <Footprints size={28} className="text-slate-300 dark:text-slate-600" />
                  <p className="mt-4 text-[14px] font-semibold text-slate-500 dark:text-slate-400">
                    Connect Google Fit and run a sync to populate local daily step buckets.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-[#6143f4] dark:border-white/10 dark:bg-white/5">
                <Bug size={20} />
              </div>
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Developer Debug</p>
                <h2 className="mt-1 text-[22px] font-black tracking-tight text-[#13082a] dark:text-white">
                  Raw aggregate response
                </h2>
              </div>
            </div>

            <details className="mt-5 rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-4 dark:border-white/10 dark:bg-[#131022]" open={Boolean(data?.raw_json)}>
              <summary className="cursor-pointer list-none text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">
                {data?.raw_json ? 'Show cached Google Fit JSON' : 'No raw JSON cached yet'}
              </summary>
              <pre className="mt-4 max-h-[460px] overflow-auto rounded-2xl bg-[#13082a] p-4 text-[11px] leading-relaxed text-slate-100">
                {JSON.stringify(data?.raw_json || { message: 'Connect and sync Google Fit to inspect the raw payload.' }, null, 2)}
              </pre>
            </details>
          </div>
        </section>
      </main>
    </div>
  );
};

export default GoogleFitSettings;
