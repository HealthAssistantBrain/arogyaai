const COOKIE_PREFIX = '; ';

export const getCookieValue = (name) => {
  if (typeof document === 'undefined') return null;

  const cookie = document.cookie
    .split(COOKIE_PREFIX)
    .find((entry) => entry.startsWith(`${name}=`));

  if (!cookie) return null;

  const value = cookie.split('=').slice(1).join('=');
  return decodeURIComponent(value);
};

export const getCsrfToken = () => getCookieValue('csrf_token');

export const applyCsrfHeader = (headers = {}) => {
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }
  return headers;
};
