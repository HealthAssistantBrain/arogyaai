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
import { apiClient } from '../lib/apiClient';
import { getUploadedReportHistory, getUploadedReportSession } from '../lib/reportUpload';
import { ROUTES } from '../router/routes';

const REPORT_HISTORY_FALLBACK = [];

const stripQuery = (value = '') => String(value).split('?')[0].split('#')[0];

const getFileNameFromUrl = (url = '') => {
    const cleaned = stripQuery(url);
    if (!cleaned) return '';
    const parts = cleaned.split('/');
    return decodeURIComponent(parts[parts.length - 1] || '');
};

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

const inferReportType = (reportName = '', reportUrl = '', reportType = '') => {
    const normalizedType = String(reportType || '').toUpperCase();
    const extension = stripQuery(reportName || reportUrl).split('.').pop()?.toLowerCase() || '';

    if (extension === 'pdf') return 'pdf';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'heif'].includes(extension)) return 'image';

    if (normalizedType.includes('XRAY') || normalizedType.includes('IMAGE') || normalizedType.includes('CLINICAL_NOTE')) {
        return 'image';
    }

    return 'pdf';
};

const toText = (value) => {
    if (value === null || value === undefined) return '';
    return String(value).trim();
};

const normalizeTextList = (value) => {
    if (Array.isArray(value)) {
        return value.map(toText).filter(Boolean);
    }

    const text = toText(value);
    return text ? [text] : [];
};

const normalizePatientInfo = (report = {}) => {
    const rawInfo = report?.patientInfo ?? report?.patient_info;
    if (rawInfo && typeof rawInfo === 'object' && !Array.isArray(rawInfo)) {
        return Object.entries(rawInfo)
            .map(([label, value]) => ({
                label: label
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (char) => char.toUpperCase()),
                value: toText(value),
            }))
            .filter((item) => item.value);
    }

    const text = toText(report?.parsedText ?? report?.parsed_text ?? report?.ocrText ?? report?.ocr_text);
    if (!text) return [];

    const patterns = [
        { label: 'Patient Name', pattern: /(?:patient name|name)\s*[:\-]\s*([^\n,;|]{2,80})/i },
        { label: 'Age', pattern: /(?:age)\s*[:\-]\s*([0-9]{1,3}(?:\s*(?:years?|yrs?))?)/i },
        { label: 'Gender', pattern: /(?:sex|gender)\s*[:\-]\s*([A-Za-z]{3,10})/i },
        { label: 'Patient ID', pattern: /(?:patient id|id)\s*[:\-]\s*([A-Za-z0-9-]{2,40})/i },
        { label: 'Report Date', pattern: /(?:report date|date of report|date)\s*[:\-]\s*([A-Za-z0-9,/\- ]{4,40})/i },
    ];

    return patterns
        .map(({ label, pattern }) => {
            const match = text.match(pattern);
            return match
                ? { label, value: toText(match[1]) }
                : null;
        })
        .filter(Boolean);
};

const normalizeMarkers = (value) => {
    if (!Array.isArray(value)) return [];

    return value
        .map((item) => ({
            name: toText(item?.name ?? item?.label ?? item?.test ?? item?.title ?? 'Biomarker'),
            value: toText(item?.value ?? item?.reading ?? item?.result),
            unit: toText(item?.unit),
            flag: toText(item?.flag ?? item?.status ?? item?.trend),
        }))
        .filter((item) => item.name || item.value || item.unit || item.flag);
};

const isFallbackSummary = (report = {}) => {
    const source = toText(report?.summarySource ?? report?.summary_source ?? report?.source ?? '');
    if (source.toLowerCase().includes('fallback')) {
        return true;
    }

    const text = [
        ...(normalizeTextList(report?.summary ?? report?.patientSummary ?? report?.patient_summary)),
        ...normalizeTextList(report?.ocrText ?? report?.ocr_text ?? report?.parsedText ?? report?.parsed_text),
    ]
        .join(' ')
        .toLowerCase();

    return (
        text.includes('no text could be extracted') ||
        text.includes('image ocr is not configured') ||
        text.includes('free mode currently supports direct text extraction') ||
        text.includes('pdf uploaded and stored successfully') ||
        text.includes('report uploaded and text extracted successfully')
    );
};

const normalizeSummaryView = (report = {}) => {
    const rawView = report?.summaryView ?? report?.summary_view;
    const summarySource = toText(report?.summarySource ?? report?.summary_source ?? rawView?.source ?? '');

    if (rawView && typeof rawView === 'object' && !Array.isArray(rawView)) {
        const combinedReport = {
            ...report,
            summary: rawView.summary ?? rawView.keyFindings ?? rawView.key_findings,
            summarySource: summarySource || rawView.source || '',
            ocrText: rawView.ocrText ?? rawView.ocr_text ?? report?.ocrText ?? report?.ocr_text,
            parsedText: rawView.parsedText ?? rawView.parsed_text ?? report?.parsedText ?? report?.parsed_text,
        };
        if (isFallbackSummary(combinedReport)) {
            return {
                title: toText(rawView.title ?? report?.title ?? report?.fileName),
                patientInfo: [],
                keyFindings: [],
                biomarkers: [],
                abnormalValues: [],
                notes: [],
                source: summarySource,
            };
        }

        return {
            title: toText(rawView.title ?? report?.title ?? report?.fileName),
            patientInfo: normalizePatientInfo({
                patientInfo: rawView.patientInfo ?? rawView.patient_info,
                parsedText: rawView.parsedText ?? rawView.parsed_text ?? report?.parsedText ?? report?.parsed_text,
                ocrText: rawView.ocrText ?? rawView.ocr_text ?? report?.ocrText ?? report?.ocr_text,
            }),
            keyFindings: normalizeTextList(rawView.keyFindings ?? rawView.key_findings ?? rawView.summary ?? rawView.findings),
            biomarkers: normalizeMarkers(rawView.biomarkers ?? rawView.markers),
            abnormalValues: normalizeTextList(rawView.abnormalValues ?? rawView.abnormal_values),
            notes: normalizeTextList(rawView.notes),
            source: summarySource,
        };
    }

    const sourceLooksFallback = isFallbackSummary(report) || summarySource.toLowerCase().includes('fallback');

    return {
        title: toText(report?.title ?? report?.fileName),
        patientInfo: sourceLooksFallback ? [] : normalizePatientInfo(report),
        keyFindings: sourceLooksFallback ? [] : normalizeTextList(report?.summary ?? report?.patientSummary ?? report?.patient_summary),
        biomarkers: sourceLooksFallback ? [] : normalizeMarkers(report?.markers),
        abnormalValues: sourceLooksFallback ? [] : normalizeTextList(report?.abnormalValues ?? report?.abnormal_values),
        notes: sourceLooksFallback ? [] : normalizeTextList(report?.notes ?? report?.ocrText ?? report?.ocr_text ?? report?.parsedText ?? report?.parsed_text),
        source: summarySource,
    };
};

const hasSummaryContent = (summaryView = {}) => (
    (summaryView.patientInfo?.length ?? 0) > 0 ||
    (summaryView.keyFindings?.length ?? 0) > 0 ||
    (summaryView.biomarkers?.length ?? 0) > 0 ||
    (summaryView.abnormalValues?.length ?? 0) > 0 ||
    (summaryView.notes?.length ?? 0) > 0
);

const mergeSummaryViews = (current = {}, next = {}) => ({
    title: next.title || current.title || '',
    patientInfo: next.patientInfo?.length ? next.patientInfo : current.patientInfo || [],
    keyFindings: next.keyFindings?.length ? next.keyFindings : current.keyFindings || [],
    biomarkers: next.biomarkers?.length ? next.biomarkers : current.biomarkers || [],
    abnormalValues: next.abnormalValues?.length ? next.abnormalValues : current.abnormalValues || [],
    notes: next.notes?.length ? next.notes : current.notes || [],
    source: next.source || current.source || '',
});

const formatValueText = (value) => {
    if (value === null || value === undefined || value === '') {
        return '';
    }

    if (typeof value === 'object') {
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return '';
        }
    }

    return String(value).trim();
};

const formatSummaryFile = (report) => {
    const summary = report?.summaryData ?? normalizeReportSummaryData(report);
    const lines = [];

    lines.push('ArogyaAI Summary Report');
    lines.push(`Report: ${report?.fileName || report?.title || 'Medical Report'}`);
    lines.push(`Date: ${formatDate(report?.createdAt)}`);
    if (summary.status) {
        lines.push(`Status: ${summary.status}`);
    }
    if (summary.risk_level) {
        lines.push(`Risk Level: ${summary.risk_level}`);
    }
    lines.push('');
    lines.push('Summary');
    if (summary.summary) {
        lines.push(summary.summary);
    } else {
        lines.push('Summary not available for this report');
    }
    lines.push('');
    lines.push('Risk Analysis');
    if (summary.risk_analysis.length) {
        summary.risk_analysis.forEach((item) => lines.push(`- ${formatValueText(item)}`));
    } else {
        lines.push('- No risk statements were returned for this report.');
    }
    lines.push('');
    lines.push('Recommendations');
    if (summary.recommendations.length) {
        summary.recommendations.forEach((item) => lines.push(`- ${formatValueText(item)}`));
    } else {
        lines.push('- No recommendations were returned for this report.');
    }
    lines.push('');
    lines.push('Extracted Values');
    if (summary.extracted_values.length) {
        summary.extracted_values.forEach((item) => {
            const normalizedItem = item && typeof item === 'object' && !Array.isArray(item)
                ? item
                : { value: item };
            const name = formatValueText(normalizedItem.name ?? normalizedItem.label ?? normalizedItem.test ?? 'Extracted Value') || 'Extracted Value';
            const value = formatValueText(
                normalizedItem.value ??
                    normalizedItem.result ??
                    normalizedItem.reading ??
                    normalizedItem.measurement ??
                    normalizedItem.amount ??
                    normalizedItem.score ??
                    normalizedItem.text ??
                    normalizedItem.summary ??
                    normalizedItem.description
            ) || 'No value';
            const unit = formatValueText(normalizedItem.unit);
            const status = formatValueText(normalizedItem.status ?? normalizedItem.flag ?? normalizedItem.trend);
            const pieces = [name, value];
            if (unit) {
                pieces[1] = `${value}${unit ? ` ${unit}` : ''}`;
            }
            if (status) {
                pieces.push(status);
            }
            lines.push(`- ${pieces.filter(Boolean).join(' | ')}`);
        });
    } else {
        lines.push('- No structured values were extracted from this report.');
    }

    return lines.join('\n');
};

const normalizeReport = (report) => {
    const fileUrl = report?.fileUrl ?? report?.file_url ?? report?.url ?? '';
    const fileName =
        report?.name ??
        report?.fileName ??
        report?.file_name ??
        report?.title ??
        getFileNameFromUrl(fileUrl) ??
        'Medical Report';
    const createdAt = report?.createdAt ?? report?.created_at ?? report?.uploaded_at ?? report?.date ?? null;
    const updatedAt = report?.updatedAt ?? report?.updated_at ?? null;
    const sizeValue = Number(report?.fileSize ?? report?.file_size ?? report?.sizeBytes ?? report?.size_bytes ?? null);
    const reportType = String(report?.reportType ?? report?.report_type ?? report?.type ?? 'OTHER').toUpperCase();
    const summarySource = toText(report?.summarySource ?? report?.summary_source ?? '');
    const parsedText = report?.parsedText ?? report?.parsed_text ?? '';
    const summaryView = normalizeSummaryView({
        ...report,
        fileName,
        title: report?.title ?? fileName,
        parsedText,
        parsed_text: parsedText,
        summarySource,
    });
    const markers = normalizeMarkers(report?.markers ?? summaryView.biomarkers);
    const summaryData = normalizeReportSummaryData({
        ...report,
        fileName,
        title: report?.title ?? fileName,
        summaryView,
        summarySource: summarySource || summaryView.source || report?.source || 'upload',
    });

    return {
        id: String(report?.id ?? report?.report_id ?? fileUrl ?? `${fileName}-${createdAt ?? 'report'}`),
        fileName,
        title: report?.title ?? fileName,
        fileUrl,
        reportType,
        reportKind: inferReportType(fileName, fileUrl, reportType),
        status: String(report?.status ?? 'COMPLETED').toUpperCase(),
        createdAt,
        updatedAt,
        fileSize: Number.isFinite(sizeValue) ? sizeValue : null,
        summary: Array.isArray(report?.summary) ? report.summary : normalizeTextList(report?.summary),
        summaryView,
        summaryData,
        markers,
        ocrText: report?.ocrText ?? report?.ocr_text ?? '',
        parsedText,
        abnormalValues: normalizeTextList(report?.abnormalValues ?? report?.abnormal_values),
        patientSummary: toText(report?.patientSummary ?? report?.patient_summary),
        risks: Array.isArray(report?.risks) ? report.risks : [],
        recommendations: Array.isArray(report?.recommendations) ? report.recommendations : [],
        source: report?.source ?? summarySource ?? 'upload',
        summarySource: summarySource || summaryView.source || report?.source || 'upload',
    };
};

const mergeReportEntries = (current, next) => ({
    ...current,
    ...next,
    id: next.id ?? current.id,
    fileName: next.fileName || current.fileName,
    title: next.title || current.title,
    fileUrl: next.fileUrl || current.fileUrl,
    reportType: next.reportType || current.reportType,
    reportKind: next.reportKind || current.reportKind,
    status: next.status || current.status,
    createdAt: next.createdAt || current.createdAt,
    updatedAt: next.updatedAt || current.updatedAt,
    fileSize: next.fileSize ?? current.fileSize ?? null,
    summary: Array.isArray(next.summary) && next.summary.length ? next.summary : current.summary,
    summaryView: mergeSummaryViews(current.summaryView, next.summaryView),
    summaryData: next.summaryData && hasReportSummaryContent(next.summaryData) ? next.summaryData : current.summaryData || normalizeReportSummaryData(current),
    markers: Array.isArray(next.markers) && next.markers.length ? next.markers : current.markers || [],
    ocrText: next.ocrText || current.ocrText,
    parsedText: next.parsedText || current.parsedText || '',
    abnormalValues: Array.isArray(next.abnormalValues) && next.abnormalValues.length ? next.abnormalValues : current.abnormalValues || [],
    patientSummary: next.patientSummary || current.patientSummary || '',
    risks: Array.isArray(next.risks) && next.risks.length ? next.risks : current.risks || [],
    recommendations: Array.isArray(next.recommendations) && next.recommendations.length ? next.recommendations : current.recommendations || [],
    source: next.source || current.source,
    summarySource: next.summarySource || current.summarySource || '',
});

const normalizeReportList = (items = []) => {
    const map = new Map();

    items.forEach((item) => {
        if (!item) return;

        const report = normalizeReport(item);
        const key = report.id || report.fileUrl || report.fileName;
        if (!key) return;

        const existing = map.get(key);
        map.set(key, existing ? mergeReportEntries(existing, report) : report);
    });

    return [...map.values()].sort((left, right) => {
        const leftTime = new Date(left.createdAt || 0).getTime();
        const rightTime = new Date(right.createdAt || 0).getTime();
        return rightTime - leftTime;
    });
};

const extractReportsArray = (payload) => {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.data)) return payload.data;
    if (Array.isArray(payload?.data?.data)) return payload.data.data;
    if (Array.isArray(payload?.data?.reports)) return payload.data.reports;
    if (Array.isArray(payload?.reports)) return payload.reports;
    if (Array.isArray(payload?.items)) return payload.items;
    return [];
};

const readLocalReports = () => {
    const history = getUploadedReportHistory();
    const session = getUploadedReportSession();
    return normalizeReportList([
        ...REPORT_HISTORY_FALLBACK,
        ...(Array.isArray(history) ? history : []),
        ...(session ? [session] : []),
    ]);
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
    const [reports, setReports] = useState(() => readLocalReports());
    const [selectedReport, setSelectedReport] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedReportLoading, setSelectedReportLoading] = useState(false);
    const focusedReportId = location.state?.reportId;

    const loadReports = useCallback(async () => {
        const localReports = readLocalReports();
        setReports(localReports);
        setIsLoading(true);

        try {
            const response = await apiClient.get('/reports', { timeout: 12000 });
            console.log('REPORTS FETCH:', response.data);
            const remoteReports = normalizeReportList(extractReportsArray(response.data));
            const mergedReports = normalizeReportList([...remoteReports, ...localReports]);
            setReports(mergedReports);
        } catch (error) {
            const status = error?.response?.status;
            if (status !== 404 && status !== 405) {
                console.warn('[Reports] Failed to load reports:', error);
            }
            setReports(localReports);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadReports();
    }, [loadReports]);

    useEffect(() => {
        const handleRefresh = () => {
            void loadReports();
        };

        window.addEventListener('focus', handleRefresh);
        window.addEventListener('storage', handleRefresh);

        return () => {
            window.removeEventListener('focus', handleRefresh);
            window.removeEventListener('storage', handleRefresh);
        };
    }, [loadReports]);

    useEffect(() => {
        if (!focusedReportId || !reports.length) {
            return;
        }

        const targetReport = reports.find((report) => report.id === focusedReportId);
        if (targetReport) {
            setSelectedReport(targetReport);
        }
    }, [focusedReportId, reports]);

    useEffect(() => {
        if (!selectedReport) {
            return;
        }

        const refreshedReport = reports.find((report) => report.id === selectedReport.id);
        if (!refreshedReport) {
            setSelectedReport(null);
            return;
        }

        if (refreshedReport !== selectedReport) {
            setSelectedReport(refreshedReport);
        }
    }, [reports, selectedReport]);

    useEffect(() => {
        if (!selectedReport?.id) {
            setSelectedReportLoading(false);
            return;
        }

        const currentSummary = selectedReport.summaryData ?? selectedReport.summaryView ?? normalizeSummaryView(selectedReport);
        const source = toText(selectedReport.summarySource ?? currentSummary.source).toLowerCase();
        const hasText = Boolean(toText(selectedReport.parsedText ?? selectedReport.parsed_text ?? selectedReport.ocrText ?? selectedReport.ocr_text));

        if (hasReportSummaryContent(currentSummary) || hasSummaryContent(currentSummary) || source.includes('fallback') || hasText) {
            setSelectedReportLoading(false);
            return;
        }

        let active = true;
        setSelectedReportLoading(true);

        const loadDetail = async () => {
            try {
                const response = await apiClient.get(`/reports/${selectedReport.id}`, { timeout: 12000 });
                if (!active) return;

                const detailedReport = normalizeReport(response.data?.data ?? response.data ?? {});
                const mergedReport = mergeReportEntries(selectedReport, detailedReport);
                setReports((currentReports) => currentReports.map((report) => (report.id === mergedReport.id ? mergedReport : report)));
                setSelectedReport(mergedReport);
            } catch (error) {
                if (active) {
                    console.warn('[Reports] Failed to load report details:', error);
                }
            } finally {
                if (active) {
                    setSelectedReportLoading(false);
                }
            }
        };

        void loadDetail();

        return () => {
            active = false;
        };
    }, [selectedReport]);

    const selectedSummaryData = selectedReport ? (selectedReport.summaryData ?? normalizeReportSummaryData(selectedReport)) : null;
    const selectedSummaryHasContent = Boolean(selectedSummaryData && hasReportSummaryContent(selectedSummaryData));

    const handleSelectReport = (report) => {
        setSelectedReport(report);
        setSelectedReportLoading(false);
    };

    const handleDownloadSummary = async () => {
        if (!selectedReport) return;

        const summary = selectedReport.summaryData ?? normalizeReportSummaryData(selectedReport);
        if (!hasReportSummaryContent(summary)) {
            return;
        }

        const fileContent = formatSummaryFile(selectedReport);
        const blob = new Blob([fileContent], { type: 'text/plain;charset=utf-8' });
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');

        link.href = blobUrl;
        link.download = `${selectedReport.fileName || selectedReport.title || 'medical-report'}-summary.txt`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(blobUrl);
    };

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Top Navbar */}
                    <header className="h-24 bg-white/40 dark:bg-[#131022]/40 backdrop-blur-2xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 z-10">
                        <div className="flex items-center gap-6 flex-1 max-w-2xl">
                            <div className="relative w-full group">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={20} />
                                <input className="w-full pl-14 pr-7 py-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[1.75rem] focus:ring-4 focus:ring-[#6143f4]/10 outline-none transition-all shadow-xl shadow-slate-200/30 dark:shadow-none placeholder:text-slate-400 font-medium" placeholder="Search reports, clinics, or diagnosis..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-8">
                            <button className="relative size-12 flex items-center justify-center text-slate-500 dark:text-slate-400 hover:bg-white dark:hover:bg-white/5 rounded-2xl transition-all shadow-xl shadow-slate-200/30 dark:shadow-none active:scale-95 group" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                                <Bell size={22} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#131022] animate-pulse"></span>
                            </button>
                            <div className="h-10 w-px bg-slate-200 dark:bg-white/5 hidden sm:block"></div>
                            <div className="flex items-center gap-4 group cursor-pointer" onClick={() => navigate(ROUTES.SETTINGS)}>
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors tracking-tight italic">Dr. Sarah Chen</p>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1.5 opacity-80 leading-none">Head of Cardiology</p>
                                </div>
                                <div className="size-12 rounded-[1.25rem] bg-[#6143f4]/10 overflow-hidden border-2 border-transparent group-hover:border-[#6143f4] shadow-2xl transition-all group-hover:scale-110 group-active:scale-95 group-hover:rotate-3">
                                    <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAq6-7j0ca9q9TIm8c_65_71OK_end-RsZzJ-J-ZRyUq8frKpBG3_cusF7FwKlQ1TXdIhnz04w6gN1FZNDlCFYxWXZswJcAwEZcfgM_AGNKGehADmBKbzDD357dAd17Obt03b0MXiw68tGcZ0Vr95mLzjQ_61NVq62x7xGp6SbdhqF3kScuEbRTtIm_zn_fzPBtzZ54LFxJBRpDVGG5-oyVNWpuyiCL1yJTmyzb6zKkAhu-0xlWykdN1GZpk4kw2VtwNugx6IiI5Zj8" alt="Dr. Sarah Chen" />
                                </div>
                            </div>
                        </div>
                    </header>

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

                        <div className="flex flex-1 gap-10 px-10 pb-10 overflow-hidden">
                            {/* Report Sidebar List - 35% Width */}
                            <div className="w-full md:w-[35%] flex flex-col gap-4 overflow-y-auto pr-4 custom-scrollbar">
                                {isLoading && reports.length === 0 ? (
                                    <div className="flex min-h-[18rem] items-center justify-center rounded-[2.25rem] border border-dashed border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/5 p-8">
                                        <div className="flex flex-col items-center gap-4 text-center">
                                            <Loader2 size={28} className="animate-spin text-[#6143f4]" />
                                            <p className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
                                                Loading uploaded reports
                                            </p>
                                        </div>
                                    </div>
                                ) : null}

                                {!isLoading && reports.length === 0 ? (
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
                                            className={`p-6 rounded-[2.25rem] border transition-all cursor-pointer flex items-center gap-5 group shadow-xl text-left ${
                                                isSelected
                                                    ? 'bg-white dark:bg-white/10 border-[#6143f4] shadow-[#6143f4]/15'
                                                    : 'bg-white/60 dark:bg-white/5 border-transparent hover:border-slate-200 dark:hover:border-white/10 shadow-slate-200/30 dark:shadow-none'
                                            }`}
                                        >
                                            <div
                                                className={`size-14 rounded-[1.25rem] flex items-center justify-center shadow-inner transition-transform group-hover:scale-110 ${
                                                    report.reportKind === 'pdf' ? 'bg-red-50 text-red-500' : 'bg-[#009cde]/10 text-[#009cde]'
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
                                                disabled={!selectedSummaryHasContent || selectedReportLoading}
                                                className="p-2.5 hover:bg-white dark:hover:bg-white/10 rounded-xl text-slate-500 dark:text-slate-400 transition-all active:scale-90 border border-transparent hover:border-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
                                            >
                                                <Download size={18} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="flex-1 overflow-hidden p-6 sm:p-10 flex items-center justify-center bg-slate-100/40 dark:bg-black/20 min-h-0">
                                        {selectedReport ? (
                                            <div className="w-full h-full bg-white dark:bg-[#1a1433] rounded-[2.5rem] shadow-2xl relative overflow-hidden flex flex-col border border-slate-200 dark:border-white/5 transition-transform group-hover:scale-[0.99] duration-700 min-h-0">
                                                {selectedReportLoading ? (
                                                    <div className="flex-1 flex items-center justify-center px-6 text-center">
                                                        <div className="max-w-sm">
                                                            <Loader2 size={34} className="mx-auto animate-spin text-[#6143f4]" />
                                                            <p className="mt-5 text-[11px] font-black uppercase tracking-[0.3em] text-slate-500">
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

            <style dangerouslySetInnerHTML={{ __html: `
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

