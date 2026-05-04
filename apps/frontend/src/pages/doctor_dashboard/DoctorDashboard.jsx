import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Bell,
  Brain,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Footprints,
  Heart,
  History,
  ListChecks,
  Moon,
  RotateCcw,
  Search,
  Send,
  Sparkles,
  Stethoscope,
  Users,
} from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, Tooltip } from 'recharts';

import {
  fetchDoctorAlerts,
  fetchDoctorPatientDetail,
  fetchDoctorPatients,
  markDoctorPatientReviewed,
  sendDoctorRecommendation,
  triggerDoctorFollowUp,
} from '../../services/doctorService';
import { useAuthStore } from '../../store/authStore';

const POLL_INTERVAL_MS = 15000;

const triageTone = {
  CRITICAL: 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-200',
  HIGH: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/20 dark:bg-orange-500/10 dark:text-orange-200',
  MODERATE: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200',
  LOW: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-200',
  UNKNOWN: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-stroke dark:bg-background/60 dark:text-text-secondary',
};

const alertTone = {
  critical: 'border-red-200 bg-red-50 text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-200',
  warning: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200',
  info: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-stroke dark:bg-background/60 dark:text-text-secondary',
};

const safeArray = (value) => (Array.isArray(value) ? value : []);

const formatDateTime = (value) => {
  if (!value) return 'No activity';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No activity';
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const relativeTime = (value) => {
  if (!value) return 'No activity';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'No activity';
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.max(0, Math.round(diffMs / 60000));
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
};

const formatRisk = (value) => (Number.isFinite(Number(value)) ? `${Math.round(Number(value))}%` : '--');

const formatSleep = (vital) => {
  const value = Number(vital?.value);
  if (!Number.isFinite(value)) return '--';
  const unit = String(vital?.unit || '').toLowerCase();
  const hours = unit.startsWith('hour') || unit === 'hr' || unit === 'hrs' ? value : value / 60;
  return `${hours.toFixed(1)}h`;
};

const formatNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.round(numeric).toLocaleString() : '--';
};

const normalizeTriage = (value) => String(value || 'UNKNOWN').toUpperCase();

function Panel({ children, className = '' }) {
  return (
    <section className={`rounded-xl border border-slate-200/80 bg-white/90 shadow-sm backdrop-blur dark:border-stroke dark:bg-[#121025]/88 ${className}`}>
      {children}
    </section>
  );
}

function MetricTile({ icon: Icon, label, value, meta, tone = 'text-slate-900 dark:text-text-primary' }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-stroke dark:bg-background/35">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-text-muted">{label}</p>
          <p className={`mt-2 text-2xl font-black tracking-tight ${tone}`}>{value}</p>
        </div>
        <div className="flex size-11 items-center justify-center rounded-xl bg-white text-slate-500 shadow-sm dark:bg-white/5 dark:text-text-secondary">
          <Icon size={20} />
        </div>
      </div>
      <p className="mt-3 text-xs font-semibold text-slate-500 dark:text-text-muted">{meta}</p>
    </div>
  );
}

function MiniLine({ data, color = '#0f766e' }) {
  const chartData = safeArray(data).map((item, index) => ({
    label: item?.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : String(index + 1),
    value: Number(item?.value),
  })).filter((item) => Number.isFinite(item.value));

  if (chartData.length < 2) {
    return (
      <div className="flex h-24 items-center justify-center rounded-xl border border-dashed border-slate-200 text-xs font-bold text-text-muted dark:border-stroke dark:text-slate-500">
        No trend yet
      </div>
    );
  }

  return (
    <div className="h-24">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
          <Tooltip
            contentStyle={{ borderRadius: 12, border: '1px solid rgba(148,163,184,.35)', fontSize: 12 }}
            labelStyle={{ fontWeight: 700 }}
          />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function PatientList({ patients, selectedPatientId, onSelect, query, onQueryChange }) {
  return (
    <Panel className="min-h-[720px] overflow-hidden">
      <div className="border-b border-slate-200/80 p-5 dark:border-stroke">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">Clinical Queue</p>
            <h2 className="mt-2 text-xl font-black tracking-tight text-slate-950 dark:text-text-primary">Patients</h2>
          </div>
          <div className="flex size-11 items-center justify-center rounded-xl bg-teal-50 text-teal-700 dark:bg-teal-500/10 dark:text-teal-200">
            <Users size={20} />
          </div>
        </div>
        <div className="relative mt-5">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" size={16} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search patients"
            className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-teal-600 focus:ring-4 focus:ring-teal-600/10 dark:border-stroke dark:bg-background/40 dark:text-slate-100"
          />
        </div>
      </div>

      <div className="max-h-[calc(100vh-260px)] space-y-3 overflow-y-auto p-4">
        {patients.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm font-semibold text-text-muted dark:border-stroke">
            No patients found
          </div>
        ) : patients.map((patient) => {
          const triage = normalizeTriage(patient.triage_level);
          const isSelected = selectedPatientId === patient.id;
          return (
            <button
              key={patient.id}
              type="button"
              onClick={() => onSelect(patient.id)}
              className={`w-full rounded-xl border p-4 text-left transition-all ${
                isSelected
                  ? 'border-teal-500 bg-teal-50/80 shadow-[0_18px_42px_-30px_rgba(15,118,110,0.85)] dark:border-teal-400/50 dark:bg-teal-500/10'
                  : 'border-slate-200 bg-white hover:-translate-y-0.5 hover:border-teal-200 hover:bg-slate-50 dark:border-stroke dark:bg-background/25 dark:hover:border-teal-400/30'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-black text-slate-950 dark:text-text-primary">{patient.name}</p>
                  <p className="mt-1 truncate text-xs font-semibold text-slate-500 dark:text-text-muted">{patient.email}</p>
                </div>
                <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-black ${triageTone[triage] || triageTone.UNKNOWN}`}>
                  {triage}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-text-muted">Risk</p>
                  <p className="mt-1 text-lg font-black text-slate-950 dark:text-text-primary">{formatRisk(patient.risk_score)}</p>
                </div>
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-text-muted">Alerts</p>
                  <p className={`mt-1 text-lg font-black ${patient.alert_status === 'critical' ? 'text-red-600' : patient.alert_status === 'active' ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {patient.active_alerts || 0}
                  </p>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-text-muted">
                <Clock size={14} />
                <span>{relativeTime(patient.last_activity)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}

function AlertsPanel({ alerts, onSelectPatient }) {
  return (
    <Panel className="min-h-[720px] overflow-hidden">
      <div className="border-b border-slate-200/80 p-5 dark:border-stroke">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-red-600 dark:text-red-300">Live Feed</p>
            <h2 className="mt-2 text-xl font-black tracking-tight text-slate-950 dark:text-text-primary">Alerts</h2>
          </div>
          <div className="relative flex size-11 items-center justify-center rounded-xl bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-200">
            <Bell size={20} />
            {alerts.length > 0 ? <span className="absolute right-2 top-2 size-2 rounded-full bg-red-500" /> : null}
          </div>
        </div>
      </div>
      <div className="max-h-[calc(100vh-220px)] space-y-3 overflow-y-auto p-4">
        {alerts.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center dark:border-stroke">
            <CheckCircle2 className="mx-auto text-emerald-500" size={30} />
            <p className="mt-3 text-sm font-bold text-slate-500 dark:text-text-muted">No active alerts</p>
          </div>
        ) : alerts.map((alert) => {
          const tone = alertTone[alert.severity] || alertTone.info;
          return (
            <button
              key={alert.id}
              type="button"
              onClick={() => onSelectPatient(alert.patient_id)}
              className={`w-full rounded-xl border p-4 text-left transition hover:-translate-y-0.5 ${tone}`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 shrink-0" size={18} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-black">{alert.title}</p>
                    {alert.emergency ? (
                      <span className="rounded-full bg-red-600 px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.16em] text-text-primary">
                        Emergency
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs font-black uppercase tracking-[0.18em] opacity-75">{alert.patient_name}</p>
                  <p className="mt-2 line-clamp-3 text-sm font-semibold leading-relaxed opacity-90">{alert.message}</p>
                  <p className="mt-3 text-xs font-bold opacity-70">{formatDateTime(alert.created_at)}</p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}

function PatientDetail({ detail, loading, onReviewed, onSendRecommendation, onFollowUp, actionLoading }) {
  const [recommendationText, setRecommendationText] = useState('');
  const [followUpReason, setFollowUpReason] = useState('');

  useEffect(() => {
    setRecommendationText('');
    setFollowUpReason('');
  }, [detail?.patient?.id]);

  if (loading && !detail) {
    return (
      <Panel className="flex min-h-[720px] items-center justify-center p-8">
        <div className="text-center">
          <Activity className="mx-auto animate-pulse text-teal-600" size={34} />
          <p className="mt-4 text-sm font-bold text-slate-500 dark:text-text-muted">Loading patient telemetry...</p>
        </div>
      </Panel>
    );
  }

  if (!detail) {
    return (
      <Panel className="flex min-h-[720px] items-center justify-center p-8">
        <div className="text-center">
          <Stethoscope className="mx-auto text-text-secondary" size={42} />
          <p className="mt-4 text-sm font-bold text-slate-500 dark:text-text-muted">Select a patient to open monitoring details.</p>
        </div>
      </Panel>
    );
  }

  const patient = detail.patient || {};
  const vitals = detail.vitals || {};
  const prediction = detail.ml_predictions?.latest || {};
  const shapInsights = safeArray(detail.shap_insights);
  const rag = detail.rag_explanation?.data || {};
  const ragRecommendations = safeArray(rag.recommendations);
  const timeline = [...safeArray(detail.history)].reverse().slice(0, 8);
  const triage = normalizeTriage(patient.triage_level);
  const shapMax = Math.max(...shapInsights.map((item) => Number(item.abs_shap_value) || 0), 0.01);

  const handleSend = async () => {
    await onSendRecommendation(recommendationText);
    setRecommendationText('');
  };

  const handleFollowUp = async () => {
    await onFollowUp(followUpReason);
    setFollowUpReason('');
  };

  return (
    <div className="space-y-5">
      <Panel className="overflow-hidden">
        <div className="border-b border-slate-200/80 bg-[linear-gradient(135deg,rgba(15,118,110,0.10),rgba(14,165,233,0.08))] p-6 dark:border-stroke">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-teal-200 bg-white/80 px-3 py-1 text-[10px] font-black uppercase tracking-[0.24em] text-teal-700 dark:border-teal-400/20 dark:bg-teal-500/10 dark:text-teal-200">
                  Doctor Dashboard
                </span>
                <span className={`rounded-full border px-3 py-1 text-xs font-black ${triageTone[triage] || triageTone.UNKNOWN}`}>
                  {triage}
                </span>
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight text-slate-950 dark:text-text-primary">{patient.name}</h1>
              <p className="mt-2 text-sm font-semibold text-slate-500 dark:text-text-muted">{patient.email}</p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/70 bg-white/80 p-4 shadow-sm dark:border-stroke dark:bg-background/35">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Risk</p>
                <p className="mt-2 text-2xl font-black text-slate-950 dark:text-text-primary">{formatRisk(patient.risk_score)}</p>
              </div>
              <div className="rounded-xl border border-white/70 bg-white/80 p-4 shadow-sm dark:border-stroke dark:bg-background/35">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Alerts</p>
                <p className="mt-2 text-2xl font-black text-red-600">{patient.active_alerts || 0}</p>
              </div>
              <div className="rounded-xl border border-white/70 bg-white/80 p-4 shadow-sm dark:border-stroke dark:bg-background/35">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Updated</p>
                <p className="mt-2 text-sm font-black text-slate-700 dark:text-text-primary">{relativeTime(patient.last_activity)}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 p-5 md:grid-cols-3">
          <MetricTile
            icon={Heart}
            label="Heart Rate"
            value={`${formatNumber(vitals.heart_rate?.value)} bpm`}
            meta={formatDateTime(vitals.heart_rate?.timestamp)}
            tone={Number(vitals.heart_rate?.value) > 100 ? 'text-red-600' : 'text-slate-950 dark:text-text-primary'}
          />
          <MetricTile
            icon={Moon}
            label="Sleep"
            value={formatSleep(vitals.sleep)}
            meta={formatDateTime(vitals.sleep?.timestamp)}
            tone="text-indigo-700 dark:text-indigo-200"
          />
          <MetricTile
            icon={Footprints}
            label="Activity"
            value={formatNumber(vitals.activity?.value)}
            meta={formatDateTime(vitals.activity?.timestamp)}
            tone="text-teal-700 dark:text-teal-200"
          />
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,0.75fr)]">
        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">Vitals Trend</p>
              <h3 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Recent telemetry</h3>
            </div>
            <Activity className="text-teal-600" size={22} />
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <div>
              <p className="mb-2 text-xs font-black text-slate-500">Heart rate</p>
              <MiniLine data={vitals.history?.heart_rate} color="#dc2626" />
            </div>
            <div>
              <p className="mb-2 text-xs font-black text-slate-500">Sleep</p>
              <MiniLine data={vitals.history?.sleep} color="#4f46e5" />
            </div>
            <div>
              <p className="mb-2 text-xs font-black text-slate-500">Activity</p>
              <MiniLine data={vitals.history?.activity} color="#0f766e" />
            </div>
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">ML Prediction</p>
              <h3 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">{prediction.risk_level || 'No prediction'}</h3>
            </div>
            <Brain className="text-sky-600" size={22} />
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/35">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Score</p>
              <p className="mt-2 text-2xl font-black text-slate-950 dark:text-text-primary">{formatRisk(prediction.risk_score)}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/35">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Confidence</p>
              <p className="mt-2 text-2xl font-black text-slate-950 dark:text-text-primary">{formatRisk(prediction.confidence)}</p>
            </div>
          </div>
          <p className="mt-4 text-xs font-bold text-slate-500 dark:text-text-muted">
            {prediction.model_version || 'Latest persisted model'} | {formatDateTime(prediction.calculated_at)}
          </p>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">SHAP Insights</p>
              <h3 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Drivers</h3>
            </div>
            <Sparkles className="text-amber-500" size={22} />
          </div>
          <div className="mt-5 space-y-3">
            {shapInsights.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 p-6 text-sm font-semibold text-text-muted dark:border-stroke">
                No SHAP driver data for the latest prediction.
              </div>
            ) : shapInsights.slice(0, 6).map((item) => {
              const width = Math.max(8, ((Number(item.abs_shap_value) || 0) / shapMax) * 100);
              return (
                <div key={item.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/35">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-black text-slate-900 dark:text-text-primary">{String(item.feature_name || '').replaceAll('_', ' ')}</p>
                    <span className={`text-xs font-black ${Number(item.shap_value) >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {Number(item.shap_value || 0).toFixed(3)}
                    </span>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-card">
                    <div className={`h-full rounded-full ${Number(item.shap_value) >= 0 ? 'bg-red-500' : 'bg-emerald-500'}`} style={{ width: `${width}%` }} />
                  </div>
                  {item.explanation ? <p className="mt-3 text-xs font-semibold leading-relaxed text-slate-500 dark:text-text-muted">{item.explanation}</p> : null}
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">RAG Explanation</p>
              <h3 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Clinical context</h3>
            </div>
            <ListChecks className="text-teal-600" size={22} />
          </div>
          <div className="mt-5 space-y-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/35">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Summary</p>
              <p className="mt-2 text-sm font-semibold leading-relaxed text-slate-700 dark:text-text-primary">
                {rag.summary || rag.clinical_insight || 'No RAG explanation available for the latest prediction.'}
              </p>
            </div>
            {ragRecommendations.length > 0 ? (
              <div className="space-y-2">
                {ragRecommendations.slice(0, 3).map((item, index) => {
                  const text = typeof item === 'string' ? item : (item.description || item.detail || item.title);
                  return (
                    <div key={`${text}-${index}`} className="flex gap-3 rounded-xl border border-teal-100 bg-teal-50 p-3 text-sm font-semibold text-teal-900 dark:border-teal-500/20 dark:bg-teal-500/10 dark:text-teal-100">
                      <CheckCircle2 className="mt-0.5 shrink-0" size={16} />
                      <span>{text}</span>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">Clinical Timeline</p>
              <h3 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Reports, labs, alerts</h3>
            </div>
            <History className="text-slate-500" size={22} />
          </div>
          <div className="mt-5 space-y-3">
            {timeline.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 p-6 text-sm font-semibold text-text-muted dark:border-stroke">
                No timeline events yet.
              </div>
            ) : timeline.map((event) => (
              <div key={event.id} className="flex gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-stroke dark:bg-background/35">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-slate-500 dark:bg-white/5">
                  {event.type === 'Reports' ? <FileText size={18} /> : event.type === 'Alerts' ? <AlertCircle size={18} /> : <Activity size={18} />}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-black text-slate-900 dark:text-text-primary">{event.title}</p>
                    <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-black text-slate-500 dark:border-stroke dark:bg-background">{event.type}</span>
                  </div>
                  <p className="mt-1 text-xs font-bold text-slate-500">{formatDateTime(event.event_date || event.timestamp)}</p>
                  <p className="mt-2 line-clamp-2 text-sm font-semibold text-slate-600 dark:text-text-secondary">{event.description}</p>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">Action Panel</p>
              <h3 className="mt-2 text-lg font-black text-slate-950 dark:text-text-primary">Care actions</h3>
            </div>
            <Stethoscope className="text-teal-600" size={22} />
          </div>
          <div className="mt-5 space-y-4">
            <button
              type="button"
              onClick={onReviewed}
              disabled={actionLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-background px-4 py-3 text-sm font-black text-text-primary transition hover:bg-card disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200"
            >
              <CheckCircle2 size={17} />
              Mark Reviewed
            </button>

            <div>
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Recommendation</label>
              <textarea
                value={recommendationText}
                onChange={(event) => setRecommendationText(event.target.value)}
                placeholder="Write a recommendation"
                className="mt-2 min-h-28 w-full resize-none rounded-xl border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-teal-600 focus:ring-4 focus:ring-teal-600/10 dark:border-stroke dark:bg-background/35 dark:text-slate-100"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={actionLoading || !recommendationText.trim()}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-teal-700 px-4 py-3 text-sm font-black text-text-primary transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Send size={17} />
                Send Recommendation
              </button>
            </div>

            <div>
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-text-muted">Follow-up</label>
              <input
                value={followUpReason}
                onChange={(event) => setFollowUpReason(event.target.value)}
                placeholder="Follow-up reason"
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-teal-600 focus:ring-4 focus:ring-teal-600/10 dark:border-stroke dark:bg-background/35 dark:text-slate-100"
              />
              <button
                type="button"
                onClick={handleFollowUp}
                disabled={actionLoading}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-black text-teal-800 transition hover:bg-teal-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-teal-500/20 dark:bg-teal-500/10 dark:text-teal-100"
              >
                <Calendar size={17} />
                Trigger Follow-up
              </button>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

export default function DoctorDashboard() {
  const role = useAuthStore((state) => String(state.role ?? state.user?.role ?? state.profile?.role ?? 'patient').toLowerCase());
  const isDoctor = role === 'doctor';
  const [patients, setPatients] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [query, setQuery] = useState('');
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadPatients = useCallback(async ({ silent = false } = {}) => {
    if (!isDoctor) return;
    try {
      if (!silent) setLoadingPatients(true);
      const data = await fetchDoctorPatients();
      const nextPatients = safeArray(data.patients);
      setPatients(nextPatients);
      setSelectedPatientId((current) => {
        if (current && nextPatients.some((patient) => patient.id === current)) return current;
        return nextPatients[0]?.id ?? null;
      });
      setError(null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error('doctor patients fetch failed', err);
      setError(err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Unable to load doctor dashboard.');
    } finally {
      if (!silent) setLoadingPatients(false);
    }
  }, [isDoctor]);

  const loadAlerts = useCallback(async () => {
    if (!isDoctor) return;
    try {
      const data = await fetchDoctorAlerts();
      setAlerts(safeArray(data.alerts));
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error('doctor alerts fetch failed', err);
    }
  }, [isDoctor]);

  const loadDetail = useCallback(async (patientId, { silent = false } = {}) => {
    if (!isDoctor || !patientId) return;
    try {
      if (!silent) setLoadingDetail(true);
      const data = await fetchDoctorPatientDetail(patientId);
      setDetail(data);
      setError(null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error('doctor patient detail fetch failed', err);
      setError(err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Unable to load patient detail.');
    } finally {
      if (!silent) setLoadingDetail(false);
    }
  }, [isDoctor]);

  useEffect(() => {
    if (!isDoctor) return undefined;
    void loadPatients({ silent: false });
    void loadAlerts();
    const interval = window.setInterval(() => {
      void loadPatients({ silent: true });
      void loadAlerts();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [isDoctor, loadAlerts, loadPatients]);

  useEffect(() => {
    if (!selectedPatientId || !isDoctor) {
      setDetail(null);
      return undefined;
    }
    void loadDetail(selectedPatientId, { silent: false });
    const interval = window.setInterval(() => {
      void loadDetail(selectedPatientId, { silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [isDoctor, loadDetail, selectedPatientId]);

  const filteredPatients = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return patients;
    return patients.filter((patient) => (
      `${patient.name || ''} ${patient.email || ''} ${patient.triage_level || ''}`
        .toLowerCase()
        .includes(normalized)
    ));
  }, [patients, query]);

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.id === selectedPatientId) || null,
    [patients, selectedPatientId]
  );

  const handleManualRefresh = async () => {
    await Promise.all([
      loadPatients({ silent: false }),
      loadAlerts(),
      selectedPatientId ? loadDetail(selectedPatientId, { silent: true }) : Promise.resolve(),
    ]);
  };

  const refreshAfterAction = async () => {
    await Promise.all([
      loadPatients({ silent: true }),
      loadAlerts(),
      selectedPatientId ? loadDetail(selectedPatientId, { silent: true }) : Promise.resolve(),
    ]);
  };

  const handleReviewed = async () => {
    if (!selectedPatientId) return;
    setActionLoading(true);
    try {
      await markDoctorPatientReviewed(selectedPatientId);
      toast.success('Patient alerts marked reviewed');
      await refreshAfterAction();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Unable to mark reviewed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRecommendation = async (message) => {
    if (!selectedPatientId || !message.trim()) return;
    setActionLoading(true);
    try {
      await sendDoctorRecommendation(selectedPatientId, { message, priority: normalizeTriage(selectedPatient?.triage_level) === 'CRITICAL' ? 'urgent' : 'medium' });
      toast.success('Recommendation sent');
      await refreshAfterAction();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Unable to send recommendation');
    } finally {
      setActionLoading(false);
    }
  };

  const handleFollowUp = async (reason) => {
    if (!selectedPatientId) return;
    setActionLoading(true);
    try {
      await triggerDoctorFollowUp(selectedPatientId, { reason });
      toast.success('Follow-up triggered');
      await refreshAfterAction();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Unable to trigger follow-up');
    } finally {
      setActionLoading(false);
    }
  };

  if (!isDoctor) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6 dark:bg-background">
        <Panel className="max-w-lg p-8 text-center">
          <Stethoscope className="mx-auto text-text-secondary" size={44} />
          <h1 className="mt-4 text-2xl font-black text-slate-950 dark:text-text-primary">Doctor access required</h1>
          <p className="mt-3 text-sm font-semibold leading-relaxed text-slate-500 dark:text-text-muted">
            This monitoring layer is restricted to authenticated doctor accounts.
          </p>
        </Panel>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f6f5f8_0%,#eef5f3_100%)] font-display text-slate-950 antialiased dark:bg-[linear-gradient(180deg,#0B0819_0%,#090d14_100%)] dark:text-slate-100">
      <main className="mx-auto max-w-[1840px] p-4 sm:p-6 xl:p-8">
        <div className="mb-6 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-[10px] font-black uppercase tracking-[0.24em] text-text-muted">
              <span>Clinical Monitoring</span>
              <ChevronRight size={12} />
              <span className="text-teal-700 dark:text-teal-300">Real-time Triage</span>
            </div>
            <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950 dark:text-text-primary">Doctor Dashboard</h1>
            <p className="mt-3 max-w-3xl text-sm font-semibold leading-relaxed text-slate-500 dark:text-text-muted">
              Monitor patient risk, alerts, vitals, ML explanations, and longitudinal history from one clinical queue.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs font-black text-slate-500 shadow-sm dark:border-stroke dark:bg-white/5 dark:text-text-secondary">
              <span className="size-2 rounded-full bg-emerald-500" />
              Polling every {POLL_INTERVAL_MS / 1000}s
            </div>
            <button
              type="button"
              onClick={handleManualRefresh}
              disabled={loadingPatients}
              className="inline-flex items-center gap-2 rounded-xl bg-teal-700 px-5 py-3 text-sm font-black text-text-primary shadow-lg shadow-teal-900/10 transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RotateCcw size={17} className={loadingPatients ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {error ? (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-200">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <div className="mb-5 grid gap-4 md:grid-cols-4">
          <MetricTile icon={Users} label="Visible Patients" value={patients.length} meta="Authenticated patient records" />
          <MetricTile icon={AlertTriangle} label="Active Alerts" value={alerts.length} meta="Emergency and abnormal events" tone="text-red-600" />
          <MetricTile icon={Brain} label="Critical Queue" value={patients.filter((p) => normalizeTriage(p.triage_level) === 'CRITICAL').length} meta="Sorted to top" tone="text-orange-600" />
          <MetricTile icon={Clock} label="Last Update" value={lastUpdated ? relativeTime(lastUpdated) : '--'} meta={formatDateTime(lastUpdated)} tone="text-teal-700 dark:text-teal-200" />
        </div>

        <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)_360px]">
          <PatientList
            patients={filteredPatients}
            selectedPatientId={selectedPatientId}
            onSelect={setSelectedPatientId}
            query={query}
            onQueryChange={setQuery}
          />

          <AnimatePresence mode="wait">
            <motion.div
              key={selectedPatientId || 'empty'}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <PatientDetail
                detail={detail}
                loading={loadingDetail}
                onReviewed={handleReviewed}
                onSendRecommendation={handleRecommendation}
                onFollowUp={handleFollowUp}
                actionLoading={actionLoading}
              />
            </motion.div>
          </AnimatePresence>

          <AlertsPanel alerts={alerts} onSelectPatient={setSelectedPatientId} />
        </div>

      </main>
    </div>
  );
}

