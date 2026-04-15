import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Dumbbell,
  HeartPulse,
  Search,
  Watch,
  X,
} from 'lucide-react';

import useDeviceStore from '../store/deviceStore';

export const DEVICE_OPTIONS = [
  {
    id: 'google_fit',
    name: 'Google Fit',
    status: 'supported',
    description: 'Sync steps, heart rate, and activity data',
    action: 'connect',
    connectPath: '/device-settings/google-fit',
    icon: Watch,
  },
  {
    id: 'apple_health',
    name: 'Apple Health',
    status: 'coming_soon',
    description: 'iOS health data integration',
    action: 'disabled',
    icon: HeartPulse,
  },
  {
    id: 'fitbit',
    name: 'Fitbit',
    status: 'coming_soon',
    description: 'Connect Fitbit wearable devices',
    action: 'disabled',
    icon: Dumbbell,
  },
];

function normalizeKey(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-');
}

function getFocusableElements(container) {
  if (!container) {
    return [];
  }

  return Array.from(
    container.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hasAttribute('aria-hidden'));
}

function getNormalizedId(value) {
  return normalizeKey(value).replace(/-/g, '_');
}

function findMatchingDevice(deviceOptions, devices) {
  return deviceOptions.map((option) => {
    const matchingDevice = devices.find((device) => {
      const optionId = getNormalizedId(option.id);
      const deviceId = getNormalizedId(device?.id || device?.provider || device?.slug || device?.integration || device?.name);
      return optionId === deviceId;
    });

    if (!matchingDevice) {
      return option;
    }

    const connected = Boolean(matchingDevice.is_connected ?? matchingDevice.connected);

    return {
      ...option,
      ...matchingDevice,
      id: option.id,
      status: connected ? 'connected' : option.status,
      action: connected ? 'disabled' : option.action,
      connectPath: option.connectPath,
    };
  });
}

function getStatusVariant(option, connected) {
  if (connected) {
    return {
      label: 'CONNECTED',
      badgeClass: 'border-sky-500/20 bg-sky-500/10 text-sky-600 dark:text-sky-400',
      dotClass: 'bg-sky-500',
    };
  }

  if (option.status === 'supported') {
    return {
      label: 'SUPPORTED',
      badgeClass: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
      dotClass: 'bg-emerald-500',
    };
  }

  return {
    label: 'COMING SOON',
    badgeClass: 'border-slate-300 bg-slate-100 text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400',
    dotClass: 'bg-slate-400',
  };
}

function AddDeviceModal({ open, onClose }) {
  const navigate = useNavigate();
  const modalRef = useRef(null);
  const inputRef = useRef(null);
  const previousFocusRef = useRef(null);
  const [query, setQuery] = useState('');
  const devices = useDeviceStore((state) => state.devices);

  const mergedDevices = useMemo(
    () => findMatchingDevice(DEVICE_OPTIONS, devices),
    [devices]
  );

  const visibleOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    if (!normalizedQuery) {
      return mergedDevices;
    }

    return mergedDevices.filter((option) => {
      const haystack = [
        option.name,
        option.description,
        option.status,
        option.action,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return haystack.includes(normalizedQuery);
    });
  }, [mergedDevices, query]);

  const connectedCount = useMemo(
    () => mergedDevices.filter((device) => device.status === 'connected').length,
    [mergedDevices]
  );

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    previousFocusRef.current = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const focusSearch = window.setTimeout(() => {
      inputRef.current?.focus();
    }, 0);

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== 'Tab') {
        return;
      }

      const focusableElements = getFocusableElements(modalRef.current);
      if (focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      window.clearTimeout(focusSearch);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocusRef.current?.focus?.();
    };
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      setQuery('');
    }
  }, [open]);

  const handlePrimaryAction = (option) => {
    if (option.status !== 'supported' || isConnected(option.id)) {
      return;
    }

    onClose();

    if (typeof option.onSelect === 'function') {
      option.onSelect();
      return;
    }

    const fallbackPath = option.connectPath || `/device-settings/${normalizeKey(option.id)}`;
    navigate(fallbackPath);
  };

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 px-4 py-6 backdrop-blur-xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-device-title"
      aria-describedby="add-device-description"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={modalRef}
        className="w-full max-w-5xl overflow-hidden rounded-[2rem] border border-slate-200/80 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.25)] dark:border-white/10 dark:bg-[#0f1424]"
      >
        <div className="border-b border-slate-100 bg-gradient-to-br from-white via-slate-50 to-cyan-50 px-6 py-6 dark:border-white/5 dark:from-[#11182a] dark:via-[#0f1424] dark:to-[#101f33]">
          <div className="flex items-start justify-between gap-4">
            <div className="max-w-2xl">
              <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">
                Device onboarding
              </p>
              <h2
                id="add-device-title"
                className="mt-2 text-[28px] font-black tracking-tight text-[#13082a] dark:text-white"
              >
                Add Device
              </h2>
              <p
                id="add-device-description"
                className="mt-2 text-[14px] leading-relaxed text-slate-500 dark:text-slate-400"
              >
                Choose a device or service to connect. Supported integrations are actionable, coming-soon entries
                stay visible but disabled, and already connected services surface their live state from Zustand.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-bold uppercase tracking-[0.18em]">
                <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                  {visibleOptions.length} options
                </span>
                <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-3 py-1 text-sky-600 dark:text-sky-300">
                  {connectedCount} connected
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition-transform duration-200 hover:scale-105 hover:border-sky-300 hover:text-sky-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
              aria-label="Close add device modal"
            >
              <X size={18} />
            </button>
          </div>

          <div className="mt-5 flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-white/10 dark:bg-white/[0.04]">
            <Search size={16} className="text-slate-400" />
            <input
              ref={inputRef}
              className="w-full bg-transparent text-[14px] font-medium text-[#13082a] outline-none placeholder:text-slate-400 dark:text-white"
              placeholder="Search devices..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="text-[12px] font-bold uppercase tracking-[0.16em] text-slate-400 transition-colors hover:text-[#6143f4]"
              >
                Clear
              </button>
            ) : null}
          </div>
        </div>

        <div className="max-h-[72vh] overflow-y-auto px-6 py-6">
          {visibleOptions.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {visibleOptions.map((option) => {
                const Icon = option.icon || Watch;
                const connected = option.status === 'connected';
                const status = getStatusVariant(option, connected);
                const isActionDisabled = connected || option.status !== 'supported' || option.action === 'disabled';

                return (
                  <article
                    key={option.id}
                    className="group flex min-h-[230px] flex-col rounded-[1.5rem] border border-slate-200/80 bg-slate-50/80 p-5 transition-all duration-200 hover:-translate-y-1 hover:border-sky-300 hover:bg-white hover:shadow-[0_18px_45px_rgba(2,132,199,0.12)] dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-sky-500/30 dark:hover:bg-white/[0.05]"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/50 bg-white text-[#6143f4] shadow-sm transition-transform duration-200 group-hover:scale-105 dark:border-white/5 dark:bg-white/5">
                        <Icon size={22} />
                      </div>
                      <span
                        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${status.badgeClass}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${status.dotClass}`} />
                        {status.label}
                      </span>
                    </div>

                    <div className="mt-4">
                      <h3 className="text-[16px] font-bold tracking-tight text-[#13082a] dark:text-white">
                        {option.name}
                      </h3>
                      <p className="mt-2 truncate text-[13px] leading-5 text-slate-500 dark:text-slate-400" title={option.description}>
                        {option.description}
                      </p>
                    </div>

                    <div className="mt-auto pt-5">
                      <button
                        type="button"
                        disabled={isActionDisabled}
                        onClick={() => handlePrimaryAction(option)}
                        className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-[12px] font-black uppercase tracking-[0.16em] transition-all duration-200 ${
                          connected
                            ? 'cursor-not-allowed border border-sky-500/20 bg-sky-500/10 text-sky-600 dark:text-sky-300'
                            : option.status === 'supported'
                              ? 'bg-[#6143f4] text-white shadow-sm hover:bg-[#5235dc] hover:shadow-md disabled:opacity-60'
                              : 'cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-500'
                        }`}
                      >
                        {connected ? (
                          <span className="inline-flex items-center gap-2">
                            <CheckCircle2 size={15} />
                            Connected
                          </span>
                        ) : option.status === 'supported' ? (
                          <span className="inline-flex items-center gap-2">
                            Connect
                            <ArrowRight size={15} />
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-2">
                            <Clock3 size={15} />
                            Coming Soon
                          </span>
                        )}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="flex min-h-[280px] flex-col items-center justify-center rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50/60 px-6 py-10 text-center dark:border-white/10 dark:bg-white/[0.03]">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/10 text-sky-600">
                <Search size={20} />
              </div>
              <h3 className="text-[16px] font-bold tracking-tight text-[#13082a] dark:text-white">
                No devices found
              </h3>
              <p className="mt-2 max-w-md text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">
                Try a different search term or clear the filter to see all supported, coming-soon, and connected
                integrations.
              </p>
              <button
                type="button"
                onClick={() => setQuery('')}
                className="mt-5 inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-[12px] font-black uppercase tracking-[0.16em] text-[#13082a] transition-colors hover:border-sky-300 hover:text-sky-600 dark:border-white/10 dark:bg-white/5 dark:text-white"
              >
                Clear Search
                <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AddDeviceModal;
