import { create } from 'zustand';

const useDeviceStore = create((set) => ({
  devices: [],
  setDevices: (devices) => set({ devices }),
  clearDevices: () => set({ devices: [] }),
}));

export default useDeviceStore;
