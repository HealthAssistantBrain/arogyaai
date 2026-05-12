import { getApiUrl } from '../lib/apiBaseUrl';
import { applyCsrfHeader } from '../lib/csrf';
import { getSupabaseClient, supabase } from '../lib/supabaseClient';
import { useAuthStore } from '../store/authStore';
import { parseStreamBuffer } from './chatTransport';

const API_URL = getApiUrl(import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000');

const getCurrentSupabaseToken = async (fallbackToken = null) => {
  const client = getSupabaseClient() ?? supabase;
  if (!client) return fallbackToken;

  try {
    const { data } = await client.auth.getSession();
    return data?.session?.access_token || fallbackToken;
  } catch {
    return fallbackToken;
  }
};

const buildHeaders = async () => {
  const headers = {
    Accept: 'application/x-ndjson',
    'Content-Type': 'application/json',
  };
  const token = await getCurrentSupabaseToken(useAuthStore.getState().token);
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  applyCsrfHeader(headers);
  return headers;
};

export const streamChatResponse = async ({
  query,
  history = [],
  sessionId = null,
  signal = null,
  onEvent = null,
} = {}) => {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: 'POST',
    credentials: 'include',
    headers: await buildHeaders(),
    body: JSON.stringify({
      query,
      history,
      session_id: sessionId,
    }),
    signal,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      message = payload?.error || payload?.detail || payload?.message || message;
    } catch {
      try {
        const text = await response.text();
        if (text) message = text;
      } catch {
        // Ignore downstream parsing errors.
      }
    }
    throw new Error(message);
  }

  if (!response.body?.getReader) {
    throw new Error('Streaming is not available in this browser.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer = parseStreamBuffer(buffer + decoder.decode(value, { stream: true }), onEvent);
  }

  parseStreamBuffer(buffer + '\n', onEvent);
};
