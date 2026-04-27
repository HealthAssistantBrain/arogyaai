const API_PREFIX = '/api/v1';

const stripTrailingSlash = (value) => value.replace(/\/+$/, '');
const stripApiPrefix = (value) => stripTrailingSlash(value).replace(/\/api\/v1$/i, '');

export const getApiRootUrl = (value, fallback = 'http://127.0.0.1:8000') => {
  const raw = (value || fallback).trim();
  return stripApiPrefix(raw);
};

export const getApiUrl = (value, fallback = 'http://127.0.0.1:8000') => {
  const root = getApiRootUrl(value, fallback);
  const sanitized = root.replace(/localhost/g, '127.0.0.1');
  return `${sanitized}${API_PREFIX}`;
};
