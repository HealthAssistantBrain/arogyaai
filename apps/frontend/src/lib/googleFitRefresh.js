import useDashboardStore from '../store/dashboardStore';
import useDeviceStore from '../store/deviceStore';
import { fetchConnectedDeviceSummaries } from './deviceApi';

export async function refreshAfterGoogleFitSync() {
  const dashboardStore = useDashboardStore.getState();

  await Promise.all([
    fetchConnectedDeviceSummaries().then((summaries) => {
      useDeviceStore.getState().setDevices(summaries);
      return summaries;
    }),
    dashboardStore.fetchDashboardData({ force: true, silent: true }),
    Promise.all([
      dashboardStore.fetchVitals('heart_rate', '24h', { force: true, silent: true }),
      dashboardStore.fetchVitals('steps', '24h', { force: true, silent: true }),
      dashboardStore.fetchVitals('sleep', '24h', { force: true, silent: true }),
    ]),
  ]);
}
