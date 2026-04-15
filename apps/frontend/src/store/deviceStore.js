import { create } from 'zustand';

function normalizeDeviceKey(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-');
}

function isConnectedDeviceRecord(device) {
  return Boolean(device?.is_connected ?? device?.connected ?? false);
}

function matchesDeviceId(device, deviceId) {
  const normalizedTarget = normalizeDeviceKey(deviceId);
  const candidates = [
    device?.id,
    device?.provider,
    device?.slug,
    device?.integration,
    device?.name,
  ]
    .filter(Boolean)
    .map(normalizeDeviceKey);

  return candidates.includes(normalizedTarget);
}

const useDeviceStore = create((set, get) => ({
  devices: [],
  setDevices: (devices) => set({ devices }),
  clearDevices: () => set({ devices: [] }),
  isConnected: (deviceId) => get().devices.some((device) => (
    matchesDeviceId(device, deviceId) && isConnectedDeviceRecord(device)
  )),
}));

export default useDeviceStore;
