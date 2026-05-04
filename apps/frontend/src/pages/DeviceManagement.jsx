import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search,
  Bell,
  Watch,
  CheckCircle2,
  RotateCw,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { ROUTES } from '../router/routes';
import googleFitLogo from '../assets/google-fit.png';
import { openCommandPalette } from '../components/CommandPalette';
import AddDeviceModal from '../components/AddDeviceModal';
import Button from '../components/ui/Button';
import { syncGoogleFit } from '../lib/googleFitApi';
import useDeviceStore from '../store/deviceStore';
import {
  fetchConnectedDeviceSummaries,
  GOOGLE_FIT_PROVIDER,
} from '../lib/deviceApi';
import { refreshAfterGoogleFitSync } from '../lib/googleFitRefresh';
import { setGoogleFitConnectionState } from '../lib/googleFitConnectionState';

function formatLastSynced(value) {
  if (!value) return null;

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed);
}

function extractErrorMessage(error, fallback) {
  return error?.response?.data?.error || error?.response?.data?.detail || error?.message || fallback;
}

function buildGoogleFitDevice(status) {
  if (!status?.connected) {
    return null;
  }

  return {
    id: GOOGLE_FIT_PROVIDER,
    provider: GOOGLE_FIT_PROVIDER,
    name: 'Google Fit',
    is_connected: true,
    statusLabel: 'Connected',
    statusDotColor: '#22c55e',
    statusTextColor: '#22c55e',
    iconElement: (
      <img
        src={googleFitLogo}
        alt="Google Fit"
        className="h-[22px] w-[22px] object-contain"
      />
    ),
    iconBg: 'rgba(34,197,94,0.08)',
    lastSyncedAt: status?.last_synced_at ?? null,
    lastSynced: formatLastSynced(status?.last_synced_at),
  };
}

function buildFallbackDevice(record) {
  const provider = String(record?.provider || record?.integration || record?.slug || record?.id || '').toLowerCase();
  const isConnected = record?.is_connected ?? record?.connected ?? true;
  const lastSyncedAt = record?.last_synced_at ?? record?.lastSyncedAt ?? null;
  const name = record?.name || record?.display_name || (provider === GOOGLE_FIT_PROVIDER ? 'Google Fit' : 'Connected Device');

  if (provider === GOOGLE_FIT_PROVIDER) {
    return buildGoogleFitDevice({
      connected: isConnected,
      last_synced_at: lastSyncedAt,
    });
  }

  return {
    id: record?.id || provider || name,
    provider: provider || 'unknown',
    name,
    is_connected: Boolean(isConnected),
    statusLabel: isConnected ? 'Connected' : 'Not connected',
    statusDotColor: isConnected ? '#22c55e' : '#94a3b8',
    statusTextColor: isConnected ? '#22c55e' : '#64748b',
    iconElement: (
      <Watch size={22} />
    ),
    iconBg: 'rgba(148,163,184,0.12)',
    lastSyncedAt,
    lastSynced: formatLastSynced(lastSyncedAt),
  };
}

function dedupeDevices(devices) {
  const seen = new Set();

  return devices.filter((device) => {
    const key = `${device?.provider || 'unknown'}:${device?.id || device?.name || 'device'}`;
    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}

function DeviceCard({ device, onSyncNow, onOpenGoogleFit, syncing }) {
  return (
    <div className="flex min-h-[220px] flex-col rounded-xl border border-slate-200/60 bg-white p-5 transition-all hover:shadow-md dark:border-stroke/50 dark:bg-card">
      <div className="mb-3.5 flex items-start justify-between">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-lg"
          style={{ backgroundColor: device.iconBg }}
        >
          {device.iconElement}
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: device.statusDotColor }}
          />
          <span
            className="text-[11px] font-semibold"
            style={{ color: device.statusTextColor }}
          >
            {device.statusLabel}
          </span>
        </div>
      </div>

      <h4 className="mb-1.5 text-[14px] font-bold tracking-tight text-text-primary dark:text-text-primary">
        {device.name}
      </h4>

      <div className="mb-4 flex items-center gap-2.5 text-[11px] font-medium text-text-muted">
        {device.lastSynced ? (
          <span className="flex items-center gap-1">
            <RotateCw size={11} />
            Last synced {device.lastSynced}
          </span>
        ) : (
          <span>Waiting for backend sync status</span>
        )}
      </div>

      <div className="mt-auto flex items-center gap-2">
        <button
          className="flex-1 rounded-lg bg-[#e8f4f8] py-2.5 text-[12px] font-semibold text-[#0ea5a8] transition-all hover:bg-[#d5eef3] disabled:cursor-not-allowed disabled:opacity-70"
          type="button"
          onClick={() => onSyncNow(device)}
          disabled={syncing}
        >
          {syncing ? (
            <span className="inline-flex items-center gap-1.5">
              <RefreshCw size={14} className="animate-spin" />
              Syncing
            </span>
          ) : (
            'Sync Now'
          )}
        </button>

        {device.provider === GOOGLE_FIT_PROVIDER ? (
          <button
            className="rounded-lg border border-slate-200 px-3 py-2.5 text-[12px] font-semibold text-slate-600 transition-all hover:border-primary/30 hover:text-primary dark:border-stroke dark:text-text-secondary"
            type="button"
            onClick={onOpenGoogleFit}
          >
            Open Fit
          </button>
        ) : null}
      </div>
    </div>
  );
}

function DeviceGrid({ devices, onSyncNow, onOpenGoogleFit, syncingDeviceId }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {devices.map((device) => (
        <DeviceCard
          key={device.id}
          device={device}
          onSyncNow={onSyncNow}
          onOpenGoogleFit={onOpenGoogleFit}
          syncing={syncingDeviceId === device.id}
        />
      ))}
    </div>
  );
}

function SyncPanel({ integrations, lastUpdated }) {
  return (
    <div className="rounded-xl border border-slate-200/60 bg-white p-6 dark:border-stroke/50 dark:bg-card">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[15px] font-bold tracking-tight text-text-primary dark:text-text-primary">
            Sync Health
          </h3>
          <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
            Connected integrations reported by the backend.
          </p>
        </div>
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#22c55e]">
          <CheckCircle2 size={14} className="text-text-primary" />
        </div>
      </div>

      {lastUpdated ? (
        <p className="mb-4 text-[11px] font-medium text-text-muted">
          Last backend update: {formatLastSynced(lastUpdated)}
        </p>
      ) : null}

      <div className="space-y-3 border-t border-slate-100 pt-4 dark:border-stroke/50">
        {integrations.length > 0 ? (
          integrations.map((item) => (
            <div key={item.name} className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="text-[14px]">💚</span>
                <span className="text-[12px] font-semibold text-text-primary dark:text-text-primary">
                  {item.name}
                </span>
              </div>
              <span className="rounded-md bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                Connected
              </span>
            </div>
          ))
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 px-4 py-5 text-center dark:border-stroke">
            <p className="text-[12px] font-semibold text-slate-500 dark:text-text-muted">
              No connected integrations returned by the backend.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

const DeviceManagement = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const devices = useDeviceStore((state) => state.devices);
  const setDevices = useDeviceStore((state) => state.setDevices);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [syncingDeviceId, setSyncingDeviceId] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const oauthHandledRef = useRef(false);

  const loadDevices = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setIsLoading(true);
    }
    setError('');

    try {
      const summaries = await fetchConnectedDeviceSummaries();
      setDevices(dedupeDevices(summaries));
      setGoogleFitConnectionState(
        Array.isArray(summaries) && summaries.some(
          (device) => device?.provider === GOOGLE_FIT_PROVIDER && device?.is_connected
        )
      );
    } catch (apiError) {
      setDevices([]);
      setGoogleFitConnectionState(false);
      setError(extractErrorMessage(apiError, 'Unable to load connected devices right now.'));
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, [setDevices]);

  useEffect(() => {
    void loadDevices();
  }, []);

  useEffect(() => {
    const googleFitStatus = searchParams.get('googleFit');
    const connectedProvider = searchParams.get('connected');
    const isConnectedCallback = googleFitStatus === 'connected' || connectedProvider === 'google_fit';
    const isErrorCallback = googleFitStatus === 'error';
    const message = searchParams.get('message');

    if ((!isConnectedCallback && !isErrorCallback && !message) || oauthHandledRef.current) {
      return;
    }

    oauthHandledRef.current = true;

    const finalize = async () => {
      if (isConnectedCallback) {
        setGoogleFitConnectionState(true);
        toast.success('Google Fit connected. Starting your first sync.');

        try {
          await syncGoogleFit({
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            days: 7,
          });
          await refreshAfterGoogleFitSync();
        } catch (apiError) {
          toast.error(extractErrorMessage(apiError, 'Google Fit connected, but the first sync failed.'));
        }
      } else if (isErrorCallback || message) {
        toast.error(message || 'Google Fit connection failed.');
      }

      await loadDevices({ silent: true });

      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('googleFit');
      nextParams.delete('connected');
      nextParams.delete('message');
      setSearchParams(nextParams, { replace: true });
    };

    void finalize();
  }, [loadDevices, searchParams, setSearchParams]);

  const connectedDevices = useMemo(
    () => devices
      .map((device) => buildFallbackDevice(device))
      .filter((device) => device?.is_connected === true),
    [devices]
  );

  const filteredDevices = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return connectedDevices;
    }

    return connectedDevices.filter((device) => {
      const haystack = `${device.name} ${device.provider}`.toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [connectedDevices, query]);

  const syncIntegrations = useMemo(
    () => connectedDevices.map((device) => ({
      name: device.name,
      is_connected: device.is_connected,
      last_synced_at: device.lastSyncedAt ?? null,
    })),
    [connectedDevices]
  );

  const lastUpdated = useMemo(() => {
    const timestamps = connectedDevices
      .map((device) => device.lastSyncedAt)
      .filter(Boolean);

    if (timestamps.length === 0) {
      return null;
    }

    return timestamps.reduce((latest, value) => {
      const latestTime = new Date(latest).getTime();
      const nextTime = new Date(value).getTime();

      if (Number.isNaN(nextTime)) {
        return latest;
      }

      if (Number.isNaN(latestTime) || nextTime > latestTime) {
        return value;
      }

      return latest;
    });
  }, [connectedDevices]);

  const handleSyncNow = async (device) => {
    if (device.provider !== GOOGLE_FIT_PROVIDER) {
      return;
    }

    setSyncingDeviceId(device.id);
    try {
      await syncGoogleFit({
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        days: 7,
      });
      await refreshAfterGoogleFitSync();
      await loadDevices({ silent: true });
      toast.success('Google Fit sync triggered.');
    } catch (apiError) {
      toast.error(extractErrorMessage(apiError, 'Google Fit sync failed.'));
    } finally {
      setSyncingDeviceId(null);
    }
  };

  const handleOpenGoogleFit = () => {
    navigate(ROUTES.GOOGLE_FIT_SETTINGS);
  };

  const handleOpenAddModal = () => {
    setShowAddModal(true);
  };

  return (
    <>
      

      <div className="mx-auto w-full max-w-[1440px] p-8 pb-16">
        <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h2 className="mb-1.5 text-[28px] font-black tracking-tight text-text-primary dark:text-text-primary">
              Device Manager
            </h2>
            <p className="text-[13px] font-medium text-text-muted">
              Connected devices and integrations are rendered directly from the backend.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500 dark:border-stroke dark:bg-white/5 dark:text-text-secondary">
              {connectedDevices.length} connected
            </div>
            <Button
              type="button"
              onClick={handleOpenAddModal}
              variant="primary"
              size="md"
              className="bg-primary text-white hover:bg-[#5235dc]"
            >
              + Add Device
            </Button>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] font-medium text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
            {error}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <h3 className="text-[14px] font-bold text-text-primary dark:text-text-primary">
                  Connected Devices
                </h3>
                <span className="rounded-md border border-primary/10 bg-primary/[0.06] px-2 py-0.5 text-[10px] font-bold text-primary">
                  {filteredDevices.length} visible
                </span>
              </div>
            </div>

            {isLoading ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center dark:border-stroke dark:bg-card">
                <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <RefreshCw size={18} className="animate-spin" />
                </div>
                <p className="text-[13px] font-semibold text-slate-500 dark:text-text-muted">
                  Loading connected devices from the backend...
                </p>
              </div>
            ) : filteredDevices.length > 0 ? (
              <DeviceGrid
                devices={filteredDevices}
                onSyncNow={handleSyncNow}
                onOpenGoogleFit={handleOpenGoogleFit}
                syncingDeviceId={syncingDeviceId}
              />
            ) : (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center dark:border-stroke dark:bg-card">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Watch size={22} />
                </div>
                <p className="text-[14px] font-semibold text-slate-500 dark:text-text-muted">
                  {query.trim()
                    ? 'No connected devices match your search.'
                    : 'No devices connected. Add a device to start syncing health data.'}
                </p>
                {!query.trim() ? (
                  <Button
                    type="button"
                    onClick={handleOpenAddModal}
                    variant="primary"
                    size="md"
                    className="mt-5 bg-primary text-white hover:bg-[#5235dc]"
                  >
                    + Add Device
                  </Button>
                ) : null}
              </div>
            )}
          </div>

          <div className="space-y-5">
            <SyncPanel integrations={syncIntegrations} lastUpdated={lastUpdated} />

            <div className="rounded-xl border border-slate-200/60 bg-white p-6 dark:border-stroke/50 dark:bg-card">
              <h3 className="mb-2 text-[15px] font-bold tracking-tight text-text-primary dark:text-text-primary">
                Search behavior
              </h3>
              <p className="text-[11px] leading-relaxed text-text-muted">
                Search is filtered against connected backend devices only, so the page never shows mock or
                placeholder integrations.
              </p>
              <button
                className="mt-5 inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-primary transition-colors hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                onClick={() => setQuery('')}
                disabled={!query}
              >
                Clear search
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>
      <AddDeviceModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
      />
    </>
  );
};

export default DeviceManagement;

