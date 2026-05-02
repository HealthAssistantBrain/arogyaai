import { apiClient } from './apiClient';

export async function fetchGoogleFitStatus(timezone) {
  const { data } = await apiClient.get('/google-fit/status', {
    params: timezone ? { timezone } : undefined,
  });
  return data.data;
}

export async function startGoogleFitConnect({ timezone, redirectPath }) {
  const { data } = await apiClient.post('/google-fit/connect/start', {
    timezone,
    redirect_path: redirectPath,
  });
  return data.data;
}

export async function fetchGoogleFitConnect({ timezone, redirectPath }) {
  const { data } = await apiClient.get('/integrations/google-fit/url', {
    params: {
      timezone,
      redirect_path: redirectPath,
    },
  });
  return data;
}

export async function syncGoogleFit({ timezone, days = 7 }) {
  const { data } = await apiClient.post('/google-fit/sync', {
    timezone,
    days,
  });
  return data;
}

export async function disconnectGoogleFit() {
  const { data } = await apiClient.delete('/google-fit/disconnect');
  return data.data;
}
