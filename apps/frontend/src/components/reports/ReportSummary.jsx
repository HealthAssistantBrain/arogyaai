import { AlertTriangle, ClipboardList, FileText, NotebookText, ShieldCheck, UserRound } from 'lucide-react';
import { safeArray } from '../../utils/safeData';

const FALLBACK_SUMMARY = 'Report uploaded successfully. Analysis is in progress.';

const firstText = (...values) => {
    for (const value of values) {
        if (Array.isArray(value)) {
            const joined = safeArray(value).map(toDisplayText).filter(Boolean).join(' ').trim();
            if (joined) return joined;
            continue;
        }

        const text = toDisplayText(value);
        if (text) return text;
    }

    return '';
};

const toList = (value) => {
    if (Array.isArray(value)) {
        return safeArray(value).filter((item) => item !== null && item !== undefined && item !== '');
    }

    if (value === null || value === undefined || value === '') {
        return [];
    }

    if (typeof value === 'object') {
        if (Array.isArray(value.items)) {
            return safeArray(value.items).filter((item) => item !== null && item !== undefined && item !== '');
        }

        if (Array.isArray(value.data)) {
            return safeArray(value.data).filter((item) => item !== null && item !== undefined && item !== '');
        }
    }

    return [value];
};

const isPlainObject = (value) => Boolean(value && typeof value === 'object' && !Array.isArray(value));

const toDisplayText = (value) => {
    if (value === null || value === undefined) return '';

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return String(value).trim();
    }

    if (Array.isArray(value)) {
        return value.map(toDisplayText).filter(Boolean).join(' ').trim();
    }

    if (typeof value === 'object') {
        const candidate = value.text ?? value.summary ?? value.message ?? value.description ?? value.label ?? value.name ?? value.value ?? value.result ?? value.reading;
        if (candidate !== undefined && candidate !== null) {
            const text = toDisplayText(candidate);
            if (text) return text;
        }

        const formatted = formatObject(value);
        if (formatted) return formatted;

        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return '';
        }
    }

    return '';
};

const formatObject = (obj) => {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return 'N/A';

    const entries = Object.entries(obj)
        .map(([key, value]) => {
            const renderedValue = toDisplayText(value);
            return renderedValue ? `${toTitleCase(key)}: ${renderedValue}` : '';
        })
        .filter(Boolean);

    return entries.length ? entries.join(', ') : 'N/A';
};

const toTitleCase = (value) => {
    const text = toDisplayText(value);
    if (!text) return '';

    return text
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
};

const stripUuidPrefix = (value = '') => String(value).replace(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/i,
    ''
);

const normalizeExtractedValue = (item) => {
    if (item && typeof item === 'object' && !Array.isArray(item)) {
        return {
            name: toTitleCase(item.name ?? item.label ?? item.test ?? item.title ?? item.metric ?? 'Extracted Value'),
            value: item.value ?? item.result ?? item.reading ?? item.measurement ?? item.amount ?? item.score ?? item.text ?? item.summary ?? item.description,
            unit: toDisplayText(item.unit),
            status: toTitleCase(item.status ?? item.flag ?? item.trend),
        };
    }

    return {
        name: 'Extracted Value',
        value: item,
        unit: '',
        status: '',
    };
};

const looksLikeRawOcrLine = (value) => {
    const text = toDisplayText(value).replace(/\s+/g, ' ').trim().toLowerCase();

    return !text ||
        text.startsWith('preview:') ||
        text.startsWith('--- page ') ||
        text.includes('raw ocr') ||
        text.includes('ocr tab') ||
        text.length > 320;
};

const cleanList = (value) => toList(value).map(toDisplayText).filter((item) => item && !looksLikeRawOcrLine(item));

const buildSummaryText = (data = {}, summaryView = {}) => {
    const summaryCandidates = [
        data.summaryText,
        data.summary_text,
        data.summary,
        data.patientSummary,
        data.patient_summary,
        summaryView.summary,
        summaryView.summary_text,
        summaryView.keyFindings,
        summaryView.key_findings,
        summaryView.findings,
    ];

    return firstText(...summaryCandidates);
};

const buildSummaryData = (data = {}) => {
    const summaryView = data.summaryView ?? data.summary_view ?? {};
    const summaryObject = isPlainObject(data.structured_summary)
        ? data.structured_summary
        : isPlainObject(data.structuredSummary)
            ? data.structuredSummary
            : isPlainObject(data.summary)
                ? data.summary
                : {};

    const summary = buildSummaryText(data, summaryView);
    const riskAnalysis = toList(
        data.risk_analysis ??
            data.riskAnalysis ??
            data.risks ??
            summaryView.risk_analysis ??
            summaryView.riskAnalysis ??
            summaryView.risks
    );
    const recommendations = toList(data.recommendations ?? summaryView.recommendations);
    const extractedValues = toList(
        summaryObject.abnormal ??
            summaryObject.abnormal_values ??
            data.abnormal_values ??
            data.abnormalValues ??
            summaryView.extracted_values ??
            summaryView.extractedValues ??
            summaryView.abnormal_values ??
            summaryView.abnormalValues
    );
    const riskLevel = firstText(
        data.risk_level,
        data.riskLevel,
        data.severity,
        summaryView.risk_level,
        summaryView.riskLevel
    ) || 'Unknown';
    const originalFileName = firstText(
        data.original_filename,
        data.originalFilename
    );
    const fileName = originalFileName || stripUuidPrefix(firstText(
        data.file_name,
        data.fileName,
        data.name,
        data.title,
        summaryView.title
    )) || 'Uploaded report.pdf';
    const status = firstText(data.status, data.summaryStatus) || (data.success ? 'Success' : 'Ready');
    const findings = cleanList(
        summaryObject.findings ??
            data.findings ??
            summaryView.key_findings ??
            summaryView.keyFindings ??
            summaryView.findings ??
            data.summary
    );
    const notes = firstText(
        summaryObject.notes,
        data.notes,
        summaryView.notes,
        data.clinical_notes,
        data.clinicalNotes
    );
    const patient = firstText(
        summaryObject.patient,
        summaryObject.patient_info,
        data.patient,
        data.patient_info,
        data.patientInfo,
        summaryView.patient_info,
        summaryView.patientInfo
    ) || 'Not specified in the uploaded report.';
    const test = firstText(
        summaryObject.test,
        summaryObject.test_type,
        data.test,
        data.test_type,
        data.testType,
        summaryView.test_type,
        summaryView.testType,
        summaryView.title
    ) || 'Medical Report';

    return {
        fileName,
        summary,
        patient,
        test,
        findings: findings.length ? findings : cleanList(summary),
        notes: notes && !looksLikeRawOcrLine(notes) ? notes : 'Clinical review is recommended for diagnosis, treatment decisions, and comparison with prior reports.',
        risk_analysis: riskAnalysis,
        recommendations,
        extracted_values: extractedValues,
        risk_level: riskLevel,
        status,
    };
};

export const hasReportSummaryContent = (data = {}) => {
    const normalized = buildSummaryData(data);

    return Boolean(
        normalized.summary ||
            normalized.patient ||
            normalized.test ||
            normalized.findings.length ||
            normalized.notes ||
            normalized.risk_analysis.length ||
            normalized.recommendations.length ||
            normalized.extracted_values.length
    );
};

export const normalizeReportSummaryData = buildSummaryData;

const ReportSummary = ({ data = {}, className = '' }) => {
    const summaryData = buildSummaryData(data);
    const hasContent = Boolean(
        summaryData.summary ||
            summaryData.risk_analysis.length ||
            summaryData.recommendations.length ||
            summaryData.extracted_values.length
    );
    const normalizedStatus = summaryData.status.toLowerCase();
    const statusLabel = normalizedStatus.includes('success') || normalizedStatus.includes('complete') ? 'Success' : summaryData.status;
    const findingItems = safeArray(summaryData.findings).map(toDisplayText).filter((item) => item && !looksLikeRawOcrLine(item));
    const extractedItems = safeArray(summaryData.extracted_values).map(normalizeExtractedValue);
    const notes = summaryData.notes || FALLBACK_SUMMARY;

    const Section = ({ icon: Icon, title, children }) => (
        <section className="border-t border-slate-200/80 dark:border-stroke pt-6 first:border-t-0 first:pt-0">
            <div className="mb-4 flex items-center gap-3">
                <div className="size-9 rounded-lg border border-slate-200 bg-white text-primary shadow-sm dark:border-stroke dark:bg-white/5 dark:text-violet-300 flex items-center justify-center">
                    <Icon size={18} strokeWidth={2} />
                </div>
                <h4 className="text-[12px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-text-secondary">
                    {title}
                </h4>
            </div>
            {children}
        </section>
    );

    return (
        <div className={`space-y-6 ${className}`.trim()}>
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 rounded-lg bg-white p-7 shadow-sm ring-1 ring-slate-200 dark:bg-card/80 dark:ring-white/10">
                <div className="size-14 bg-primary/10 rounded-lg flex items-center justify-center text-primary border border-primary/20 shrink-0">
                    <FileText size={28} strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-text-muted">
                        Clinical Report Summary
                    </p>
                    <h3 className="font-black text-xl text-text-primary dark:text-text-primary tracking-tight truncate leading-tight">
                        {summaryData.fileName}
                    </h3>
                    <div className="mt-3 flex flex-wrap items-center gap-3">
                        <span className="text-[10px] uppercase font-black text-text-muted tracking-widest opacity-60">
                            Status: Structured
                        </span>
                        <div className="size-1 bg-slate-200 rounded-full"></div>
                        <span className="text-[10px] uppercase font-black text-primary tracking-widest">
                            Risk Level: {summaryData.risk_level}
                        </span>
                    </div>
                </div>
                <div className="px-4 py-2 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-black rounded-lg uppercase tracking-[0.18em] border border-emerald-500/20 flex items-center gap-2 shrink-0 shadow-sm">
                    <ShieldCheck size={14} strokeWidth={3} />
                    {statusLabel}
                </div>
            </div>

            {hasContent || findingItems.length || notes ? (
                <div className="space-y-7 rounded-lg bg-white p-8 shadow-sm ring-1 ring-slate-200 dark:bg-card/80 dark:ring-white/10">
                    <Section icon={UserRound} title="Patient Info">
                        <p className="text-[14px] font-medium leading-[1.6] text-text-primary dark:text-text-primary">
                            {summaryData.patient}
                        </p>
                    </Section>

                    <Section icon={ClipboardList} title="Test Type">
                        <p className="text-[14px] font-semibold leading-[1.6] text-text-primary dark:text-text-primary">
                            {summaryData.test}
                        </p>
                    </Section>

                    <Section icon={FileText} title="Key Findings">
                        <div className="space-y-3">
                            {findingItems.length ? (
                                findingItems.map((finding, index) => (
                                    <div key={`${finding}-${index}`} className="flex items-start gap-3 text-[14px] text-text-primary dark:text-text-primary">
                                        <div className="mt-2 size-1.5 rounded-full bg-primary shrink-0"></div>
                                        <p className="leading-[1.6] whitespace-pre-wrap">{finding}</p>
                                    </div>
                                ))
                            ) : (
                                <p className="text-[14px] leading-[1.6] text-slate-500 dark:text-text-secondary">No key findings were returned for this report.</p>
                            )}
                        </div>
                    </Section>

                    <Section icon={AlertTriangle} title="Abnormal Values">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {extractedItems.length ? (
                                extractedItems.map((item, index) => {
                                    const renderedValue = toDisplayText(item.value);
                                    const renderedStatus = toDisplayText(item.status);
                                    const renderedUnit = toDisplayText(item.unit);

                                    return (
                                        <div key={`${item.name}-${index}`} className="p-5 rounded-lg bg-red-50/80 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20">
                                            <div className="mb-3 flex items-start justify-between gap-3">
                                                <p className="text-[10px] text-red-700 dark:text-red-300 uppercase font-black tracking-[0.18em]">{item.name || 'Abnormal Value'}</p>
                                                <span className="rounded-md bg-red-600 px-2 py-1 text-[9px] font-black uppercase tracking-[0.14em] text-text-primary">
                                                    {renderedStatus || 'Abnormal'}
                                                </span>
                                            </div>
                                            <p className="text-lg font-black text-red-900 dark:text-red-100 leading-[1.4]">
                                                {renderedValue || 'No value'}
                                                {renderedUnit ? <span className="ml-1 text-sm text-red-500 dark:text-red-200 font-bold">{renderedUnit}</span> : null}
                                            </p>
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="text-[14px] leading-[1.6] text-slate-500 dark:text-text-secondary">No abnormal values were identified in the structured summary.</p>
                            )}
                        </div>
                    </Section>

                    <Section icon={NotebookText} title="Clinical Notes">
                        <p className="text-[14px] font-medium leading-[1.6] text-text-primary dark:text-text-primary">
                            {notes}
                        </p>
                    </Section>
                </div>
            ) : (
                <div className="p-8 rounded-lg bg-surface/80 border border-slate-100 dark:border-stroke text-center">
                    <p className="text-[13px] text-slate-500 dark:text-text-secondary">Summary not available for this report</p>
                </div>
            )}
        </div>
    );
};

export default ReportSummary;

