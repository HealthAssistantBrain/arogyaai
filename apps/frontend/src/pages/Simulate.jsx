import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  Info,
  SlidersHorizontal,
  Sparkles,
  Stethoscope,
  TrendingUp,
} from 'lucide-react';
import api from '../lib/axios';
import HeartLoader from '../components/ui/HeartLoader';
import { useUserStore } from '../store/userStore';
import { calculateAge, calculateBMI } from '../utils/userDerived';

const PERIODS = [
  { label: '1 Month', value: 1 },
  { label: '3 Months', value: 3 },
  { label: '6 Months', value: 6 },
  { label: '12 Months', value: 12 },
];

const conditionInputs = {
  cardiovascular: ['heart_rate', 'systolic_bp', 'diastolic_bp', 'steps', 'sleep', 'bmi'],
  diabetes: ['glucose', 'hba1c', 'bmi', 'steps', 'sleep', 'diet_score'],
  respiratory: ['spo2', 'resp_rate', 'activity', 'air_quality', 'smoking', 'sleep'],
};

const INPUT_FIELDS = {
  heart_rate: { label: 'Heart Rate', min: 45, max: 140, step: 1, unit: 'bpm', defaultValue: 72 },
  systolic_bp: { label: 'Systolic BP', min: 90, max: 190, step: 1, unit: 'mmHg', defaultValue: 120 },
  diastolic_bp: { label: 'Diastolic BP', min: 55, max: 120, step: 1, unit: 'mmHg', defaultValue: 80 },
  steps: { label: 'Daily Steps', min: 1500, max: 20000, step: 100, unit: 'steps', defaultValue: 7000 },
  sleep: { label: 'Sleep', min: 4, max: 10, step: 0.5, unit: 'hrs', defaultValue: 7 },
  bmi: { label: 'BMI', min: 12, max: 60, step: 0.1, unit: 'kg/m2', defaultValue: 24 },
  glucose: { label: 'Glucose', min: 60, max: 260, step: 1, unit: 'mg/dL', defaultValue: 90 },
  hba1c: { label: 'HbA1c', min: 4, max: 14, step: 0.1, unit: '%', defaultValue: 5.4 },
  diet_score: { label: 'Diet Score', min: 0, max: 100, step: 1, unit: '/100', defaultValue: 70 },
  spo2: { label: 'SpO2', min: 70, max: 100, step: 1, unit: '%', defaultValue: 97 },
  resp_rate: { label: 'Respiratory Rate', min: 6, max: 40, step: 1, unit: 'breaths/min', defaultValue: 16 },
  activity: { label: 'Active Minutes', min: 0, max: 180, step: 5, unit: 'min/day', defaultValue: 70 },
  air_quality: { label: 'Air Quality Index', min: 0, max: 500, step: 1, unit: 'AQI', defaultValue: 50 },
  smoking: { label: 'Smoking', type: 'boolean', defaultValue: false },
};

const FOCUS_LABELS = {
  cardiovascular: 'Cardiovascular',
  diabetes: 'Diabetes',
  respiratory: 'Respiratory',
};

const clampPercent = (value) => Math.max(0, Math.min(100, Number(value) || 0));

const formatValue = (value, unit) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  const numericValue = Number(value);
  const prettyValue = Number.isInteger(numericValue) ? numericValue.toLocaleString() : numericValue.toFixed(1);
  return unit ? `${prettyValue} ${unit}` : prettyValue;
};

const valueForField = (params, baseline, key) => {
  const field = INPUT_FIELDS[key] || {};
  const value = params?.[key] ?? baseline?.[key] ?? field.defaultValue;
  if (field.type === 'boolean') return Boolean(value);
  return value ?? '';
};

const normalizeControlValue = (key, value) => {
  const field = INPUT_FIELDS[key] || {};
  if (field.type === 'boolean') return Boolean(value);
  if (value === '') return '';
  return Number(value);
};

const metricLabel = (key) =>
  String(key || '')
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');

const conciseClinicalCopy = (value, fallback = '--') => {
  if (!value) return fallback;

  return String(value)
    .replace(/Simulation does not improve cardiovascular risk/gi, 'No meaningful risk improvement')
    .replace(/Simulation required to calculate recovery trajectory\./gi, 'Run a simulation to view recovery trend.')
    .replace(/The simulator will generate a scenario-specific clinical explanation here\./gi, 'Clinical scenario summary will appear here.')
    .replace(/Simulation output is driven by the latest backend scenario analysis\./gi, 'Based on the latest scenario analysis.')
    .replace(/No symptom inference available\./gi, 'No symptom signal detected.')
    .replace(/No condition signals detected\./gi, 'No disease signal detected.')
    .replace(/\s+/g, ' ')
    .trim();
};

const Simulate = () => {
  const { user } = useUserStore();
  const age = calculateAge(user?.dob);

  const [baseline, setBaseline] = useState(null);
  const [medicalConditions, setMedicalConditions] = useState([]);
  const [assumptions, setAssumptions] = useState([]);
  const [focusOptions, setFocusOptions] = useState(['cardiovascular', 'diabetes', 'respiratory']);
  const [focusCondition, setFocusCondition] = useState('cardiovascular');
  const [selectedPeriod, setSelectedPeriod] = useState('6 Months');
  const [params, setParams] = useState({});
  const [simulationResponse, setSimulationResponse] = useState(null);
  const [loadingBaseline, setLoadingBaseline] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState('');
  const [animatedProgress, setAnimatedProgress] = useState(0);

  const timeframeMonths = useMemo(
    () => PERIODS.find((period) => period.label === selectedPeriod)?.value ?? 6,
    [selectedPeriod]
  );
  const activeInputKeys = useMemo(
    () => conditionInputs[focusCondition] || conditionInputs.cardiovascular,
    [focusCondition]
  );
  const activeSimulationParams = useMemo(
    () =>
      activeInputKeys.reduce((payload, key) => {
        const value = valueForField(params, baseline, key);
        if (value !== '') {
          payload[key] = normalizeControlValue(key, value);
        }
        return payload;
      }, {}),
    [activeInputKeys, baseline, params]
  );
  const simulationSignature = useMemo(
    () => JSON.stringify(activeSimulationParams),
    [activeSimulationParams]
  );

  const result = simulationResponse?.data ?? null;
  const riskComparison = result?.risk_comparison || [];
  const keyDrivers = result?.key_drivers || result?.drivers || [];
  const possibleConditions = result?.possible_conditions || [];
  const symptoms = result?.symptoms || [];
  const recommendations = result?.recommendations || [];
  const focusRiskCard = riskComparison.find((item) => item.key === focusCondition);
  const progress = focusRiskCard ? clampPercent(100 - focusRiskCard.simulated_risk) : 0;
  const userBmi = user?.bmi || calculateBMI(user?.height, user?.weight) || '--';

  useEffect(() => {
    let frameId;
    let startTime;
    const from = animatedProgress;
    const to = progress;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const duration = 500;
      const nextValue = from + (to - from) * Math.min(elapsed / duration, 1);
      setAnimatedProgress(nextValue);

      if (elapsed < duration) {
        frameId = window.requestAnimationFrame(animate);
      }
    };

    frameId = window.requestAnimationFrame(animate);

    return () => window.cancelAnimationFrame(frameId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [progress]);

  useEffect(() => {
    const fetchBaseline = async () => {
      setLoadingBaseline(true);
      setError('');
      try {
        const response = await api.get('prediction/simulator/baseline');
        const payload = response.data?.data;
        const nextBaseline = payload?.baseline || {};
        const nextFocusOptions = payload?.focus_options?.length ? payload.focus_options : ['cardiovascular', 'diabetes', 'respiratory'];

        setBaseline(nextBaseline);
        setParams(nextBaseline);
        setMedicalConditions(payload?.medical_conditions || []);
        setAssumptions(payload?.assumptions || []);
        setFocusOptions(nextFocusOptions);
        setFocusCondition(nextFocusOptions[0] || 'cardiovascular');
      } catch (fetchError) {
        setError(fetchError?.response?.data?.error || 'Failed to load simulator baseline.');
      } finally {
        setLoadingBaseline(false);
      }
    };

    void fetchBaseline();
  }, []);

  const executeSimulation = async () => {
    setIsSimulating(true);
    setError('');
    try {
      const response = await api.post('prediction/simulator/run', {
        focus_condition: focusCondition,
        timeframe_months: timeframeMonths,
        simulation: activeSimulationParams,
      });
      setSimulationResponse(response.data ?? null);
    } catch (runError) {
      setError(runError?.response?.data?.error || 'Failed to run simulation.');
    } finally {
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    if (!baseline) return undefined;

    const timer = window.setTimeout(() => {
      void executeSimulation();
    }, 300);

    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    baseline,
    focusCondition,
    timeframeMonths,
    simulationSignature,
  ]);

  if (loadingBaseline) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <div className="flex flex-col items-center gap-4 text-sm font-semibold tracking-wide text-slate-500 dark:text-text-secondary">
          <HeartLoader size={48} color="var(--color-primary)" />
          Loading disease simulator...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#eef2ff_0%,#f8fafc_38%,#edf2f7_100%)] pb-8 antialiased">
      <main className="max-w-[1400px] mx-auto px-4 py-4 md:px-6 md:py-6">
        {error && (
          <div className="mb-4 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-sm">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-6 lg:grid-cols-12 lg:gap-6">
          <div className="md:col-span-3 lg:col-span-4">
            <section className="flex h-full flex-col rounded-2xl border border-white/70 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg">
              <div className="flex items-start justify-between gap-3 border-b border-gray-200 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                    <SlidersHorizontal size={18} />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-gray-900">Simulation Controls</h2>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">Scenario Inputs</p>
                  </div>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${isSimulating ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'}`}>
                  {isSimulating ? 'Updating' : 'Live'}
                </span>
              </div>

              <div className="mt-4 flex-1 space-y-4">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold uppercase tracking-[0.16em] text-gray-500">Condition</label>
                    <select
                      value={focusCondition}
                      onChange={(event) => setFocusCondition(event.target.value)}
                      className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm font-medium text-gray-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15"
                    >
                      {focusOptions.map((option) => (
                        <option key={option} value={option}>
                          {FOCUS_LABELS[option] || option}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold uppercase tracking-[0.16em] text-gray-500">Timeframe</label>
                    <select
                      value={selectedPeriod}
                      onChange={(event) => setSelectedPeriod(event.target.value)}
                      className="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm font-medium text-gray-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15"
                    >
                      {PERIODS.map((period) => (
                        <option key={period.value} value={period.label}>
                          {period.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-3 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-gray-500">Existing Records</p>
                    <p className="text-xs font-semibold text-text-muted">{medicalConditions.length || 0} tracked</p>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {medicalConditions.length > 0 ? (
                      medicalConditions.map((condition) => (
                        <span key={condition} className="rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-xs font-semibold text-gray-700">
                          {condition}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs italic text-text-muted">No chronic condition saved.</span>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 p-3 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-sm">
                  <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                    <h3 className="text-sm font-bold text-gray-900">{FOCUS_LABELS[focusCondition] || metricLabel(focusCondition)} Inputs</h3>
                    <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-text-muted">{activeInputKeys.length} controls</span>
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-3">
                    {activeInputKeys.map((key) => {
                      const field = INPUT_FIELDS[key] || { label: metricLabel(key), defaultValue: '' };
                      const currentValue = valueForField(params, baseline, key);

                      if (field.type === 'boolean') {
                        return (
                          <label key={key} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-3">
                            <span className="text-sm font-semibold text-gray-700">{field.label}</span>
                            <input
                              type="checkbox"
                              checked={Boolean(currentValue)}
                              onChange={(event) =>
                                setParams((current) => ({
                                  ...current,
                                  [key]: event.target.checked,
                                }))
                              }
                              className="size-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                            />
                          </label>
                        );
                      }

                      return (
                        <div key={key} className="space-y-2 rounded-xl bg-slate-50 px-3 py-2.5">
                          <div className="flex items-center justify-between gap-2">
                            <label htmlFor={`simulation-${key}`} className="text-sm font-semibold text-gray-700">
                              {field.label}
                            </label>
                            <span className="text-sm font-bold text-indigo-600">{formatValue(currentValue, field.unit)}</span>
                          </div>
                          <input
                            id={`simulation-${key}`}
                            type="number"
                            min={field.min}
                            max={field.max}
                            step={field.step}
                            value={currentValue}
                            onChange={(event) =>
                              setParams((current) => ({
                                ...current,
                                [key]: normalizeControlValue(key, event.target.value),
                              }))
                            }
                            className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm font-semibold text-gray-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/15"
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="sticky bottom-0 mt-4 border-t border-gray-200 bg-white pt-4">
                <button
                  onClick={() => void executeSimulation()}
                  disabled={isSimulating}
                  className="w-full rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 py-3 text-sm font-bold uppercase tracking-[0.16em] text-text-primary shadow-lg shadow-indigo-900/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSimulating ? 'Recomputing…' : 'Recalculate'}
                </button>
              </div>
            </section>
          </div>

          <div className="space-y-4 md:col-span-3 lg:col-span-5">
            <section className={`relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 p-6 text-text-primary shadow-xl shadow-indigo-950/15 ring-1 ring-white/10 transition-all duration-300 hover:scale-[1.01] ${isSimulating ? 'opacity-70 blur-[1px] animate-pulse' : ''}`}>
              <div className="absolute -right-4 -top-4 opacity-10">
                <Sparkles size={110} />
              </div>

              <div className="relative z-10 space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-purple-100">Projected Recovery</p>
                    <h2 className="mt-1 text-xl font-bold">Low-risk Proximity Score</h2>
                  </div>
                  <div className="rounded-2xl border border-white/15 bg-white/10 px-3 py-2 text-right backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-purple-100">Current Profile</p>
                    <p className="mt-1 text-sm font-semibold text-text-primary/95">
                      Age <span className="font-bold text-text-primary">{age || '--'}</span> • BMI <span className="font-bold text-text-primary">{userBmi}</span> •{' '}
                      <span className="font-bold text-text-primary">{user?.weight || '--'}kg</span>
                    </p>
                  </div>
                </div>

                <div className="flex flex-col gap-4 rounded-2xl border border-stroke bg-white/10 p-4 backdrop-blur-sm sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <div className="font-number text-5xl font-bold leading-none tabular-nums">{Math.round(animatedProgress)}%</div>
                    <p className="mt-2 text-sm opacity-80">
                      {conciseClinicalCopy(result?.normalization?.headline, 'Run a simulation to view recovery trend.')}
                    </p>
                  </div>
                  <div className="w-full max-w-sm space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.14em] text-purple-100">
                      <span>Low-risk progress</span>
                      <span className="font-number text-text-primary tabular-nums">{Math.round(animatedProgress)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/20">
                      <div className="h-full rounded-full bg-white transition-all duration-700" style={{ width: `${animatedProgress}%` }} />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-stroke pt-4">
                  <div className="rounded-xl bg-white/10 p-3 backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-purple-100">Likelihood</p>
                    <p className="mt-1 text-base font-bold text-text-primary">{result?.normalization?.likelihood || '--'}</p>
                  </div>
                  <div className="rounded-xl bg-white/10 p-3 backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-purple-100">Reduction</p>
                    <p className="mt-1 text-base font-bold text-text-primary">
                      {Number.isFinite(Number(result?.normalization?.risk_reduction_points))
                        ? `${Number(result.normalization.risk_reduction_points).toFixed(1)} pts`
                        : '--'}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-stroke bg-black/10 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-purple-100">Simulation Outcome</p>
                    <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-text-primary/90">
                      {conciseClinicalCopy(result?.outcome?.headline, 'Outcome pending')}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-purple-50/90">
                    {conciseClinicalCopy(result?.summary, 'Clinical scenario summary will appear here.')}
                  </p>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-white/70 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg">
              <div className="flex items-center justify-between gap-3 border-b border-gray-200 pb-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                    <Activity size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-gray-900">Risk Comparison</h3>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">Baseline vs Simulated</p>
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {riskComparison.length > 0 ? (
                  riskComparison.map((risk) => (
                    <div key={risk.key} className="rounded-2xl border border-gray-200 bg-slate-50/80 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h4 className="text-sm font-bold uppercase tracking-[0.08em] text-gray-800">{risk.label}</h4>
                        <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${risk.delta > 0 ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                          {risk.delta > 0 ? 'Worse' : 'Improved'}
                        </span>
                      </div>

                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.12em]">
                            <span className="text-text-muted">Current Risk</span>
                            <span className="text-gray-600">{risk.current_risk}%</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                            <div className="h-full bg-gray-500 transition-all duration-500" style={{ width: `${clampPercent(risk.current_risk)}%` }} />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.12em]">
                            <span className="text-indigo-500">Simulated Risk</span>
                            <span className={risk.delta > 0 ? 'text-red-500' : 'text-indigo-600'}>{risk.simulated_risk}%</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                            <div
                              className={`h-full transition-all duration-500 ${risk.delta > 0 ? 'bg-red-500' : 'bg-indigo-600'} ${isSimulating ? 'animate-pulse' : ''}`}
                              style={{ width: `${clampPercent(risk.simulated_risk)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-gray-200 bg-slate-50 p-4 text-sm text-gray-500">
                    No risk comparison data available yet.
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="md:col-span-6 lg:col-span-3">
            <section className="sticky top-6 h-fit">
              <div className="max-h-[80vh] overflow-y-auto rounded-2xl bg-background p-4 text-text-primary shadow-xl transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl">
                <div className="flex items-center gap-3 border-b border-stroke pb-3">
                  <div className="flex size-10 items-center justify-center rounded-2xl bg-card text-indigo-300">
                    <Brain size={18} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold">AI Insights</h3>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-gray-500">Interpreted Scenario Signals</p>
                  </div>
                </div>

                <div className="mt-4 space-y-4">
                  <div className="rounded-xl bg-card p-3 transition-all duration-300 hover:-translate-y-0.5">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-indigo-300">
                      {conciseClinicalCopy(result?.outcome?.headline, 'Outcome pending')}
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-text-primary">
                      {conciseClinicalCopy(result?.summary, 'Clinical scenario summary will appear here.')}
                    </p>
                  </div>

                  <div className="space-y-2 border-t border-stroke pt-3">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Key Drivers</h4>
                    {keyDrivers.length > 0 ? (
                      keyDrivers.map((driver) => (
                        <div key={`${driver.feature_name}-${driver.source || 'driver'}`} className="rounded-xl bg-card p-3 text-xs text-text-secondary transition-all duration-300 hover:-translate-y-0.5">
                          <div className="flex items-start gap-2.5">
                            <Info size={14} className="mt-0.5 shrink-0 text-sky-400" />
                            <div>
                              <p className="font-bold text-text-primary">{driver.title || metricLabel(driver.feature_name)}</p>
                              <p className="mt-1 leading-relaxed text-text-secondary">
                                {conciseClinicalCopy(driver.description, 'Contributes to the simulated risk.')}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl bg-card p-3 text-xs italic text-gray-500">No key drivers were returned by the simulator.</div>
                    )}
                  </div>

                  <div className="space-y-2 border-t border-stroke pt-3">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Possible Diseases</h4>
                    {possibleConditions.length > 0 ? (
                      possibleConditions.map((condition) => (
                        <div key={condition} className="rounded-xl bg-card p-3 text-sm font-semibold text-amber-100 transition-all duration-300 hover:-translate-y-0.5">
                          {condition}
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl bg-card p-3 text-xs italic text-gray-500">No condition signals detected.</div>
                    )}
                  </div>

                  <div className="space-y-2 border-t border-stroke pt-3">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Symptoms</h4>
                    {symptoms.length > 0 ? (
                      symptoms.map((symptom) => (
                        <div key={symptom} className="rounded-xl bg-card p-3 text-sm font-semibold text-sky-100 transition-all duration-300 hover:-translate-y-0.5">
                          {symptom}
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl bg-card p-3 text-xs italic text-gray-500">No symptom signal detected.</div>
                    )}
                  </div>

                  <div className="space-y-2 border-t border-stroke pt-3">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">Recommendations</h4>
                    {recommendations.length > 0 ? (
                      recommendations.map((recommendation) => (
                        <div key={`${recommendation.feature}-${recommendation.title}`} className="rounded-xl bg-card p-3 text-xs text-text-primary transition-all duration-300 hover:-translate-y-0.5">
                          <div className="flex items-start gap-2.5">
                            <TrendingUp size={14} className="mt-0.5 shrink-0 text-emerald-400" />
                            <div>
                              <p className="font-bold text-text-primary">{recommendation.title}</p>
                              <p className="mt-1 leading-relaxed text-text-secondary">{conciseClinicalCopy(recommendation.description, 'Clinical action recommended.')}</p>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-xl bg-card p-3 text-xs italic text-gray-500">No recommendations returned.</div>
                    )}
                  </div>

                  <div className="space-y-2 border-t border-stroke pt-3">
                    <div className="rounded-xl bg-card p-3 transition-all duration-300 hover:-translate-y-0.5">
                      <div className="flex items-center gap-2.5">
                        <Stethoscope size={16} className="text-indigo-300" />
                        <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-text-secondary">
                          {simulationResponse?.source === 'hybrid_ml_plus_rules' ? 'Hybrid ML + Rule Engine' : 'Deterministic Rule Engine'}
                        </span>
                      </div>
                      <p className="mt-2 text-[11px] leading-relaxed text-text-muted">
                        {conciseClinicalCopy(result?.outcome?.summary, 'Based on the latest scenario analysis.')}
                      </p>
                    </div>

                    <div className="rounded-xl bg-card p-3 transition-all duration-300 hover:-translate-y-0.5">
                      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-gray-500">Engine Assumptions</p>
                      <div className="mt-2 space-y-2">
                        {assumptions.length > 0 ? (
                          assumptions.map((item) => (
                            <div key={item} className="flex items-start gap-2 text-[11px] text-text-muted">
                              <div className="mt-1 size-1.5 shrink-0 rounded-full bg-indigo-400" />
                              <span>{item}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-[11px] italic text-gray-500">No assumptions provided.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Simulate;

