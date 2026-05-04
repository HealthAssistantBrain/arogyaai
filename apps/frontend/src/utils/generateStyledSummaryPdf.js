import jsPDF from 'jspdf';

const DEFAULT_FILE_NAME = 'report-summary.pdf';

const PAGE = {
    width: 210,
    height: 297,
    margin: 12,
    top: 12,
    bottom: 14,
    footer: 12,
    contentWidth: 186,
};

const COLORS = {
    primary: [91, 61, 245],
    secondary: [124, 58, 237],
    bg: [248, 250, 252],
    card: [255, 255, 255],
    border: [229, 231, 235],
    text: [31, 41, 55],
    subtext: [107, 114, 128],
    neutralSoft: [243, 244, 246],
    success: [16, 185, 129],
    successSoft: [236, 253, 245],
    warning: [245, 158, 11],
    warningSoft: [255, 251, 235],
    danger: [239, 68, 68],
    dangerSoft: [254, 242, 242],
};

const sanitizeFileName = (value) => {
    const text = String(value || '')
        .replace(/[<>:"/\\|?*]+/g, '-')
        .split('')
        .filter((character) => character.charCodeAt(0) >= 32)
        .join('')
        .replace(/\s+/g, ' ')
        .trim()
        .replace(/-+/g, '-');

    return text || 'medical-report';
};

const firstText = (...values) => {
    for (const value of values) {
        const text = toDisplayText(value);
        if (text) return text;
    }

    return '';
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

        const parts = Object.entries(value)
            .map(([key, item]) => {
                const rendered = toDisplayText(item);
                return rendered ? `${toTitleCase(key)}: ${rendered}` : '';
            })
            .filter(Boolean);

        if (parts.length) {
            return parts.join(', ');
        }

        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return '';
        }
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

const formatDateValue = (value) => {
    if (!value) return 'Unknown date';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown date';

    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
};

const truncateText = (pdf, value, maxWidth) => {
    const text = toDisplayText(value);
    if (!text) return '';

    if (pdf.getTextWidth(text) <= maxWidth) {
        return text;
    }

    let output = text;
    while (output.length && pdf.getTextWidth(`${output}…`) > maxWidth) {
        output = output.slice(0, -1);
    }

    return output ? `${output}…` : '';
};

const wrapText = (pdf, value, maxWidth) => {
    const text = toDisplayText(value);
    if (!text) return [];

    return pdf
        .splitTextToSize(text, maxWidth)
        .map((line) => String(line).trim())
        .filter(Boolean);
};

const wrapBulletLines = (pdf, value, maxWidth) => {
    const text = toDisplayText(value);
    if (!text) return [];

    const bulletWidth = pdf.getTextWidth('• ');
    const wrapped = pdf
        .splitTextToSize(text, Math.max(12, maxWidth - bulletWidth))
        .map((line) => String(line).trim())
        .filter(Boolean);

    return wrapped.map((line, index) => `${index === 0 ? '• ' : '  '}${line}`);
};

const clampWrappedLines = (pdf, value, maxWidth, maxLines = 2) => {
    const lines = wrapText(pdf, value, maxWidth);
    if (lines.length <= maxLines) {
        return lines;
    }

    const clipped = lines.slice(0, maxLines);
    clipped[maxLines - 1] = truncateText(pdf, `${clipped[maxLines - 1]}…`, maxWidth);
    return clipped;
};

const getStatusTheme = (value = '') => {
    const normalized = toDisplayText(value).toLowerCase();

    if (/(critical|high|abnormal|elevated|fail|risk)/.test(normalized)) {
        return {
            fill: COLORS.dangerSoft,
            text: COLORS.danger,
            border: [252, 165, 165],
        };
    }

    if (/(warning|moderate|watch|pending|process)/.test(normalized)) {
        return {
            fill: COLORS.warningSoft,
            text: COLORS.warning,
            border: [253, 230, 138],
        };
    }

    if (/(normal|stable|success|complete|clear|ok|good|low)/.test(normalized)) {
        return {
            fill: COLORS.successSoft,
            text: COLORS.success,
            border: [167, 243, 208],
        };
    }

    return {
        fill: COLORS.neutralSoft,
        text: COLORS.primary,
        border: COLORS.border,
    };
};

const normalizeExtractedValue = (item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
        return {
            name: 'Extracted Value',
            value: item,
            unit: '',
            status: '',
        };
    }

    return {
        name: toTitleCase(item.name ?? item.label ?? item.test ?? item.title ?? item.metric ?? item.key ?? 'Extracted Value'),
        value: item.value ?? item.result ?? item.reading ?? item.measurement ?? item.amount ?? item.score ?? item.text ?? item.summary ?? item.description ?? item.raw ?? item,
        unit: toDisplayText(item.unit),
        status: toTitleCase(item.status ?? item.flag ?? item.trend ?? item.state),
    };
};

const normalizeExtractedValues = (value) => {
    if (Array.isArray(value)) {
        return value.map(normalizeExtractedValue).filter(Boolean);
    }

    if (value && typeof value === 'object') {
        if (Array.isArray(value.items)) {
            return value.items.map(normalizeExtractedValue).filter(Boolean);
        }

        if (Array.isArray(value.data)) {
            return value.data.map(normalizeExtractedValue).filter(Boolean);
        }

        return Object.entries(value)
            .map(([key, item]) => ({
                name: toTitleCase(key),
                value: item,
                unit: '',
                status: '',
            }))
            .filter((item) => item.name || item.value);
    }

    if (value === null || value === undefined || value === '') {
        return [];
    }

    return [normalizeExtractedValue(value)];
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

const normalizeReportSummaryData = (data = {}) => {
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

const buildPdfReportData = (report = {}) => {
    const summaryCandidate = report.summaryData ?? report.summary_data ?? report.summaryView ?? report.summary_view;
    const summaryData = summaryCandidate && typeof summaryCandidate === 'object'
        ? summaryCandidate
        : normalizeReportSummaryData(report);

    const summary = firstText(
        summaryData.summary,
        summaryData.summaryText,
        summaryData.summary_text,
        report.summary,
        report.summaryText,
        report.summary_text,
        report.patientSummary,
        report.patient_summary
    ) || 'Summary not available for this report';

    const riskAnalysis = toList(
        summaryData.risk_analysis ??
        summaryData.riskAnalysis ??
        report.risk_analysis ??
        report.riskAnalysis ??
        report.risks ??
        report.risk
    ).map(toDisplayText).filter(Boolean);

    const recommendations = toList(summaryData.recommendations ?? report.recommendations)
        .map(toDisplayText)
        .filter(Boolean);

    const extractedValues = normalizeExtractedValues(
        summaryData.extracted_values ??
        summaryData.extractedValues ??
        report.extracted_values ??
        report.extractedValues ??
        report.abnormal_values ??
        report.abnormalValues ??
        report.markers
    );

    const originalFileName = firstText(
        report.originalFilename,
        report.original_filename,
        summaryData.originalFilename,
        summaryData.original_filename
    );
    const fileName = originalFileName || stripUuidPrefix(firstText(
        summaryData.fileName,
        report.fileName,
        report.file_name,
        report.title,
        report.name,
        report.summaryTitle,
        report.summary_view?.title,
        report.summaryView?.title
    )) || 'Medical report';

    const status = firstText(
        summaryData.status,
        report.status,
        report.summaryStatus,
        report.summary_status
    ) || (report.success ? 'Success' : 'Ready');

    const riskLevel = firstText(
        summaryData.risk_level,
        summaryData.riskLevel,
        report.risk_level,
        report.riskLevel,
        report.severity
    ) || 'Unknown';

    const reportDate = formatDateValue(
        report.created_at ??
        report.createdAt ??
        report.report_date ??
        report.reportDate ??
        report.date ??
        report.uploadedAt ??
        report.updatedAt
    );

    const reportType = firstText(report.reportType, report.type, report.documentType) || 'Medical report';
    const patientName = firstText(report.patientName, report.patient_name, report.patientInfo?.name, report.patientInfo?.patient_name);

    return {
        summaryData,
        summary,
        riskAnalysis,
        recommendations,
        extractedValues,
        fileName,
        status,
        riskLevel,
        reportDate,
        reportType,
        patientName,
    };
};

const drawPageBackground = (pdf) => {
    pdf.setFillColor(...COLORS.bg);
    pdf.rect(0, 0, PAGE.width, PAGE.height, 'F');
};

const drawCardShell = (pdf, x, y, w, h, accent = COLORS.primary) => {
    pdf.setFillColor(...COLORS.card);
    pdf.setDrawColor(...COLORS.border);
    pdf.setLineWidth(0.35);
    pdf.roundedRect(x, y, w, h, 4, 4, 'FD');

    pdf.setFillColor(...accent);
    pdf.roundedRect(x, y, Math.min(24, w), 4, 4, 4, 'F');
};

const drawPill = (pdf, x, y, label, theme = getStatusTheme(label), maxWidth = 38) => {
    const text = truncateText(pdf, label, maxWidth);
    if (!text) return 0;

    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(7);

    const width = Math.max(16, pdf.getTextWidth(text) + 6);
    pdf.setFillColor(...theme.fill);
    pdf.setDrawColor(...theme.border);
    pdf.roundedRect(x, y, width, 7, 3, 3, 'FD');
    pdf.setTextColor(...theme.text);
    pdf.text(text.toUpperCase(), x + width / 2, y + 4.7, { align: 'center' });

    return width;
};

const drawFirstPageHeader = (pdf, state, report) => {
    drawPageBackground(pdf);

    const x = PAGE.margin;
    const y = PAGE.top;
    const w = PAGE.contentWidth;
    const h = 36;

    pdf.setFillColor(...COLORS.primary);
    pdf.roundedRect(x, y, w, h, 7, 7, 'F');

    pdf.setDrawColor(255, 255, 255);
    pdf.setLineWidth(0.45);
    pdf.roundedRect(x + 6, y + 7, 58, 13, 4, 4, 'S');

    pdf.setTextColor(255, 255, 255);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(8);
    pdf.text('ArogyaAI', x + 10, y + 14);

    pdf.setFontSize(16);
    pdf.text('Medical Report', x + 10, y + 22);

    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(8.5);
    pdf.text('AI-powered clinical summary and insights', x + 10, y + 28);

    pdf.setFillColor(255, 255, 255);
    pdf.roundedRect(x + w - 48, y + 7, 38, 10, 4, 4, 'F');
    pdf.setTextColor(...COLORS.primary);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(7.5);
    pdf.text('CONFIDENTIAL', x + w - 29, y + 13, { align: 'center' });

    pdf.setTextColor(255, 255, 255);
    pdf.setFontSize(8.5);
    pdf.text(truncateText(pdf, report.fileName, 84), x + 10, y + 34);

    state.y = y + h + 8;
};

const drawContinuationHeader = (pdf, state, report) => {
    drawPageBackground(pdf);

    pdf.setDrawColor(...COLORS.border);
    pdf.setLineWidth(0.35);
    pdf.line(PAGE.margin, PAGE.top + 12, PAGE.width - PAGE.margin, PAGE.top + 12);

    pdf.setTextColor(...COLORS.primary);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(10);
    pdf.text('ArogyaAI Medical Report', PAGE.margin, PAGE.top + 5);

    pdf.setTextColor(...COLORS.subtext);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(7.5);
    pdf.text(truncateText(pdf, report.fileName, 90), PAGE.margin, PAGE.top + 9);
    pdf.text(`Page ${state.pageNumber}`, PAGE.width - PAGE.margin, PAGE.top + 5, { align: 'right' });

    state.y = PAGE.top + 18;
};

const addNewPage = (pdf, state, report) => {
    pdf.addPage();
    state.pageNumber += 1;
    state.y = PAGE.top;
    drawContinuationHeader(pdf, state, report);
};

const ensureSpace = (pdf, state, report, requiredHeight) => {
    const availableHeight = PAGE.height - PAGE.bottom - state.y;
    if (availableHeight < requiredHeight) {
        addNewPage(pdf, state, report);
    }
};

const renderInfoCard = (pdf, state, report) => {
    const x = PAGE.margin;
    const w = PAGE.contentWidth;
    const h = 34;

    ensureSpace(pdf, state, report, h + 2);

    drawCardShell(pdf, x, state.y, w, h, COLORS.secondary);

    pdf.setTextColor(...COLORS.primary);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(8.5);
    pdf.text('REPORT SNAPSHOT', x + 6, state.y + 8);

    pdf.setTextColor(...COLORS.subtext);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(7.2);
    pdf.text(`Generated for ${truncateText(pdf, report.reportType, 48)}`, x + w - 6, state.y + 8, { align: 'right' });

    const items = [
        { label: 'Report', value: report.fileName, tone: getStatusTheme(report.reportType) },
        { label: 'Date', value: report.reportDate, tone: getStatusTheme('pending') },
        { label: 'Status', value: report.status, tone: getStatusTheme(report.status) },
        { label: 'Risk', value: report.riskLevel, tone: getStatusTheme(report.riskLevel) },
    ];

    const colWidth = (w - 14) / 2;
    const startY = state.y + 15;

    items.forEach((item, index) => {
        const col = index % 2;
        const row = Math.floor(index / 2);
        const fieldX = x + 6 + col * (colWidth + 2);
        const fieldY = startY + row * 9.2;

        pdf.setTextColor(...COLORS.subtext);
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(6.8);
        pdf.text(item.label.toUpperCase(), fieldX, fieldY);

        pdf.setTextColor(...COLORS.text);
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(8.6);
        pdf.text(truncateText(pdf, item.value, colWidth - 6), fieldX, fieldY + 4.9);
    });

    const riskPill = drawPill(pdf, x + w - 48, state.y + 18, report.riskLevel, getStatusTheme(report.riskLevel), 38);
    if (riskPill) {
        pdf.setTextColor(...COLORS.subtext);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(7);
        pdf.text(truncateText(pdf, report.patientName || '', 46), x + w - 6, state.y + 30, { align: 'right' });
    }

    state.y += h + 8;
};

const renderChunkedTextCard = (pdf, state, report, options) => {
    const {
        title,
        lines,
        accent = COLORS.primary,
        emptyText = 'No data available',
        label = '',
    } = options;

    const x = PAGE.margin;
    const w = PAGE.contentWidth;
    const padX = 6;
    const padY = 6;
    const titleHeight = 9;
    const lineHeight = 4.5;
    const contentLines = lines.length ? lines : [emptyText];
    let remaining = contentLines.slice();
    let chunkIndex = 0;

    while (remaining.length) {
        const availableHeight = PAGE.height - PAGE.bottom - state.y;
        if (availableHeight < 24) {
            addNewPage(pdf, state, report);
            continue;
        }

        let take = Math.floor((availableHeight - padY * 2 - titleHeight) / lineHeight);
        if (take < 3) {
            addNewPage(pdf, state, report);
            continue;
        }

        take = Math.min(take, remaining.length);
        let chunk = remaining.slice(0, take);
        let cardHeight = padY * 2 + titleHeight + chunk.length * lineHeight;

        while (cardHeight > availableHeight && chunk.length > 3) {
            chunk = remaining.slice(0, chunk.length - 1);
            cardHeight = padY * 2 + titleHeight + chunk.length * lineHeight;
        }

        if (cardHeight > availableHeight) {
            addNewPage(pdf, state, report);
            continue;
        }

        drawCardShell(pdf, x, state.y, w, cardHeight, accent);

        pdf.setTextColor(...COLORS.primary);
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(10.5);
        pdf.text(title.toUpperCase(), x + padX, state.y + 11);

        if (chunkIndex > 0) {
            drawPill(pdf, x + w - 36, state.y + 6, 'CONTINUED', getStatusTheme('pending'), 30);
        } else if (label) {
            pdf.setTextColor(...COLORS.subtext);
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(7.2);
            pdf.text(label, x + w - 6, state.y + 10, { align: 'right' });
        }

        pdf.setTextColor(...COLORS.text);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(9.2);

        let textY = state.y + 18;
        chunk.forEach((line) => {
            pdf.text(line, x + padX, textY);
            textY += lineHeight;
        });

        state.y += cardHeight + 6;
        remaining = remaining.slice(chunk.length);
        chunkIndex += 1;

        if (remaining.length) {
            addNewPage(pdf, state, report);
        }
    }
};

const computeValueCardHeight = (pdf, item, width) => {
    const valueLines = clampWrappedLines(pdf, item.value, width - 10, 2);
    const lineHeight = 4.4;
    const valueHeight = Math.max(4.4, valueLines.length * lineHeight);
    const unitHeight = item.unit ? 3.4 : 0;
    const statusHeight = item.status ? 7.4 : 0;

    return 16 + valueHeight + unitHeight + statusHeight;
};

const renderValueCard = (pdf, item, x, y, width, height) => {
    const tone = getStatusTheme(item.status || item.value);
    drawCardShell(pdf, x, y, width, height, tone.fill);

    pdf.setTextColor(...COLORS.subtext);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(7.2);
    pdf.text(truncateText(pdf, item.name.toUpperCase(), width - 34), x + 5, y + 6);

    if (item.status) {
        drawPill(pdf, x + width - 28, y + 3.2, item.status, tone, 24);
    }

    const valueLines = clampWrappedLines(pdf, item.value, width - 10, 2);
    pdf.setTextColor(...COLORS.text);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(10.5);

    let valueY = y + 13.2;
    valueLines.forEach((line) => {
        pdf.text(line, x + 5, valueY);
        valueY += 4.4;
    });

    if (item.unit) {
        pdf.setTextColor(...COLORS.subtext);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(8);
        pdf.text(item.unit, x + 5, valueY + 0.4);
    }
};

const renderExtractedValuesSection = (pdf, state, report) => {
    const hasValues = report.extractedValues.length > 0;

    ensureSpace(pdf, state, report, 20);

    const drawHeading = () => {
        pdf.setTextColor(...COLORS.primary);
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(12);
        pdf.text('EXTRACTED VALUES', PAGE.margin, state.y);

        pdf.setTextColor(...COLORS.subtext);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(8);
        pdf.text('Grid of parsed biomarkers and report fields', PAGE.margin, state.y + 5);

        state.y += 10;
    };

    drawHeading();

    if (!hasValues) {
        const emptyHeight = 24;
        ensureSpace(pdf, state, report, emptyHeight);
        drawCardShell(pdf, PAGE.margin, state.y, PAGE.contentWidth, emptyHeight, COLORS.neutralSoft);
        pdf.setTextColor(...COLORS.subtext);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(9);
        pdf.text('No structured values were extracted from this report.', PAGE.margin + 6, state.y + 14);
        state.y += emptyHeight + 6;
        return;
    }

    const gap = 6;
    const halfWidth = (PAGE.contentWidth - gap) / 2;

    for (let index = 0; index < report.extractedValues.length; index += 2) {
        const left = report.extractedValues[index];
        const right = report.extractedValues[index + 1];
        const leftWidth = right ? halfWidth : PAGE.contentWidth;
        const leftHeight = computeValueCardHeight(pdf, left, leftWidth);
        const rightHeight = right ? computeValueCardHeight(pdf, right, halfWidth) : 0;
        const rowHeight = Math.max(leftHeight, rightHeight);

        if (state.y + rowHeight > PAGE.height - PAGE.bottom) {
            addNewPage(pdf, state, report);
            drawHeading();
        }

        if (right) {
            renderValueCard(pdf, left, PAGE.margin, state.y, halfWidth, rowHeight);
            renderValueCard(pdf, right, PAGE.margin + halfWidth + gap, state.y, halfWidth, rowHeight);
        } else {
            renderValueCard(pdf, left, PAGE.margin, state.y, PAGE.contentWidth, rowHeight);
        }

        state.y += rowHeight + 6;
    }
};

const drawFooters = (pdf, report) => {
    const totalPages = pdf.getNumberOfPages();

    for (let page = 1; page <= totalPages; page += 1) {
        pdf.setPage(page);
        pdf.setDrawColor(...COLORS.border);
        pdf.setLineWidth(0.35);
        pdf.line(PAGE.margin, PAGE.height - PAGE.footer, PAGE.width - PAGE.margin, PAGE.height - PAGE.footer);

        pdf.setTextColor(...COLORS.subtext);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(7.2);
        pdf.text('ArogyaAI confidential medical report', PAGE.margin, PAGE.height - 6);
        pdf.text(truncateText(pdf, report.fileName, 90), PAGE.margin + 62, PAGE.height - 6);
        pdf.text(`Page ${page} of ${totalPages}`, PAGE.width - PAGE.margin, PAGE.height - 6, { align: 'right' });
    }
};

export const buildSummaryPdfFileName = (report = {}) => {
    const baseName = report?.originalFilename || report?.original_filename || stripUuidPrefix(report?.fileName || report?.title || report?.name || 'medical-report');
    return `${sanitizeFileName(baseName)}-summary.pdf`;
};

export const generateStyledSummaryPdf = async (reportInput = {}, fileName = DEFAULT_FILE_NAME) => {
    const report = buildPdfReportData(reportInput);
    const pdf = new jsPDF('p', 'mm', 'a4');
    const state = {
        y: PAGE.top,
        pageNumber: 1,
    };

    pdf.setProperties({
        title: report.fileName,
        subject: 'ArogyaAI Medical Report',
        author: 'ArogyaAI',
        creator: 'ArogyaAI',
    });

    pdf.setLineHeightFactor(1.12);

    drawFirstPageHeader(pdf, state, report);
    renderInfoCard(pdf, state, report);

    renderChunkedTextCard(pdf, state, report, {
        title: 'Summary',
        lines: wrapText(pdf, report.summary, PAGE.contentWidth - 12),
        accent: COLORS.primary,
        emptyText: 'Summary not available for this report.',
    });

    renderChunkedTextCard(pdf, state, report, {
        title: 'Risk Analysis',
        lines: report.riskAnalysis.length
            ? report.riskAnalysis.flatMap((line) => wrapBulletLines(pdf, line, PAGE.contentWidth - 12))
            : ['No risk statements were returned for this report.'],
        accent: COLORS.warning,
        emptyText: 'No risk statements were returned for this report.',
    });

    renderChunkedTextCard(pdf, state, report, {
        title: 'Recommendations',
        lines: report.recommendations.length
            ? report.recommendations.flatMap((line) => wrapBulletLines(pdf, line, PAGE.contentWidth - 12))
            : ['No recommendations were returned for this report.'],
        accent: COLORS.success,
        emptyText: 'No recommendations were returned for this report.',
    });

    renderExtractedValuesSection(pdf, state, report);
    drawFooters(pdf, report);

    pdf.save(fileName);
    return pdf;
};

export const captureElementToPdf = generateStyledSummaryPdf;
