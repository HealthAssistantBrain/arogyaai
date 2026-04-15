import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
    <div className="flex min-h-[220px] flex-col rounded-xl border border-slate-200/60 bg-white p-5 transition-all hover:shadow-md dark:border-white/5 dark:bg-[#131022]">
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

      <h4 className="mb-1.5 text-[14px] font-bold tracking-tight text-[#13082a] dark:text-white">
        {device.name}
      </h4>

      <div className="mb-4 flex items-center gap-2.5 text-[11px] font-medium text-slate-400">
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
            className="rounded-lg border border-slate-200 px-3 py-2.5 text-[12px] font-semibold text-slate-600 transition-all hover:border-[#6143f4]/30 hover:text-[#6143f4] dark:border-white/10 dark:text-slate-300"
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
    <div className="rounded-xl border border-slate-200/60 bg-white p-6 dark:border-white/5 dark:bg-[#131022]">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[15px] font-bold tracking-tight text-[#13082a] dark:text-white">
            Sync Health
          </h3>
          <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
            Connected integrations reported by the backend.
          </p>
        </div>
        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#22c55e]">
          <CheckCircle2 size={14} className="text-white" />
        </div>
      </div>

      {lastUpdated ? (
        <p className="mb-4 text-[11px] font-medium text-slate-400">
          Last backend update: {formatLastSynced(lastUpdated)}
        </p>
      ) : null}

      <div className="space-y-3 border-t border-slate-100 pt-4 dark:border-white/5">
        {integrations.length > 0 ? (
          integrations.map((item) => (
            <div key={item.name} className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="text-[14px]">💚</span>
                <span className="text-[12px] font-semibold text-[#13082a] dark:text-white">
                  {item.name}
                </span>
              </div>
              <span className="rounded-md bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                Connected
              </span>
            </div>
          ))
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 px-4 py-5 text-center dark:border-white/10">
            <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">
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
  const [query, setQuery] = useState('');
  const devices = useDeviceStore((state) => state.devices);
  const setDevices = useDeviceStore((state) => state.setDevices);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [syncingDeviceId, setSyncingDeviceId] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);

  const loadDevices = async ({ silent = false } = {}) => {
    if (!silent) {
      setIsLoading(true);
    }
    setError('');

    try {
      const summaries = await fetchConnectedDeviceSummaries();
      setDevices(dedupeDevices(summaries));
    } catch (apiError) {
      setDevices([]);
      setError(extractErrorMessage(apiError, 'Unable to load connected devices right now.'));
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    void loadDevices();
  }, []);

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
        days: 30,
      });
      await refreshAfterGoogleFitSync();
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
      <header className="sticky top-0 z-20 flex h-[64px] items-center justify-between border-b border-slate-100 bg-white/90 px-8 backdrop-blur-xl dark:border-white/5 dark:bg-[#0B0819]/70">
        <div className="max-w-md flex-1">
          <div className="relative">
            <Search
              onClick={openCommandPalette}
              style={{ cursor: 'pointer', pointerEvents: 'auto' }}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              size={16}
            />
            <input
              className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-4 text-[13px] font-medium placeholder:text-slate-400 outline-none transition-all focus:border-[#6143f4]/30 focus:ring-2 focus:ring-[#6143f4]/20 dark:border-white/10 dark:bg-white/5 dark:text-white"
              placeholder="Search connected devices and integrations..."
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-400 transition-all hover:text-[#6143f4] dark:border-white/10 dark:bg-white/5"
            type="button"
            onClick={() => navigate(ROUTES.NOTIFICATIONS)}
          >
            <Bell size={16} />
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full border-[1.5px] border-white bg-red-500 dark:border-[#0B0819]" />
          </button>
          <div className="mx-0.5 h-5 w-px bg-slate-200 dark:bg-white/10" />
          <div
            className="flex cursor-pointer items-center gap-2.5 group"
            onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}
          >
            <div className="text-right">
              <p className="text-[12px] font-bold leading-tight text-[#13082a] transition-colors group-hover:text-[#6143f4] dark:text-white">
                Alex Rivera
              </p>
              <p className="mt-0.5 text-[8px] font-bold uppercase tracking-wider text-[#6143f4] opacity-80">
                Premium User
              </p>
            </div>
            <div className="h-9 w-9 overflow-hidden rounded-lg border-2 border-transparent bg-[#6143f4]/10 transition-all group-hover:border-[#6143f4]">
              <img
                className="h-full w-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBPXRQiJMy2AjUx1s7i8PF4VDCzzfdMwtRfXLHjRrgzSIQ81oYqk6GcXc_Tm6Ib463MN9qj5KL1eXMwKaIUQqZyLXkCGGM0RK7qH6_iMVzNLpTGdw_hpYS5eDo18scXpzHZLuA8PvMMwFaC9CelQUkXVlVugIOSU1LjxQxNnTgdaAoSC7uRYkemunPnF3SOoLmjXYVC4OpM1LtTBr1anc-24LOv7M9ZO_rUwQce_duaAsBqEKaY9ovz3riujUqxQDIK68cUxpyCDQox"
                alt="Alex Rivera"
              />
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-[1440px] p-8 pb-16">
        <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h2 className="mb-1.5 text-[28px] font-black tracking-tight text-[#13082a] dark:text-white">
              Device Manager
            </h2>
            <p className="text-[13px] font-medium text-slate-400">
              Connected devices and integrations are rendered directly from the backend.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
              {connectedDevices.length} connected
            </div>
            <Button
              type="button"
              onClick={handleOpenAddModal}
              variant="primary"
              size="md"
              className="bg-[#6143f4] text-white hover:bg-[#5235dc]"
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
                <h3 className="text-[14px] font-bold text-[#13082a] dark:text-white">
                  Connected Devices
                </h3>
                <span className="rounded-md border border-[#6143f4]/10 bg-[#6143f4]/[0.06] px-2 py-0.5 text-[10px] font-bold text-[#6143f4]">
                  {filteredDevices.length} visible
                </span>
              </div>
            </div>

            {isLoading ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center dark:border-white/10 dark:bg-[#131022]">
                <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-[#6143f4]/10 text-[#6143f4]">
                  <RefreshCw size={18} className="animate-spin" />
                </div>
                <p className="text-[13px] font-semibold text-slate-500 dark:text-slate-400">
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
              <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center dark:border-white/10 dark:bg-[#131022]">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#6143f4]/10 text-[#6143f4]">
                  <Watch size={22} />
                </div>
                <p className="text-[14px] font-semibold text-slate-500 dark:text-slate-400">
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
                    className="mt-5 bg-[#6143f4] text-white hover:bg-[#5235dc]"
                  >
                    + Add Device
                  </Button>
                ) : null}
              </div>
            )}
          </div>

          <div className="space-y-5">
            <SyncPanel integrations={syncIntegrations} lastUpdated={lastUpdated} />

            <div className="rounded-xl border border-slate-200/60 bg-white p-6 dark:border-white/5 dark:bg-[#131022]">
              <h3 className="mb-2 text-[15px] font-bold tracking-tight text-[#13082a] dark:text-white">
                Search behavior
              </h3>
              <p className="text-[11px] leading-relaxed text-slate-400">
                Search is filtered against connected backend devices only, so the page never shows mock or
                placeholder integrations.
              </p>
              <button
                className="mt-5 inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#6143f4] transition-colors hover:underline disabled:cursor-not-allowed disabled:opacity-50"
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
