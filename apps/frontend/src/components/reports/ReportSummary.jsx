import { FileText, ShieldCheck } from 'lucide-react';

const firstText = (...values) => {
    for (const value of values) {
        if (Array.isArray(value)) {
            const joined = value.map(toDisplayText).filter(Boolean).join(' ').trim();
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
        return value.filter((item) => item !== null && item !== undefined && item !== '');
    }

    if (value === null || value === undefined || value === '') {
        return [];
    }

    if (typeof value === 'object') {
        if (Array.isArray(value.items)) {
            return value.items.filter((item) => item !== null && item !== undefined && item !== '');
        }

        if (Array.isArray(value.data)) {
            return value.data.filter((item) => item !== null && item !== undefined && item !== '');
        }
    }

    return [value];
};

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
        data.extracted_values ??
            data.extractedValues ??
            data.abnormal_values ??
            data.abnormalValues ??
            summaryView.extracted_values ??
            summaryView.extractedValues ??
            summaryView.abnormal_values ??
            summaryView.abnormalValues ??
            summaryView.biomarkers ??
            data.markers
    );
    const riskLevel = firstText(
        data.risk_level,
        data.riskLevel,
        data.severity,
        summaryView.risk_level,
        summaryView.riskLevel
    ) || 'Unknown';
    const fileName = firstText(
        data.file_name,
        data.fileName,
        data.name,
        data.title,
        summaryView.title
    ) || 'Uploaded report.pdf';
    const status = firstText(data.status, data.summaryStatus) || (data.success ? 'Success' : 'Ready');

    return {
        fileName,
        summary,
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
    const safeSummary = summaryData.summary || 'Summary not available for this report';
    const riskItems = summaryData.risk_analysis.map(toDisplayText).filter(Boolean);
    const recommendationItems = summaryData.recommendations.map(toDisplayText).filter(Boolean);
    const extractedItems = summaryData.extracted_values.map(normalizeExtractedValue);

    return (
        <div className={`space-y-8 ${className}`.trim()}>
            <div className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-[2rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10">
                <div className="size-16 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] border border-[#6143f4]/20 shrink-0">
                    <FileText size={32} strokeWidth={1.5} />
                </div>
                <div className="flex-1 text-center sm:text-left min-w-0">
                    <h3 className="font-black text-xl text-[#13082a] dark:text-white tracking-tight truncate leading-none mb-3 italic">
                        {summaryData.fileName}
                    </h3>
                    <div className="flex items-center justify-center sm:justify-start gap-3">
                        <span className="text-[10px] uppercase font-black text-slate-400 tracking-widest opacity-60">
                            Status: Parsed by AI
                        </span>
                        <div className="size-1 bg-slate-200 rounded-full"></div>
                        <span className="text-[10px] uppercase font-black text-[#6143f4] tracking-widest">
                            Risk Level: {summaryData.risk_level}
                        </span>
                    </div>
                </div>
                <div className="px-5 py-2.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-black rounded-xl uppercase tracking-[0.2em] border border-emerald-500/20 flex items-center gap-2 shrink-0 shadow-sm">
                    <ShieldCheck size={14} strokeWidth={3} />
                    {statusLabel}
                </div>
            </div>

            {hasContent ? (
                <>
                    <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-3">Summary</p>
                        <p className="text-[14px] text-[#13082a] dark:text-white font-medium leading-7">{safeSummary}</p>
                    </div>

                    <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-4">Risk Analysis</p>
                        <div className="space-y-3">
                            {riskItems.length ? (
                                riskItems.map((risk, index) => (
                                    <div key={`${risk}-${index}`} className="flex items-start gap-3 text-[13px] text-[#13082a] dark:text-white">
                                        <div className="mt-1.5 size-2 rounded-full bg-[#6143f4] shrink-0"></div>
                                        <p className="leading-6 whitespace-pre-wrap">{risk}</p>
                                    </div>
                                ))
                            ) : (
                                <p className="text-[13px] text-slate-500 dark:text-slate-300">No risk statements were returned for this report.</p>
                            )}
                        </div>
                    </div>

                    <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-4">Recommendations</p>
                        <div className="space-y-3">
                            {recommendationItems.length ? (
                                recommendationItems.map((recommendation, index) => (
                                    <div key={`${recommendation}-${index}`} className="flex items-start gap-3 text-[13px] text-[#13082a] dark:text-white">
                                        <div className="mt-1.5 size-2 rounded-full bg-emerald-500 shrink-0"></div>
                                        <p className="leading-6 whitespace-pre-wrap">{recommendation}</p>
                                    </div>
                                ))
                            ) : (
                                <p className="text-[13px] text-slate-500 dark:text-slate-300">No recommendations were returned for this report.</p>
                            )}
                        </div>
                    </div>

                    <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10">
                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] mb-4">Extracted Values</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {extractedItems.length ? (
                                extractedItems.map((item, index) => {
                                    const renderedValue = toDisplayText(item.value);
                                    const renderedStatus = toDisplayText(item.status);
                                    const renderedUnit = toDisplayText(item.unit);

                                    return (
                                        <div key={`${item.name}-${index}`} className="p-5 rounded-2xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10">
                                            <p className="text-[10px] text-slate-400 uppercase font-black tracking-[0.2em] mb-2">{item.name || 'Extracted Value'}</p>
                                            <p className="text-lg font-black text-[#13082a] dark:text-white">
                                                {renderedValue || 'No value'}
                                                {renderedUnit ? <span className="ml-1 text-sm text-slate-400 font-bold">{renderedUnit}</span> : null}
                                            </p>
                                            <p className="text-[10px] uppercase font-black tracking-[0.2em] mt-2 text-[#6143f4]">
                                                {renderedStatus || 'Reviewed'}
                                            </p>
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="text-[13px] text-slate-500 dark:text-slate-300">No structured values were extracted from this report.</p>
                            )}
                        </div>
                    </div>
                </>
            ) : (
                <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-[#131022]/80 border border-slate-100 dark:border-white/10 text-center">
                    <p className="text-[13px] text-slate-500 dark:text-slate-300">Summary not available for this report</p>
                </div>
            )}
        </div>
    );
};

export default ReportSummary;
