import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  HeartPulse,
  Info,
  LoaderCircle,
  SlidersHorizontal,
  Sparkles,
  Stethoscope,
  TrendingUp,
} from 'lucide-react';
import api from '../lib/axios';

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

const getSliderPercent = (value, min, max) => {
  if (max <= min) return 0;
  return ((Number(value) - min) / (max - min)) * 100;
};

const Simulate = () => {
  const [baseline, setBaseline] = useState(null);
  const [profile, setProfile] = useState(null);
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
        setProfile(payload?.profile || null);
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
      <div className="min-h-screen bg-[#13082A] text-white flex items-center justify-center">
        <div className="flex items-center gap-3 text-sm font-semibold tracking-wide text-white/80">
          <LoaderCircle className="animate-spin" size={18} />
          Loading disease simulator...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#13082A] text-slate-100 antialiased">
      <main className="flex-1 flex flex-col overflow-y-auto bg-[radial-gradient(circle_at_top_left,_rgba(96,67,244,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(0,156,222,0.12),_transparent_32%),linear-gradient(180deg,_#140a2c_0%,_#0f0820_100%)]">
        <header className="h-16 flex items-center justify-between px-8 bg-[#140c2d]/80 backdrop-blur-md sticky top-0 z-30 border-b border-white/5">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-white/40 font-bold">Clinical Sandbox</p>
            <h1 className="text-2xl font-black tracking-tight text-white">Disease Simulator</h1>
          </div>
          <div className="flex bg-white/5 p-1 rounded-xl border border-white/10">
            {PERIODS.map((period) => (
              <button
                key={period.label}
                onClick={() => setSelectedPeriod(period.label)}
                className={`px-4 py-2 text-sm font-bold rounded-lg transition-all ${
                  period.label === selectedPeriod
                    ? 'bg-[#6043F4] text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
        </header>

        <div className="p-8 max-w-[1400px] mx-auto w-full space-y-6">
          {error ? (
            <div className="rounded-2xl border border-red-400/20 bg-red-500/10 px-5 py-4 text-sm text-red-100 flex items-start gap-3">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}

          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-12 lg:col-span-4 space-y-6">
              <section className="bg-white/5 border border-white/10 rounded-3xl p-6 shadow-2xl shadow-black/20">
                <div className="flex items-center gap-3 mb-5">
                  <div className="size-11 rounded-2xl bg-[#6043F4]/20 border border-[#6043F4]/30 flex items-center justify-center">
                    <HeartPulse className="text-[#8B75FF]" size={22} />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-white/40 font-bold">Focus Disease</p>
                    <h2 className="text-lg font-black text-white">Scenario Setup</h2>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-white/70 block mb-2">Condition to simulate</label>
                    <select
                      value={focusCondition}
                      onChange={(e) => setFocusCondition(e.target.value)}
                      className="w-full rounded-2xl border border-white/10 bg-[#20103f] px-4 py-3 text-sm font-semibold text-white outline-none"
                    >
                      {focusOptions.map((option) => (
                        <option key={option} value={option}>
                          {FOCUS_LABELS[option] || option}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="rounded-2xl border border-white/8 bg-black/15 p-4">
                    <p className="text-[11px] uppercase tracking-[0.22em] text-white/35 font-bold mb-2">Existing health record</p>
                    <div className="flex flex-wrap gap-2">
                      {medicalConditions.length > 0 ? (
                        medicalConditions.map((condition) => (
                          <span key={condition} className="px-3 py-1.5 rounded-full bg-white/8 border border-white/10 text-xs font-semibold text-white/80">
                            {condition}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-white/55">No chronic condition saved yet. Generic risk model use hoga.</span>
                      )}
                    </div>
                  </div>
                </div>
              </section>

              <section className="bg-white/5 border border-white/10 rounded-3xl p-6 shadow-2xl shadow-black/20">
                <h3 className="font-bold text-lg mb-6 flex items-center gap-2 text-white">
                  <SlidersHorizontal className="text-[#6043F4]" size={20} />
                  Adjustable Parameters
                </h3>

                <div className="space-y-6">
                  {SLIDERS.map((slider) => (
                    <div key={slider.key}>
                      <div className="flex justify-between mb-2">
                        <label className="text-sm font-bold text-white/70">{slider.label}</label>
                        <span className="text-sm font-black text-[#8B75FF]">
                          {formatValue(params?.[slider.key], slider.unit)}
                        </span>
                      </div>
                      <div className="relative h-8 flex items-center">
                        <div className="absolute inset-x-0 h-2 rounded-full bg-white/10" />
                        <div
                          className="absolute left-0 h-2 rounded-full bg-gradient-to-r from-[#6043F4] to-[#8B75FF]"
                          style={{
                            width: `${getSliderPercent(
                              params?.[slider.key] ?? baseline?.[slider.key] ?? slider.min,
                              slider.min,
                              slider.max
                            )}%`,
                          }}
                        />
                        <input
                          className="relative z-10 w-full h-8 appearance-none cursor-pointer bg-transparent simulator-slider"
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
                  className="w-full mt-8 py-3 rounded-2xl bg-[#6043F4] text-white font-bold hover:brightness-110 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isSimulating ? 'Running clinical scenario...' : 'Run Simulation'}
                </button>
              </section>
            </div>

            <div className="col-span-12 lg:col-span-8 space-y-6">
              <section className="bg-white/5 border border-white/10 rounded-3xl p-8">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-8">
                  <div>
                    <h3 className="font-bold text-lg flex items-center gap-2 text-white">
                      <Activity className="text-[#00C2FF]" size={20} />
                      Risk Comparison: Before vs. After Simulation
                    </h3>
                    <p className="text-sm text-white/55 mt-2">
                      Existing record ke basis par yeh free rule-based engine estimate karta hai ki selected change se risk kitna move karega.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-black/15 px-4 py-3">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-white/35 font-bold">Current profile</p>
                    <p className="text-sm font-semibold text-white/80 mt-1">
                      Age {profile?.age ?? '--'} • BMI {profile?.bmi ?? '--'} • Weight {profile?.weight_kg ?? '--'} kg
                    </p>
                  </div>
                </div>

                <div className="space-y-8">
                  {riskComparison.map((risk) => (
                    <div key={risk.key} className="grid grid-cols-12 gap-4 items-center">
                      <div className="col-span-12 md:col-span-3 text-sm font-black text-white/55 uppercase tracking-tight">
                        {risk.label}
                      </div>
                      <div className="col-span-12 md:col-span-9 space-y-3">
                        <div className="relative h-11 bg-white/5 rounded-2xl overflow-hidden flex items-center">
                          <div
                            className="h-full bg-slate-500/70 flex items-center px-4"
                            style={{ width: `${clampPercent(risk.current_risk)}%` }}
                          >
                            <span className="text-[10px] font-black uppercase tracking-widest text-white/80 whitespace-nowrap">
                              Current Risk
                            </span>
                          </div>
                          <span className="ml-auto mr-4 text-sm font-black text-white/80">{risk.current_risk}%</span>
                        </div>
                        <div className="relative h-11 bg-white/5 rounded-2xl overflow-hidden flex items-center">
                          <div
                            className={`h-full bg-[#6043F4]/70 flex items-center px-4 transition-all ${isSimulating ? 'animate-pulse' : ''}`}
                            style={{ width: `${clampPercent(risk.simulated_risk)}%` }}
                          >
                            <span className="text-[10px] font-black uppercase tracking-widest text-white whitespace-nowrap">
                              Simulated Risk
                            </span>
                          </div>
                          <span className={`ml-auto mr-4 text-sm font-black ${risk.delta > 0 ? 'text-red-300' : 'text-[#8B75FF]'}`}>
                            {risk.simulated_risk}%
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <div className="grid grid-cols-12 gap-6 items-start">
                <section className="col-span-12 xl:col-span-5 self-start bg-gradient-to-br from-[#6043F4] to-[#009CDE] rounded-3xl p-6 text-white shadow-2xl shadow-[#6043F4]/10">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.25em] text-white/70 font-bold">Projected Recovery</p>
                      <h3 className="text-xl font-black mt-2">Can you become normal?</h3>
                    </div>
                    <Sparkles size={30} className="text-white/85" />
                  </div>

                  <div className="mt-8 flex items-end gap-4">
                    <div className="text-5xl font-black">{Math.round(progress)}%</div>
                    <div className="text-sm font-semibold text-white/80 mb-1">
                      low-risk proximity score
                    </div>
                  </div>

                  <div className="mt-6 h-2.5 w-full bg-white/20 rounded-full overflow-hidden">
                    <div className="h-full bg-white rounded-full" style={{ width: `${progress}%` }} />
                  </div>

                  <p className="mt-5 text-sm leading-relaxed text-white/90">
                    {focusSummary?.headline || 'Simulation chalne ke baad yahan normalization insight dikhega.'}
                  </p>
                  <p className="mt-3 text-sm font-bold text-white/90">
                    Likelihood: {focusSummary?.likelihood || '--'} • Risk reduction: {focusSummary?.risk_reduction_points ?? '--'} points
                  </p>
                </section>

                <section className="col-span-12 xl:col-span-7 bg-white/5 border border-white/10 rounded-3xl p-8 relative overflow-hidden">
                  <div className="absolute right-0 top-0 p-6 opacity-5">
                    <Brain size={120} />
                  </div>
                  <h3 className="font-bold text-lg mb-6 flex items-center gap-2 text-white">
                    <Brain className="text-[#8B75FF]" size={20} />
                    Scenario Analysis: AI Logic
                  </h3>
                  <div className="bg-black/20 p-6 rounded-2xl border-l-4 border-[#6043F4] relative z-10">
                    <p className="text-[15px] leading-relaxed text-white/85 italic font-medium">
                      {result?.focus_summary || 'Baseline load hone ke baad model aapke condition-specific scenario ko explain karega.'}
                    </p>
                  </div>

                  <div className="mt-6 space-y-3">
                    {(result?.drivers || []).map((driver) => (
                      <div key={driver} className="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3 text-sm text-white/80">
                        {driver}
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              <div className="grid grid-cols-12 gap-6">
                <section className="col-span-12 xl:col-span-7 bg-white/5 border border-white/10 rounded-3xl p-8">
                  <h3 className="font-bold text-lg flex items-center gap-2 text-white">
                    <TrendingUp className="text-[#8B75FF]" size={20} />
                    Suggested Targets
                  </h3>
                  <div className="mt-6 grid gap-3">
                    {(result?.recommendations || []).map((recommendation) => (
                      <div key={recommendation} className="rounded-2xl border border-white/8 bg-black/15 px-4 py-3 text-sm text-white/80">
                        {recommendation}
                      </div>
                    ))}
                  </div>

                  <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
                    {SLIDERS.slice(0, 4).map((slider) => (
                      <div key={slider.key} className="rounded-2xl border border-white/8 bg-white/[0.04] p-4">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-white/35 font-bold">{slider.label}</p>
                        <p className="mt-3 text-lg font-black text-white">{formatValue(params?.[slider.key], slider.unit)}</p>
                        <p className="text-xs text-white/45 mt-1">
                          Baseline {formatValue(baseline?.[slider.key], slider.unit)}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="col-span-12 xl:col-span-5 bg-[#10091d] border border-white/8 rounded-3xl p-8">
                  <h3 className="font-bold text-lg flex items-center gap-2 text-white">
                    <Info className="text-[#00C2FF]" size={20} />
                    Free Engine Notes
                  </h3>
                  <div className="mt-6 space-y-3">
                    {assumptions.map((assumption) => (
                      <div key={assumption} className="rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-white/72">
                        {assumption}
                      </div>
                    ))}
                  </div>
                  <div className="mt-8 rounded-2xl border border-[#6043F4]/20 bg-[#6043F4]/10 p-4">
                    <p className="text-sm text-white/85 leading-relaxed">
                      Yeh simulator fully free stack par hai: existing database data + explainable rule engine. Koi paid AI API ki zarurat nahi hai.
                    </p>
                  </div>
                </section>
              </div>

              <section className="flex flex-col md:flex-row items-center justify-between p-8 bg-[#0F081D] rounded-3xl border border-white/8">
                <div className="flex items-center gap-5 mb-6 md:mb-0">
                  <div className="w-14 h-14 rounded-2xl bg-[#6043F4] flex items-center justify-center text-white shadow-xl shadow-[#6043F4]/20">
                    <Stethoscope size={28} />
                  </div>
                  <div>
                    <h4 className="text-white text-xl font-black tracking-tight">Clinical next step</h4>
                    <p className="text-slate-400 text-sm font-medium mt-1">
                      Scenario ko doctor review ke liye export ya report screen se connect kiya ja sakta hai.
                    </p>
                  </div>
                </div>
                <div className="text-sm text-white/75 font-semibold">
                  Focus: {FOCUS_LABELS[focusCondition] || focusCondition} • Window: {timeframeMonths} months
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>

      <style>{`
        .simulator-slider::-webkit-slider-runnable-track {
          height: 8px;
          background: transparent;
        }

        .simulator-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          margin-top: -6px;
          width: 20px;
          height: 20px;
          border-radius: 9999px;
          background: #6043F4;
          border: 2px solid #c4b5fd;
          box-shadow: 0 0 0 4px rgba(96, 67, 244, 0.18);
        }

        .simulator-slider::-moz-range-track {
          height: 8px;
          background: transparent;
        }

        .simulator-slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 9999px;
          background: #6043F4;
          border: 2px solid #c4b5fd;
          box-shadow: 0 0 0 4px rgba(96, 67, 244, 0.18);
        }
      `}</style>
    </div>
  );
};

export default Simulate;
