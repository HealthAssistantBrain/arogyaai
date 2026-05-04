import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { ArrowLeft, Bell, ChevronRight, CheckCircle2, Database, FileText, HelpCircle, Lock, RotateCw, SearchCode, Settings, ShieldCheck } from 'lucide-react';

import { ROUTES } from '../router/routes';
import { useReportUploadStore } from '../store/reportUploadStore';
import { apiClient } from '../lib/apiClient';
import { resolveReportType, saveUploadedReportSession } from '../lib/reportUpload';
import ReportLoader from '../components/ui/ReportLoader';

const PIPELINE_STAGES = [
    { key: 'uploading', label: 'Uploading file', target: 20, detail: 'Sending the report securely to ArogyaAI.' },
    { key: 'extracting', label: 'Extracting text', target: 40, detail: 'Running OCR and extracting readable medical text.' },
    { key: 'processing', label: 'AI processing', target: 70, detail: 'Prediction service is analysing clinical markers and patterns.' },
    { key: 'insights', label: 'Generating insights', target: 100, detail: 'Preparing the final summary, risks, and recommendations.' },
];

const STAGE_TARGETS = Object.fromEntries(PIPELINE_STAGES.map((stage) => [stage.key, stage.target]));

const ReportProcessing = () => {
    const navigate = useNavigate();
    const pendingFile = useReportUploadStore((state) => state.pendingFile);
    const uploadedFileName = useReportUploadStore((state) => state.uploadedFileName);
    const setReportResult = useReportUploadStore((state) => state.setReportResult);
    const setProcessing = useReportUploadStore((state) => state.setProcessing);
    const setErrorMessageInStore = useReportUploadStore((state) => state.setErrorMessage);

    const [progress, setProgress] = useState(0);
    const [stageKey, setStageKey] = useState('uploading');
    const [errorMessage, setErrorMessage] = useState('');

    const stageKeyRef = useRef('uploading');
    const errorMessageRef = useRef('');

    useEffect(() => {
        stageKeyRef.current = stageKey;
    }, [stageKey]);

    useEffect(() => {
        errorMessageRef.current = errorMessage;
    }, [errorMessage]);

    useEffect(() => {
        if (!pendingFile) {
            navigate(ROUTES.UPLOAD, { replace: true });
            return;
        }

        const controller = new AbortController();
        let isMounted = true;
        let uploadFallbackTimeout;
        let extractingStageTimeout;
        let processingStageTimeout;
        let insightStageTimeout;

        setProcessing(true);
        setErrorMessage('');
        setErrorMessageInStore('');

        const interval = setInterval(() => {
            if (!isMounted) return;

            setProgress((prev) => {
                if (errorMessageRef.current) return prev;

                const cap = STAGE_TARGETS[stageKeyRef.current] ?? 100;
                if (prev >= cap) return prev;

                const remaining = cap - prev;
                const increment = cap === 100 ? Math.min(remaining, 4) : Math.max(1, Math.ceil(remaining / 10));
                return Math.min(prev + increment, cap);
            });
        }, 250);

        const analyzeReport = async () => {
            const formData = new FormData();
            formData.append('file', pendingFile);
            formData.append('report_type', resolveReportType(pendingFile));

            try {
                setStageKey('uploading');
                setProgress(1);

                uploadFallbackTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setProgress((prev) => Math.max(prev, 8));
                }, 150);

                extractingStageTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setStageKey('extracting');
                    setProgress((prev) => Math.max(prev, 24));
                }, 600);

                processingStageTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setStageKey('processing');
                    setProgress((prev) => Math.max(prev, 45));
                }, 1400);

                const response = await apiClient.post('/reports/upload', formData, {
                    signal: controller.signal,
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    onUploadProgress: (event) => {
                        if (!isMounted || !event.total) return;

                        const uploadPercent = Math.min(20, Math.round((event.loaded / event.total) * 20));
                        setProgress((prev) => Math.max(prev, uploadPercent));

                        if (event.loaded >= event.total) {
                            setStageKey('extracting');
                        }
                    },
                });

                if (!isMounted) return;

                console.log('UPLOAD RESPONSE:', response);
                clearTimeout(uploadFallbackTimeout);
                clearTimeout(extractingStageTimeout);
                clearTimeout(processingStageTimeout);

                if (!response.data?.success) {
                    throw new Error(response.data?.error || 'Processing failed');
                }

                setStageKey('insights');
                setProgress((prev) => Math.max(prev, 72));

                insightStageTimeout = setTimeout(() => {
                    if (!isMounted) return;
                    setProgress((prev) => Math.max(prev, 100));
                }, 300);

                const reportData = response.data.data || {};
                saveUploadedReportSession(reportData);
                setReportResult(reportData, pendingFile.name);

                setTimeout(() => {
                    if (!isMounted) return;
                    setProcessing(false);
                    navigate(ROUTES.UPLOAD_SUCCESS);
                }, 900);
            } catch (err) {
                if (!isMounted) return;

                if (axios.isCancel(err) || err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') {
                    return;
                }

                const message = err?.response?.data?.error || err?.response?.data?.detail || err?.message || 'Processing failed';
                setErrorMessage(message);
                setErrorMessageInStore(message);
                setProcessing(false);
                toast.error(message);
            }
        };

        analyzeReport();

        return () => {
            isMounted = false;
            controller.abort();
            setProcessing(false);
            clearTimeout(uploadFallbackTimeout);
            clearTimeout(extractingStageTimeout);
            clearTimeout(processingStageTimeout);
            clearTimeout(insightStageTimeout);
            clearInterval(interval);
        };
    }, [navigate, pendingFile, setErrorMessageInStore, setProcessing, setReportResult]);

    const activeStage = PIPELINE_STAGES.find((stage) => stage.key === stageKey) || PIPELINE_STAGES[0];
    const getStageStatus = (stageTarget) => {
        if (progress >= stageTarget) return 'done';
        if (progress >= Math.max(0, stageTarget - 20)) return 'active';
        return 'pending';
    };

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">


                    <div className="flex-1 flex flex-col items-center justify-center p-10 max-w-4xl mx-auto w-full relative z-10 pb-20">
                        <div className="relative size-64 flex flex-col items-center justify-center mb-16">
                            <ReportLoader />

                            <div className="text-center z-10 flex flex-col items-center mt-6">
                                <div className="px-4 py-1.5 bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black uppercase tracking-[0.25em] rounded-full border border-[#6143f4]/20 shadow-sm leading-none">
                                    {errorMessage ? 'Processing Failed' : activeStage.label}
                                </div>
                            </div>
                        </div>

                        <div className="text-center mb-12 space-y-4">
                            <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none uppercase italic">Analyzing your medical report</h2>
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-relaxed max-w-xl mx-auto">
                                {errorMessage || activeStage.detail}
                            </p>
                            <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-300">{uploadedFileName || pendingFile?.name}</p>
                        </div>

                        <div className="w-full max-w-2xl bg-white dark:bg-[#131022] border border-slate-100 dark:border-white/10 rounded-[2.5rem] p-10 shadow-2xl">
                            <div className="space-y-8">
                                {[
                                    { icon: RotateCw, text: 'Uploading file', trigger: 20 },
                                    { icon: SearchCode, text: 'Extracting text', trigger: 40 },
                                    { icon: Database, text: 'AI processing', trigger: 70 },
                                    { icon: ShieldCheck, text: 'Generating insights', trigger: 100 },
                                ].map((step) => {
                                    const status = getStageStatus(step.trigger);

                                    return (
                                        <div key={step.text} className={`flex items-center gap-6 transition-all duration-500 ${status === 'pending' ? 'opacity-30' : 'opacity-100'}`}>
                                            <div className={`size-14 rounded-2xl flex items-center justify-center shrink-0 border-2 transition-all ${status === 'done'
                                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
                                                : status === 'active'
                                                    ? 'bg-[#6143f4]/10 border-[#6143f4]/20 text-[#6143f4]'
                                                    : 'bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 text-slate-400'
                                                }`}>
                                                {status === 'done' ? <CheckCircle2 size={24} strokeWidth={2.5} /> : <step.icon size={24} strokeWidth={1.5} />}
                                            </div>
                                            <div className="flex-1">
                                                <span className={`text-[15px] font-black uppercase tracking-tight block ${status === 'pending' ? 'text-slate-400' : 'text-[#13082a] dark:text-white'}`}>
                                                    {step.text}
                                                </span>
                                                <span className={`text-[9px] font-bold uppercase tracking-[0.2em] ${status === 'done' ? 'text-emerald-500' : status === 'active' ? 'text-[#6143f4]' : 'text-slate-400'}`}>
                                                    {errorMessage ? (status === 'done' ? 'Completed' : 'Stopped') : status === 'done' ? 'Completed' : status === 'active' ? 'Active Pipeline' : 'Queued'}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="mt-12 pt-8 border-t border-slate-50 dark:border-white/5 space-y-4">
                                <div className="flex justify-between items-end mb-2">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[10px] font-black tracking-[0.3em] uppercase text-slate-400 leading-none">Analysis Status</span>
                                        <p className="text-[9px] font-bold text-[#6143f4] uppercase tracking-widest opacity-60">{errorMessage ? 'Processing failed' : activeStage.label}</p>
                                    </div>
                                    <span className="text-2xl font-black text-[#6143f4] italic tracking-tighter leading-none">PROCESSING...</span>
                                </div>
                                <div className="h-5 w-full bg-slate-100 dark:bg-white/5 rounded-full p-1 border border-slate-200/50 dark:border-white/5 shadow-inner">
                                    <div className="h-full bg-gradient-to-r from-[#6143f4] to-[#009cde] rounded-full transition-all duration-700" style={{ width: `${progress}%` }} />
                                </div>
                            </div>
                        </div>

                        {errorMessage && (
                            <div className="mt-8 w-full max-w-2xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-[2rem] p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div>
                                    <h4 className="text-lg font-black text-red-600 dark:text-red-300 uppercase tracking-tight leading-none mb-2">Processing failed</h4>
                                    <p className="text-[12px] text-red-500 dark:text-red-200 font-bold leading-relaxed">{errorMessage}</p>
                                </div>
                                <button
                                    onClick={() => navigate(ROUTES.UPLOAD)}
                                    className="px-5 py-3 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-black uppercase tracking-[0.2em] text-[10px] transition-all"
                                >
                                    Try Again
                                </button>
                            </div>
                        )}

                        <div className="mt-12 inline-flex items-center gap-3 px-6 py-2.5 bg-white/50 dark:bg-white/5 backdrop-blur-3xl rounded-full border border-slate-100 dark:border-white/10 shadow-sm">
                            <Lock size={14} className="text-emerald-500" />
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] leading-none">Secure encrypted inference pipeline</p>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default ReportProcessing;
