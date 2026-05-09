import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Clock3,
  History,
  Loader2,
  Plus,
  RefreshCcw,
  ShieldAlert,
  Sparkles,
  Stethoscope,
  TrendingUp,
} from 'lucide-react';

import { apiClient } from '../../lib/apiClient';

const MotionDiv = motion.div;

const PRESET_SYMPTOMS = [
  'Fever',
  'Cough',
  'Fatigue',
  'Headache',
  'Dizziness',
  'Chest pain',
  'Breathlessness',
  'Sore throat',
  'Body aches',
  'Nausea',
  'Palpitations',
  'Abdominal pain',
];

const DURATION_UNITS = ['hours', 'days', 'weeks', 'months'];
const PREVIOUS_EPISODE_OPTIONS = ['First time', 'Occasional', 'Recurring'];

const initialForm = {
  chief_complaint: '',
  duration_value: '2',
  duration_unit: 'days',
  severity: 5,
  associated_symptoms: [],
  aggravating_factors: '',
  relieving_factors: '',
  previous_episodes: '',
  medications: '',
  notes: '',
};

const pillBaseClass =
  'inline-flex items-center justify-center rounded-full border px-3 py-2 text-[11px] font-black uppercase tracking-[0.22em] transition-all duration-200';

const textInputClass =
  'w-full rounded-[1.5rem] border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-secondary focus:ring-4 focus:ring-[#009cde]/10 disabled:cursor-not-allowed disabled:opacity-70 dark:border-stroke dark:bg-background/60 dark:text-slate-100';

const formatSessionDate = (value) => {
  if (!value) return 'Just now';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Just now';
  return parsed.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const riskTone = (value) => {
  const normalized = String(value || '').toLowerCase();
  if (normalized.includes('elevated') || normalized.includes('high')) {
    return 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300';
  }
  if (normalized.includes('moderate') || normalized.includes('medium')) {
    return 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300';
  }
  return 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300';
};

const confidenceWidth = (score) => {
  const numeric = Number(score);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(8, Math.min(100, Math.round(numeric * 100)));
};

function SectionLabel({ icon: Icon, eyebrow, title, subtitle }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">
        <Icon size={14} />
        <span>{eyebrow}</span>
      </div>
      <div>
        <h3 className="text-xl font-black tracking-tight text-slate-950 dark:text-text-primary">{title}</h3>
        {subtitle ? <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-text-muted">{subtitle}</p> : null}
      </div>
    </div>
  );
}

function SymptomPill({ active, label, disabled, onClick }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`${pillBaseClass} ${
        active
          ? 'border-secondary/40 bg-secondary/10 text-[#06668d] shadow-sm dark:border-secondary/30 dark:bg-secondary/15 dark:text-[#8ad6ff]'
          : 'border-slate-200 bg-white/85 text-slate-500 hover:border-primary/20 hover:text-primary dark:border-stroke dark:bg-background/70 dark:text-text-secondary dark:hover:border-secondary/30'
      }`}
    >
      {label}
    </button>
  );
}

function LoadingAnalysisState() {
  const steps = [
    'Structuring symptom intake',
    'Reviewing risk signals',
    'Generating a cautious summary',
  ];

  return (
    <div className="rounded-[2rem] border border-primary/15 bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.15),transparent_55%),linear-gradient(180deg,rgba(255,255,255,0.92),rgba(240,247,255,0.94))] p-6 shadow-[0_24px_80px_-40px_rgba(97,67,244,0.5)] dark:border-primary/20 dark:bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.2),transparent_50%),linear-gradient(180deg,rgba(16,12,32,0.96),rgba(10,9,22,0.96))]">
      <div className="flex items-center gap-3">
        <div className="flex size-12 items-center justify-center rounded-[1.2rem] bg-primary/12 text-primary">
          <Loader2 size={20} className="animate-spin" />
        </div>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.28em] text-primary">AI Processing</p>
          <h4 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Analyzing symptom pattern</h4>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {steps.map((step, index) => (
          <div
            key={step}
            className="rounded-[1.3rem] border border-white/70 bg-white/80 px-4 py-3 shadow-sm dark:border-stroke dark:bg-white/5"
            style={{ animationDelay: `${index * 120}ms` }}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-600 dark:text-text-secondary">{step}</p>
              <Sparkles size={14} className="text-primary" />
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200/80 dark:bg-background/60">
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: '100%' }}
                transition={{ duration: 1.4, repeat: Number.POSITIVE_INFINITY, ease: 'linear' }}
                className="h-full w-1/3 rounded-full bg-[linear-gradient(90deg,rgba(0,156,222,0),rgba(0,156,222,0.9),rgba(97,67,244,0))]"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultPlaceholder() {
  return (
    <div className="flex min-h-[22rem] flex-col items-center justify-center rounded-[2rem] border border-dashed border-slate-200 bg-white/70 px-6 text-center dark:border-stroke dark:bg-white/5">
      <div className="flex size-16 items-center justify-center rounded-[1.6rem] bg-primary/10 text-primary">
        <Brain size={30} />
      </div>
      <p className="mt-6 text-[10px] font-black uppercase tracking-[0.3em] text-text-muted">AI Symptom Analysis Center</p>
      <h4 className="mt-4 text-2xl font-black tracking-tight text-slate-950 dark:text-text-primary">
        Turn today&apos;s symptoms into a structured clinical snapshot
      </h4>
      <p className="mt-4 max-w-md text-sm leading-7 text-slate-500 dark:text-text-muted">
        Add the complaint, timing, severity, and related symptoms on the left. We&apos;ll store the session, run a cautious reasoning pass, and show what to monitor next.
      </p>
    </div>
  );
}

export default function SymptomAnalysisPanel() {
  const [form, setForm] = useState(initialForm);
  const [customSymptom, setCustomSymptom] = useState('');
  const [validationError, setValidationError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [history, setHistory] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [loadingSessionId, setLoadingSessionId] = useState('');
  const [savingToTimeline, setSavingToTimeline] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadHistory = async () => {
      setIsLoadingHistory(true);
      try {
        const response = await apiClient.get('/symptoms/history?limit=6');
        if (cancelled) return;
        const rows = response?.data?.data ?? [];
        setHistory(rows);
        setActiveSession((current) => current ?? rows[0] ?? null);
      } catch (error) {
        if (cancelled) return;
        console.warn('[SymptomAnalysisPanel] Failed to load history:', error);
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    };

    void loadHistory();

    return () => {
      cancelled = true;
    };
  }, []);

  const updateForm = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const syncSessionIntoHistory = (sessionPayload) => {
    if (!sessionPayload?.id) return;
    setHistory((current) => {
      const next = [sessionPayload, ...current.filter((item) => item.id !== sessionPayload.id)];
      return next.slice(0, 6);
    });
  };

  const toggleSymptom = (symptom) => {
    setForm((current) => {
      const exists = current.associated_symptoms.includes(symptom);
      return {
        ...current,
        associated_symptoms: exists
          ? current.associated_symptoms.filter((item) => item !== symptom)
          : [...current.associated_symptoms, symptom],
      };
    });
  };

  const addCustomSymptom = () => {
    const value = customSymptom.trim();
    if (!value) return;
    if (form.associated_symptoms.some((item) => item.toLowerCase() === value.toLowerCase())) {
      setCustomSymptom('');
      return;
    }
    setForm((current) => ({
      ...current,
      associated_symptoms: [...current.associated_symptoms, value],
    }));
    setCustomSymptom('');
  };

  const validate = () => {
    if (!form.chief_complaint.trim()) {
      return 'Add the chief complaint before running analysis.';
    }
    if (!String(form.duration_value).trim()) {
      return 'Specify how long the symptoms have been present.';
    }
    if (!form.associated_symptoms.length) {
      return 'Select at least one associated symptom.';
    }
    return '';
  };

  const handleAnalyze = async (event) => {
    event.preventDefault();
    const errorMessage = validate();
    setValidationError(errorMessage);
    setSubmitError('');

    if (errorMessage) {
      toast.error(errorMessage);
      return;
    }

    setIsAnalyzing(true);
    try {
      const payload = {
        ...form,
        chief_complaint: form.chief_complaint.trim(),
        duration_value: Number(form.duration_value),
        severity: Number(form.severity),
        aggravating_factors: form.aggravating_factors.trim() || null,
        relieving_factors: form.relieving_factors.trim() || null,
        previous_episodes: form.previous_episodes || null,
        medications: form.medications.trim() || null,
        notes: form.notes.trim() || null,
      };
      const response = await apiClient.post('/symptoms/analyze', payload, { timeout: 25000 });
      const sessionPayload = response?.data?.data ?? null;
      setActiveSession(sessionPayload);
      syncSessionIntoHistory(sessionPayload);
      toast.success('Symptom analysis ready.');
    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'We could not analyze these symptoms right now.';
      setSubmitError(message);
      toast.error(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleLoadSession = async (sessionId) => {
    if (!sessionId || loadingSessionId === sessionId) return;
    setLoadingSessionId(sessionId);
    try {
      const response = await apiClient.get(`/symptoms/${sessionId}`);
      const sessionPayload = response?.data?.data ?? null;
      setActiveSession(sessionPayload);
      syncSessionIntoHistory(sessionPayload);
    } catch (error) {
      toast.error('Unable to load this analysis.');
    } finally {
      setLoadingSessionId('');
    }
  };

  const handleSaveToTimeline = async () => {
    if (!activeSession?.id || savingToTimeline || activeSession?.timeline?.saved_to_timeline) return;
    setSavingToTimeline(true);
    try {
      const response = await apiClient.post(`/symptoms/${activeSession.id}/timeline`, { force: false });
      const updatedSession = response?.data?.data ?? null;
      setActiveSession(updatedSession);
      syncSessionIntoHistory(updatedSession);
      toast.success('Analysis saved to Health Timeline.');
    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Timeline save failed.';
      toast.error(message);
    } finally {
      setSavingToTimeline(false);
    }
  };

  const analysis = activeSession?.analysis ?? null;
  const confidence = confidenceWidth(analysis?.confidence_score);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar px-1">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.02fr)_minmax(320px,0.98fr)]">
        <motion.form
          layout
          onSubmit={handleAnalyze}
          className="rounded-[2.3rem] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(240,248,255,0.95))] p-5 shadow-[0_28px_80px_-42px_rgba(15,23,42,0.45)] dark:border-stroke dark:bg-[linear-gradient(180deg,rgba(16,23,42,0.96),rgba(9,9,20,0.96))]"
        >
          <div className="rounded-[1.9rem] border border-white/70 bg-white/70 p-5 shadow-sm dark:border-stroke dark:bg-background/35">
            <SectionLabel
              icon={Sparkles}
              eyebrow="Structured Intake"
              title="Analyze Symptoms"
              subtitle="Capture today’s symptom pattern in a form that can be stored, reasoned over, and optionally pushed into the Health Timeline."
            />

            <div className="mt-6 space-y-5">
              <label className="block space-y-2">
                <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Chief Complaint</span>
                <textarea
                  rows={3}
                  disabled={isAnalyzing}
                  value={form.chief_complaint}
                  onChange={(event) => updateForm('chief_complaint', event.target.value)}
                  placeholder="Describe the main concern in plain language."
                  className={textInputClass}
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-[120px_minmax(0,1fr)]">
                <label className="block space-y-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Duration</span>
                  <input
                    min="1"
                    type="number"
                    disabled={isAnalyzing}
                    value={form.duration_value}
                    onChange={(event) => updateForm('duration_value', event.target.value)}
                    className={textInputClass}
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Unit</span>
                  <select
                    disabled={isAnalyzing}
                    value={form.duration_unit}
                    onChange={(event) => updateForm('duration_unit', event.target.value)}
                    className={textInputClass}
                  >
                    {DURATION_UNITS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="rounded-[1.6rem] border border-slate-200 bg-white/85 px-4 py-4 dark:border-stroke dark:bg-background/55">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Severity</p>
                    <p className="mt-1 text-sm text-slate-500 dark:text-text-muted">How intense does this feel right now?</p>
                  </div>
                  <span className="rounded-full border border-primary/15 bg-primary/10 px-3 py-1 text-lg font-black text-primary">
                    {form.severity}/10
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  disabled={isAnalyzing}
                  value={form.severity}
                  onChange={(event) => updateForm('severity', Number(event.target.value))}
                  className="mt-4 h-2 w-full cursor-pointer accent-[#009cde]"
                />
              </div>

              <div className="space-y-3">
                <SectionLabel
                  icon={Activity}
                  eyebrow="Symptom Tags"
                  title="Associated Symptoms"
                  subtitle="Pick the nearby symptoms that are present right now."
                />
                <div className="flex flex-wrap gap-2">
                  {PRESET_SYMPTOMS.map((symptom) => (
                    <SymptomPill
                      key={symptom}
                      label={symptom}
                      disabled={isAnalyzing}
                      active={form.associated_symptoms.includes(symptom)}
                      onClick={() => toggleSymptom(symptom)}
                    />
                  ))}
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    value={customSymptom}
                    disabled={isAnalyzing}
                    onChange={(event) => setCustomSymptom(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        addCustomSymptom();
                      }
                    }}
                    placeholder="Add another symptom tag"
                    className={textInputClass}
                  />
                  <button
                    type="button"
                    disabled={isAnalyzing}
                    onClick={addCustomSymptom}
                    className="inline-flex items-center justify-center gap-2 rounded-[1.3rem] border border-slate-200 bg-white px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-slate-700 transition hover:border-primary/20 hover:text-primary disabled:cursor-not-allowed disabled:opacity-70 dark:border-stroke dark:bg-background/60 dark:text-text-primary"
                  >
                    <Plus size={14} />
                    Add Tag
                  </button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Aggravating Factors</span>
                  <textarea
                    rows={3}
                    disabled={isAnalyzing}
                    value={form.aggravating_factors}
                    onChange={(event) => updateForm('aggravating_factors', event.target.value)}
                    placeholder="Movement, meals, stress, posture..."
                    className={textInputClass}
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Relieving Factors</span>
                  <textarea
                    rows={3}
                    disabled={isAnalyzing}
                    value={form.relieving_factors}
                    onChange={(event) => updateForm('relieving_factors', event.target.value)}
                    placeholder="Rest, hydration, medication..."
                    className={textInputClass}
                  />
                </label>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Previous Episodes</span>
                  <select
                    disabled={isAnalyzing}
                    value={form.previous_episodes}
                    onChange={(event) => updateForm('previous_episodes', event.target.value)}
                    className={textInputClass}
                  >
                    <option value="">Select pattern</option>
                    {PREVIOUS_EPISODE_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block space-y-2">
                  <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Medications Taken</span>
                  <input
                    disabled={isAnalyzing}
                    value={form.medications}
                    onChange={(event) => updateForm('medications', event.target.value)}
                    placeholder="Paracetamol, inhaler, antacid..."
                    className={textInputClass}
                  />
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-[11px] font-black uppercase tracking-[0.22em] text-text-muted">Describe the Condition</span>
                <textarea
                  rows={4}
                  disabled={isAnalyzing}
                  value={form.notes}
                  onChange={(event) => updateForm('notes', event.target.value)}
                  placeholder="Mention progression, context, home readings, or anything that feels unusual."
                  className={textInputClass}
                />
              </label>

              {validationError ? (
                <div className="rounded-[1.4rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
                  {validationError}
                </div>
              ) : null}
              {submitError ? (
                <div className="rounded-[1.4rem] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                  {submitError}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={isAnalyzing}
                className="inline-flex w-full items-center justify-center gap-3 rounded-[1.6rem] bg-primary px-5 py-4 text-[11px] font-black uppercase tracking-[0.28em] text-white shadow-[0_24px_60px_-24px_rgba(97,67,244,0.8)] transition hover:bg-[#4a34c1] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isAnalyzing ? <Loader2 size={16} className="animate-spin" /> : <Stethoscope size={16} />}
                <span>{isAnalyzing ? 'Analyzing...' : 'Analyze Symptoms'}</span>
              </button>
            </div>
          </div>
        </motion.form>

        <div className="space-y-5">
          <div className="rounded-[2.3rem] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(246,248,255,0.96))] p-5 shadow-[0_28px_80px_-42px_rgba(15,23,42,0.45)] dark:border-stroke dark:bg-[linear-gradient(180deg,rgba(15,12,28,0.96),rgba(9,9,20,0.96))]">
            <div className="rounded-[1.9rem] border border-white/70 bg-white/70 p-5 shadow-sm dark:border-stroke dark:bg-background/35">
              <SectionLabel
                icon={Brain}
                eyebrow="AI Result Dashboard"
                title="Analysis Output"
                subtitle="Structured summary, likely causes, risk signals, and next-step guidance."
              />

              <div className="mt-6">
                {isAnalyzing ? (
                  <LoadingAnalysisState />
                ) : !analysis ? (
                  <ResultPlaceholder />
                ) : (
                  <AnimatePresence mode="wait">
                    <MotionDiv
                      key={activeSession?.id || 'analysis'}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="space-y-4"
                    >
                      {analysis.warning_banner ? (
                        <div className="rounded-[1.6rem] border border-red-200 bg-red-50/95 p-4 dark:border-red-500/20 dark:bg-red-500/10">
                          <div className="flex items-start gap-3">
                            <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-[1rem] bg-red-100 text-red-600 dark:bg-red-500/15 dark:text-red-300">
                              <ShieldAlert size={18} />
                            </div>
                            <div>
                              <p className="text-[10px] font-black uppercase tracking-[0.28em] text-red-600 dark:text-red-300">Warning Banner</p>
                              <p className="mt-2 text-sm leading-6 text-red-700 dark:text-red-200">
                                Severe or red-flag symptom language was detected. If symptoms are happening now, worsening, or feel alarming, seek urgent in-person care rather than relying on the app alone.
                              </p>
                            </div>
                          </div>
                        </div>
                      ) : null}

                      <div className="grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(220px,0.9fr)]">
                        <div className="rounded-[1.8rem] border border-primary/10 bg-primary/5 p-5 dark:border-primary/20 dark:bg-primary/10">
                          <div className="flex items-center gap-2 text-primary">
                            <Sparkles size={15} />
                            <p className="text-[10px] font-black uppercase tracking-[0.28em]">AI Summary</p>
                          </div>
                          <p className="mt-4 text-sm leading-7 text-slate-700 dark:text-text-primary">{analysis.summary}</p>
                        </div>

                        <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 dark:border-stroke dark:bg-background/55">
                          <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">Severity Snapshot</p>
                          <div className="mt-4 flex flex-wrap items-center gap-2">
                            <span className="rounded-full border border-primary/15 bg-primary/10 px-3 py-1 text-sm font-black text-primary">
                              {activeSession?.input?.severity}/10 reported
                            </span>
                            <span className={`rounded-full border px-3 py-1 text-sm font-black ${riskTone(analysis.risk_level)}`}>
                              {analysis.risk_level}
                            </span>
                          </div>
                          <p className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-text-secondary">
                            <Clock3 size={15} />
                            {analysis.urgency_level}
                          </p>
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 dark:border-stroke dark:bg-background/55">
                          <div className="flex items-center gap-2">
                            <TrendingUp size={15} className="text-primary" />
                            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">Possible Causes</p>
                          </div>
                          <div className="mt-4 flex flex-wrap gap-2">
                            {(analysis.possible_causes || []).map((item) => (
                              <span
                                key={item}
                                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-bold text-slate-600 dark:border-stroke dark:bg-background/60 dark:text-text-primary"
                              >
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 dark:border-stroke dark:bg-background/55">
                          <div className="flex items-center gap-2">
                            <Activity size={15} className="text-secondary" />
                            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">Confidence Meter</p>
                          </div>
                          <div className="mt-4 rounded-full bg-slate-200/80 p-1 dark:bg-background/70">
                            <div
                              className="h-3 rounded-full bg-[linear-gradient(90deg,#009cde,#6143f4)] transition-all duration-500"
                              style={{ width: `${confidence}%` }}
                            />
                          </div>
                          <p className="mt-3 text-sm font-semibold text-slate-600 dark:text-text-secondary">
                            {confidence}% confidence based on the structured symptom detail available.
                          </p>
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 dark:border-stroke dark:bg-background/55">
                          <div className="flex items-center gap-2">
                            <ShieldAlert size={15} className="text-primary" />
                            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">Risk Indicators</p>
                          </div>
                          <div className="mt-4 space-y-3">
                            {(analysis.risk_indicators || []).length > 0 ? (
                              analysis.risk_indicators.map((item) => (
                                <div
                                  key={item}
                                  className="rounded-[1.1rem] border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-6 text-slate-600 dark:border-stroke dark:bg-background/60 dark:text-text-primary"
                                >
                                  {item}
                                </div>
                              ))
                            ) : (
                              <p className="text-sm text-slate-500 dark:text-text-muted">No major risk indicators were highlighted by the current structured input.</p>
                            )}
                          </div>
                        </div>

                        <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 dark:border-stroke dark:bg-background/55">
                          <div className="flex items-center gap-2">
                            <AlertTriangle size={15} className="text-red-500" />
                            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">Red Flags</p>
                          </div>
                          <div className="mt-4 space-y-3">
                            {(analysis.red_flags || []).length > 0 ? (
                              analysis.red_flags.map((item, index) => (
                                <div
                                  key={`${item.trigger || 'flag'}-${index}`}
                                  className="rounded-[1.1rem] border border-red-200 bg-red-50/80 px-4 py-3 text-sm leading-6 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-200"
                                >
                                  {item.reason || item.trigger}
                                </div>
                              ))
                            ) : (
                              <p className="text-sm text-slate-500 dark:text-text-muted">No explicit red-flag combination was detected from this entry.</p>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 dark:border-stroke dark:bg-background/55">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 size={15} className="text-secondary" />
                          <p className="text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">Recommendations</p>
                        </div>
                        <div className="mt-4 grid gap-3">
                          {(analysis.recommendations || []).map((item) => (
                            <div
                              key={item}
                              className="rounded-[1.1rem] border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-6 text-slate-600 dark:border-stroke dark:bg-background/60 dark:text-text-primary"
                            >
                              {item}
                            </div>
                          ))}
                        </div>
                        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                          <button
                            type="button"
                            disabled={savingToTimeline || activeSession?.timeline?.saved_to_timeline}
                            onClick={handleSaveToTimeline}
                            className="inline-flex items-center justify-center gap-2 rounded-[1.4rem] bg-background px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-text-primary transition hover:bg-card disabled:cursor-not-allowed disabled:opacity-70 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
                          >
                            {savingToTimeline ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
                            <span>{activeSession?.timeline?.saved_to_timeline ? 'Saved to Timeline' : 'Save Analysis to Timeline'}</span>
                          </button>
                          <button
                            type="button"
                            disabled={isAnalyzing}
                            onClick={(event) => handleAnalyze(event)}
                            className="inline-flex items-center justify-center gap-2 rounded-[1.4rem] border border-slate-200 bg-white px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-slate-700 transition hover:border-primary/20 hover:text-primary disabled:cursor-not-allowed disabled:opacity-70 dark:border-stroke dark:bg-background/60 dark:text-text-primary"
                          >
                            <RefreshCcw size={15} />
                            Retry Analysis
                          </button>
                        </div>
                        <p className="mt-4 text-xs leading-6 text-slate-500 dark:text-text-muted">{analysis.disclaimer}</p>
                      </div>
                    </MotionDiv>
                  </AnimatePresence>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-[2.3rem] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,255,0.96))] p-5 shadow-[0_28px_80px_-42px_rgba(15,23,42,0.45)] dark:border-stroke dark:bg-[linear-gradient(180deg,rgba(15,12,28,0.96),rgba(9,9,20,0.96))]">
            <div className="rounded-[1.9rem] border border-white/70 bg-white/70 p-5 shadow-sm dark:border-stroke dark:bg-background/35">
              <SectionLabel
                icon={History}
                eyebrow="Stored Sessions"
                title="Recent Symptom Analyses"
                subtitle="Reload a previous AI pass or continue refining the current entry."
              />

              <div className="mt-5 space-y-3">
                {isLoadingHistory ? (
                  <div className="rounded-[1.4rem] border border-slate-200 bg-white/80 px-4 py-4 text-sm text-slate-500 dark:border-stroke dark:bg-background/55 dark:text-text-muted">
                    Loading recent analyses...
                  </div>
                ) : history.length === 0 ? (
                  <div className="rounded-[1.4rem] border border-dashed border-slate-200 bg-white/70 px-4 py-5 text-sm text-slate-500 dark:border-stroke dark:bg-background/55 dark:text-text-muted">
                    Your analyzed sessions will appear here after the first submission.
                  </div>
                ) : (
                  history.map((session) => {
                    const isActive = activeSession?.id === session.id;
                    return (
                      <button
                        key={session.id}
                        type="button"
                        onClick={() => handleLoadSession(session.id)}
                        className={`w-full rounded-[1.5rem] border p-4 text-left transition-all ${
                          isActive
                            ? 'border-primary/30 bg-primary/5 shadow-sm dark:border-primary/25 dark:bg-primary/10'
                            : 'border-slate-200 bg-white/80 hover:border-slate-300 dark:border-stroke dark:bg-background/55 dark:hover:border-white/15'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-black text-slate-900 dark:text-text-primary">
                              {session.input?.chief_complaint || 'Symptom analysis'}
                            </p>
                            <p className="mt-2 text-[11px] font-bold uppercase tracking-[0.2em] text-text-muted">
                              {formatSessionDate(session.created_at)}
                            </p>
                          </div>
                          {loadingSessionId === session.id ? (
                            <Loader2 size={14} className="shrink-0 animate-spin text-primary" />
                          ) : (
                            <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${riskTone(session.analysis?.risk_level)}`}>
                              {session.analysis?.risk_level || 'Ready'}
                            </span>
                          )}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {(session.input?.associated_symptoms || []).slice(0, 3).map((item) => (
                            <span
                              key={`${session.id}:${item}`}
                              className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500 dark:border-stroke dark:bg-background/60 dark:text-text-secondary"
                            >
                              {item}
                            </span>
                          ))}
                          {session.timeline?.saved_to_timeline ? (
                            <span className="rounded-full border border-secondary/25 bg-secondary/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-secondary">
                              Timeline saved
                            </span>
                          ) : null}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
