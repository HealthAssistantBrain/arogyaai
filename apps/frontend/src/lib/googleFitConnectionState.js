import useDeviceStore from '../store/deviceStore';
import useHealthStore from '../store/healthStore';

export function setGoogleFitConnectionState(isConnected) {
  const connected = Boolean(isConnected);

  useDeviceStore.getState().setGoogleFitConnected(connected);
  useHealthStore.getState().setConnection(connected);

  if (!connected) {
    useHealthStore.getState().setSyncing(false);
  }
}
