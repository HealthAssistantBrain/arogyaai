import useDashboardStore from '../store/dashboardStore';
import useHealthStore from '../store/healthStore';
import { fetchConnectedDeviceSummaries } from './deviceApi';
import { GOOGLE_FIT_PROVIDER } from './deviceApi';
import useDeviceStore from '../store/deviceStore';
import { setGoogleFitConnectionState } from './googleFitConnectionState';
import useRecommendationSnapshotStore from '../store/recommendationSnapshotStore';

export async function refreshAfterGoogleFitSync() {
  const dashboardStore = useDashboardStore.getState();
  const cacheBust = `${Date.now()}-google-fit-sync`;

  dashboardStore.invalidateWearableCache?.(['heart_rate', 'steps', 'sleep', 'spo2', 'blood_pressure', 'body_temperature', 'glucose']);
  useHealthStore.getState().invalidateMetricsCache?.();
  useRecommendationSnapshotStore.getState().invalidateSnapshot?.();

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
    useHealthStore.getState().fetchHealthMetrics({ force: true, silent: true }),
    Promise.all([
      dashboardStore.fetchVitals('heart_rate', '24h', { force: true, silent: true, cacheBust: `${cacheBust}-heart_rate` }),
      dashboardStore.fetchVitals('steps', '24h', { force: true, silent: true, cacheBust: `${cacheBust}-steps` }),
      dashboardStore.fetchVitals('sleep', '24h', { force: true, silent: true, cacheBust: `${cacheBust}-sleep` }),
    ]),
  ]);

  await dashboardStore.fetchDashboardData({ force: true, silent: true });
}
