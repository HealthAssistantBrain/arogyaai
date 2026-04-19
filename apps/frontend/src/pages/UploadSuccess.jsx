import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Bell, CheckCircle2, ChevronRight, HelpCircle, Lock } from 'lucide-react';

import ReportSummary, { normalizeReportSummaryData } from '../components/reports/ReportSummary';
import { ROUTES } from '../router/routes';
import { useReportUploadStore } from '../store/reportUploadStore';

const UploadSuccess = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const storedReportResult = useReportUploadStore((state) => state.reportResult);
    const clearReportFlow = useReportUploadStore((state) => state.clearReportFlow);

    const reportData = location.state?.reportData || storedReportResult || {};

    useEffect(() => {
        if (!reportData || !Object.keys(reportData).length) {
            navigate(ROUTES.UPLOAD, { replace: true });
        }
    }, [navigate, reportData]);

    const summaryData = normalizeReportSummaryData(reportData);

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    

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
                                <ReportSummary data={summaryData} />
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
                                    onClick={() => navigate(ROUTES.MEDICAL_REPORTS, { state: { refreshReports: true, reportId: reportData.id } })}
                                    className="flex-1 py-5 bg-white dark:bg-white/5 border-2 border-[#6143f4]/20 text-[#6143f4] dark:text-white rounded-[1.5rem] font-black tracking-[0.2em] text-[11px] uppercase transition-all"
                                >
                                    Go to Reports
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
