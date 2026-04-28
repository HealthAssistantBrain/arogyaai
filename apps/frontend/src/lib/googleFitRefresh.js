import useDashboardStore from '../store/dashboardStore';
import useHealthStore from '../store/healthStore';
import { fetchConnectedDeviceSummaries } from './deviceApi';
import { GOOGLE_FIT_PROVIDER } from './deviceApi';
import useDeviceStore from '../store/deviceStore';
import { setGoogleFitConnectionState } from './googleFitConnectionState';

export async function refreshAfterGoogleFitSync() {
  const dashboardStore = useDashboardStore.getState();

  await Promise.all([
    fetchConnectedDeviceSummaries().then((summaries) => {
      useDeviceStore.getState().setDevices(summaries);
      setGoogleFitConnectionState(
        Array.isArray(summaries) && summaries.some(
          (device) => device?.provider === GOOGLE_FIT_PROVIDER && device?.is_connected
        )
      );
      return summaries;
    }),
    dashboardStore.fetchDashboardData({ force: true, silent: true }),
    useHealthStore.getState().fetchHealthMetrics({ force: true, silent: true }),
    Promise.all([
      dashboardStore.fetchVitals('heart_rate', '24h', { force: true, silent: true }),
      dashboardStore.fetchVitals('steps', '24h', { force: true, silent: true }),
      dashboardStore.fetchVitals('sleep', '24h', { force: true, silent: true }),
    ]),
  ]);
}
