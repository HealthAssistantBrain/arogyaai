export const safeArray = (value) => (Array.isArray(value) ? value : []);

export const safeObject = (value) => (
  value && typeof value === 'object' && !Array.isArray(value) ? value : {}
);

export const safeNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const safeString = (value, fallback = '') => {
  if (typeof value === 'string' && value.trim()) {
    return value.trim();
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  return fallback;
};

/**
 * Safely coerces any value to a renderable string.
 * If the value is an object (e.g. a backend recommendation/insight),
 * it extracts the most meaningful text field.
 */
export const safeText = (value, fallback = '') => {
  if (value === null || value === undefined) return fallback;
  if (typeof value === 'string') return value.trim() || fallback;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (typeof value === 'object' && !Array.isArray(value)) {
    return (
      value.title ||
      value.detail ||
      value.message ||
      value.text ||
      value.description ||
      value.label ||
      fallback
    );
  }
  return fallback;
};

export const deepEqual = (obj1, obj2) => {
  if (obj1 === obj2) return true;
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object' || obj1 === null || obj2 === null) {
    return false;
  }

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) return false;

  for (const key of keys1) {
    if (!Object.prototype.hasOwnProperty.call(obj2, key)) return false;
    if (!deepEqual(obj1[key], obj2[key])) return false;
  }

  return true;
};
