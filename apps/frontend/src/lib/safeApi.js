function getErrorStatus(error) {
  return error?.response?.status ?? error?.status ?? null;
}

function shouldIgnoreError(error, ignoreStatuses = []) {
  const status = getErrorStatus(error);
  return status !== null && ignoreStatuses.includes(status);
}

export async function safeApiRequest(request, {
  fallback = null,
  ignoreStatuses = [],
  logLabel = 'API request',
} = {}) {
  try {
    return await request();
  } catch (error) {
    if (shouldIgnoreError(error, ignoreStatuses)) {
      console.warn(`[safeApi] ${logLabel} unavailable`, {
        status: getErrorStatus(error),
      });
      return fallback;
    }

    console.error(`[safeApi] ${logLabel} failed`, error);
    return fallback;
  }
}

export async function safeApiGet(client, url, config = {}, options = {}) {
  return safeApiRequest(
    () => client.get(url, config),
    {
      logLabel: `GET ${url}`,
      ...options,
    }
  );
}

export async function safeFetch(url, options = {}) {
  const {
    fallback = null,
    ignoreStatuses = [],
    parseAs = 'json',
    logLabel = url,
    ...requestOptions
  } = options;

  try {
    const response = await fetch(url, requestOptions);

    if (!response.ok) {
      if (ignoreStatuses.includes(response.status)) {
        console.warn(`[safeFetch] ${logLabel} unavailable`, {
          status: response.status,
        });
      } else {
        console.error(`[safeFetch] ${logLabel} failed`, {
          status: response.status,
          statusText: response.statusText,
        });
      }
      return fallback;
    }

    if (parseAs === 'text') {
      return await response.text();
    }

    try {
      return await response.json();
    } catch (error) {
      console.error(`[safeFetch] ${logLabel} returned invalid JSON`, error);
      return fallback;
    }
  } catch (error) {
    console.error(`[safeFetch] ${logLabel} failed`, error);
    return fallback;
  }
}
