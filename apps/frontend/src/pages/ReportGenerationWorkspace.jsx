import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  ArrowRight,
  Brain,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  HeartPulse,
  Layers3,
  Loader2,
  Share2,
  Sparkles,
  Stethoscope,
  Waves,
} from 'lucide-react';

import { apiClient } from '../lib/apiClient';
import { ROUTES } from '../router/routes';
import useReportsStore from '../store/reportsStore';

const MotionDiv = motion.div;
const DRAFT_KEY = 'arogyaai:report-generation-draft:v1';

const inputClass =
  'w-full rounded-[1.3rem] border border-slate-200/80 bg-white/85 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10 dark:border-stroke dark:bg-background/60 dark:text-slate-100';

const formatDate = (value) => {
  if (!value) return 'Not set';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
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

export default function ReportGenerationWorkspace() {
  const reports = useReportsStore((state) => state.reports);
  const fetchReports = useReportsStore((state) => state.fetchReports);
  const [history, setHistory] = useState([]);
  const [symptomSessions, setSymptomSessions] = useState([]);
  const [draft, setDraft] = useState({
    title: 'AI Longitudinal Clinical Report',
    report_ids: [],
    symptom_session_ids: [],
    timeline_start: '',
    timeline_end: '',
    include_wearables: true,
    include_biomarkers: true,
    include_timeline_events: true,
  });
  const [generatedReport, setGeneratedReport] = useState(null);
  const [generatedHistory, setGeneratedHistory] = useState([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(DRAFT_KEY);
      if (raw) {
        setDraft((current) => ({ ...current, ...JSON.parse(raw) }));
      }
    } catch (error) {
      console.warn('[ReportGenerationWorkspace] Draft restore failed:', error);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft]);

  useEffect(() => {
    let cancelled = false;
    const loadSources = async () => {
      setLoadingSources(true);
      try {
        await fetchReports({ force: true });
        const [symptomResponse, timelineResponse, generatedHistoryResponse] = await Promise.all([
          apiClient.get('/symptoms/history?limit=8'),
          apiClient.get('/health/timeline'),
          apiClient.get('/report-generation/history?limit=6'),
        ]);
        if (cancelled) return;
        setSymptomSessions(symptomResponse?.data?.data ?? []);
        setHistory(timelineResponse?.data?.data ?? []);
        const reportsHistory = generatedHistoryResponse?.data?.data ?? [];
        setGeneratedHistory(reportsHistory);
        setGeneratedReport((current) => current ?? reportsHistory[0] ?? null);
      } catch (error) {
        if (!cancelled) {
          toast.error('Unable to load report-generation context.');
        }
      } finally {
        if (!cancelled) {
          setLoadingSources(false);
        }
      }
    };
    void loadSources();
    return () => {
      cancelled = true;
    };
  }, [fetchReports]);

  const toggleId = (field, value) => {
    setDraft((current) => {
      const exists = current[field].includes(value);
      return {
        ...current,
        [field]: exists ? current[field].filter((item) => item !== value) : [...current[field], value],
      };
    });
  };

  const selectedCounts = useMemo(() => ({
    reports: draft.report_ids.length,
    symptoms: draft.symptom_session_ids.length,
    timeline: history.length,
  }), [draft.report_ids.length, draft.symptom_session_ids.length, history.length]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const response = await apiClient.post('/report-generation/generate', draft, { timeout: 120000 });
      const payload = response?.data?.data ?? null;
      setGeneratedReport(payload);
      setGeneratedHistory((current) => [payload, ...current.filter((item) => item.id !== payload?.id)].slice(0, 6));
      toast.success('AI report generated.');
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'Report generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (reportId) => {
    if (!reportId) return;
    setDownloading(true);
    try {
      const response = await apiClient.get(`/report-generation/${reportId}/export`, { responseType: 'blob', timeout: 30000 });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${generatedReport?.title || 'ai-report'}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Clinical report PDF downloaded.');
    } catch (error) {
      toast.error(error?.response?.data?.detail || error?.message || 'PDF export failed.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <motion.main
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="min-h-full bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.08),transparent_28%),linear-gradient(180deg,rgba(248,250,252,0.94),rgba(255,255,255,0.98))] px-4 py-6 sm:px-6 lg:px-8 dark:bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.12),transparent_26%),linear-gradient(180deg,rgba(11,8,21,0.98),rgba(8,7,18,1))]">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
        <section className="relative overflow-hidden rounded-[2.4rem] border border-white/70 bg-[linear-gradient(135deg,rgba(255,255,255,0.96),rgba(244,243,255,0.95))] px-6 py-7 shadow-[0_34px_100px_-54px_rgba(15,23,42,0.42)] dark:border-stroke dark:bg-[linear-gradient(135deg,rgba(18,13,36,0.96),rgba(11,10,28,0.96))] sm:px-8 sm:py-8">
          <div className="absolute inset-y-0 right-0 w-[40%] bg-[radial-gradient(circle_at_center,rgba(97,67,244,0.18),transparent_60%)] dark:bg-[radial-gradient(circle_at_center,rgba(97,67,244,0.18),transparent_58%)]" />
          <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-primary/5 px-3 py-1 text-[10px] font-black uppercase tracking-[0.28em] text-primary">
                <Sparkles size={12} />
                <span>Longitudinal Report Center</span>
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight text-slate-950 dark:text-text-primary sm:text-[2.5rem]">
                Report Generation Workspace
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 dark:text-text-muted sm:text-[15px]">
                Combine reports, symptom analyses, wearable signals, biomarkers, and timeline events into a professional AI-generated clinical summary.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { label: 'Reports', value: `${selectedCounts.reports} selected`, icon: FileText },
                { label: 'Symptoms', value: `${selectedCounts.symptoms} sessions`, icon: Stethoscope },
                { label: 'Timeline', value: `${selectedCounts.timeline} events`, icon: Clock3 },
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

        <section className="grid gap-6 xl:grid-cols-[minmax(380px,0.9fr)_minmax(0,1.1fr)]">
          <div className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_30px_90px_-58px_rgba(15,23,42,0.34)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={Layers3}
                eyebrow="Source Selection"
                title="Build the report context"
                subtitle="Select the clinical inputs that should drive the generated summary."
              />

              <div className="mt-6 space-y-5">
                <div>
                  <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Report Title</label>
                  <input value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} className={inputClass} />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Timeline Start</label>
                    <input type="date" value={draft.timeline_start} onChange={(event) => setDraft((current) => ({ ...current, timeline_start: event.target.value }))} className={inputClass} />
                  </div>
                  <div>
                    <label className="mb-2 block text-xs font-black uppercase tracking-[0.22em] text-text-muted">Timeline End</label>
                    <input type="date" value={draft.timeline_end} onChange={(event) => setDraft((current) => ({ ...current, timeline_end: event.target.value }))} className={inputClass} />
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  {[
                    { field: 'include_wearables', label: 'Wearables' },
                    { field: 'include_biomarkers', label: 'Biomarkers' },
                    { field: 'include_timeline_events', label: 'Timeline' },
                  ].map((item) => (
                    <button
                      key={item.field}
                      type="button"
                      onClick={() => setDraft((current) => ({ ...current, [item.field]: !current[item.field] }))}
                      className={`rounded-[1.3rem] border px-4 py-4 text-left transition ${
                        draft[item.field]
                          ? 'border-primary/30 bg-primary/5'
                          : 'border-slate-200/80 bg-slate-50/80 dark:border-stroke dark:bg-background/40'
                      }`}
                    >
                      <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">{item.label}</p>
                      <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{draft[item.field] ? 'Included' : 'Excluded'}</p>
                    </button>
                  ))}
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-black uppercase tracking-[0.22em] text-text-muted">Uploaded Reports</label>
                    <a href={ROUTES.MEDICAL_REPORTS} className="text-[11px] font-black uppercase tracking-[0.18em] text-primary">Open Hub</a>
                  </div>
                  <div className="mt-3 space-y-3">
                    {loadingSources ? (
                      <div className="rounded-[1.3rem] border border-slate-200/80 bg-slate-50/80 px-4 py-4 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
                        Loading sources...
                      </div>
                    ) : reports.length === 0 ? (
                      <div className="rounded-[1.3rem] border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
                        Upload reports in the hub to include them here.
                      </div>
                    ) : reports.slice(0, 8).map((report) => (
                      <button
                        key={report.id}
                        type="button"
                        onClick={() => toggleId('report_ids', report.id)}
                        className={`w-full rounded-[1.4rem] border px-4 py-4 text-left transition ${
                          draft.report_ids.includes(report.id)
                            ? 'border-primary/30 bg-primary/5'
                            : 'border-slate-200/80 bg-slate-50/80 hover:border-primary/20 hover:bg-white dark:border-stroke dark:bg-background/40'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-black text-slate-900 dark:text-text-primary">{report.fileName}</p>
                            <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-text-secondary">{report.reportType.replace(/_/g, ' ')} • {formatDate(report.createdAt)}</p>
                          </div>
                          {draft.report_ids.includes(report.id) ? <CheckCircle2 size={18} className="text-primary" /> : null}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-black uppercase tracking-[0.22em] text-text-muted">Symptom Sessions</label>
                  <div className="mt-3 space-y-3">
                    {symptomSessions.length === 0 ? (
                      <div className="rounded-[1.3rem] border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
                        Run a symptom analysis to include structured clinical reasoning here.
                      </div>
                    ) : symptomSessions.map((session) => (
                      <button
                        key={session.id}
                        type="button"
                        onClick={() => toggleId('symptom_session_ids', session.id)}
                        className={`w-full rounded-[1.4rem] border px-4 py-4 text-left transition ${
                          draft.symptom_session_ids.includes(session.id)
                            ? 'border-secondary/35 bg-secondary/5'
                            : 'border-slate-200/80 bg-slate-50/80 hover:border-secondary/20 hover:bg-white dark:border-stroke dark:bg-background/40'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-black text-slate-900 dark:text-text-primary">{session.input?.chief_complaint || 'Symptom session'}</p>
                            <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-text-secondary">{formatDate(session.created_at)}</p>
                          </div>
                          {draft.symptom_session_ids.includes(session.id) ? <CheckCircle2 size={18} className="text-secondary" /> : null}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[linear-gradient(135deg,var(--color-primary)_0%,#8f67ff_56%,#009cde_100%)] px-6 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-white shadow-[0_24px_50px_-24px_rgba(97,67,244,0.78)] transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isGenerating ? <Loader2 size={15} className="animate-spin" /> : <Brain size={15} />}
                  Generate Report
                </button>
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_28px_80px_-58px_rgba(15,23,42,0.34)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={FileText}
                eyebrow="Generated History"
                title="Recent AI reports"
                subtitle="Reopen previous generated summaries and export them again."
              />
              <div className="mt-5 space-y-3">
                {generatedHistory.length === 0 ? (
                  <div className="rounded-[1.3rem] border border-dashed border-slate-200 bg-slate-50/80 px-4 py-4 text-sm font-semibold text-slate-500 dark:border-stroke dark:bg-background/40 dark:text-text-secondary">
                    Your generated longitudinal reports will appear here.
                  </div>
                ) : generatedHistory.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setGeneratedReport(item)}
                    className={`w-full rounded-[1.4rem] border px-4 py-4 text-left transition ${
                      generatedReport?.id === item.id
                        ? 'border-primary/30 bg-primary/5'
                        : 'border-slate-200/80 bg-slate-50/80 hover:border-primary/20 hover:bg-white dark:border-stroke dark:bg-background/40'
                    }`}
                  >
                    <p className="text-sm font-black text-slate-900 dark:text-text-primary">{item.title}</p>
                    <p className="mt-1 text-xs font-semibold text-slate-500 dark:text-text-secondary">{formatDate(item.created_at)}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_30px_90px_-56px_rgba(15,23,42,0.36)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={Brain}
                eyebrow="Generated Preview"
                title="Clinical report canvas"
                subtitle="Professional report composition with recommendations, confidence, and export-ready structure."
              />

              <div className="mt-6">
                {isGenerating ? (
                  <div className="rounded-[2rem] border border-primary/15 bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.16),transparent_52%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,243,255,0.96))] p-6 shadow-[0_30px_120px_-52px_rgba(97,67,244,0.55)] dark:border-primary/20 dark:bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.18),transparent_50%),linear-gradient(180deg,rgba(13,10,28,0.98),rgba(8,8,22,0.98))]">
                    <div className="flex items-center gap-4">
                      <div className="flex size-12 items-center justify-center rounded-[1.3rem] bg-primary/12 text-primary">
                        <Loader2 size={22} className="animate-spin" />
                      </div>
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-[0.28em] text-primary">AI Composition</p>
                        <h4 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Generating longitudinal report</h4>
                      </div>
                    </div>
                    <div className="mt-5 space-y-3">
                      {['Collecting selected reports', 'Correlating symptom sessions', 'Synthesizing wearable and timeline context'].map((step) => (
                        <div key={step} className="rounded-[1.2rem] border border-white/80 bg-white/80 px-4 py-3 text-sm font-semibold text-slate-600 dark:border-stroke dark:bg-white/5 dark:text-text-secondary">
                          {step}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : !generatedReport ? (
                  <div className="flex min-h-[24rem] flex-col items-center justify-center rounded-[2rem] border border-dashed border-slate-200 bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.07),transparent_48%),rgba(255,255,255,0.76)] px-6 text-center dark:border-stroke dark:bg-[radial-gradient(circle_at_top,rgba(97,67,244,0.09),transparent_44%),rgba(255,255,255,0.03)]">
                    <div className="flex size-16 items-center justify-center rounded-[1.6rem] bg-primary/10 text-primary">
                      <FileText size={30} />
                    </div>
                    <p className="mt-6 text-[10px] font-black uppercase tracking-[0.28em] text-text-muted">AI Report Center</p>
                    <h4 className="mt-4 text-2xl font-black tracking-tight text-slate-950 dark:text-text-primary">Generated summary will appear here</h4>
                    <p className="mt-4 max-w-md text-sm leading-7 text-slate-500 dark:text-text-muted">
                      Select your sources, choose a timeline window, and generate a doctor-style structured report with export support.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-[1.8rem] border border-primary/15 bg-[linear-gradient(135deg,rgba(97,67,244,0.08),rgba(0,156,222,0.08),rgba(255,255,255,0.95))] p-5 dark:border-primary/20 dark:bg-[linear-gradient(135deg,rgba(97,67,244,0.12),rgba(0,156,222,0.1),rgba(18,13,36,0.96))]">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                        <div>
                          <p className="text-[10px] font-black uppercase tracking-[0.26em] text-primary">Generated Summary</p>
                          <h4 className="mt-2 text-2xl font-black tracking-tight text-slate-950 dark:text-text-primary">{generatedReport.title}</h4>
                          <p className="mt-3 text-sm leading-7 text-slate-600 dark:text-text-secondary">{generatedReport.summary}</p>
                        </div>
                        <div className="grid gap-2 sm:grid-cols-3">
                          <div className="rounded-[1.2rem] border border-white/80 bg-white/70 px-3 py-3 dark:border-stroke dark:bg-white/5">
                            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Confidence</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{Math.round(Number(generatedReport.confidence_score || 0) * 100)}%</p>
                          </div>
                          <div className="rounded-[1.2rem] border border-white/80 bg-white/70 px-3 py-3 dark:border-stroke dark:bg-white/5">
                            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Timeline</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{generatedReport.timeline?.saved_to_timeline ? 'Logged' : 'Ready'}</p>
                          </div>
                          <div className="rounded-[1.2rem] border border-white/80 bg-white/70 px-3 py-3 dark:border-stroke dark:bg-white/5">
                            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Export</p>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">PDF ready</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => handleDownload(generatedReport.id)}
                        disabled={downloading}
                        className="inline-flex items-center justify-center gap-2 rounded-full bg-background px-5 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-text-primary transition hover:bg-card dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200 disabled:opacity-50"
                      >
                        {downloading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                        Export PDF
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-slate-600 transition hover:border-primary/25 hover:text-primary dark:border-stroke dark:bg-background/55 dark:text-text-secondary"
                      >
                        <Share2 size={15} />
                        Shareable architecture ready
                      </button>
                    </div>

                    <AnimatePresence>
                      {generatedReport?.report?.sections?.map((section, index) => (
                        <MotionDiv
                          key={`${generatedReport.id}:${section.title}`}
                          initial={{ opacity: 0, y: 14 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -8 }}
                          transition={{ duration: 0.25, delay: index * 0.04 }}
                          className="rounded-[1.8rem] border border-slate-200/80 bg-white/88 p-5 shadow-sm dark:border-stroke dark:bg-background/38"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex size-11 items-center justify-center rounded-[1.1rem] bg-primary/10 text-primary">
                              {index === 0 ? <Brain size={20} /> : index === 1 ? <FileText size={20} /> : index === 2 ? <Stethoscope size={20} /> : index === 3 ? <Waves size={20} /> : <ArrowRight size={20} />}
                            </div>
                            <div>
                              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">Clinical Section</p>
                              <h5 className="mt-1 text-lg font-black text-slate-950 dark:text-text-primary">{section.title}</h5>
                            </div>
                          </div>
                          <div className="mt-4 space-y-3">
                            {(section.content || []).map((item) => (
                              <div key={`${section.title}:${item}`} className="rounded-[1.2rem] border border-slate-200/70 bg-slate-50/80 px-4 py-3 text-sm leading-7 text-slate-600 dark:border-stroke dark:bg-background/56 dark:text-text-secondary">
                                {item}
                              </div>
                            ))}
                          </div>
                        </MotionDiv>
                      ))}
                    </AnimatePresence>

                    <div className="rounded-[1.8rem] border border-slate-200/80 bg-white/88 p-5 shadow-sm dark:border-stroke dark:bg-background/38">
                      <SectionHeading
                        icon={CalendarDays}
                        eyebrow="Source Ledger"
                        title="Included source context"
                        subtitle="Everything used to build this report remains visible for review."
                      />
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <div className="rounded-[1.2rem] border border-slate-200/70 bg-slate-50/80 px-4 py-4 dark:border-stroke dark:bg-background/56">
                          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Reports</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{generatedReport.sources?.reports?.length || 0} included</p>
                        </div>
                        <div className="rounded-[1.2rem] border border-slate-200/70 bg-slate-50/80 px-4 py-4 dark:border-stroke dark:bg-background/56">
                          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Symptom Sessions</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{generatedReport.sources?.symptom_sessions?.length || 0} included</p>
                        </div>
                        <div className="rounded-[1.2rem] border border-slate-200/70 bg-slate-50/80 px-4 py-4 dark:border-stroke dark:bg-background/56">
                          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Timeline Window</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">
                            {(generatedReport.sources?.timeline?.start || 'Start not set')} to {(generatedReport.sources?.timeline?.end || 'latest')}
                          </p>
                        </div>
                        <div className="rounded-[1.2rem] border border-slate-200/70 bg-slate-50/80 px-4 py-4 dark:border-stroke dark:bg-background/56">
                          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Wearables</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-text-primary">{generatedReport.sources?.include_wearables ? 'Included' : 'Excluded'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[2rem] border border-slate-200/80 bg-white/92 p-5 shadow-[0_28px_80px_-58px_rgba(15,23,42,0.34)] dark:border-stroke dark:bg-[#120d24]/88 sm:p-6">
              <SectionHeading
                icon={HeartPulse}
                eyebrow="Workflow Status"
                title="Future-ready intelligence"
                subtitle="This workspace is prepared for PDF export, shareable summaries, and orchestrator-aware longitudinal memory."
              />
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {[
                  { label: 'Persistence', value: generatedReport?.id ? 'Stored' : 'Waiting' },
                  { label: 'Timeline Event', value: generatedReport?.timeline?.saved_to_timeline ? 'Created' : 'Pending' },
                  { label: 'Export Layer', value: 'PDF enabled' },
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
