import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  HeartPulse,
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

const SLIDERS = [
  { key: 'sleep_hours', label: 'Sleep', min: 4, max: 12, step: 0.5, unit: 'hrs' },
  { key: 'daily_steps', label: 'Daily Steps', min: 2000, max: 20000, step: 100, unit: '' },
  { key: 'heart_rate_bpm', label: 'Heart Rate', min: 45, max: 150, step: 1, unit: 'bpm' },
  { key: 'systolic_bp', label: 'Systolic BP', min: 90, max: 190, step: 1, unit: 'mmHg' },
  { key: 'diastolic_bp', label: 'Diastolic BP', min: 55, max: 120, step: 1, unit: 'mmHg' },
  { key: 'weight_kg', label: 'Weight', min: 35, max: 150, step: 1, unit: 'kg' },
  { key: 'stress_level', label: 'Stress Level', min: 1, max: 10, step: 1, unit: '/10' },
  { key: 'weekly_exercise_hours', label: 'Weekly Exercise', min: 0, max: 20, step: 0.5, unit: 'hrs' },
];

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


const Simulate = () => {
  // Centralized user store
  const { user } = useUserStore();

  console.log("GLOBAL USER (Simulator):", user);

  const age = calculateAge(user?.dob);

  const [baseline, setBaseline] = useState(null);
  const [medicalConditions, setMedicalConditions] = useState([]);
  const [assumptions, setAssumptions] = useState([]);
  const [focusOptions, setFocusOptions] = useState(['cardiovascular', 'diabetes', 'respiratory']);
  const [focusCondition, setFocusCondition] = useState('cardiovascular');
  const [selectedPeriod, setSelectedPeriod] = useState('6 Months');
  const [params, setParams] = useState({});
  const [result, setResult] = useState(null);
  const [loadingBaseline, setLoadingBaseline] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState('');

  const timeframeMonths = useMemo(
    () => PERIODS.find((period) => period.label === selectedPeriod)?.value ?? 6,
    [selectedPeriod]
  );

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
        setError(fetchError?.response?.data?.error || 'Simulator baseline load nahi ho paaya.');
      } finally {
        setLoadingBaseline(false);
      }
    };

    fetchBaseline();
  }, []);

  useEffect(() => {
    if (!baseline) return;

    const runInitialSimulation = async () => {
      setIsSimulating(true);
      setError('');
      try {
        const response = await api.post('prediction/simulator/run', {
          focus_condition: focusCondition,
          timeframe_months: timeframeMonths,
          simulation: params,
        });
        setResult(response.data?.data || null);
      } catch (runError) {
        setError(runError?.response?.data?.error || 'Simulation run nahi ho paaya.');
      } finally {
        setIsSimulating(false);
      }
    };

    runInitialSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseline, focusCondition, timeframeMonths]);

  const runSimulation = async () => {
    setIsSimulating(true);
    setError('');
    try {
      const response = await api.post('prediction/simulator/run', {
        focus_condition: focusCondition,
        timeframe_months: timeframeMonths,
        simulation: params,
      });
      setResult(response.data?.data || null);
    } catch (runError) {
      setError(runError?.response?.data?.error || 'Simulation run nahi ho paaya.');
    } finally {
      setIsSimulating(false);
    }
  };

  const focusSummary = result?.normalization;
  const riskComparison = result?.risk_comparison || [];
  const progress = focusSummary ? clampPercent(100 - (result?.risk_comparison?.find((item) => item.key === focusCondition)?.simulated_risk || 0)) : 0;

  if (loadingBaseline) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <div className="flex flex-col items-center gap-4 text-sm font-semibold tracking-wide text-slate-500 dark:text-white/80">
          <HeartLoader size={48} color="#6143f4" />
          Loading disease simulator...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f1f3f7] pb-12 antialiased">
      <main className="max-w-[1600px] mx-auto p-4 md:p-8">
        {error && (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 flex items-start gap-3 shadow-md">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="bg-[#e9ecf2] rounded-[2rem] p-6 md:p-8 border border-white/60 shadow-inner">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
            {/* LEFT PANEL: INPUT CONTROLS */}
            <div className="md:col-span-4 space-y-6">
              <section className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-lg hover:shadow-xl transition-all duration-300 p-7 border border-white/60">
                <div className="flex items-center gap-3 mb-6">
                  <div className="size-12 rounded-2xl bg-purple-50 flex items-center justify-center border border-purple-100/50">
                    <SlidersHorizontal className="text-purple-600" size={22} />
                  </div>
                  <div>
                    <h2 className="text-lg font-extrabold text-gray-900">Simulation Controls</h2>
                    <p className="text-xs text-gray-500 uppercase tracking-widest font-bold">Scenario Setup</p>
                  </div>
                </div>

                <div className="space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-semibold text-gray-700 block mb-2">Condition</label>
                      <select
                        value={focusCondition}
                        onChange={(e) => setFocusCondition(e.target.value)}
                        className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-900 outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all"
                      >
                        {focusOptions.map((option) => (
                          <option key={option} value={option}>
                            {FOCUS_LABELS[option] || option}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-sm font-semibold text-gray-700 block mb-2">Timeframe</label>
                      <select
                        value={selectedPeriod}
                        onChange={(e) => setSelectedPeriod(e.target.value)}
                        className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-900 outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 transition-all"
                      >
                        {PERIODS.map((p) => (
                          <option key={p.value} value={p.label}>
                            {p.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="rounded-xl bg-gray-50 border border-gray-100 p-4">
                    <p className="text-[11px] uppercase tracking-wider text-gray-400 font-bold mb-3">Existing Records</p>
                    <div className="flex flex-wrap gap-2">
                      {medicalConditions.length > 0 ? (
                        medicalConditions.map((condition) => (
                          <span key={condition} className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-xs font-semibold text-gray-700 shadow-sm">
                            {condition}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-gray-400 italic">No chronic condition saved.</span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-6 pt-4 border-t border-gray-100">
                    <h3 className="text-sm font-bold text-gray-900 mb-4">Adjust Parameters</h3>
                    {SLIDERS.map((slider) => (
                      <div key={slider.key} className="space-y-3">
                        <div className="flex justify-between items-center">
                          <label className="text-sm font-semibold text-gray-600">{slider.label}</label>
                          <span className="text-sm font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-md">
                            {formatValue(params?.[slider.key], slider.unit)}
                          </span>
                        </div>
                        <div className="relative h-6 flex items-center group">
                          <input
                            className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-purple-600"
                            type="range"
                            min={slider.min}
                            max={slider.max}
                            step={slider.step}
                            value={params?.[slider.key] ?? baseline?.[slider.key] ?? slider.min}
                            onChange={(e) =>
                              setParams((current) => ({
                                ...current,
                                [slider.key]: slider.step < 1 ? parseFloat(e.target.value) : Number(e.target.value),
                              }))
                            }
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={runSimulation}
                    disabled={isSimulating}
                    className="w-full mt-6 py-4 rounded-2xl bg-purple-600 text-white font-bold hover:bg-purple-700 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-purple-600/20 text-sm uppercase tracking-wide"
                  >
                    {isSimulating ? (
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Running Simulation...
                      </div>
                    ) : 'Run Simulation'}
                  </button>
                </div>
              </section>
            </div>

            {/* CENTER PANEL: RESULTS + METRICS */}
            <div className="md:col-span-5 space-y-6">
              <section className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-lg hover:shadow-xl transition-all duration-300 p-7 border border-white/60">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-3">
                    <div className="size-12 rounded-2xl bg-blue-50 flex items-center justify-center border border-blue-100/50">
                      <Activity className="text-blue-600" size={22} />
                    </div>
                    <div>
                      <h2 className="text-lg font-extrabold text-gray-900">Risk Comparison</h2>
                      <p className="text-xs text-gray-500 uppercase tracking-widest font-bold">Before vs. After</p>
                    </div>
                  </div>
                  <div className="text-right hidden sm:block">
                    <p className="text-[10px] text-gray-400 font-bold uppercase">Current Profile</p>
                    <p className="text-xs font-bold text-gray-600">
                      Age {age || '--'} • BMI {user?.bmi || calculateBMI(user?.height, user?.weight) || '--'} • {user?.weight || '--'}kg
                    </p>
                  </div>
                </div>

                <div className="space-y-10">
                  {riskComparison.map((risk) => (
                    <div key={risk.key} className="space-y-4">
                      <h4 className="text-sm font-bold text-gray-800 uppercase tracking-tight">{risk.label}</h4>
                      <div className="grid gap-3">
                        {/* Current Risk Bar */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between text-[11px] font-bold">
                            <span className="text-gray-400 uppercase">Current Risk</span>
                            <span className="text-gray-500">{risk.current_risk}%</span>
                          </div>
                          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gray-400 transition-all duration-500"
                              style={{ width: `${clampPercent(risk.current_risk)}%` }}
                            />
                          </div>
                        </div>
                        {/* Simulated Risk Bar */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between text-[11px] font-bold">
                            <span className="text-purple-400 uppercase">Simulated Risk</span>
                            <span className={`${risk.delta > 0 ? 'text-red-500' : 'text-purple-600'}`}>{risk.simulated_risk}%</span>
                          </div>
                          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full transition-all duration-500 ${risk.delta > 0 ? 'bg-red-500' : 'bg-purple-600'} ${isSimulating ? 'animate-pulse' : ''}`}
                              style={{ width: `${clampPercent(risk.simulated_risk)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="bg-gradient-to-br from-purple-600 to-indigo-600 rounded-3xl p-8 text-white shadow-2xl shadow-purple-900/10 relative overflow-hidden">
                <div className="absolute -right-6 -top-6 opacity-10">
                  <Sparkles size={120} />
                </div>

                <div className="relative z-10">
                  <p className="text-[11px] uppercase tracking-widest text-purple-100 font-bold mb-1">Projected Recovery</p>
                  <h3 className="text-xl font-bold mb-6">Low-risk Proximity Score</h3>

                  <div className="flex items-center gap-6">
                    <div className="text-6xl font-black">{Math.round(progress)}%</div>
                    <div className="flex-1 space-y-4">
                      <div className="h-3 bg-white/20 rounded-full overflow-hidden backdrop-blur-sm">
                        <div className="h-full bg-white rounded-full transition-all duration-1000" style={{ width: `${progress}%` }} />
                      </div>
                      <p className="text-xs font-medium text-purple-50 leading-relaxed">
                        {focusSummary?.headline || 'Simulation required to calculate score.'}
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 pt-5 border-t border-white/10 grid grid-cols-2 gap-4">
                    <div className="bg-white/10 rounded-xl p-3">
                      <p className="text-[10px] uppercase text-purple-100 font-bold">Likelihood</p>
                      <p className="text-sm font-bold mt-0.5">{focusSummary?.likelihood || '--'}</p>
                    </div>
                    <div className="bg-white/10 rounded-xl p-3">
                      <p className="text-[10px] uppercase text-purple-100 font-bold">Reduction</p>
                      <p className="text-sm font-bold mt-0.5">-{focusSummary?.risk_reduction_points ?? '--'} pts</p>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {/* RIGHT PANEL: AI INSIGHTS */}
            <div className="md:col-span-3 space-y-6">
              <section className="bg-gradient-to-br from-[#0f172a] to-[#1e293b] text-gray-200 rounded-3xl p-7 shadow-2xl border border-slate-700/50 relative overflow-hidden h-full">
                <div className="absolute right-0 top-0 p-4 opacity-5 rotate-12">
                  <Brain size={140} />
                </div>

                <div className="relative z-10 flex flex-col h-full">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="size-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 backdrop-blur-sm">
                      <Brain className="text-purple-400" size={22} />
                    </div>
                    <h3 className="font-extrabold text-lg text-white">AI Insights</h3>
                  </div>

                  <div className="flex-1 space-y-6">
                    <div className="bg-purple-500/10 border-l-4 border-purple-500 p-4 rounded-r-xl">
                      <p className="text-sm leading-relaxed text-purple-50 italic">
                        "{result?.focus_summary || 'Detailed condition-specific insights will appear here after calculation.'}"
                      </p>
                    </div>

                    <div className="space-y-3">
                      <h4 className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Key Risk Drivers</h4>
                      <div className="space-y-2">
                        {(result?.drivers || []).length > 0 ? (
                          (result?.drivers || []).map((driver) => (
                            <div key={driver} className="flex items-start gap-2.5 p-3 rounded-xl bg-white/5 border border-white/5 text-xs text-gray-300">
                              <Info size={14} className="mt-0.5 text-blue-400 shrink-0" />
                              <span>{driver}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-gray-500 italic">Drivers will be identified post-simulation.</p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-3 pt-2">
                      <h4 className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Recommendations</h4>
                      <div className="space-y-2">
                        {(result?.recommendations || []).length > 0 ? (
                          (result?.recommendations || []).map((rec) => (
                            <div key={rec} className="flex items-start gap-2.5 p-3 rounded-xl bg-green-500/10 border border-green-500/10 text-xs text-green-100">
                              <TrendingUp size={14} className="mt-0.5 text-green-400 shrink-0" />
                              <span>{rec}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-gray-500 italic">Awaiting simulation data...</p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-3 pt-2 border-t border-white/5 mt-4">
                      <h4 className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Engine Assumptions</h4>
                      <div className="space-y-2">
                        {assumptions.length > 0 ? (
                          assumptions.map((item) => (
                            <div key={item} className="flex items-start gap-2.5 p-2 rounded-lg bg-white/5 text-[10px] text-gray-400">
                              <div className="size-1.5 rounded-full bg-purple-500 mt-1 shrink-0" />
                              <span>{item}</span>
                            </div>
                          ))
                        ) : (
                          <p className="text-[10px] text-gray-500 italic">No assumptions provided.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-auto pt-8">
                    <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                      <div className="flex items-center gap-3 mb-2">
                        <Stethoscope size={18} className="text-blue-400" />
                        <span className="text-xs font-bold uppercase tracking-tight">Clinical Next Step</span>
                      </div>
                      <p className="text-[11px] text-gray-400 leading-relaxed">
                        This scenario analysis can be exported for medical professional review.
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Simulate;
