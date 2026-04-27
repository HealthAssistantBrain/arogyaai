import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import { hasReportSummaryContent, normalizeReportSummaryData } from '../components/reports/ReportSummary';
import { apiClient } from '../lib/apiClient';
import { useAuthStore } from './authStore';

const REPORTS_STORAGE_KEY = 'arogyaai-reports';
const STALE_THRESHOLD_MS = 60_000;

const stripQuery = (value = '') => String(value).split('?')[0].split('#')[0];

const getFileNameFromUrl = (url = '') => {
  const cleaned = stripQuery(url);
  if (!cleaned) return '';
  const parts = cleaned.split('/');
  return decodeURIComponent(parts[parts.length - 1] || '');
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

export const toText = (value) => {
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

export const hasSummaryContent = (summaryView = {}) => (
  (summaryView.patientInfo?.length ?? 0) > 0 ||
  (summaryView.keyFindings?.length ?? 0) > 0 ||
  (summaryView.biomarkers?.length ?? 0) > 0 ||
  (summaryView.abnormalValues?.length ?? 0) > 0 ||
  (summaryView.notes?.length ?? 0) > 0
);

export const normalizeReport = (report) => {
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
  const summaryView = report?.summaryView ?? report?.summary_view ?? {
    title: fileName,
    patientInfo: [],
    keyFindings: [],
    biomarkers: [],
    abnormalValues: [],
    notes: [],
    source: summarySource,
  };
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

export const normalizeReportList = (items = []) => {
  return items.filter(Boolean).map(normalizeReport).sort((left, right) => {
    return new Date(right.createdAt || 0).getTime() - new Date(left.createdAt || 0).getTime();
  });
};

export const extractReportsArray = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.data?.data)) return payload.data.data;
  if (Array.isArray(payload?.data?.reports)) return payload.data.reports;
  if (Array.isArray(payload?.reports)) return payload.reports;
  if (Array.isArray(payload?.items)) return payload.items;
  return [];
};

export const reportHasRenderableSummary = (report) => {
  const currentSummary = report?.summaryData ?? report?.summaryView ?? {};
  const source = toText(report?.summarySource ?? currentSummary.source).toLowerCase();
  const hasText = Boolean(toText(report?.parsedText ?? report?.parsed_text ?? report?.ocrText ?? report?.ocr_text));

  return hasReportSummaryContent(currentSummary) || hasSummaryContent(currentSummary) || source.includes('fallback') || hasText;
};

const getCurrentUserId = () => useAuthStore.getState()?.user?.id ?? null;

export const useReportsStore = create(
  persist(
    devtools((set, get) => ({
      reports: [],
      selectedReportId: null,
      loading: false,
      isFetching: false,
      detailFetchingId: null,
      error: null,
      lastFetchedAt: null,
      cacheOwnerId: null,
      hasHydratedCache: false,

      setHasHydratedCache: (value = true) => set({ hasHydratedCache: !!value }, false, 'reports/cacheHydrated'),
      setSelectedReportId: (selectedReportId = null) => set({ selectedReportId }, false, 'reports/select'),

      fetchReports: async ({ force = false } = {}) => {
        const state = get();
        const currentUserId = getCurrentUserId();
        const ownsCache = Boolean(currentUserId) && state.cacheOwnerId === currentUserId;

        if (!force && state.isFetching) {
          return state.reports;
        }

        if (
          !force &&
          ownsCache &&
          state.lastFetchedAt &&
          (Date.now() - state.lastFetchedAt) < STALE_THRESHOLD_MS
        ) {
          return state.reports;
        }

        set({ loading: true, isFetching: true, error: null }, false, 'reports/fetchStart');

        try {
          const response = await apiClient.get('/reports', { timeout: 12000 });
          const remoteReports = normalizeReportList(extractReportsArray(response.data));
          const selectedReportStillExists = remoteReports.some((report) => report.id === get().selectedReportId);

          set({
            reports: remoteReports,
            selectedReportId: selectedReportStillExists ? get().selectedReportId : null,
            loading: false,
            isFetching: false,
            error: null,
            lastFetchedAt: Date.now(),
            cacheOwnerId: currentUserId,
          }, false, 'reports/fetchSuccess');

          return remoteReports;
        } catch (error) {
          const status = error?.response?.status;
          const message = status === 404 || status === 405
            ? null
            : (error?.response?.data?.error || error?.message || 'Unable to load reports');

          set({
            loading: false,
            isFetching: false,
            error: message,
          }, false, 'reports/fetchError');

          return get().reports;
        }
      },

      fetchReportDetail: async (reportId, { force = false } = {}) => {
        const report = get().reports.find((item) => item.id === reportId);

        if (!reportId || (!force && report && reportHasRenderableSummary(report))) {
          return report ?? null;
        }

        set({ detailFetchingId: reportId }, false, 'reports/detailStart');

        try {
          const response = await apiClient.get(`/reports/${reportId}`, { timeout: 12000 });
          const detailedReport = normalizeReport(response.data?.data ?? response.data ?? {});
          const currentUserId = getCurrentUserId();
          const existingReports = get().reports;
          const nextReports = existingReports.some((item) => item.id === detailedReport.id)
            ? existingReports.map((item) => (item.id === detailedReport.id ? detailedReport : item))
            : [detailedReport, ...existingReports];

          set({
            reports: nextReports,
            detailFetchingId: null,
            error: null,
            lastFetchedAt: Date.now(),
            cacheOwnerId: currentUserId,
          }, false, 'reports/detailSuccess');

          return detailedReport;
        } catch (error) {
          set({
            detailFetchingId: null,
            error: error?.response?.data?.error || error?.message || 'Unable to load report details',
          }, false, 'reports/detailError');

          return report ?? null;
        }
      },
    }), { name: 'arogyaai-reports-store' }),
    {
      name: REPORTS_STORAGE_KEY,
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        reports: state.reports,
        selectedReportId: state.selectedReportId,
        lastFetchedAt: state.lastFetchedAt,
        cacheOwnerId: state.cacheOwnerId,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.warn('[reportsStore] Persist rehydration failed:', error);
        }
        state?.setHasHydratedCache?.(true);
      },
    }
  )
);

export default useReportsStore;
