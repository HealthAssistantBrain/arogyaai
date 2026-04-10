const API_PREFIX = '/api/v1';

const stripTrailingSlash = (value) => value.replace(/\/+$/, '');
const stripApiPrefix = (value) => stripTrailingSlash(value).replace(/\/api\/v1$/i, '');

export const getApiRootUrl = (value, fallback = 'http://localhost:8000') => {
  const raw = (value || fallback).trim();
  return stripApiPrefix(raw);
};

export const getApiUrl = (value, fallback = 'http://localhost:8000') =>
  `${getApiRootUrl(value, fallback)}${API_PREFIX}`;
