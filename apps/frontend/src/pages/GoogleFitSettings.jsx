import React, { useEffect, useRef, useState } from 'react';
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
} from '../lib/googleFitApi';
import { runGoogleFitSyncOnce } from '../lib/googleFitSyncController';
import { setGoogleFitConnectionState } from '../lib/googleFitConnectionState';

const DEFAULT_TIMEZONE = import.meta.env.VITE_GOOGLE_FIT_DEFAULT_TIMEZONE || 'Asia/Kolkata';
const DEFAULT_WINDOW_DAYS = 7;

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

function isTimeoutError(error) {
  return error?.code === 'ECONNABORTED' || String(error?.message || '').toLowerCase().includes('timeout');
}

function extractSyncError(error) {
  if (isTimeoutError(error)) {
    return 'Sync is taking longer than expected. Please wait or retry.';
  }

  return extractApiError(error, 'Google Fit sync failed.');
}

function availabilityText(isAvailable, isMissingScope) {
  if (isAvailable) return 'Available';
  if (isMissingScope) return 'Permission missing';
  return 'Not available';
}

function StatCard({ label, value, helper, icon: Icon, accent }) {
  return (
    <div className="rounded-3xl border border-slate-200/70 dark:border-stroke bg-white dark:bg-white/[0.03] p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.2em] text-text-muted mb-2">{label}</p>
          <p className="text-[26px] font-black tracking-tight text-text-primary dark:text-text-primary">{value}</p>
          <p className="text-[12px] text-slate-500 dark:text-text-muted mt-2 leading-relaxed">{helper}</p>
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
  const oauthHandledRef = useRef(false);

  async function loadStatus(nextTimezone = timezone, { silent = false } = {}) {
    if (!silent) {
      setIsLoading(true);
    }
    setError('');

    try {
      const response = await fetchGoogleFitStatus(nextTimezone);
      setData(response);
      setGoogleFitConnectionState(Boolean(response?.connected));
      if (response?.timezone) {
        setTimezone(response.timezone);
      }
    } catch (apiError) {
      setGoogleFitConnectionState(false);
      setError(extractApiError(apiError, 'Unable to load Google Fit status right now.'));
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }

  async function handleSync(showSuccessMessage = true) {
    setIsSyncing(true);
    setIsLoading(true);
    setNotice('');
    setError('');

    try {
      const response = await runGoogleFitSyncOnce({
        timezone,
        days: DEFAULT_WINDOW_DAYS,
        requireConnected: false,
      });
      await Promise.all([
        loadStatus(timezone, { silent: true }),
      ]);
      if (showSuccessMessage) {
        const missing = Array.isArray(response?.missing) ? response.missing : [];
        const hasStepData = Array.isArray(response?.stats?.daily_steps) && response.stats.daily_steps.some((item) => Number(item?.steps || 0) >= 0);
        const missingMessage = missing.length > 0 && !hasStepData ? ` Missing: ${missing.join(', ')}.` : '';
        setNotice((response?.message || `Google Fit steps synced for the last ${DEFAULT_WINDOW_DAYS} local days.`) + missingMessage);
      }
    } catch (apiError) {
      setError(extractSyncError(apiError));
    } finally {
      setIsSyncing(false);
      setIsLoading(false);
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
      setGoogleFitConnectionState(false);
      setData({
        connected: false,
        timezone,
        last_synced_at: null,
        stats: {
          daily_steps: [],
          total_steps: 0,
          average_steps: 0,
          average_daily_steps: 0,
          average_steps_on_active_days: 0,
          best_day: null,
          latest_day: null,
          latest_complete_day: null,
          current_day: null,
          active_day_count: 0,
          valid_day_count: 0,
          partial_day_count: 0,
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

    if ((!oauthState && !message) || oauthHandledRef.current) {
      return;
    }

    oauthHandledRef.current = true;

    if (oauthState === 'connected') {
      setGoogleFitConnectionState(true);
      setNotice('Google account connected. Pulling your latest Google Fit steps now.');
      (async () => {
        try {
          await loadStatus(timezone, { silent: true });
          await handleSync(false);
          navigate(ROUTES.DEVICES, { replace: true });
        } catch (syncError) {
          setError(extractSyncError(syncError));
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
    average_steps: 0,
    average_daily_steps: 0,
    average_steps_on_active_days: 0,
    best_day: null,
    latest_day: null,
    latest_complete_day: null,
    current_day: null,
    active_day_count: 0,
    valid_day_count: 0,
    partial_day_count: 0,
  };
  const availability = data?.data_availability || { steps: false, heart_rate: false, sleep: false };
  const missingScopes = Array.isArray(data?.missing_scopes) ? data.missing_scopes : [];
  const latestDisplayDay = stats.latest_day;

  return (
    <div className="min-h-screen bg-background text-text-primary dark:bg-background dark:text-slate-100">
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
          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-stroke dark:bg-white/[0.03]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-text-muted">Actions</p>
                <h2 className="mt-2 text-[22px] font-black tracking-tight text-text-primary dark:text-text-primary">
                  Sync and manage Google Fit
                </h2>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleConnect}
                  disabled={isConnecting || isSyncing}
                  className="inline-flex items-center gap-2 rounded-2xl bg-primary px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc] disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Link2 size={16} />
                  {isConnecting ? 'Opening Google...' : data?.connected ? 'Reconnect Google' : 'Connect Google'}
                </button>
                <button
                  onClick={() => handleSync(true)}
                  disabled={!data?.connected || isSyncing || isConnecting}
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-text-primary transition hover:border-primary/30 hover:text-primary disabled:cursor-not-allowed disabled:opacity-60 dark:border-stroke dark:bg-white/5 dark:text-text-primary"
                >
                  <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} />
                  {isSyncing ? 'Syncing Steps...' : 'Sync Latest 7 Days'}
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

            {isSyncing && (
              <div
                role="status"
                aria-live="polite"
                className="mt-4 flex items-center gap-3 rounded-2xl border border-primary/20 bg-primary/10 px-4 py-3 text-[13px] font-semibold text-primary dark:border-[#8b7cf6]/30 dark:bg-primary/15 dark:text-[#c7c0ff]"
              >
                <RefreshCw size={16} className="shrink-0 animate-spin" />
                <span>Syncing Google Fit data… this may take up to 30 seconds</span>
              </div>
            )}

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <StatCard
                label={latestDisplayDay?.is_partial ? 'Today So Far' : 'Daily Steps'}
                value={formatNumber(latestDisplayDay?.steps ?? null)}
                helper={latestDisplayDay?.date ? formatLocalDay(latestDisplayDay.date) : 'No sync yet'}
                icon={Footprints}
                accent="#22c55e"
              />
              <StatCard
                label="Total Steps"
                value={formatNumber(stats.total_steps ?? null)}
                helper={`Total across ${formatNumber(stats.valid_day_count ?? 0)} complete local days`}
                icon={TrendingUp}
                accent="var(--color-primary)"
              />
              <StatCard
                label="Average Daily"
                value={formatNumber(stats.average_steps ?? stats.average_daily_steps ?? null)}
                helper="Backend-computed average across synced local days"
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
                helper={stats.latest_day?.date ? `Latest local day: ${formatLocalDay(stats.latest_day.date)}` : 'No synced history yet'}
                icon={CalendarDays}
                accent="#14b8a6"
              />
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-stroke dark:bg-white/[0.03]">
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-text-muted">Implementation notes</p>
            <ul className="mt-4 space-y-3 text-[13px] leading-relaxed text-slate-600 dark:text-text-muted">
              <li>The server handles OAuth code exchange and token refresh so Google secrets stay server-side.</li>
              <li>Daily buckets are generated from local-midnight boundaries using your configured timezone.</li>
              <li>Fetched daily steps are normalized once and stored in backend-owned user vitals.</li>
              <li>The raw Google aggregate response is preserved for debugging in the panel below.</li>
            </ul>

            <div className="mt-6 rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-4 dark:border-stroke dark:bg-card">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 text-amber-500" size={18} />
                <div>
                  <p className="text-[12px] font-black uppercase tracking-[0.14em] text-text-primary dark:text-text-primary">
                    Google Fit status
                  </p>
                  <p className="mt-2 text-[13px] leading-relaxed text-slate-500 dark:text-text-muted">
                    Google Fit APIs are being deprecated by Google in favor of Health Connect. This integration keeps
                    your current flow working, but future migration planning is recommended.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-4 dark:border-stroke dark:bg-card">
              <p className="text-[12px] font-black uppercase tracking-[0.14em] text-text-primary dark:text-text-primary">
                Data availability
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {[
                  { key: 'steps', label: 'Steps' },
                  { key: 'heart_rate', label: 'Heart Rate' },
                  { key: 'sleep', label: 'Sleep' },
                ].map((item) => (
                  <div key={item.key} className="rounded-2xl border border-slate-200/70 bg-white px-4 py-3 dark:border-stroke dark:bg-white/5">
                    <p className="text-[11px] font-black uppercase tracking-[0.14em] text-text-muted">{item.label}</p>
                    <p className="mt-2 text-[14px] font-semibold text-text-primary dark:text-text-primary">
                      {availabilityText(Boolean(availability[item.key]), missingScopes.includes(item.key))}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-stroke dark:bg-white/[0.03]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-text-muted">Daily buckets</p>
                <h2 className="mt-2 text-[22px] font-black tracking-tight text-text-primary dark:text-text-primary">
                  Last {DEFAULT_WINDOW_DAYS} local days
                </h2>
              </div>
              {isLoading && <RefreshCw className="animate-spin text-text-muted" size={18} />}
            </div>

            <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-slate-200/70 dark:border-stroke">
              <div className="grid grid-cols-[1.2fr_0.8fr] bg-slate-50 px-4 py-3 text-[11px] font-black uppercase tracking-[0.16em] text-text-muted dark:bg-white/5">
                <span>Date</span>
                <span className="text-right">Steps</span>
              </div>
              {stats.daily_steps.length > 0 ? (
                <div className="max-h-[420px] overflow-y-auto">
                  {stats.daily_steps.map((item) => (
                      <div
                        key={item.date}
                        className="grid grid-cols-[1.2fr_0.8fr] border-t border-slate-100 px-4 py-3 text-[13px] dark:border-stroke/50"
                      >
                        <span className="font-semibold text-text-primary dark:text-text-primary">
                          {formatLocalDay(item.date)}
                          {item.is_partial ? <span className="ml-2 text-[10px] font-black uppercase tracking-[0.12em] text-amber-500">Partial</span> : null}
                        </span>
                        <span className="text-right font-black text-primary">{formatNumber(item.steps)}</span>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="flex min-h-[220px] flex-col items-center justify-center px-6 py-10 text-center">
                  <Footprints size={28} className="text-text-secondary dark:text-slate-600" />
                  <p className="mt-4 text-[14px] font-semibold text-slate-500 dark:text-text-muted">
                    Connect Google Fit and run a sync to populate local daily step buckets.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-stroke dark:bg-white/[0.03]">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 text-primary dark:border-stroke dark:bg-white/5">
                <Bug size={20} />
              </div>
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-text-muted">Developer Debug</p>
                <h2 className="mt-1 text-[22px] font-black tracking-tight text-text-primary dark:text-text-primary">
                  Raw aggregate response
                </h2>
              </div>
            </div>

            <details className="mt-5 rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-4 dark:border-stroke dark:bg-card" open={Boolean(data?.raw_json)}>
              <summary className="cursor-pointer list-none text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">
                {data?.raw_json ? 'Show cached Google Fit JSON' : 'No raw JSON cached yet'}
              </summary>
              <pre className="mt-4 max-h-[460px] overflow-auto rounded-2xl bg-card p-4 text-[11px] leading-relaxed text-slate-100">
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

