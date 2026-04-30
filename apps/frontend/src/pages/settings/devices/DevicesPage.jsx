import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Bell, Link2, LoaderCircle, Smartphone, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { apiClient } from '../../../lib/apiClient';
import { ROUTES } from '../../../router/routes';

function formatLastActive(value) {
  if (!value) return 'Never';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Never';
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed);
}

function iconForDevice(device) {
  if (device.provider === 'google-fit') return Activity;
  if (device.provider === 'browser-push') return Bell;
  return Smartphone;
}

const DevicesPage = () => {
  const [devices, setDevices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [disconnectingId, setDisconnectingId] = useState(null);

  const connectedGoogleFit = useMemo(
    () => devices.find((device) => device.provider === 'google-fit'),
    [devices]
  );

  const loadDevices = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/devices');
      const nextDevices = response?.data?.data?.devices ?? [];
      setDevices(Array.isArray(nextDevices) ? nextDevices : []);
    } catch (error) {
      toast.error(error?.response?.data?.error || error?.message || 'Unable to load connected devices.');
      setDevices([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadDevices();
  }, []);

  const handleDisconnect = async (device) => {
    setDisconnectingId(device.id);
    try {
      await apiClient.delete(`/devices/${device.id}`);
      setDevices((current) => current.filter((item) => item.id !== device.id));
      toast.success(`${device.name} disconnected.`);
    } catch (error) {
      toast.error(error?.response?.data?.error || error?.message || 'Unable to disconnect device.');
    } finally {
      setDisconnectingId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-16">
      <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
        <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Connected Devices</h2>
        <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug">
          Manage active wearable integrations and browser push endpoints from one place.
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="rounded-[2rem] border border-[#6143f4]/10 bg-white/80 dark:bg-[#131022]/80 px-6 py-5">
          <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">Active Endpoints</p>
          <p className="mt-3 text-3xl font-black tracking-tighter text-[#13082a] dark:text-white">{devices.length}</p>
        </div>
        <Link
          to={ROUTES.GOOGLE_FIT_SETTINGS}
          className="inline-flex items-center justify-center gap-3 rounded-[1.4rem] bg-[#6143f4] px-8 py-4 text-xs font-black uppercase tracking-[0.2em] text-white shadow-[0_20px_40px_-10px_rgba(97,67,244,0.35)] transition hover:bg-[#4a34c1]"
        >
          <Link2 size={16} strokeWidth={3} />
          {connectedGoogleFit ? 'Manage Google Fit' : 'Connect Google Fit'}
        </Link>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-4 rounded-[2.5rem] border border-[#6143f4]/10 bg-white dark:bg-[#131022] px-8 py-10">
          <LoaderCircle className="animate-spin text-[#6143f4]" size={22} />
          <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Loading device registry</span>
        </div>
      ) : devices.length === 0 ? (
        <div className="rounded-[3rem] border border-dashed border-[#6143f4]/20 bg-white dark:bg-[#131022] px-10 py-16 text-center">
          <div className="mx-auto flex size-20 items-center justify-center rounded-[2rem] bg-[#6143f4]/10 text-[#6143f4]">
            <Smartphone size={34} />
          </div>
          <h3 className="mt-8 text-3xl font-black uppercase italic tracking-tighter text-[#13082a] dark:text-white">No devices connected</h3>
          <p className="mt-4 text-sm font-bold uppercase tracking-tight text-slate-500 dark:text-slate-400 opacity-80">
            Connect Google Fit or enable push notifications to populate your device registry.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {devices.map((device) => {
            const DeviceIcon = iconForDevice(device);
            const isDisconnecting = disconnectingId === device.id;

            return (
              <div
                key={device.id}
                className="flex flex-col gap-6 rounded-[2.5rem] border border-[#6143f4]/8 bg-white dark:bg-[#131022] p-8 shadow-[0_30px_70px_-30px_rgba(19,8,42,0.18)] md:flex-row md:items-center md:justify-between"
              >
                <div className="flex items-start gap-5">
                  <div className="flex size-16 items-center justify-center rounded-[1.4rem] bg-[#6143f4]/10 text-[#6143f4]">
                    <DeviceIcon size={28} />
                  </div>
                  <div className="space-y-3">
                    <div>
                      <p className="text-2xl font-black uppercase italic tracking-tighter text-[#13082a] dark:text-white">{device.name}</p>
                      <p className="mt-1 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">{device.platform}</p>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-2xl bg-slate-50 px-4 py-3 dark:bg-white/5">
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Last Active</p>
                        <p className="mt-2 text-sm font-black uppercase tracking-tight text-[#13082a] dark:text-white">{formatLastActive(device.last_active || device.last_synced_at)}</p>
                      </div>
                      <div className="rounded-2xl bg-slate-50 px-4 py-3 dark:bg-white/5">
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Status</p>
                        <p className="mt-2 text-sm font-black uppercase tracking-tight text-emerald-600">{device.status || 'connected'}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDisconnect(device)}
                  disabled={isDisconnecting}
                  className="inline-flex items-center justify-center gap-3 rounded-[1.3rem] border border-red-500/20 bg-red-500/10 px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-red-500 transition hover:bg-red-500/15 disabled:opacity-60"
                >
                  {isDisconnecting ? <LoaderCircle size={15} className="animate-spin" /> : <Trash2 size={15} />}
                  {isDisconnecting ? 'Disconnecting' : 'Disconnect'}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DevicesPage;
