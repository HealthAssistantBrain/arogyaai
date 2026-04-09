import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Bell, CheckCircle2, ChevronRight, FileText, HelpCircle, Lock, ShieldCheck } from 'lucide-react';

import { ROUTES } from '../router/routes';
import { useReportUploadStore } from '../store/reportUploadStore';

const UploadSuccess = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const storedReportResult = useReportUploadStore((state) => state.reportResult);
    const storedFileName = useReportUploadStore((state) => state.uploadedFileName);
    const clearReportFlow = useReportUploadStore((state) => state.clearReportFlow);

    const reportData = location.state?.reportData || storedReportResult || {};
    const fileName = location.state?.fileName || storedFileName || reportData.file_name || 'Uploaded report.pdf';

    useEffect(() => {
        if (!reportData || !Object.keys(reportData).length) {
            navigate(ROUTES.UPLOAD, { replace: true });
        }
    }, [navigate, reportData]);

    const extractedValues = reportData.abnormal_values || [];
    const summary = reportData.summary || reportData.patient_summary || 'No report summary was returned.';
    const risks = reportData.risks || [];
    const recommendations = reportData.recommendations || [];
    const riskLevel = reportData.risk_level || 'Unknown';

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    <header className="h-24 bg-white/70 dark:bg-[#0B0819]/70 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex items-center gap-6">
                            <button onClick={() => navigate(ROUTES.MEDICAL_REPORTS)} className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 shadow-sm">
                                <ArrowLeft size={18} strokeWidth={3} />
                            </button>
                            <nav className="flex items-center gap-4">
                                <span className="text-slate-400 text-[10px] font-black uppercase tracking-[0.2em]">Reports</span>
                                <ChevronRight size={14} className="text-slate-300" />
                                <span className="text-[#13082a] dark:text-white font-black text-[10px] uppercase tracking-[0.2em]">Analysis Complete</span>
                            </nav>
                        </div>
                        <div className="flex items-center gap-6">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 shadow-sm">
                                <Bell size={20} />
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                        </div>
                    </header>

                    <div className="flex-1 p-10 space-y-10 max-w-4xl mx-auto w-full relative z-10 pb-20 pt-16">
                        <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_100px_-20px_rgba(0,0,0,0.08)] overflow-hidden border border-slate-100 dark:border-white/5 relative">
                            <div className="p-16 text-center border-b border-slate-50 dark:border-white/5 bg-gradient-to-b from-emerald-500/5 to-transparent">
                                <div className="size-28 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-[2.5rem] flex items-center justify-center mx-auto mb-10 border-2 border-emerald-500/30">
                                    <CheckCircle2 size={64} strokeWidth={2} />
                                </div>
                                <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white mb-4 uppercase italic leading-none">Report Analysis Complete</h2>
                                <p className="text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.3em] max-w-lg mx-auto leading-relaxed">
                                    Summary, risk analysis, and recommendations are now available.
                                </p>
                            </div>

                            <div className="p-16 space-y-8">
                                <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-[2rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10">
                                    <div className="size-16 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] border border-[#6143f4]/20 shrink-0">
                                        <FileText size={32} strokeWidth={1.5} />
                                    </div>
                                    <div className="flex-1 text-center sm:text-left min-w-0">
                                        <h3 className="font-black text-xl text-[#13082a] dark:text-white tracking-tight truncate leading-none mb-3 italic">{fileName}</h3>
                                        <div className="flex items-center justify-center sm:justify-start gap-3">
                                            <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest opacity-60">Status: Parsed by AI</span>
                                            <div className="size-1 bg-slate-200 rounded-full"></div>
                                            <span className="text-[10px] uppercase font-black text-[#6143f4] tracking-widest">Risk Level: {riskLevel}</span>
                                        </div>
                                    </div>
                                    <div className="px-5 py-2.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-black rounded-xl uppercase tracking-[0.2em] border border-emerald-500/20 flex items-center gap-2 shrink-0 shadow-sm">
                                        <ShieldCheck size={14} strokeWidth={3} />
                                        Success
                                    </div>
                                </div>

                                <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                                    <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-3">Summary</p>
                                    <p className="text-[14px] text-[#13082a] dark:text-white font-medium leading-7">{summary}</p>
                                </div>

                                <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                                    <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-4">Risk Analysis</p>
                                    <div className="space-y-3">
                                        {risks.length ? risks.map((risk, index) => (
                                            <div key={index} className="flex items-start gap-3 text-[13px] text-[#13082a] dark:text-white">
                                                <div className="mt-1.5 size-2 rounded-full bg-[#6143f4] shrink-0"></div>
                                                <p className="leading-6">{risk}</p>
                                            </div>
                                        )) : (
                                            <p className="text-[13px] text-slate-500 dark:text-slate-300">No risk statements were returned for this report.</p>
                                        )}
                                    </div>
                                </div>

                                <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                                    <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-4">Recommendations</p>
                                    <div className="space-y-3">
                                        {recommendations.length ? recommendations.map((recommendation, index) => (
                                            <div key={index} className="flex items-start gap-3 text-[13px] text-[#13082a] dark:text-white">
                                                <div className="mt-1.5 size-2 rounded-full bg-emerald-500 shrink-0"></div>
                                                <p className="leading-6">{recommendation}</p>
                                            </div>
                                        )) : (
                                            <p className="text-[13px] text-slate-500 dark:text-slate-300">No recommendations were returned for this report.</p>
                                        )}
                                    </div>
                                </div>

                                <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                                    <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-4">Extracted Values</p>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        {extractedValues.length ? extractedValues.map((item, index) => (
                                            <div key={index} className="p-5 rounded-2xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10">
                                                <p className="text-[10px] text-slate-400 uppercase font-black tracking-[0.2em] mb-2">{item.name}</p>
                                                <p className="text-lg font-black text-[#13082a] dark:text-white">{item.value}</p>
                                                <p className="text-[10px] uppercase font-black tracking-[0.2em] mt-2 text-[#6143f4]">{item.status}</p>
                                            </div>
                                        )) : (
                                            <p className="text-[13px] text-slate-500 dark:text-slate-300">No structured values were extracted from this report.</p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="p-16 pt-0 flex flex-col sm:flex-row gap-5">
                                <button
                                    onClick={() => navigate(ROUTES.LAB_RESULTS)}
                                    className="flex-[2] py-5 bg-[#6143f4] hover:bg-[#4a34c1] text-white rounded-[1.5rem] font-black tracking-[0.3em] text-[11px] uppercase transition-all flex items-center justify-center gap-4"
                                >
                                    View Full Lab Results
                                    <ArrowRight size={18} strokeWidth={3} />
                                </button>
                                <button
                                    onClick={() => {
                                        clearReportFlow();
                                        navigate(ROUTES.UPLOAD);
                                    }}
                                    className="flex-1 py-5 bg-white dark:bg-white/5 border-2 border-slate-100 dark:border-white/10 text-[#13082a] dark:text-white rounded-[1.5rem] font-black tracking-[0.2em] text-[11px] uppercase transition-all"
                                >
                                    Upload Another
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 px-6 py-2.5 bg-white/50 dark:bg-white/5 rounded-full border border-slate-100 dark:border-white/10 shadow-sm">
                            <Lock size={14} className="text-emerald-500" />
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] leading-none">HIPAA-compliant encrypted processing</p>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default UploadSuccess;
