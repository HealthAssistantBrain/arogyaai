import { safeArray, safeObject, safeText } from '../utils/safeData';

const CONDITION_DEFAULTS = {
  diabetes: { condition: 'Type 2 Diabetes Mellitus', icdCode: 'E11' },
  hypertension: { condition: 'Essential Hypertension', icdCode: 'I10' },
  cardiovascular: { condition: 'Cardiovascular Disease', icdCode: 'I25.9' },
  respiratory: { condition: 'Respiratory Disorder, Unspecified', icdCode: 'J98.9' },
  sleep: { condition: 'Sleep Disorder, Unspecified', icdCode: 'G47.9' },
  general: { condition: 'General Health Risk Assessment', icdCode: 'Z13.9' },
};

const cleanText = (value, fallback = '', { limit = 420, ensureSentence = false } = {}) => {
  let text = safeText(value, fallback);
  if (!text) return fallback;

  text = text
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s*(.*?)\s*#*\s*$/gm, '$1.')
    .replace(/(^|\s)#{1,6}\s?/g, '. ')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/[*`]+/g, '')
    .replace(/_/g, ' ')
    .replace(/\s*\n+\s*/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:!?])/g, '$1')
    .trim()
    .replace(/^[.\s:-]+|[\s:-]+$/g, '');

  if (limit && text.length > limit) {
    text = text.slice(0, limit).trim().replace(/[\s,;:-]+$/g, '');
  }

  if (ensureSentence && text && !/[.!?]$/.test(text)) {
    text = `${text}.`;
  }

  return text || fallback;
};

const cleanList = (value, { limit = 6, itemLimit = 180, ensureSentence = false } = {}) => {
  const items = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? value.split(/(?<=[.!?])\s+|,\s+/)
      : [];
  const seen = new Set();
  const cleaned = [];

  items.forEach((item) => {
    const text = cleanText(item, '', { limit: itemLimit, ensureSentence });
    const key = text.toLowerCase();
    if (!text || seen.has(key) || cleaned.length >= limit) return;
    seen.add(key);
    cleaned.push(text);
  });

  return cleaned;
};

const toProbability = (value, fallback = 0) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  const normalized = Math.abs(numeric) > 1 ? numeric / 100 : numeric;
  return Math.min(1, Math.max(0, normalized));
};

export const riskLevelFromConfidence = (value) => {
  const probability = toProbability(value);
  if (probability > 0.8) return 'high';
  if (probability >= 0.5) return 'moderate';
  return 'low';
};

export const clinicalRiskTone = (level) => {
  const normalized = String(level || '').toLowerCase();
  if (['high', 'critical'].includes(normalized)) return 'high';
  if (['moderate', 'medium'].includes(normalized)) return 'moderate';
  return 'low';
};

const conditionKey = (value) => {
  const text = String(value || '').toLowerCase();
  if (text.includes('diabetes') || text.includes('glucose') || text.includes('metabolic')) return 'diabetes';
  if (text.includes('hypertension') || text.includes('blood pressure') || text.includes('bp')) return 'hypertension';
  if (text.includes('respiratory') || text.includes('breath')) return 'respiratory';
  if (text.includes('sleep')) return 'sleep';
  if (text.includes('cardio') || text.includes('heart') || text.includes('coronary')) return 'cardiovascular';
  return 'general';
};

const referenceText = (item, index) => {
  if (typeof item === 'string') return cleanText(item, '', { limit: 160 });
  const payload = safeObject(item);
  const citation = safeObject(payload.citation);
  const source = cleanText(payload.source_org ?? payload.source ?? citation.source, '', { limit: 100 });
  const title = cleanText(payload.title ?? citation.title, '', { limit: 140 });
  if (source && title && !title.toLowerCase().includes(source.toLowerCase())) {
    return `${source}: ${title}`;
  }
  return source || title || `Clinical reference ${index + 1}`;
};

const referencesFrom = (...groups) => {
  const seen = new Set();
  const references = [];
  groups.flat().forEach((item, index) => {
    const text = referenceText(item, index);
    const key = text.toLowerCase();
    if (!text || seen.has(key) || references.length >= 4) return;
    seen.add(key);
    references.push(text);
  });
  return references;
};

const recommendationTexts = (value) => cleanList(
  safeArray(value).map((item) => {
    const payload = safeObject(item);
    return payload.description ?? payload.detail ?? payload.text ?? payload.title ?? item;
  }),
  { limit: 5, itemLimit: 260, ensureSentence: true }
);

export const normalizeClinicalCard = (item = {}, fallback = {}) => {
  const payload = safeObject(item);
  const fallbackPayload = safeObject(fallback);
  const key = conditionKey(payload.condition ?? fallbackPayload.condition ?? payload.focus_condition);
  const defaults = CONDITION_DEFAULTS[key] ?? CONDITION_DEFAULTS.general;
  const confidence = toProbability(
    payload.confidence ??
      payload.risk_score ??
      payload.riskScore ??
      payload.risk_percent ??
      payload.riskPercent ??
      fallbackPayload.confidence ??
      fallbackPayload.riskScore ??
      fallbackPayload.risk_score
  );
  const riskLevel = String(payload.risk_level ?? payload.riskLevel ?? riskLevelFromConfidence(confidence)).toLowerCase();
  const recommendations = recommendationTexts(payload.recommendations).length
    ? recommendationTexts(payload.recommendations)
    : recommendationTexts(fallbackPayload.recommendations);

  return {
    condition: cleanText(payload.condition ?? fallbackPayload.condition, defaults.condition, { limit: 120 }),
    icdCode: cleanText(payload.icd_code ?? payload.icdCode ?? fallbackPayload.icd_code, defaults.icdCode, { limit: 24 }),
    confidence,
    confidencePercent: Math.round(confidence * 1000) / 10,
    confidenceLabel: cleanText(payload.confidence_label ?? payload.confidenceLabel ?? riskLevelFromConfidence(confidence), riskLevelFromConfidence(confidence), { limit: 40 }).toUpperCase(),
    riskLevel,
    tone: clinicalRiskTone(riskLevel),
    clinicalInsight: cleanText(
      payload.clinical_insight ?? payload.clinicalInsight ?? fallbackPayload.clinicalInsight ?? fallbackPayload.clinical_insight ?? fallbackPayload.summary,
      `The calibrated model shows a ${riskLevelFromConfidence(confidence)} probability signal for ${defaults.condition}. This is a risk estimate for clinical review, not a final diagnosis.`,
      { limit: 520, ensureSentence: true }
    ),
    symptoms: cleanList(payload.symptoms?.length ? payload.symptoms : fallbackPayload.symptoms, { limit: 6, itemLimit: 100 }),
    recommendations: recommendations.length
      ? recommendations
      : ['Review this risk pattern with a qualified clinician, especially if symptoms are new, persistent, or worsening.'],
    references: referencesFrom(payload.references ?? [], payload.sources ?? [], fallbackPayload.references ?? [], fallbackPayload.sources ?? []),
  };
};

export const normalizeClinicalCards = (payload = {}, fallback = {}) => {
  const source = safeObject(payload);
  const cards = safeArray(source.clinical_cards ?? source.clinicalCards);
  if (cards.length > 0) {
    return cards.map((card) => normalizeClinicalCard(card, { ...fallback, sources: source.sources }));
  }

  const clinicalReport = safeObject(source.clinical_report ?? source.clinicalReport);
  if (Object.keys(clinicalReport).length > 0) {
    return [normalizeClinicalCard(clinicalReport, { ...fallback, sources: source.sources })];
  }

  if (Object.keys(source).length > 0) {
    return [normalizeClinicalCard(source, fallback)];
  }

  return [normalizeClinicalCard({}, fallback)];
};
