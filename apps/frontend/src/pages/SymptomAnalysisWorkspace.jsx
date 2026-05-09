import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Clock3,
  HeartPulse,
  Loader2,
  Save,
  ShieldAlert,
  Sparkles,
  Stethoscope,
  Waves,
} from 'lucide-react';

import { apiClient } from '../lib/apiClient';
import { ROUTES } from '../router/routes';

const MotionDiv = motion.div;
const DRAFT_KEY = 'arogyaai:symptom-analysis-draft:v2';
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
const ONSET_OPTIONS = ['Sudden', 'Gradual', 'Intermittent', 'Unknown'];

const initialForm = {
  chief_complaint: '',
  associated_symptoms: [],
  duration_value: '2',
  duration_unit: 'days',
  severity: 5,
  onset: 'Gradual',
  aggravating_factors: '',
  relieving_factors: '',
  medications: '',
  notes: '',
};

const inputClass =
  'w-full rounded-[1.3rem] border border-slate-200/80 bg-white/85 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10 dark:border-stroke dark:bg-background/60 dark:text-slate-100';

const chipClass =
  'inline-flex items-center justify-center rounded-full border px-3.5 py-2 text-[11px] font-black uppercase tracking-[0.2em] transition-all duration-200';

const formatDate = (value) => {
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

const confidenceValue = (score) => {
  const numeric = Number(score);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(12, Math.min(100, Math.round(numeric * 100)));
};

function SectionHeading({ icon: Icon, eyebrow, title, subtitle }) {
  return (
    <div>
      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">
        <Icon size={14} />
        <span>{eyebrow}</span>
      </div>
      <h3 className="mt-3 text-xl font-black tracking-tight text-slate-950 dark:text-text-primary">{title}</h3>
      {subtitle ? <p className="mt-2 text-sm leading-7 text-slate-500 dark:text-text-muted">{subtitle}</p> : null}
    </div>
  );
}

function LoadingReasoning() {
  const steps = ['Structuring intake', 'Cross-checking risk signals', 'Correlating longitudinal context', 'Preparing reasoning summary'];
  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-primary/15 bg-[radial-gradient(circle_at_top,rgba(0,156,222,0.16),transparent_52%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(237,246,255,0.96))] p-6 shadow-[0_30px_120px_-52px_rgba(0,156,222,0.55)] dark:border-primary/20 dark:bg-[radial-gradient(circle_at_top,rgba(0,156,222,0.18),transparent_50%),linear-gradient(180deg,rgba(13,10,28,0.98),rgba(8,8,22,0.98))]">
      <div className="flex items-center gap-4">
        <div className="flex size-12 items-center justify-center rounded-[1.3rem] bg-primary/12 text-primary">
          <Loader2 size={22} className="animate-spin" />
        </div>
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.28em] text-primary">AI Processing</p>
          <h4 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Analyzing symptom pattern</h4>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {steps.map((step) => (
          <div key={step} className="rounded-[1.3rem] border border-white/80 bg-white/80 px-4 py-3 shadow-sm dark:border-stroke dark:bg-white/5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-600 dark:text-text-secondary">{step}</p>
              <Sparkles size={14} className="text-primary" />
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200/80 dark:bg-background/60">
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: '100%' }}
                transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY, ease: 'linear' }}
                className="h-full w-1/3 rounded-full bg-[linear-gradient(90deg,rgba(0,156,222,0),rgba(0,156,222,0.9),rgba(97,67,244,0))]"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SymptomAnalysisWorkspace() {
  const [form, setForm] = useState(initialForm);
  const [customSymptom, setCustomSymptom] = useState('');
  const [validationError, setValidationError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [history, setHistory] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [draftSavedAt, setDraftSavedAt] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [loadingSessionId, setLoadingSessionId] = useState('');
  const [revealCount, setRevealCount] = useState(0);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(DRAFT_KEY);
      if (raw) {
        setForm((current) => ({ ...current, ...JSON.parse(raw) }));
      }
    } catch (error) {
      console.warn('[SymptomAnalysisWorkspace] Draft restore failed:', error);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        window.localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
        setDraftSavedAt(new Date().toISOString());
      } catch (error) {
        console.warn('[SymptomAnalysisWorkspace] Draft save failed:', error);
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [form]);

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
        if (!cancelled) {
          console.warn('[SymptomAnalysisWorkspace] Failed to load history:', error);
        }
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

  useEffect(() => {
    const summary = activeSession?.analysis?.summary;
    if (!summary) {
      setRevealCount(0);
      return;
    }
    setRevealCount(1);
    const interval = window.setInterval(() => {
      setRevealCount((current) => {
        if (current >= 7) {
          window.clearInterval(interval);
          return current;
        }
        return current + 1;
      });
    }, 180);
    return () => window.clearInterval(interval);
  }, [activeSession?.id, activeSession?.analysis?.summary]);

  const updateForm = (field, value) => setForm((current) => ({ ...current, [field]: value }));

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

  const syncSessionIntoHistory = (sessionPayload) => {
    if (!sessionPayload?.id) return;
    setHistory((current) => [sessionPayload, ...current.filter((item) => item.id !== sessionPayload.id)].slice(0, 6));
  };

  const validate = () => {
    if (!form.chief_complaint.trim()) return 'Add the chief complaint before running analysis.';
    if (!String(form.duration_value).trim()) return 'Specify how long the symptoms have been present.';
    if (!form.associated_symptoms.length) return 'Select at least one symptom chip or add a custom symptom.';
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

  const analysis = activeSession?.analysis ?? null;
  const confidence = confidenceValue(analysis?.confidence_score);
  const insightBlocks = useMemo(() => ([
    {
      key: 'summary',
      title: 'AI Summary',
      icon: Brain,
      content: analysis?.summary ? [analysis.summary] : [],
      visibleAt: 1,
    },
    {
      key: 'causes',
      title: 'Likely Causes',
      icon: Stethoscope,
      content: analysis?.possible_causes || [],
      visibleAt: 2,
    },
    {
      key: 'risk',
      title: 'Risk Indicators',
      icon: ShieldAlert,
      content: analysis?.risk_indicators || [],
      visibleAt: 3,
    },
    {
      key: 'recommendations',
      title: 'Recommendations',
      icon: ArrowRight,
      content: analysis?.recommendations || [],
      visibleAt: 4,
    },
    {
      key: 'wearables',
      title: 'Wearable Correlations',
      icon: Waves,
      content: analysis?.wearable_correlations || [],
      visibleAt: 5,
    },
    {
      key: 'timeline',
      title: 'Timeline Correlations',
      icon: Activity,
      content: analysis?.timeline_correlations || [],
      visibleAt: 6,
    },
    {
      key: 'alerts',
      title: 'Escalation Warnings',
      icon: AlertTriangle,
      content: (analysis?.red_flags || []).map((item) => item?.reason).filter(Boolean),
      visibleAt: 7,
    },
  ]), [analysis]);

  return (
    <motion.main
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="min-h-full bg-[radial-gradient(circle_at_top,rgba(0,156,222,0.08),transparent_28%),linear-gradient(180deg,rgba(248,250,252,0.94),rgba(255,255,255,0.98))] px-4 py-6 sm:px-6 lg:px-8 dark:bg-[radial-gradient(circle_at_top,rgba(0,156,222,0.12),transparent_26%),linear-gradient(180deg,rgba(11,8,21,0.98),rgba(8,7,18,1))]">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
        <section className="relative overflow-hidden rounded-[2.4rem] border border-white/70 bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(236,248,255,0.94))] px-6 py-7 shadow-[0_34px_100px_-54px_rgba(15,23,42,0.42)] dark:border-stroke dark:bg-[linear-gradient(135deg,rgba(18,13,36,0.96),rgba(7,12,28,0.94))] sm:px-8 sm:py-8">
          <div className="absolute inset-y-0 right-0 w-[40%] bg-[radial-gradient(circle_at_center,rgba(0,156,222,0.16),transparent_60%)] dark:bg-[radial-gradient(circle_at_center,rgba(0,156,222,0.18),transparent_58%)]" />
          <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-primary/5 px-3 py-1 text-[10px] font-black uppercase tracking-[0.28em] text-primary">
                <Sparkles size={12} />
                <span>Clinical Intake Workspace</span>
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight text-slate-950 dark:text-text-primary sm:text-[2.5rem]">
                AI Symptom Analysis Workspace
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 dark:text-text-muted sm:text-[15px]">
                Structured clinical reasoning powered by wearable intelligence and longitudinal health context.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: 'Draft', value: draftSavedAt ? `Saved ${formatDate(draftSavedAt)}` : 'Autosave active', icon: Save },
                { label: 'Timeline', value: activeSession?.timeline?.saved_to_timeline ? 'Synced' : 'Next analysis will sync', icon: Activity },
                { label: 'Workspace', value: 'Longitudinal mode', icon: HeartPulse },
              ].map((item) => (
                <div key={item.label} className="rounded-[1.4rem] border border-white/80 bg-white/75 px-4 py-4 shadow-sm backdrop-blur dark:border-stroke dark:bg-white/5">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">
                    <item.icon size={13} />
                    <span>{item.label}</span>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-800 dark:text-text-primary">{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,0.96fr)_minmax(360px,1.04fr)]">
          <form onSubmit={handleAnalyze} className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_30px_90px_-58px_rgba(15,23,42,0.34)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={Stethoscope}
                eyebrow="Structured Intake"
                title="Capture the clinical pattern"
                subtitle="Use clear symptom structure so the reasoning layer can correlate severity, timing, medications, and longitudinal memory."
              />

              <div className="mt-6 space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Chief Complaint</label>
                  <textarea
                    rows={3}
                    value={form.chief_complaint}
                    onChange={(event) => updateForm('chief_complaint', event.target.value)}
                    className={`${inputClass} min-h-[112px] resize-none`}
                    placeholder="Describe the main concern in clinical language or plain words."
                  />
                </div>

                <div>
                  <label className="mb-3 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Symptom Chips</label>
                  <div className="flex flex-wrap gap-2.5">
                    {PRESET_SYMPTOMS.map((symptom) => {
                      const active = form.associated_symptoms.includes(symptom);
                      return (
                        <button
                          key={symptom}
                          type="button"
                          onClick={() => toggleSymptom(symptom)}
                          className={`${chipClass} ${
                            active
                              ? 'border-secondary/40 bg-secondary/10 text-[#06668d] shadow-sm dark:border-secondary/30 dark:bg-secondary/15 dark:text-[#8ad6ff]'
                              : 'border-slate-200 bg-white text-slate-500 hover:border-primary/25 hover:text-primary dark:border-stroke dark:bg-background/60 dark:text-text-secondary'
                          }`}
                        >
                          {symptom}
                        </button>
                      );
                    })}
                  </div>
                  <div className="mt-3 flex gap-2">
                    <input
                      value={customSymptom}
                      onChange={(event) => setCustomSymptom(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault();
                          addCustomSymptom();
                        }
                      }}
                      className={inputClass}
                      placeholder="Add another symptom tag"
                    />
                    <button
                      type="button"
                      onClick={addCustomSymptom}
                      className="rounded-[1.2rem] border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-slate-600 transition hover:border-primary/25 hover:text-primary dark:border-stroke dark:bg-background/60 dark:text-text-secondary"
                    >
                      Add
                    </button>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Duration</label>
                    <div className="flex gap-2">
                      <input
                        value={form.duration_value}
                        onChange={(event) => updateForm('duration_value', event.target.value)}
                        className={inputClass}
                        inputMode="numeric"
                      />
                      <select value={form.duration_unit} onChange={(event) => updateForm('duration_unit', event.target.value)} className={inputClass}>
                        {DURATION_UNITS.map((unit) => (
                          <option key={unit} value={unit}>{unit}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Onset</label>
                    <select value={form.onset} onChange={(event) => updateForm('onset', event.target.value)} className={inputClass}>
                      {ONSET_OPTIONS.map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Severity</label>
                    <div className="rounded-[1.4rem] border border-slate-200/80 bg-white/70 px-4 py-4 dark:border-stroke dark:bg-background/40">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-600 dark:text-text-secondary">Clinical intensity</span>
                        <span className="text-lg font-black text-slate-950 dark:text-text-primary">{form.severity}/10</span>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={form.severity}
                        onChange={(event) => updateForm('severity', Number(event.target.value))}
                        className="mt-4 h-2 w-full cursor-pointer appearance-none rounded-full bg-[linear-gradient(90deg,var(--color-secondary),var(--color-primary))]"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Aggravating Factors</label>
                    <textarea rows={3} value={form.aggravating_factors} onChange={(event) => updateForm('aggravating_factors', event.target.value)} className={`${inputClass} resize-none`} />
                  </div>
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Relieving Factors</label>
                    <textarea rows={3} value={form.relieving_factors} onChange={(event) => updateForm('relieving_factors', event.target.value)} className={`${inputClass} resize-none`} />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Medications</label>
                    <textarea rows={3} value={form.medications} onChange={(event) => updateForm('medications', event.target.value)} className={`${inputClass} resize-none`} placeholder="Current medicines, supplements, or recent changes" />
                  </div>
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Notes</label>
                    <textarea rows={3} value={form.notes} onChange={(event) => updateForm('notes', event.target.value)} className={`${inputClass} resize-none`} placeholder="Anything else the reasoning engine should consider" />
                  </div>
                </div>

                {validationError || submitError ? (
                  <div className="rounded-[1.4rem] border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                    {submitError || validationError}
                  </div>
                ) : null}

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-xs font-bold uppercase tracking-[0.2em] text-text-muted">
                    Draft autosave {draftSavedAt ? `updated ${formatDate(draftSavedAt)}` : 'ready'}
                  </div>
                  <div className="flex gap-3">
                    <a
                      href={ROUTES.TIMELINE}
                      className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-slate-600 transition hover:border-primary/25 hover:text-primary dark:border-stroke dark:bg-background/55 dark:text-text-secondary"
                    >
                      <Clock3 size={14} />
                      Open Timeline
                    </a>
                    <button
                      type="submit"
                      disabled={isAnalyzing}
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-[linear-gradient(135deg,var(--color-primary)_0%,#009cde_100%)] px-6 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-white shadow-[0_24px_50px_-24px_rgba(0,156,222,0.75)] transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isAnalyzing ? <Loader2 size={15} className="animate-spin" /> : <Brain size={15} />}
                      Analyze Symptoms
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_28px_80px_-58px_rgba(15,23,42,0.32)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={Clock3}
                eyebrow="Recent Sessions"
                title="Reasoning history"
                subtitle="Jump back into prior symptom sessions and compare how the clinical picture evolved."
              />
              <div className="mt-5 space-y-3">
                {isLoadingHistory ? (
                  <div className="rounded-[1.4rem] border border-slate-200/80 bg-slate-50/80 px-4 py-5 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
                    Loading recent analyses...
                  </div>
                ) : history.length === 0 ? (
                  <div className="rounded-[1.4rem] border border-dashed border-slate-200 bg-slate-50/80 px-4 py-5 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
                    Your first structured intake will appear here.
                  </div>
                ) : history.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => handleLoadSession(session.id)}
                    className={`w-full rounded-[1.5rem] border px-4 py-4 text-left transition ${
                      activeSession?.id === session.id
                        ? 'border-primary/30 bg-primary/5 shadow-sm'
                        : 'border-slate-200/80 bg-slate-50/80 hover:border-primary/20 hover:bg-white dark:border-stroke dark:bg-background/40 dark:hover:bg-background/70'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-black text-slate-900 dark:text-text-primary">{session.input?.chief_complaint || 'Symptom session'}</p>
                        <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-text-secondary">{formatDate(session.created_at)}</p>
                      </div>
                      {loadingSessionId === session.id ? <Loader2 size={16} className="animate-spin text-primary" /> : null}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(session.input?.associated_symptoms || []).slice(0, 3).map((item) => (
                        <span key={`${session.id}:${item}`} className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 dark:border-stroke dark:bg-background/60 dark:text-text-secondary">
                          {item}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </form>

          <div className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_30px_90px_-56px_rgba(15,23,42,0.36)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={Brain}
                eyebrow="Live Analysis"
                title="Reasoning canvas"
                subtitle="Progressively revealed clinical reasoning, urgency framing, and timeline-aware recommendations."
              />

              <div className="mt-6">
                {isAnalyzing ? (
                  <LoadingReasoning />
                ) : !analysis?.summary ? (
                  <div className="flex min-h-[24rem] flex-col items-center justify-center rounded-[2rem] border border-dashed border-slate-200 bg-[radial-gradient(circle_at_top,rgba(0,156,222,0.07),transparent_48%),rgba(255,255,255,0.76)] px-6 text-center dark:border-stroke dark:bg-[radial-gradient(circle_at_top,rgba(0,156,222,0.09),transparent_44%),rgba(255,255,255,0.03)]">
                    <div className="flex size-16 items-center justify-center rounded-[1.6rem] bg-primary/10 text-primary">
                      <Brain size={30} />
                    </div>
                    <p className="mt-6 text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">AI Symptom Analysis Center</p>
                    <h4 className="mt-4 text-2xl font-black tracking-tight text-slate-950 dark:text-text-primary">Structured reasoning will appear here</h4>
                    <p className="mt-4 max-w-md text-sm leading-7 text-slate-500 dark:text-text-muted">
                      The workspace reveals likely causes, urgency, recommendations, wearable signals, and timeline correlations instead of dumping a raw payload.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-[1.8rem] border border-primary/15 bg-[linear-gradient(135deg,rgba(0,156,222,0.08),rgba(97,67,244,0.08),rgba(255,255,255,0.95))] p-5 dark:border-primary/20 dark:bg-[linear-gradient(135deg,rgba(0,156,222,0.1),rgba(97,67,244,0.12),rgba(18,13,36,0.96))]">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                        <div>
                          <p className="text-[10px] font-black uppercase tracking-[0.26em] text-primary">Session Overview</p>
                          <h4 className="mt-2 text-2xl font-black tracking-tight text-slate-950 dark:text-text-primary">
                            {activeSession?.input?.chief_complaint || 'Symptom analysis'}
                          </h4>
                        </div>
                        <div className="grid gap-2 sm:grid-cols-3">
                          <div className="rounded-[1.2rem] border border-white/80 bg-white/70 px-3 py-3 dark:border-stroke dark:bg-white/5">
                            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Urgency</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{analysis.urgency_level || 'Routine'}</p>
                          </div>
                          <div className="rounded-[1.2rem] border border-white/80 bg-white/70 px-3 py-3 dark:border-stroke dark:bg-white/5">
                            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Risk</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{analysis.risk_level || 'Low'}</p>
                          </div>
                          <div className="rounded-[1.2rem] border border-white/80 bg-white/70 px-3 py-3 dark:border-stroke dark:bg-white/5">
                            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Timeline</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">
                              {activeSession?.timeline?.saved_to_timeline ? 'Synced' : 'Pending'}
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="mt-5 rounded-full bg-white/70 p-1 dark:bg-background/50">
                        <div className="flex items-center justify-between px-3">
                          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Confidence indicator</span>
                          <span className="text-xs font-black text-slate-900 dark:text-text-primary">{confidence}%</span>
                        </div>
                        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200/80 dark:bg-background/70">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${confidence}%` }} className="h-full rounded-full bg-[linear-gradient(90deg,var(--color-secondary),var(--color-primary))]" />
                        </div>
                      </div>
                    </div>

                    <AnimatePresence>
                      {insightBlocks.filter((block) => block.content.length > 0 && revealCount >= block.visibleAt).map((block, index) => (
                        <MotionDiv
                          key={block.key}
                          initial={{ opacity: 0, y: 18, scale: 0.985 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ duration: 0.28, delay: index * 0.03 }}
                          className="rounded-[1.8rem] border border-slate-200/80 bg-white/88 p-5 shadow-sm dark:border-stroke dark:bg-background/38"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex size-11 items-center justify-center rounded-[1.1rem] bg-primary/10 text-primary">
                              <block.icon size={20} />
                            </div>
                            <div>
                              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">AI Layer</p>
                              <h5 className="mt-1 text-lg font-black text-slate-950 dark:text-text-primary">{block.title}</h5>
                            </div>
                          </div>
                          <div className="mt-4 space-y-3">
                            {block.content.map((item) => (
                              <div key={`${block.key}:${item}`} className="rounded-[1.2rem] border border-slate-200/70 bg-slate-50/80 px-4 py-3 text-sm leading-7 text-slate-600 dark:border-stroke dark:bg-background/56 dark:text-text-secondary">
                                {item}
                              </div>
                            ))}
                          </div>
                        </MotionDiv>
                      ))}
                    </AnimatePresence>

                    {analysis.red_flags?.length ? (
                      <div className="rounded-[1.8rem] border border-red-200/80 bg-red-50/85 p-5 dark:border-red-500/20 dark:bg-red-500/10">
                        <div className="flex items-center gap-3 text-red-600 dark:text-red-300">
                          <AlertTriangle size={18} />
                          <p className="text-[10px] font-black uppercase tracking-[0.24em]">Escalation Warnings</p>
                        </div>
                        <p className="mt-3 text-sm leading-7 text-red-700 dark:text-red-200">
                          Severe or red-flag symptom language was detected. If symptoms are happening now, worsening, or feel alarming, seek urgent in-person care instead of relying on the app alone.
                        </p>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_28px_80px_-58px_rgba(15,23,42,0.34)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={CheckCircle2}
                eyebrow="Workflow Status"
                title="Longitudinal memory"
                subtitle="Each analysis session is stored for future orchestration and timeline-aware follow-up."
              />
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {[
                  { label: 'Stored Session', value: activeSession?.id ? 'Available' : 'Waiting' },
                  { label: 'Timeline Event', value: activeSession?.timeline?.saved_to_timeline ? 'Created' : 'Pending' },
                  { label: 'Future Routing', value: 'Orchestrator-ready' },
                ].map((item) => (
                  <div key={item.label} className="rounded-[1.3rem] border border-slate-200/70 bg-slate-50/80 px-4 py-4 dark:border-stroke dark:bg-background/40">
                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">{item.label}</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </motion.main>
  );
}
