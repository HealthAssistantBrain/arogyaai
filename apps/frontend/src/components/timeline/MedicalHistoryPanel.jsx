import { useMemo, useState } from 'react';
import {
  ActivitySquare,
  AlertCircle,
  CheckCircle2,
  ClipboardPlus,
  FileUp,
  LoaderCircle,
  Sparkles,
  Stethoscope,
} from 'lucide-react';

import api from '../../lib/axios';

const ASSOCIATED_SYMPTOM_OPTIONS = [
  'Fatigue',
  'Fever',
  'Cough',
  'Dizziness',
  'Breathlessness',
  'Palpitations',
  'Headache',
  'Nausea',
];

const NEGATIVE_HISTORY_OPTIONS = [
  'fever',
  'chest pain',
  'dizziness',
  'cough',
  'breathlessness',
];

const REPORT_TYPE_OPTIONS = [
  'BLOOD_TEST',
  'MRI',
  'XRAY',
  'PRESCRIPTION',
  'CLINICAL_NOTE',
  'GENETIC',
  'OTHER',
];

const initialSymptomForm = {
  chief_complaint: '',
  duration_value: '',
  duration_unit: 'days',
  onset: '',
  severity: 5,
  associated_symptoms: [],
  negative_symptoms: [],
  aggravating_factors: '',
  relieving_factors: '',
  previous_episodes: '',
  treatment_taken: '',
};

const initialReportForm = {
  file: null,
  report_type: 'CLINICAL_NOTE',
  date_of_report: '',
};

const titleCase = (value) =>
  String(value || '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (match) => match.toUpperCase());

const pillBaseClasses =
  'rounded-full border px-3 py-2 text-xs font-bold tracking-wide transition-all duration-200';

function SelectionPill({ active, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`${pillBaseClasses} ${
        active
          ? 'border-[#009cde]/40 bg-[#009cde]/10 text-[#06668d] dark:border-[#009cde]/30 dark:bg-[#009cde]/15 dark:text-[#8ad6ff]'
          : 'border-slate-200 bg-white text-slate-500 hover:border-[#6143f4]/25 hover:text-[#6143f4] dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300 dark:hover:border-[#009cde]/40'
      }`}
    >
      {label}
    </button>
  );
}

function SectionLabel({ icon: Icon, title, subtitle }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.25em] text-slate-400 dark:text-slate-500">
        <Icon size={14} />
        <span>{title}</span>
      </div>
      {subtitle ? <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p> : null}
    </div>
  );
}

export default function MedicalHistoryPanel({ onTimelineRefresh }) {
  const [activeTab, setActiveTab] = useState('symptoms');
  const [symptomForm, setSymptomForm] = useState(initialSymptomForm);
  const [reportForm, setReportForm] = useState(initialReportForm);
  const [submittingSymptoms, setSubmittingSymptoms] = useState(false);
  const [uploadingReport, setUploadingReport] = useState(false);
  const [symptomError, setSymptomError] = useState('');
  const [reportError, setReportError] = useState('');
  const [latestHistory, setLatestHistory] = useState(null);
  const [latestReport, setLatestReport] = useState(null);

  const severityTone = useMemo(() => {
    if (symptomForm.severity >= 8) return 'text-red-500';
    if (symptomForm.severity >= 5) return 'text-amber-500';
    return 'text-emerald-500';
  }, [symptomForm.severity]);

  const toggleMultiValue = (field, value) => {
    setSymptomForm((current) => {
      const exists = current[field].includes(value);
      return {
        ...current,
        [field]: exists
          ? current[field].filter((item) => item !== value)
          : [...current[field], value],
      };
    });
  };

  const handleSymptomChange = (field, value) => {
    setSymptomForm((current) => ({ ...current, [field]: value }));
  };

  const handleReportChange = (field, value) => {
    setReportForm((current) => ({ ...current, [field]: value }));
  };

  const handleSymptomSubmit = async (event) => {
    event.preventDefault();
    setSubmittingSymptoms(true);
    setSymptomError('');

    try {
      const payload = {
        chief_complaint: symptomForm.chief_complaint || undefined,
        duration_value: symptomForm.duration_value ? Number(symptomForm.duration_value) : undefined,
        duration_unit: symptomForm.duration_unit || undefined,
        onset: symptomForm.onset || undefined,
        severity: Number(symptomForm.severity),
        associated_symptoms: symptomForm.associated_symptoms,
        negative_symptoms: symptomForm.negative_symptoms,
        aggravating_factors: symptomForm.aggravating_factors || undefined,
        relieving_factors: symptomForm.relieving_factors || undefined,
        previous_episodes:
          symptomForm.previous_episodes === ''
            ? undefined
            : symptomForm.previous_episodes === 'yes',
        treatment_taken: symptomForm.treatment_taken || undefined,
      };

      const response = await api.post('/clinical-history', payload);
      const savedHistory = response?.data?.data ?? response?.data ?? null;
      setLatestHistory(savedHistory);
      setSymptomForm(initialSymptomForm);
      await onTimelineRefresh?.();
    } catch (error) {
      setSymptomError(
        error?.response?.data?.error ||
          error?.response?.data?.detail ||
          error?.message ||
          'Unable to save clinical history.'
      );
    } finally {
      setSubmittingSymptoms(false);
    }
  };

  const handleReportSubmit = async (event) => {
    event.preventDefault();
    setUploadingReport(true);
    setReportError('');

    try {
      if (!reportForm.file) {
        throw new Error('Please attach a PDF or image report before submitting.');
      }

      const formData = new FormData();
      formData.append('file', reportForm.file);
      formData.append('report_type', reportForm.report_type);
      if (reportForm.date_of_report) {
        formData.append('date_of_report', reportForm.date_of_report);
      }

      const response = await api.post('/reports/upload', formData, {
        timeout: 90000,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      const uploadedReport = response?.data?.data ?? response?.data ?? null;
      setLatestReport(uploadedReport);
      setReportForm(initialReportForm);
      await onTimelineRefresh?.();
    } catch (error) {
      setReportError(
        error?.response?.data?.error ||
          error?.response?.data?.detail ||
          error?.message ||
          'Unable to upload this report right now.'
      );
    } finally {
      setUploadingReport(false);
    }
  };

  return (
    <aside className="lg:sticky lg:top-8 self-start rounded-[2rem] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(242,248,252,0.94))] p-5 shadow-[0_28px_80px_-42px_rgba(15,23,42,0.45)] backdrop-blur dark:border-slate-800 dark:bg-[linear-gradient(180deg,rgba(16,23,42,0.96),rgba(11,18,32,0.94))]">
      <div className="overflow-hidden rounded-[1.6rem] border border-white/60 bg-white/70 dark:border-white/5 dark:bg-slate-950/35">
        <div className="border-b border-slate-200/80 bg-[radial-gradient(circle_at_top_left,rgba(0,156,222,0.14),transparent_55%),radial-gradient(circle_at_top_right,rgba(97,67,244,0.16),transparent_52%)] px-5 py-5 dark:border-slate-800">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-[0.28em] text-slate-500 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
            <ClipboardPlus size={13} />
            Structured Intake
          </div>
          <div className="mt-4 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white">Add Medical History</h2>
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                Capture complaints, negative history, and supporting reports in a format that can flow into timeline analysis and AI insights.
              </p>
            </div>
            <div className="rounded-2xl border border-white/70 bg-white/80 p-3 text-[#009cde] shadow-sm dark:border-white/10 dark:bg-white/5">
              <Stethoscope size={20} />
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 rounded-2xl bg-slate-900/5 p-1 dark:bg-white/5">
            {[
              { key: 'symptoms', label: 'Symptoms', icon: ActivitySquare },
              { key: 'reports', label: 'Reports', icon: FileUp },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                onClick={() => setActiveTab(key)}
                className={`flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold transition-all ${
                  activeTab === key
                    ? 'bg-white text-slate-950 shadow-sm dark:bg-slate-900 dark:text-white'
                    : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
                }`}
              >
                <Icon size={16} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="p-5">
          {activeTab === 'symptoms' ? (
            <form onSubmit={handleSymptomSubmit} className="space-y-5">
              <SectionLabel
                icon={Sparkles}
                title="Symptom Intake"
                subtitle="Complaint to differential in one structured submission."
              />

              <label className="block space-y-2">
                <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Chief Complaint</span>
                <textarea
                  value={symptomForm.chief_complaint}
                  onChange={(event) => handleSymptomChange('chief_complaint', event.target.value)}
                  rows={3}
                  placeholder="Example: chest pain, headache, persistent cough"
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                />
              </label>

              <div className="grid grid-cols-[112px_minmax(0,1fr)] gap-3">
                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Duration</span>
                  <input
                    type="number"
                    min="1"
                    value={symptomForm.duration_value}
                    onChange={(event) => handleSymptomChange('duration_value', event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Unit</span>
                  <select
                    value={symptomForm.duration_unit}
                    onChange={(event) => handleSymptomChange('duration_unit', event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  >
                    <option value="hours">Hours</option>
                    <option value="days">Days</option>
                    <option value="weeks">Weeks</option>
                  </select>
                </label>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Onset</span>
                  <select
                    value={symptomForm.onset}
                    onChange={(event) => handleSymptomChange('onset', event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  >
                    <option value="">Select onset</option>
                    <option value="sudden">Sudden</option>
                    <option value="gradual">Gradual</option>
                  </select>
                </label>
                <div className="rounded-[1.5rem] border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-950/60">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Severity</span>
                    <span className={`text-lg font-black ${severityTone}`}>{symptomForm.severity}/10</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={symptomForm.severity}
                    onChange={(event) => handleSymptomChange('severity', event.target.value)}
                    className="mt-3 h-2 w-full cursor-pointer accent-[#009cde]"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <SectionLabel icon={ClipboardPlus} title="Associated Symptoms" subtitle="Select all that apply." />
                <div className="flex flex-wrap gap-2">
                  {ASSOCIATED_SYMPTOM_OPTIONS.map((symptom) => (
                    <SelectionPill
                      key={symptom}
                      label={symptom}
                      active={symptomForm.associated_symptoms.includes(symptom)}
                      onClick={() => toggleMultiValue('associated_symptoms', symptom)}
                    />
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <SectionLabel icon={CheckCircle2} title="Negative History" subtitle="Mark symptoms that are specifically absent." />
                <div className="flex flex-wrap gap-2">
                  {NEGATIVE_HISTORY_OPTIONS.map((symptom) => (
                    <SelectionPill
                      key={symptom}
                      label={`No ${titleCase(symptom)}`}
                      active={symptomForm.negative_symptoms.includes(symptom)}
                      onClick={() => toggleMultiValue('negative_symptoms', symptom)}
                    />
                  ))}
                </div>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Aggravating Factors</span>
                <input
                  value={symptomForm.aggravating_factors}
                  onChange={(event) => handleSymptomChange('aggravating_factors', event.target.value)}
                  placeholder="Activity, stairs, meals, posture..."
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Relieving Factors</span>
                <input
                  value={symptomForm.relieving_factors}
                  onChange={(event) => handleSymptomChange('relieving_factors', event.target.value)}
                  placeholder="Rest, hydration, medication..."
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Previous Episodes</span>
                  <select
                    value={symptomForm.previous_episodes}
                    onChange={(event) => handleSymptomChange('previous_episodes', event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  >
                    <option value="">Not specified</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Treatment Taken</span>
                  <input
                    value={symptomForm.treatment_taken}
                    onChange={(event) => handleSymptomChange('treatment_taken', event.target.value)}
                    placeholder="Antacid, paracetamol, inhaler..."
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  />
                </label>
              </div>

              {symptomError ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                  {symptomError}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submittingSymptoms}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
              >
                {submittingSymptoms ? <LoaderCircle size={16} className="animate-spin" /> : <ClipboardPlus size={16} />}
                <span>{submittingSymptoms ? 'Saving History...' : 'Save to Timeline'}</span>
              </button>

              {latestHistory?.analysis ? (
                <div className="rounded-[1.6rem] border border-[#009cde]/15 bg-[linear-gradient(180deg,rgba(0,156,222,0.07),rgba(97,67,244,0.03))] p-4 dark:border-[#009cde]/20 dark:bg-[linear-gradient(180deg,rgba(0,156,222,0.12),rgba(15,23,42,0.08))]">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-black uppercase tracking-[0.24em] text-[#06668d] dark:text-[#8ad6ff]">Clinical Summary</p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                        {latestHistory.analysis.summary}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/70 bg-white/70 px-3 py-2 text-right dark:border-white/10 dark:bg-white/5">
                      <p className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-400">Priority</p>
                      <p className="mt-1 text-sm font-black text-slate-900 dark:text-white">
                        {titleCase(latestHistory.analysis.priority)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4">
                    <div>
                      <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Possible Conditions</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {(latestHistory.analysis.possible_conditions || []).map((condition) => (
                          <span
                            key={condition}
                            className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs font-bold text-slate-600 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-200"
                          >
                            {condition}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Recommendations</p>
                      <div className="mt-2 space-y-2">
                        {(latestHistory.analysis.recommendations || []).map((recommendation) => (
                          <div
                            key={recommendation}
                            className="rounded-2xl border border-slate-200 bg-white/80 px-3 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-300"
                          >
                            {recommendation}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </form>
          ) : (
            <form onSubmit={handleReportSubmit} className="space-y-5">
              <SectionLabel
                icon={FileUp}
                title="Report Submission"
                subtitle="Attach a PDF or image report and keep the upload structured for timeline review."
              />

              <label className="flex cursor-pointer flex-col gap-3 rounded-[1.6rem] border border-dashed border-slate-300 bg-slate-50/70 px-4 py-5 transition hover:border-[#009cde]/40 hover:bg-[#009cde]/5 dark:border-slate-700 dark:bg-slate-950/40 dark:hover:border-[#009cde]/30">
                <div className="flex items-start gap-3">
                  <div className="rounded-2xl border border-white/80 bg-white/80 p-3 text-[#009cde] shadow-sm dark:border-white/10 dark:bg-white/5">
                    <FileUp size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-black text-slate-900 dark:text-white">
                      {reportForm.file ? reportForm.file.name : 'Upload PDF or image'}
                    </p>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      Supported: PDF, JPG, JPEG, PNG
                    </p>
                  </div>
                </div>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/*"
                  className="hidden"
                  onChange={(event) => handleReportChange('file', event.target.files?.[0] || null)}
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Report Type</span>
                  <select
                    value={reportForm.report_type}
                    onChange={(event) => handleReportChange('report_type', event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  >
                    {REPORT_TYPE_OPTIONS.map((reportType) => (
                      <option key={reportType} value={reportType}>
                        {titleCase(reportType)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-2">
                  <span className="text-xs font-bold uppercase tracking-[0.22em] text-slate-400">Date of Report</span>
                  <input
                    type="date"
                    value={reportForm.date_of_report}
                    onChange={(event) => handleReportChange('date_of_report', event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-[#009cde] focus:ring-4 focus:ring-[#009cde]/10 dark:border-slate-700 dark:bg-slate-950/60 dark:text-slate-100"
                  />
                </label>
              </div>

              {reportError ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                  {reportError}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={uploadingReport}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
              >
                {uploadingReport ? <LoaderCircle size={16} className="animate-spin" /> : <FileUp size={16} />}
                <span>{uploadingReport ? 'Uploading Report...' : 'Submit Report'}</span>
              </button>

              {latestReport ? (
                <div className="rounded-[1.6rem] border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-500/20 dark:bg-emerald-500/10">
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-300">
                    <CheckCircle2 size={18} />
                    <p className="text-sm font-black">Report added to timeline</p>
                  </div>
                  <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                    <p><span className="font-bold text-slate-900 dark:text-white">Title:</span> {latestReport.title || latestReport.file_name}</p>
                    <p><span className="font-bold text-slate-900 dark:text-white">Type:</span> {titleCase(latestReport.report_type)}</p>
                    <p><span className="font-bold text-slate-900 dark:text-white">Date:</span> {latestReport.date_of_report || 'Not specified'}</p>
                    {Array.isArray(latestReport.summary) && latestReport.summary.length > 0 ? (
                      <p className="rounded-2xl border border-white/80 bg-white/80 px-3 py-3 text-sm leading-relaxed dark:border-white/10 dark:bg-white/5">
                        {latestReport.summary[0]}
                      </p>
                    ) : null}
                  </div>
                </div>
              ) : null}

              <div className="rounded-[1.6rem] border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                  <AlertCircle size={16} />
                  <p className="text-sm font-semibold">Reports stay structured</p>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                  Report type and report date are stored with the upload so the timeline and downstream analysis can correlate symptoms with supporting documents.
                </p>
              </div>
            </form>
          )}
        </div>
      </div>
    </aside>
  );
}
