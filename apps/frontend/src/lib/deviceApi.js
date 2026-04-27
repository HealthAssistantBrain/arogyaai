import { Watch } from 'lucide-react';

import { apiClient } from './apiClient';
import { fetchGoogleFitStatus } from './googleFitApi';
import { safeApiGet } from './safeApi';

export const GOOGLE_FIT_PROVIDER = 'google-fit';

function normalizeDeviceKey(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-');
}

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

function normalizeConnectionFlag(record = {}) {
  if (typeof record?.is_connected === 'boolean') {
    return record.is_connected;
  }

  if (typeof record?.connected === 'boolean') {
    return record.connected;
  }

  const normalizedStatus = String(
    record?.status ?? record?.connection_status ?? record?.state ?? ''
  ).trim().toLowerCase();

  if (['connected', 'active', 'enabled', 'ok'].includes(normalizedStatus)) {
    return true;
  }

  if (['not_connected', 'disconnected', 'inactive', 'disabled', 'pending', 'error'].includes(normalizedStatus)) {
    return false;
  }

  return true;
}

function normalizeDeviceSummary(record = {}) {
  const name = record?.name || record?.display_name || 'Connected Device';
  const provider = normalizeDeviceKey(
    record?.provider || record?.integration || record?.slug || record?.id || name
  );
  const isConnected = normalizeConnectionFlag(record);
  const lastSyncedAt = record?.last_synced_at ?? record?.lastSyncedAt ?? null;

  return {
    id: record?.id || provider || name,
    provider: provider || 'unknown',
    name,
    is_connected: Boolean(isConnected),
    last_synced_at: lastSyncedAt,
  };
}

export async function fetchConnectedDeviceSummaries() {
  const response = await safeApiGet(
    apiClient,
    '/users/devices',
    {},
    {
      fallback: null,
      ignoreStatuses: [404, 405],
      logLabel: 'GET /users/devices',
    }
  );

  const backendDevices = normalizeListResponse(response?.data)
    .map((device) => normalizeDeviceSummary(device))
    .filter(Boolean);

  if (backendDevices.length > 0) {
    return backendDevices;
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
    if (error?.response?.status !== 404 && error?.response?.status !== 405) {
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

  return [googleFitIntegration];
}
