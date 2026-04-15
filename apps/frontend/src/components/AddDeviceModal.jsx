import React from 'react';
import { X, Watch } from 'lucide-react';

import Button from './ui/Button';

function AddDeviceModal({ open, onClose, integrations = [] }) {
  if (!open) {
    return null;
  }

  const items = integrations.length > 0
    ? integrations
    : [
        {
          id: 'google-fit',
          name: 'Google Fit',
          description: 'Connect or reconnect Google Fit using the existing backend flow.',
          actionLabel: 'Connect Google Fit',
          icon: Watch,
          onSelect: () => {},
        },
      ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#0B0819]/60 px-4 py-6 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-device-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-[#131022]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">
              Device onboarding
            </p>
            <h2 id="add-device-title" className="mt-2 text-[26px] font-black tracking-tight text-[#13082a] dark:text-white">
              Add Device
            </h2>
            <p className="mt-2 max-w-xl text-[13px] leading-relaxed text-slate-500 dark:text-slate-400">
              Choose a backend-backed integration to continue the device setup flow.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition-colors hover:border-[#6143f4]/30 hover:text-[#6143f4] dark:border-white/10 dark:text-slate-300"
            aria-label="Close add device modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {items.map((integration) => {
            const Icon = integration.icon || Watch;

            return (
              <div
                key={integration.id}
                className="flex min-h-[220px] flex-col rounded-[1.5rem] border border-slate-200/70 bg-slate-50/80 p-5 dark:border-white/10 dark:bg-white/[0.03]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div
                    className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#6143f4]/10 text-[#6143f4]"
                  >
                    <Icon size={20} />
                  </div>
                  <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-600">
                    Supported
                  </span>
                </div>

                <h3 className="mt-4 text-[16px] font-bold tracking-tight text-[#13082a] dark:text-white">
                  {integration.name}
                </h3>
                <p className="mt-2 text-[12px] leading-relaxed text-slate-500 dark:text-slate-400">
                  {integration.description}
                </p>

                <div className="mt-auto pt-5">
                  <Button
                    type="button"
                    onClick={() => {
                      onClose();
                      if (typeof integration.onSelect === 'function') {
                        integration.onSelect();
                      }
                    }}
                    className="w-full"
                  >
                    {integration.actionLabel || `Connect ${integration.name}`}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default AddDeviceModal;
