import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
    FileText,
    Search,
    Bell,
    Plus,
    Eye,
    Download,
    Image as LucideImage,
    Loader2,
    AlertCircle,
} from 'lucide-react';
import ReportSummary, { hasReportSummaryContent, normalizeReportSummaryData } from '../components/reports/ReportSummary';
import { buildSummaryPdfFileName, generateStyledSummaryPdf } from '../utils/generateStyledSummaryPdf';
import { ROUTES } from '../router/routes';
import HeartLoader from '../components/ui/HeartLoader';
import Skeleton from '../components/ui/Skeleton';
import { useAuthStore } from '../store/authStore';
import useReportsStore, { reportHasRenderableSummary, toText } from '../store/reportsStore';
import ReportsSkeleton from '../components/skeleton/ReportsSkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const formatBytes = (bytes) => {
    const size = Number(bytes);

    if (!Number.isFinite(size) || size < 0) {
        return 'Unknown size';
    }

    if (size < 1024) {
        return `${size} B`;
    }

    const units = ['KB', 'MB', 'GB'];
    let value = size / 1024;
    let unitIndex = 0;

    while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024;
        unitIndex += 1;
    }

    const decimals = value >= 10 || unitIndex === 0 ? 0 : 1;
    return `${value.toFixed(decimals)} ${units[unitIndex]}`;
};

const formatDate = (value) => {
    if (!value) return 'Unknown date';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown date';

    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
};

const getStatusStyles = (status = '') => {
    const normalized = String(status).toUpperCase();

    if (normalized.includes('PROCESS')) {
        return 'bg-amber-100 text-amber-700 border-amber-200/60';
    }

    if (normalized.includes('FAIL')) {
        return 'bg-rose-100 text-rose-700 border-rose-200/60';
    }

    if (normalized.includes('PEND')) {
        return 'bg-slate-200 text-slate-600 border-slate-300/60';
    }

    return 'bg-emerald-100 text-emerald-700 border-emerald-200/60';
};

const Reports = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const authUserId = useAuthStore((state) => state.user?.id ?? null);
    const {
        reports,
        selectedReportId,
        loading,
        isFetching,
        detailFetchingId,
        lastFetchedAt,
        cacheOwnerId,
        hasHydratedCache,
        fetchReports,
        fetchReportDetail,
        setSelectedReportId,
    } = useReportsStore();
    const focusedReportId = location.state?.reportId;
    const selectedReport = reports.find((report) => report.id === selectedReportId) ?? null;
    const hasReportsSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
    const showPageSkeleton = !hasReportsSnapshot && (isFetching || !hasHydratedCache);
    const showReportsOverlay = useSmartFetchOverlay(isFetching, hasReportsSnapshot, { exitDelayMs: 200 });
    const selectedReportLoading = detailFetchingId === selectedReport?.id;
    const hasSelectedSummary = selectedReport ? reportHasRenderableSummary(selectedReport) : false;
    const showDetailOverlay = useSmartFetchOverlay(selectedReportLoading, hasSelectedSummary, { exitDelayMs: 200 });

    useEffect(() => {
        void fetchReports();
    }, [fetchReports]);

    useEffect(() => {
        const handleRefresh = () => {
            void fetchReports({ force: true });
        };

        window.addEventListener('focus', handleRefresh);
        window.addEventListener('storage', handleRefresh);

        return () => {
            window.removeEventListener('focus', handleRefresh);
            window.removeEventListener('storage', handleRefresh);
        };
    }, [fetchReports]);

    useEffect(() => {
        if (!focusedReportId || !reports.length) {
            return;
        }

        const targetReport = reports.find((report) => report.id === focusedReportId);
        if (targetReport) {
            setSelectedReportId(targetReport.id);
        }
    }, [focusedReportId, reports, setSelectedReportId]);

    useEffect(() => {
        if (!selectedReportId) {
            return;
        }

        const stillExists = reports.some((report) => report.id === selectedReportId);
        if (!stillExists) {
            setSelectedReportId(null);
        }
    }, [reports, selectedReportId, setSelectedReportId]);

    useEffect(() => {
        if (!selectedReport?.id) {
            return;
        }

        if (reportHasRenderableSummary(selectedReport)) {
            return;
        }

        void fetchReportDetail(selectedReport.id);
    }, [fetchReportDetail, selectedReport]);

    const selectedSummaryData = selectedReport ? (selectedReport.summaryData ?? normalizeReportSummaryData(selectedReport)) : null;
    const handleSelectReport = (report) => {
        setSelectedReportId(report.id);
    };

    const handleDownloadSummary = async () => {
        if (!selectedReport) return;

        if (selectedReportLoading) {
            console.warn('[Reports] PDF export skipped because the report is still loading.', {
                reportId: selectedReport.id,
            });
            return;
        }

        try {
            console.log('[Reports] Download Summary clicked.', {
                reportId: selectedReport.id,
                fileName: selectedReport.fileName,
                hasSummaryContent: hasReportSummaryContent(selectedReport.summaryData ?? normalizeReportSummaryData(selectedReport)),
            });
            await generateStyledSummaryPdf(selectedReport, buildSummaryPdfFileName(selectedReport));
        } catch (error) {
            console.error('[Reports] Failed to export summary PDF:', error);
            alert(`PDF generation failed: ${error?.message || 'Unknown error'}`);
        }
    };

    if (showPageSkeleton) {
        return <ReportsSkeleton />;
    }

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Top Navbar */}


                    {/* Content Section */}
                    <div className="flex-1 overflow-hidden flex flex-col">
                        <div className="flex flex-col md:flex-row md:items-center justify-between px-10 py-10 shrink-0 gap-6">
                            <div>
                                <h2 className="text-4xl lg:text-5xl font-black tracking-tighter uppercase text-[#13082a] dark:text-white leading-none italic">Medical Reports Hub</h2>
                                <p className="text-slate-400 font-bold uppercase tracking-[0.25em] text-[11px] mt-4 opacity-80 leading-none">Manage and analyze clinical diagnostics via AI Extraction engines</p>
                            </div>
                            <button
                                onClick={() => navigate(ROUTES.UPLOAD)}
                                className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-9 py-5 rounded-[1.5rem] font-black text-[11px] uppercase tracking-[0.25em] flex items-center gap-4 transition-all shadow-2xl shadow-[#6143f4]/40 active:scale-95 group leading-none"
                            >
                                <Plus size={18} strokeWidth={3} className="group-hover:rotate-90 transition-transform" />
                                Upload New Report
                            </button>
                        </div>

                        <div className="relative flex flex-1 gap-10 px-10 pb-10 overflow-hidden">
                            {showReportsOverlay ? <SmartLoadingOverlay label="Refreshing reports" className="rounded-[2.5rem]" /> : null}
                            {/* Report Sidebar List - 35% Width */}
                            <div className="w-full md:w-[35%] flex flex-col gap-4 overflow-y-auto pr-4 custom-scrollbar">
                                {loading && !hasReportsSnapshot ? (
                                    <div className="w-full flex flex-col gap-4">
                                        <Skeleton height={88} className="w-full" />
                                        <Skeleton height={88} className="w-full" />
                                        <Skeleton height={88} className="w-full" />
                                        <Skeleton height={88} className="w-full" />
                                    </div>
                                ) : null}

                                {!loading && reports.length === 0 ? (
                                    <div className="flex min-h-[18rem] items-center justify-center rounded-[2.25rem] border border-dashed border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/5 p-8">
                                        <div className="flex flex-col items-center gap-4 text-center">
                                            <AlertCircle size={28} className="text-slate-300" />
                                            <div>
                                                <p className="text-[13px] font-black text-[#13082a] dark:text-white uppercase tracking-[0.2em]">
                                                    No reports uploaded yet
                                                </p>
                                                <p className="mt-3 text-[11px] font-bold uppercase tracking-[0.25em] text-slate-400 leading-relaxed">
                                                    Upload a report to see it appear here.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                ) : null}

                                {reports.map((report) => {
                                    const isSelected = selectedReport?.id === report.id;
                                    const icon = report.reportKind === 'image' ? (
                                        <LucideImage size={24} strokeWidth={2.5} />
                                    ) : (
                                        <FileText size={24} strokeWidth={2.5} />
                                    );

                                    return (
                                        <button
                                            key={report.id}
                                            type="button"
                                            onClick={() => handleSelectReport(report)}
                                            className={`p-6 rounded-[2.25rem] border transition-all cursor-pointer flex items-center gap-5 group shadow-xl text-left ${isSelected
                                                ? 'bg-white dark:bg-white/10 border-[#6143f4] shadow-[#6143f4]/15'
                                                : 'bg-white/60 dark:bg-white/5 border-transparent hover:border-slate-200 dark:hover:border-white/10 shadow-slate-200/30 dark:shadow-none'
                                                }`}
                                        >
                                            <div
                                                className={`size-14 rounded-[1.25rem] flex items-center justify-center shadow-inner transition-transform group-hover:scale-110 ${report.reportKind === 'pdf' ? 'bg-red-50 text-red-500' : 'bg-[#009cde]/10 text-[#009cde]'
                                                    }`}
                                            >
                                                {icon}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h4 className="font-black text-[#13082a] dark:text-white text-[15px] tracking-tight truncate leading-none mb-2">
                                                    {report.fileName}
                                                </h4>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest leading-none">
                                                    {formatDate(report.createdAt)} • {formatBytes(report.fileSize)}
                                                </p>
                                            </div>
                                            <div>
                                                <span className={`px-4 py-2 rounded-full text-[9px] font-black uppercase tracking-widest shadow-sm border leading-none ${getStatusStyles(report.status)}`}>
                                                    {report.status}
                                                </span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Preview Area */}
                            <div className="flex-1 flex overflow-hidden min-w-0">
                                <div className="flex-1 bg-white/40 dark:bg-white/5 backdrop-blur-2xl rounded-[3rem] overflow-hidden flex flex-col shadow-2xl border border-white/40 dark:border-white/10 relative group min-w-0">
                                    <div className="p-7 bg-white/40 dark:bg-white/5 border-b border-white/20 dark:border-white/10 flex items-center justify-between relative z-10">
                                        <div className="flex items-center gap-4">
                                            <div className="size-8 bg-[#6143f4]/10 rounded-lg flex items-center justify-center text-[#6143f4]">
                                                <Eye size={18} />
                                            </div>
                                            <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400 leading-none">
                                                Summary view:{' '}
                                                <span className="text-[#13082a] dark:text-white opacity-100">
                                                    {selectedReport?.fileName || 'Select a report to preview'}
                                                </span>
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <button
                                                type="button"
                                                onClick={handleDownloadSummary}
                                                disabled={!selectedReport || selectedReportLoading}
                                                className="p-2.5 hover:bg-white dark:hover:bg-white/10 rounded-xl text-slate-500 dark:text-slate-400 transition-all active:scale-90 border border-transparent hover:border-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
                                            >
                                                <Download size={18} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="flex-1 overflow-hidden p-6 sm:p-10 flex items-center justify-center bg-slate-100/40 dark:bg-black/20 min-h-0">
                                        {selectedReport ? (
                                            <div className="w-full h-full bg-white dark:bg-[#1a1433] rounded-[2.5rem] shadow-2xl relative overflow-hidden flex flex-col border border-slate-200 dark:border-white/5 transition-transform group-hover:scale-[0.99] duration-700 min-h-0">
                                                {showDetailOverlay ? <SmartLoadingOverlay label="Refreshing summary" /> : null}
                                                {selectedReportLoading && !hasSelectedSummary ? (
                                                    <div className="flex-1 flex items-center justify-center px-6 text-center">
                                                        <div className="max-w-sm">
                                                            <div className="h-12 flex justify-center mb-4"><HeartLoader size={48} /></div>
                                                            <p className="mt-5 text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
                                                                Loading extracted summary
                                                            </p>
                                                            <p className="mt-3 text-[13px] text-slate-500 dark:text-slate-400 leading-6">
                                                                Fetching the report detail so we can render the real summary data.
                                                            </p>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="flex-1 min-h-0 bg-slate-50 dark:bg-[#0f0b1f] p-4 sm:p-6">
                                                        <div className="h-full rounded-[2rem] border border-slate-200/80 dark:border-white/5 bg-white dark:bg-[#090611] shadow-xl overflow-hidden flex flex-col min-h-0">
                                                            <div className="flex-1 overflow-y-auto custom-scrollbar p-5 sm:p-7">
                                                                <ReportSummary data={selectedSummaryData || selectedReport} />
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="w-full h-full rounded-[2.5rem] border border-dashed border-slate-200 dark:border-white/10 bg-white/70 dark:bg-white/5 flex items-center justify-center text-center px-8">
                                                <div className="max-w-md">
                                                    <div className="size-16 mx-auto rounded-[1.75rem] bg-[#6143f4]/10 text-[#6143f4] flex items-center justify-center">
                                                        <Eye size={28} />
                                                    </div>
                                                    <p className="mt-6 text-[12px] font-black uppercase tracking-[0.3em] text-slate-500">
                                                        Select a report to inspect
                                                    </p>
                                                    <p className="mt-4 text-[13px] text-slate-500 dark:text-slate-400 leading-7">
                                                        Click any uploaded report on the left to view the extracted summary, biomarkers, and notes.
                                                    </p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
            `}} />
        </div>
    );
};

export default Reports;

