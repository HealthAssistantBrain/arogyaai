import { Watch } from 'lucide-react';

import { apiClient } from './apiClient';
import { fetchGoogleFitStatus } from './googleFitApi';

export const GOOGLE_FIT_PROVIDER = 'google-fit';

function normalizeListResponse(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload?.data)) {
    return payload.data;
  }

  if (Array.isArray(payload?.data?.data)) {
    return payload.data.data;
  }

  if (Array.isArray(payload?.data?.devices)) {
    return payload.data.devices;
  }

  if (Array.isArray(payload?.data?.items)) {
    return payload.data.items;
  }

  if (Array.isArray(payload?.devices)) {
    return payload.devices;
  }

  return [];
}

function isIgnoredRouteError(error) {
  const status = error?.response?.status;
  return status === 404 || status === 405;
}

function normalizeDeviceSummary(record = {}) {
  const provider = String(record?.provider || record?.integration || record?.slug || record?.id || '').toLowerCase();
  const isConnected = record?.is_connected ?? record?.connected ?? true;
  const lastSyncedAt = record?.last_synced_at ?? record?.lastSyncedAt ?? null;
  const name = record?.name || record?.display_name || (provider === GOOGLE_FIT_PROVIDER ? 'Google Fit' : 'Connected Device');

  return {
    id: record?.id || provider || name,
    provider: provider || 'unknown',
    name,
    is_connected: Boolean(isConnected),
    last_synced_at: lastSyncedAt,
  };
}

export async function fetchConnectedDeviceSummaries() {
  let deviceApiError = null;

  try {
    const { data } = await apiClient.get('/devices');
    const backendDevices = normalizeListResponse(data)
      .map((device) => normalizeDeviceSummary(device))
      .filter(Boolean);

    if (backendDevices.length > 0) {
      return backendDevices;
    }
  } catch (error) {
    if (!isIgnoredRouteError(error)) {
      deviceApiError = error;
    }
  }

  try {
    const googleFitStatus = await fetchGoogleFitStatus();
    if (googleFitStatus?.connected) {
      return [normalizeDeviceSummary({
        id: GOOGLE_FIT_PROVIDER,
        provider: GOOGLE_FIT_PROVIDER,
        name: 'Google Fit',
        is_connected: true,
        last_synced_at: googleFitStatus?.last_synced_at ?? null,
      })];
    }
  } catch (error) {
    if (deviceApiError) {
      throw deviceApiError;
    }
    if (!isIgnoredRouteError(error)) {
      throw error;
    }
  }

  return [];
}

export async function fetchSupportedDeviceIntegrations(onGoogleFitConnect) {
  const googleFitIntegration = {
    id: GOOGLE_FIT_PROVIDER,
    name: 'Google Fit',
    description: 'Connect or reconnect Google Fit using the existing backend flow.',
    actionLabel: 'Connect Google Fit',
    icon: Watch,
    onSelect: onGoogleFitConnect,
  };

  try {
    const { data } = await apiClient.get('/devices/available');
    const integrations = normalizeListResponse(data)
      .map((integration) => {
        const provider = String(integration?.provider || integration?.slug || integration?.id || '').toLowerCase();
        if (provider !== GOOGLE_FIT_PROVIDER) {
          return null;
        }

        return {
          id: GOOGLE_FIT_PROVIDER,
          name: integration?.name || googleFitIntegration.name,
          description: integration?.description || googleFitIntegration.description,
          actionLabel: integration?.action_label || integration?.actionLabel || googleFitIntegration.actionLabel,
          icon: Watch,
          onSelect: onGoogleFitConnect,
        };
      })
      .filter(Boolean);

    return integrations.length > 0 ? integrations : [googleFitIntegration];
  } catch {
    return [googleFitIntegration];
  }
}
