import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../lib/axios';

const clamp = (value, min = 0, max = 100) => Math.max(min, Math.min(max, Number(value) || 0));

const titleCase = (value) =>
  String(value || '')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');

const computeRiskMeta = (value) => {
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return null;
  }

  const riskLevel = score >= 65 ? 'CRITICAL' : score >= 45 ? 'HIGH' : score >= 25 ? 'MODERATE' : 'LOW';
  const status = score >= 65 ? 'Critical' : score >= 45 ? 'High' : score >= 25 ? 'Moderate' : 'Low';

  return {
    score,
    riskLevel,
    status,
    progress: clamp(score),
    deltaFromNeutral: Number((score - 50).toFixed(1)),
    trend: `${score >= 50 ? '+' : '-'}${Math.abs(score - 50).toFixed(1)}% vs neutral`,
  };
};

const normalizeRiskCards = (risks = {}) => {
  const cardSpecs = [
    { key: 'diabetes', title: 'Diabetes', value: risks.diabetes_risk },
    { key: 'hypertension', title: 'Hypertension', value: risks.hypertension_risk },
    { key: 'cad', title: 'CAD', value: risks.cad_risk },
  ];

  return cardSpecs.reduce((acc, card) => {
    const meta = computeRiskMeta(card.value);
    if (!meta) return acc;

    acc.push({
      key: card.key,
      title: card.title,
      label: card.title,
      value: meta.score,
      score: meta.score,
      riskLevel: meta.riskLevel,
      status: meta.status,
      progress: meta.progress,
      deltaFromNeutral: meta.deltaFromNeutral,
      trend: meta.trend,
    });
    return acc;
  }, []);
};

const normalizeDrivers = (drivers = []) => {
  const items = Array.isArray(drivers) ? drivers : [];
  const maxMagnitude = Math.max(...items.map((item) => Math.abs(Number(item.contribution ?? 0))), 1);

  return items.map((driver) => {
    const contribution = Number(driver.contribution ?? 0);
    return {
      key: driver.key ?? driver.label,
      label: driver.label ?? titleCase(driver.key),
      impact: driver.impact ?? `${contribution >= 0 ? '+' : '-'}${Math.abs(contribution).toFixed(1)}`,
      contribution,
      direction: driver.direction ?? (contribution >= 0 ? 'increasing' : 'decreasing'),
      domains: Array.isArray(driver.domains) ? driver.domains : [],
      detail: driver.detail ?? '',
      value: driver.value ?? null,
      barWidth: `${Math.max(8, Math.round((Math.abs(contribution) / maxMagnitude) * 100))}%`,
    };
  });
};

export const useInsightsData = () => {
  const [state, setState] = useState({
    loading: true,
    error: null,
    data: null,
  });

  const fetchInsights = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const response = await api.get('/insights');
      const envelope = response.data ?? {};
      const payload = envelope.data ?? {};
      const status = envelope.status ?? payload.status ?? 'ready';
      console.log('INSIGHTS API:', payload);
      setState({
        loading: false,
        error: null,
        data: {
          status,
          risks: payload.risks ?? {},
          cards: normalizeRiskCards(payload.risks ?? {}),
          drivers: normalizeDrivers(payload.drivers ?? []),
          analysis: payload.analysis ?? '',
          recommendations: Array.isArray(payload.recommendations) ? payload.recommendations : [],
          lastUpdated: payload.last_updated ?? envelope.last_updated ?? null,
          confidence: Number(payload.confidence ?? 0),
          dataPoints: Number(payload.data_points ?? 0),
          featureSnapshot: payload.feature_snapshot ?? {},
        },
      });
    } catch (error) {
      setState({
        loading: false,
        error: error?.response?.data?.error || error?.response?.data?.detail || error?.message || 'Unable to load insights.',
        data: null,
      });
    }
  }, []);

  useEffect(() => {
    void fetchInsights();
  }, [fetchInsights]);

  const sortedCards = useMemo(() => {
    const cards = state.data?.cards || [];
    return [...cards].sort((left, right) => Number(right.score ?? 0) - Number(left.score ?? 0));
  }, [state.data?.cards]);

  return {
    loading: state.loading,
    error: state.error,
    data: state.data || null,
    status: state.data?.status || null,
    risks: state.data?.risks || {},
    cards: sortedCards,
    drivers: state.data?.drivers || [],
    analysis: state.data?.analysis || '',
    recommendations: state.data?.recommendations || [],
    lastUpdated: state.data?.lastUpdated || null,
    confidence: state.data?.confidence || 0,
    dataPoints: state.data?.dataPoints || 0,
    featureSnapshot: state.data?.featureSnapshot || {},
    refresh: fetchInsights,
  };
};
