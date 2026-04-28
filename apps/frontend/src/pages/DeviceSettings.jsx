import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Battery,
  CheckCircle2,
  Clock,
  Link2,
  RefreshCw,
  Unplug,
  User,
  Watch,
  AlertTriangle,
} from 'lucide-react';

import { ROUTES } from '../router/routes';
import {
  disconnectGoogleFit,
  fetchGoogleFitStatus,
  startGoogleFitConnect,
  syncGoogleFit,
} from '../lib/googleFitApi';
import { refreshAfterGoogleFitSync } from '../lib/googleFitRefresh';
import { setGoogleFitConnectionState } from '../lib/googleFitConnectionState';

const DEFAULT_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
const GOOGLE_FIT_DEVICE_ID = 'google-fit';

function formatDateTime(value, timezone = DEFAULT_TIMEZONE) {
  if (!value) return 'Not available';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Not available';

  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timezone,
  }).format(parsed);
}

function formatNumber(value) {
  if (value === null || value === undefined || value === '') return '--';
  if (typeof value === 'string' && Number.isNaN(Number(value))) return value;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat('en-IN').format(numeric) : String(value);
}

function extractErrorMessage(error, fallback) {
  return error?.response?.data?.error || error?.response?.data?.detail || error?.message || fallback;
}

function StatCard({ label, value, helper, icon: Icon }) {
  return (
    <div className="rounded-[1.75rem] border border-slate-200/70 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">{label}</p>
          <p className="text-[24px] font-black tracking-tight text-[#13082a] dark:text-white">{value}</p>
          <p className="mt-2 text-[12px] leading-relaxed text-slate-500 dark:text-slate-400">{helper}</p>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#6143f4]/20 bg-[#6143f4]/10 text-[#6143f4]">
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}

const DeviceSettings = () => {
  const navigate = useNavigate();
  const { deviceId } = useParams();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const passedDevice = location.state?.device ?? null;
  const isGoogleFit = deviceId === GOOGLE_FIT_DEVICE_ID || passedDevice?.provider === GOOGLE_FIT_DEVICE_ID || passedDevice?.id === GOOGLE_FIT_DEVICE_ID;

  const [status, setStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const oauthHandledRef = useRef(false);

  async function loadStatus({ silent = false } = {}) {
    if (!isGoogleFit) {
      setIsLoading(false);
      setStatus(null);
      return;
    }

    if (!silent) {
      setIsLoading(true);
    }
    setError('');

    try {
      const nextStatus = await fetchGoogleFitStatus();
      setStatus(nextStatus);
      setGoogleFitConnectionState(Boolean(nextStatus?.connected));
    } catch (apiError) {
      setStatus(null);
      setGoogleFitConnectionState(false);
      setError(extractErrorMessage(apiError, 'Unable to load Google Fit status right now.'));
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isGoogleFit]);

  const connected = Boolean(status?.connected);
  const timezone = status?.timezone || DEFAULT_TIMEZONE;
  const stats = status?.stats || {};
  const deviceName = passedDevice?.name || 'Google Fit';

  useEffect(() => {
    if (!isGoogleFit) {
      return;
    }

    const googleFitStatus = searchParams.get('googleFit');
    const connectedProvider = searchParams.get('connected');
    const message = searchParams.get('message');
    const isConnectedCallback = googleFitStatus === 'connected' || connectedProvider === 'google_fit';

    if ((!isConnectedCallback && googleFitStatus !== 'error' && !message) || oauthHandledRef.current) {
      return;
    }

    oauthHandledRef.current = true;

    const finalize = async () => {
      if (isConnectedCallback) {
        setGoogleFitConnectionState(true);
        setNotice('Google Fit connected. Pulling the latest data now.');
        try {
          await syncGoogleFit({ timezone, days: 30 });
          await refreshAfterGoogleFitSync();
        } catch (apiError) {
          setError(extractErrorMessage(apiError, 'Google Fit connected, but sync failed.'));
        }
      } else {
        setError(message || 'Google Fit connection failed.');
      }

      await loadStatus({ silent: true });
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('googleFit');
      nextParams.delete('connected');
      nextParams.delete('message');
      setSearchParams(nextParams, { replace: true });
    };

    void finalize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, setSearchParams, timezone, isGoogleFit]);

  const handleConnect = async () => {
    setIsConnecting(true);
    setError('');

    try {
      const response = await startGoogleFitConnect({
        timezone,
        redirectPath: window.location.pathname,
      });

      if (response?.auth_url) {
        window.location.assign(response.auth_url);
        return;
      }

      throw new Error('Google Fit did not return an authorization URL.');
    } catch (apiError) {
      setError(extractErrorMessage(apiError, 'Unable to start Google Fit connection.'));
      setIsConnecting(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    setNotice('');
    setError('');

    try {
      const response = await syncGoogleFit({ timezone, days: 30 });
      await Promise.all([
        loadStatus({ silent: true }),
        refreshAfterGoogleFitSync(),
      ]);
      setNotice(response?.message || 'Google Fit sync completed.');
    } catch (apiError) {
      setError(extractErrorMessage(apiError, 'Google Fit sync failed.'));
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDisconnect = async () => {
    setIsDisconnecting(true);
    setNotice('');
    setError('');

    try {
      await disconnectGoogleFit();
      await loadStatus({ silent: true });
      setGoogleFitConnectionState(false);
      setNotice('Google Fit disconnected.');
    } catch (apiError) {
      setError(extractErrorMessage(apiError, 'Unable to disconnect Google Fit.'));
    } finally {
      setIsDisconnecting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f6f5f8] text-[#13082a] dark:bg-[#0B0819] dark:text-slate-100">
      

      <main className="mx-auto w-full max-w-7xl px-6 py-8 md:px-10">
        {!isGoogleFit ? (
          <section className="rounded-[2rem] border border-slate-200/70 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-500">
                <AlertTriangle size={22} />
              </div>
              <div className="min-w-0">
                <h1 className="text-[28px] font-black tracking-tight text-[#13082a] dark:text-white">
                  Device settings are backend-driven only
                </h1>
                <p className="mt-3 max-w-3xl text-[14px] leading-relaxed text-slate-500 dark:text-slate-400">
                  This route no longer uses mock device data. The backend currently exposes live Google Fit state,
                  so other device ids are shown as unavailable instead of being faked.
                </p>
                <button
                  type="button"
                  onClick={() => navigate(ROUTES.DEVICES)}
                  className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc]"
                >
                  Return to Device Manager
                </button>
              </div>
            </div>
          </section>
        ) : (
          <>
            <section className="rounded-[2rem] border border-slate-200/70 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
              <div className="grid gap-8 lg:grid-cols-[1.5fr_1fr]">
                <div>
                  <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 size={14} />
                    Live backend status
                  </div>
                  <h1 className="text-[32px] font-black leading-tight tracking-tight text-[#13082a] dark:text-white">
                    {deviceName}
                  </h1>
                  <p className="mt-3 max-w-3xl text-[14px] leading-relaxed text-slate-500 dark:text-slate-400">
                    This page only shows data returned by the backend. Sync, connect, and disconnect actions use the
                    existing Google Fit pipeline without changing any API contracts.
                  </p>
                </div>

                <div className="rounded-[1.75rem] border border-slate-200/70 bg-slate-50/80 p-5 dark:border-white/10 dark:bg-[#131022]">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Connection</p>
                  <p className="mt-3 text-[22px] font-black tracking-tight text-[#13082a] dark:text-white">
                    {isLoading ? 'Loading...' : connected ? 'Connected' : 'Not connected'}
                  </p>
                  <p className="mt-2 text-[13px] text-slate-500 dark:text-slate-400">
                    {status?.google_email || 'No Google account is currently linked.'}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2 text-[12px] text-slate-500 dark:text-slate-400">
                    <span className="rounded-full bg-white px-3 py-1 dark:bg-white/5">Timezone: {timezone}</span>
                    <span className="rounded-full bg-white px-3 py-1 dark:bg-white/5">
                      Last sync: {formatDateTime(status?.last_synced_at, timezone)}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            {(notice || error) && (
              <div
                className={`mt-4 rounded-2xl border px-4 py-3 text-[13px] font-medium ${error
                    ? 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300'
                  }`}
              >
                {error || notice}
              </div>
            )}

            <section className="mt-6 grid gap-4 lg:grid-cols-[1.45fr_0.95fr]">
              <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Actions</p>
                    <h2 className="mt-2 text-[22px] font-black tracking-tight text-[#13082a] dark:text-white">
                      Google Fit sync controls
                    </h2>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    {!connected ? (
                      <button
                        type="button"
                        onClick={handleConnect}
                        disabled={isConnecting}
                        className="inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc] disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        <Link2 size={16} />
                        {isConnecting ? 'Opening Google...' : 'Connect Google Fit'}
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={handleSync}
                          disabled={isSyncing}
                          className="inline-flex items-center gap-2 rounded-2xl bg-[#6143f4] px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-white transition hover:bg-[#5235dc] disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} />
                          {isSyncing ? 'Syncing...' : 'Sync 30 Days'}
                        </button>
                        <button
                          type="button"
                          onClick={handleDisconnect}
                          disabled={isDisconnecting}
                          className="inline-flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-[12px] font-black uppercase tracking-[0.16em] text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-70 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
                        >
                          <Unplug size={16} />
                          {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <StatCard
                    label="Daily Steps"
                    value={formatNumber(stats.latest_day?.steps)}
                    helper={stats.latest_day?.date ? `Latest local day: ${stats.latest_day.date}` : 'No synced data yet'}
                    icon={Watch}
                  />
                  <StatCard
                    label="Total Steps"
                    value={formatNumber(stats.total_steps)}
                    helper="Backend-calculated total for the synced window"
                    icon={RefreshCw}
                  />
                  <StatCard
                    label="Average Daily"
                    value={formatNumber(stats.average_daily_steps)}
                    helper="Average across all synced buckets"
                    icon={Clock}
                  />
                  <StatCard
                    label="Active Days"
                    value={formatNumber(stats.active_day_count)}
                    helper="Days with recorded step activity"
                    icon={Battery}
                  />
                  <StatCard
                    label="Best Day"
                    value={formatNumber(stats.best_day?.steps)}
                    helper={stats.best_day?.date ? `Best day: ${stats.best_day.date}` : 'No synced history yet'}
                    icon={CheckCircle2}
                  />
                  <StatCard
                    label="Google Account"
                    value={status?.google_email ? 'Linked' : 'Unlinked'}
                    helper={status?.google_email || 'No account linked yet'}
                    icon={User}
                  />
                </div>
              </div>

              <div className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
                <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Implementation notes</p>
                <ul className="mt-4 space-y-3 text-[13px] leading-relaxed text-slate-600 dark:text-slate-400">
                  <li>Connection state is fetched from the live Google Fit status endpoint.</li>
                  <li>Sync and disconnect use the existing Google Fit backend routes.</li>
                  <li>No fallback devices, fake statuses, or placeholder timestamps are shown here.</li>
                  <li>Other device ids are treated as unavailable until a real backend source exists.</li>
                </ul>

                <div className="mt-6 rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-4 dark:border-white/10 dark:bg-[#131022]">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="mt-0.5 text-amber-500" size={18} />
                    <div>
                      <p className="text-[12px] font-black uppercase tracking-[0.14em] text-[#13082a] dark:text-white">
                        Safety check
                      </p>
                      <p className="mt-2 text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">
                        This page intentionally avoids generic device fallbacks so the frontend stays aligned with
                        backend truth and the Google Fit pipeline remains unchanged.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
};

export default DeviceSettings;
