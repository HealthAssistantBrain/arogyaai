import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
    FileText,
    Plus,
    Eye,
    Download,
    Trash2,
    Image as LucideImage,
    Loader2,
    AlertCircle,
} from 'lucide-react';
import ReportSummary, { hasReportSummaryContent, normalizeReportSummaryData } from '../components/reports/ReportSummary';
import { ROUTES } from '../router/routes';
import HeartLoader from '../components/ui/HeartLoader';
import Skeleton from '../components/ui/Skeleton';
import { useAuthStore } from '../store/authStore';
import { useReportUploadStore } from '../store/reportUploadStore';
import useReportsStore, { isReportProcessingStatus, normalizeReport, reportHasRenderableSummary } from '../store/reportsStore';
import ReportsSkeleton from '../components/skeleton/ReportsSkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';
import { apiClient } from '../lib/apiClient';
import { resolveReportType, saveUploadedReportSession } from '../lib/reportUpload';

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

const getFilenameFromContentDisposition = (header = '') => {
    const encodedMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
    if (encodedMatch?.[1]) {
        return decodeURIComponent(encodedMatch[1].replace(/"/g, '').trim());
    }

    const match = header.match(/filename="?([^";]+)"?/i);
    return match?.[1]?.trim() || '';
};

const triggerBlobDownload = (blob, fileName) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName || 'clinical-report-summary.pdf';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
};

const DocumentPreview = ({ report }) => {
    const previewUrl = report?.localPreviewUrl || report?.fileUrl;

    if (!previewUrl) {
        return (
            <div className="h-full min-h-[18rem] flex items-center justify-center rounded-[1.5rem] border border-dashed border-slate-200 dark:border-stroke bg-slate-50 dark:bg-white/5 text-center px-6">
                <div>
                    <FileText size={28} className="mx-auto text-text-secondary mb-4" />
                    <p className="text-[10px] font-black uppercase tracking-[0.25em] text-text-muted">Preview is being prepared</p>
                </div>
            </div>
        );
    }

    if (report?.reportKind === 'image') {
        return (
            <img
                src={previewUrl}
                alt={report.fileName}
                className="h-full max-h-full w-full object-contain rounded-[1.5rem] bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-stroke"
            />
        );
    }

    return (
        <iframe
            title={`Preview ${report.fileName}`}
            src={previewUrl}
            className="h-full min-h-[24rem] w-full rounded-[1.5rem] bg-white border border-slate-200 dark:border-stroke"
        />
    );
};

const ProcessingSummarySkeleton = ({ statusMessage = 'Analyzing report...' }) => (
    <div className="h-full rounded-[1.5rem] border border-slate-200/80 dark:border-stroke/50 bg-white dark:bg-[#090611] p-6 shadow-xl">
        <div className="flex items-center gap-3 mb-7">
            <Loader2 size={18} className="animate-spin text-primary" />
            <div>
                <p className="text-[10px] font-black uppercase tracking-[0.25em] text-primary">Analyzing report...</p>
                <p className="mt-2 text-[12px] text-text-muted">{statusMessage}</p>
            </div>
        </div>
        <div className="space-y-4">
            <Skeleton height={18} className="w-2/3" />
            <Skeleton height={14} className="w-full" />
            <Skeleton height={14} className="w-5/6" />
            <Skeleton height={72} className="w-full" />
            <Skeleton height={14} className="w-4/5" />
            <Skeleton height={14} className="w-3/5" />
        </div>
    </div>
);

const Reports = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const authUserId = useAuthStore((state) => state.user?.id ?? null);
    const pendingFile = useReportUploadStore((state) => state.pendingFile);
    const pendingPreviewUrl = useReportUploadStore((state) => state.pendingPreviewUrl);
    const pendingReportId = useReportUploadStore((state) => state.pendingReportId);
    const uploadInProgress = useReportUploadStore((state) => state.isProcessing);
    const setReportResult = useReportUploadStore((state) => state.setReportResult);
    const setProcessing = useReportUploadStore((state) => state.setProcessing);
    const setUploadErrorMessage = useReportUploadStore((state) => state.setErrorMessage);
    const startedUploadRef = useRef('');
    const [downloadingReportId, setDownloadingReportId] = useState(null);
    const [reportPendingDelete, setReportPendingDelete] = useState(null);
    const [deletingReportId, setDeletingReportId] = useState(null);
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
        fetchReportStatus,
        setSelectedReportId,
        replaceOptimisticReport,
        markReportFailed,
        deleteReport,
    } = useReportsStore();
    const focusedReportId = location.state?.reportId;
    const selectedReport = reports.find((report) => report.id === selectedReportId) ?? null;
    const hasReportsSnapshot = cacheOwnerId === authUserId && lastFetchedAt !== null;
    const showPageSkeleton = !hasReportsSnapshot && (isFetching || !hasHydratedCache);
    const showReportsOverlay = useSmartFetchOverlay(isFetching, hasReportsSnapshot, { exitDelayMs: 200 });
    const selectedReportLoading = detailFetchingId === selectedReport?.id;
    const selectedReportProcessing = selectedReport ? isReportProcessingStatus(selectedReport.status) : false;
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

        if (isReportProcessingStatus(selectedReport.status)) {
            return;
        }

        if (reportHasRenderableSummary(selectedReport)) {
            return;
        }

        void fetchReportDetail(selectedReport.id);
    }, [fetchReportDetail, selectedReport]);

    useEffect(() => {
        const shouldStartUpload = Boolean(location.state?.startUpload);
        const temporaryReportId = location.state?.reportId || pendingReportId;

        if (!shouldStartUpload || !pendingFile || !temporaryReportId || startedUploadRef.current === temporaryReportId) {
            return;
        }

        startedUploadRef.current = temporaryReportId;
        setProcessing(true);
        setUploadErrorMessage('');

        const uploadReport = async () => {
            const reportType = resolveReportType(pendingFile);
            const formData = new FormData();
            formData.append('file', pendingFile);
            formData.append('report_type', reportType);

            try {
                const response = await apiClient.post('/reports/upload', formData, {
                    timeout: 30000,
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                });
                const payload = response.data?.data ?? response.data ?? {};
                const normalizedReport = normalizeReport({
                    ...payload,
                    fileName: pendingFile.name,
                    file_name: pendingFile.name,
                    originalFilename: pendingFile.name,
                    original_filename: pendingFile.name,
                    fileSize: pendingFile.size,
                    file_size: pendingFile.size,
                    reportType: payload.report_type ?? reportType,
                    report_type: payload.report_type ?? reportType,
                    status: payload.status ?? 'PROCESSING',
                    localPreviewUrl: pendingPreviewUrl,
                    statusMessage: 'Analyzing report...',
                });
                const nextReport = replaceOptimisticReport(temporaryReportId, normalizedReport);
                saveUploadedReportSession(nextReport);
                setReportResult(nextReport, pendingFile.name);
                toast.success('Report uploaded. Analysis is running.');
            } catch (error) {
                const message = error?.response?.data?.error || error?.response?.data?.detail || error?.message || 'Upload failed.';
                markReportFailed(temporaryReportId, message);
                setUploadErrorMessage(message);
                setProcessing(false);
                toast.error(message);
            }
        };

        void uploadReport();
    }, [
        location.state,
        markReportFailed,
        pendingFile,
        pendingPreviewUrl,
        pendingReportId,
        replaceOptimisticReport,
        setProcessing,
        setReportResult,
        setUploadErrorMessage,
    ]);

    useEffect(() => {
        const processingIds = reports
            .filter((report) => isReportProcessingStatus(report.status) && !String(report.id).startsWith('local-'))
            .map((report) => report.id);

        setProcessing(reports.some((report) => isReportProcessingStatus(report.status)));

        if (!processingIds.length) {
            return;
        }

        let cancelled = false;
        const refreshStatuses = async () => {
            await Promise.all(processingIds.map((reportId) => fetchReportStatus(reportId)));
            if (cancelled) return;
            const stillProcessing = useReportsStore
                .getState()
                .reports
                .some((report) => isReportProcessingStatus(report.status));
            setProcessing(stillProcessing);
        };

        void refreshStatuses();
        const intervalId = window.setInterval(refreshStatuses, 2500);

        return () => {
            cancelled = true;
            window.clearInterval(intervalId);
        };
    }, [fetchReportStatus, reports, setProcessing]);

    const selectedSummaryData = selectedReport ? (selectedReport.summaryData ?? normalizeReportSummaryData(selectedReport)) : null;
    const selectedReportIsLocal = selectedReport ? String(selectedReport.id || '').startsWith('local-') : false;
    const selectedReportDownloading = selectedReport ? downloadingReportId === selectedReport.id : false;
    const downloadDisabled = !selectedReport || selectedReportLoading || selectedReportProcessing || selectedReportIsLocal || selectedReportDownloading;
    const handleSelectReport = (report) => {
        setSelectedReportId(report.id);
    };
    const handleRequestDelete = (event, report) => {
        event.stopPropagation();
        setReportPendingDelete(report);
    };

    const handleConfirmDelete = async () => {
        if (!reportPendingDelete?.id) return;

        const reportId = reportPendingDelete.id;
        setDeletingReportId(reportId);
        setReportPendingDelete(null);

        try {
            await deleteReport(reportId);
            toast.success('Report deleted.');
        } catch (error) {
            console.error('[Reports] Failed to delete report:', error);
            toast.error('Failed to delete report');
        } finally {
            setDeletingReportId(null);
        }
    };

    const handleDownloadSummary = async () => {
        if (!selectedReport) return;

        if (downloadDisabled) {
            console.warn('[Reports] PDF export skipped because the report is not ready for download.', {
                reportId: selectedReport.id,
            });
            return;
        }

        try {
            setDownloadingReportId(selectedReport.id);
            console.log('[Reports] Download Summary clicked.', {
                reportId: selectedReport.id,
                fileName: selectedReport.fileName,
                hasSummaryContent: hasReportSummaryContent(selectedReport.summaryData ?? normalizeReportSummaryData(selectedReport)),
            });
            const response = await apiClient.get(`/reports/${selectedReport.id}/download`, {
                responseType: 'blob',
                timeout: 60000,
            });
            const headerName = getFilenameFromContentDisposition(response.headers?.['content-disposition']);
            const fallbackName = `${selectedReport.fileName?.replace(/\.[^.]+$/, '') || 'clinical-report'}-clinical-summary.pdf`;
            triggerBlobDownload(response.data, headerName || fallbackName);
            toast.success('Clinical PDF downloaded.');
        } catch (error) {
            console.error('[Reports] Failed to export summary PDF:', error);
            toast.error(error?.response?.data?.detail || error?.message || 'PDF generation failed.');
        } finally {
            setDownloadingReportId(null);
        }
    };

    if (showPageSkeleton) {
        return <ReportsSkeleton />;
    }

    return (
        <div className="bg-background dark:bg-card text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Top Navbar */}


                    {/* Content Section */}
                    <div className="flex-1 overflow-hidden flex flex-col">
                        <div className="flex flex-col md:flex-row md:items-center justify-between px-10 py-10 shrink-0 gap-6">
                            <div>
                                <h2 className="text-4xl lg:text-5xl font-black tracking-tighter uppercase text-text-primary dark:text-text-primary leading-none italic">Medical Reports Hub</h2>
                                <p className="text-text-muted font-bold uppercase tracking-[0.25em] text-[11px] mt-4 opacity-80 leading-none">Manage and analyze clinical diagnostics via AI Extraction engines</p>
                            </div>
                            <button
                                onClick={() => navigate(ROUTES.UPLOAD)}
                                disabled={uploadInProgress}
                                className="bg-primary hover:bg-[#4a34c1] text-white px-9 py-5 rounded-[1.5rem] font-black text-[11px] uppercase tracking-[0.25em] flex items-center gap-4 transition-all shadow-2xl shadow-primary/40 active:scale-95 group leading-none disabled:opacity-60 disabled:cursor-not-allowed"
                            >
                                {uploadInProgress ? <Loader2 size={18} strokeWidth={3} className="animate-spin" /> : <Plus size={18} strokeWidth={3} className="group-hover:rotate-90 transition-transform" />}
                                {uploadInProgress ? 'Analyzing Report' : 'Upload New Report'}
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
                                    <div className="flex min-h-[18rem] items-center justify-center rounded-[2.25rem] border border-dashed border-slate-200 dark:border-stroke bg-white/60 dark:bg-white/5 p-8">
                                        <div className="flex flex-col items-center gap-4 text-center">
                                            <AlertCircle size={28} className="text-text-secondary" />
                                            <div>
                                                <p className="text-[13px] font-black text-text-primary dark:text-text-primary uppercase tracking-[0.2em]">
                                                    No reports uploaded yet
                                                </p>
                                                <p className="mt-3 text-[11px] font-bold uppercase tracking-[0.25em] text-text-muted leading-relaxed">
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
                                        <div
                                            key={report.id}
                                            className={`p-6 rounded-[2.25rem] border transition-all cursor-pointer flex items-center gap-5 group shadow-xl text-left ${isSelected
                                                ? 'bg-white dark:bg-white/10 border-primary shadow-primary/15'
                                                : 'bg-white/60 dark:bg-white/5 border-transparent hover:border-slate-200 dark:hover:border-stroke shadow-slate-200/30 dark:shadow-none'
                                                }`}
                                        >
                                            <button
                                                type="button"
                                                onClick={() => handleSelectReport(report)}
                                                className="flex min-w-0 flex-1 items-center gap-5 text-left"
                                            >
                                                <div
                                                    className={`size-14 rounded-[1.25rem] flex items-center justify-center shadow-inner transition-transform group-hover:scale-110 ${report.reportKind === 'pdf' ? 'bg-red-50 text-red-500' : 'bg-secondary/10 text-secondary'
                                                        }`}
                                                >
                                                    {icon}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <h4 className="font-black text-text-primary dark:text-text-primary text-[15px] tracking-tight truncate leading-none mb-2">
                                                        {report.fileName}
                                                    </h4>
                                                    <p className="text-[10px] text-text-muted font-bold uppercase tracking-widest leading-none">
                                                        {formatDate(report.createdAt)} • {formatBytes(report.fileSize)}
                                                    </p>
                                                </div>
                                                <div className="shrink-0">
                                                    <span className={`px-4 py-2 rounded-full text-[9px] font-black uppercase tracking-widest shadow-sm border leading-none ${getStatusStyles(report.status)}`}>
                                                        {isReportProcessingStatus(report.status) ? (
                                                            <span className="inline-flex items-center gap-1.5">
                                                                <Loader2 size={10} className="animate-spin" />
                                                                {report.status}
                                                            </span>
                                                        ) : report.status}
                                                    </span>
                                                </div>
                                            </button>
                                            <button
                                                type="button"
                                                onClick={(event) => handleRequestDelete(event, report)}
                                                disabled={deletingReportId === report.id}
                                                title="Delete report"
                                                aria-label={`Delete ${report.fileName}`}
                                                className="size-10 shrink-0 rounded-full border border-transparent bg-slate-100/80 text-text-muted transition-all hover:border-red-100 hover:bg-red-50 hover:text-red-600 active:scale-90 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white/5 dark:hover:border-red-400/20 dark:hover:bg-red-500/10 dark:hover:text-red-300"
                                            >
                                                {deletingReportId === report.id ? <Loader2 size={16} className="mx-auto animate-spin" /> : <Trash2 size={16} className="mx-auto" />}
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Preview Area */}
                            <div className="flex-1 flex overflow-hidden min-w-0">
                                <div className="flex-1 bg-white/40 dark:bg-white/5 backdrop-blur-2xl rounded-[3rem] overflow-hidden flex flex-col shadow-2xl border border-white/40 dark:border-stroke relative group min-w-0">
                                    <div className="p-7 bg-white/40 dark:bg-white/5 border-b border-stroke dark:border-stroke flex items-center justify-between relative z-10">
                                        <div className="flex items-center gap-4">
                                            <div className="size-8 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
                                                <Eye size={18} />
                                            </div>
                                            <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-text-muted leading-none">
                                                Summary view:{' '}
                                                <span className="text-text-primary dark:text-text-primary opacity-100">
                                                    {selectedReport?.fileName || 'Select a report to preview'}
                                                </span>
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <button
                                                type="button"
                                                onClick={handleDownloadSummary}
                                                disabled={downloadDisabled}
                                                title="Download clinical report"
                                                aria-label="Download clinical report"
                                                className="p-2.5 hover:bg-white dark:hover:bg-white/10 rounded-xl text-slate-500 dark:text-text-muted transition-all active:scale-90 border border-transparent hover:border-slate-100 hover:text-primary hover:shadow-lg hover:shadow-primary/10 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-500 disabled:hover:shadow-none"
                                            >
                                                {selectedReportDownloading ? <Loader2 size={18} className="animate-spin" /> : <Download size={18} />}
                                            </button>
                                        </div>
                                    </div>
                                    <div className="flex-1 overflow-hidden p-6 sm:p-10 flex items-center justify-center bg-slate-100/40 dark:bg-black/20 min-h-0">
                                        {selectedReport ? (
                                            <div className="w-full h-full bg-white dark:bg-[#1a1433] rounded-[2.5rem] shadow-2xl relative overflow-hidden flex flex-col border border-slate-200 dark:border-stroke/50 transition-transform group-hover:scale-[0.99] duration-700 min-h-0">
                                                {showDetailOverlay ? <SmartLoadingOverlay label="Refreshing summary" /> : null}
                                                {selectedReportProcessing ? (
                                                    <div className="flex-1 min-h-0 bg-slate-50 dark:bg-[#0f0b1f] p-4 sm:p-6">
                                                        <div className="grid h-full min-h-0 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)]">
                                                            <DocumentPreview report={selectedReport} />
                                                            <ProcessingSummarySkeleton statusMessage={selectedReport.statusMessage || 'OCR, parsing, and clinical extraction are running in the background.'} />
                                                        </div>
                                                    </div>
                                                ) : selectedReportLoading && !hasSelectedSummary ? (
                                                    <div className="flex-1 flex items-center justify-center px-6 text-center">
                                                        <div className="max-w-sm">
                                                            <div className="h-12 flex justify-center mb-4"><HeartLoader size={48} /></div>
                                                            <p className="mt-5 text-[11px] font-black uppercase tracking-[0.3em] text-text-muted">
                                                                Loading extracted summary
                                                            </p>
                                                            <p className="mt-3 text-[13px] text-slate-500 dark:text-text-muted leading-6">
                                                                Fetching the report detail so we can render the real summary data.
                                                            </p>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="flex-1 min-h-0 bg-slate-50 dark:bg-[#0f0b1f] p-4 sm:p-6">
                                                        <div className="h-full rounded-[2rem] border border-slate-200/80 dark:border-stroke/50 bg-white dark:bg-[#090611] shadow-xl overflow-hidden flex flex-col min-h-0">
                                                            <div className="flex-1 overflow-y-auto custom-scrollbar p-5 sm:p-7">
                                                                <ReportSummary data={selectedSummaryData || selectedReport} />
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            <div className="w-full h-full rounded-[2.5rem] border border-dashed border-slate-200 dark:border-stroke bg-white/70 dark:bg-white/5 flex items-center justify-center text-center px-8">
                                                <div className="max-w-md">
                                                    <div className="size-16 mx-auto rounded-[1.75rem] bg-primary/10 text-primary flex items-center justify-center">
                                                        <Eye size={28} />
                                                    </div>
                                                    <p className="mt-6 text-[12px] font-black uppercase tracking-[0.3em] text-slate-500">
                                                        Select a report to inspect
                                                    </p>
                                                    <p className="mt-4 text-[13px] text-slate-500 dark:text-text-muted leading-7">
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

            {reportPendingDelete ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="delete-report-title">
                    <div className="w-full max-w-md rounded-[2rem] border border-white/70 bg-white p-7 shadow-2xl dark:border-stroke dark:bg-[#171126]">
                        <h3 id="delete-report-title" className="text-lg font-black text-text-primary dark:text-text-primary">
                            Delete report?
                        </h3>
                        <p className="mt-4 text-sm font-semibold leading-6 text-slate-500 dark:text-text-secondary">
                            Are you sure you want to delete this report?
                        </p>
                        <p className="mt-3 truncate text-xs font-bold uppercase tracking-[0.2em] text-text-muted">
                            {reportPendingDelete.fileName}
                        </p>
                        <div className="mt-7 flex justify-end gap-3">
                            <button
                                type="button"
                                onClick={() => setReportPendingDelete(null)}
                                className="rounded-full border border-slate-200 px-5 py-3 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 transition-all hover:bg-slate-50 dark:border-stroke dark:text-text-secondary dark:hover:bg-white/5"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={handleConfirmDelete}
                                className="rounded-full bg-red-600 px-5 py-3 text-[10px] font-black uppercase tracking-[0.2em] text-text-primary shadow-lg shadow-red-600/20 transition-all hover:bg-red-700 active:scale-95"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
};

export default Reports;


