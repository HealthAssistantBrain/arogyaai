import { create } from 'zustand';
import { createJSONStorage, devtools, persist } from 'zustand/middleware';
import { hasReportSummaryContent, normalizeReportSummaryData } from '../components/reports/ReportSummary';
import { apiClient } from '../lib/apiClient';
import { useAuthStore } from './authStore';

const REPORTS_STORAGE_KEY = 'arogyaai-reports';
const STALE_THRESHOLD_MS = 60_000;
const PROCESSING_STATUSES = new Set(['PENDING', 'PROCESSING', 'UPLOADING']);

export const isReportProcessingStatus = (status = '') => PROCESSING_STATUSES.has(String(status || '').toUpperCase());

const stripQuery = (value = '') => String(value).split('?')[0].split('#')[0];

const getFileNameFromUrl = (url = '') => {
  const cleaned = stripQuery(url);
  if (!cleaned) return '';
  const parts = cleaned.split('/');
  return stripUuidPrefix(decodeURIComponent(parts[parts.length - 1] || ''));
};

const stripUuidPrefix = (value = '') => String(value).replace(
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/i,
  ''
);

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
  const fileAccessRequired = Boolean(report?.fileAccessRequired ?? report?.file_access_required ?? !fileUrl);
  const fileName =
    toText(report?.originalFilename ?? report?.original_filename) ||
    stripUuidPrefix(toText(report?.fileName ?? report?.file_name)) ||
    stripUuidPrefix(toText(report?.name)) ||
    toText(report?.title) ||
    getFileNameFromUrl(fileUrl) ||
    'Medical Report';
  const storedFilename = report?.storedFilename ?? report?.stored_filename ?? '';
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
    originalFilename: fileName,
    storedFilename,
    title: report?.title ?? fileName,
    fileUrl,
    fileAccessRequired,
    reportType,
    reportKind: inferReportType(fileName, fileUrl, reportType),
    status: String(report?.status ?? 'COMPLETED').toUpperCase(),
    createdAt,
    updatedAt,
    fileSize: Number.isFinite(sizeValue) ? sizeValue : null,
    localPreviewUrl: report?.localPreviewUrl ?? report?.local_preview_url ?? '',
    isOptimistic: Boolean(report?.isOptimistic ?? report?.is_optimistic),
    uploadProgress: Number.isFinite(Number(report?.uploadProgress ?? report?.upload_progress))
      ? Number(report?.uploadProgress ?? report?.upload_progress)
      : null,
    statusMessage: toText(report?.statusMessage ?? report?.status_message),
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

const mergeReportPreservingLocalPreview = (remoteReport, existingReport) => {
  if (!existingReport) return remoteReport;

  return {
    ...remoteReport,
    localPreviewUrl: existingReport.localPreviewUrl || remoteReport.localPreviewUrl,
    uploadProgress: remoteReport.uploadProgress ?? existingReport.uploadProgress,
    statusMessage: remoteReport.statusMessage || existingReport.statusMessage,
  };
};

export const normalizeReportList = (items = []) => {
  const uniqueReports = new Map();

  items.filter(Boolean).map(normalizeReport).forEach((report) => {
    const existing = uniqueReports.get(report.id);
    if (!existing) {
      uniqueReports.set(report.id, report);
      return;
    }

    const existingTimestamp = new Date(existing.updatedAt || existing.createdAt || 0).getTime();
    const nextTimestamp = new Date(report.updatedAt || report.createdAt || 0).getTime();
    const preferred = nextTimestamp >= existingTimestamp ? report : existing;
    const fallback = preferred === report ? existing : report;

    uniqueReports.set(report.id, {
      ...preferred,
      localPreviewUrl: preferred.localPreviewUrl || fallback.localPreviewUrl,
      uploadProgress: preferred.uploadProgress ?? fallback.uploadProgress,
      statusMessage: preferred.statusMessage || fallback.statusMessage,
    });
  });

  return Array.from(uniqueReports.values()).sort((left, right) => {
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
      addOptimisticReport: (report) => {
        const optimisticReport = normalizeReport({
          ...report,
          isOptimistic: true,
          status: report?.status ?? 'PROCESSING',
          createdAt: report?.createdAt ?? new Date().toISOString(),
        });

        set((state) => ({
          reports: [
            optimisticReport,
            ...state.reports.filter((item) => item.id !== optimisticReport.id),
          ],
          selectedReportId: optimisticReport.id,
        }), false, 'reports/addOptimistic');

        return optimisticReport;
      },
      upsertReport: (report) => {
        const normalized = normalizeReport(report);
        const existing = get().reports.find((item) => item.id === normalized.id);
        const merged = mergeReportPreservingLocalPreview(normalized, existing);
        const nextReports = get().reports.some((item) => item.id === merged.id)
          ? get().reports.map((item) => (item.id === merged.id ? merged : item))
          : [merged, ...get().reports];

        set({ reports: normalizeReportList(nextReports) }, false, 'reports/upsert');
        return merged;
      },
      replaceOptimisticReport: (temporaryId, report) => {
        const normalized = normalizeReport(report);
        const temporaryReport = get().reports.find((item) => item.id === temporaryId);
        const merged = mergeReportPreservingLocalPreview(
          { ...normalized, isOptimistic: false },
          temporaryReport,
        );
        const nextReports = get().reports
          .filter((item) => item.id !== temporaryId && item.id !== merged.id)
          .concat(merged);

        set({
          reports: normalizeReportList(nextReports),
          selectedReportId: merged.id,
        }, false, 'reports/replaceOptimistic');

        return merged;
      },
      markReportFailed: (reportId, message = 'Upload failed') => {
        set((state) => ({
          reports: state.reports.map((report) => (
            report.id === reportId
              ? { ...report, status: 'FAILED', statusMessage: message, isOptimistic: false }
              : report
          )),
        }), false, 'reports/markFailed');
      },
      deleteReport: async (reportId) => {
        const targetId = String(reportId || '');
        if (!targetId) {
          return null;
        }

        const previousReports = get().reports;
        const previousSelectedReportId = get().selectedReportId;
        const deletedReport = previousReports.find((report) => report.id === targetId) ?? null;
        const nextReports = previousReports.filter((report) => report.id !== targetId);

        set({
          reports: nextReports,
          selectedReportId: previousSelectedReportId === targetId ? (nextReports[0]?.id ?? null) : previousSelectedReportId,
        }, false, 'reports/deleteOptimistic');

        if (targetId.startsWith('local-') || deletedReport?.isOptimistic) {
          return deletedReport;
        }

        try {
          await apiClient.delete(`/reports/${targetId}`, { timeout: 12000 });
          set({
            error: null,
            lastFetchedAt: Date.now(),
            cacheOwnerId: getCurrentUserId(),
          }, false, 'reports/deleteSuccess');
          return deletedReport;
        } catch (error) {
          set({
            reports: previousReports,
            selectedReportId: previousSelectedReportId,
            error: error?.response?.data?.error || error?.response?.data?.detail || error?.message || 'Unable to delete report',
          }, false, 'reports/deleteRollback');
          throw error;
        }
      },

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
          const currentReports = get().reports;
          const optimisticReports = currentReports.filter((report) => report.isOptimistic || String(report.id).startsWith('local-'));
          const mergedRemoteReports = remoteReports.map((report) => (
            mergeReportPreservingLocalPreview(report, currentReports.find((item) => item.id === report.id))
          ));
          const allReports = normalizeReportList([
            ...optimisticReports.filter((optimistic) => !mergedRemoteReports.some((report) => report.id === optimistic.id)),
            ...mergedRemoteReports,
          ]);
          const selectedReportStillExists = allReports.some((report) => report.id === get().selectedReportId);

          set({
            reports: allReports,
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
          const existingReport = existingReports.find((item) => item.id === detailedReport.id);
          const mergedReport = mergeReportPreservingLocalPreview(detailedReport, existingReport);
          const nextReports = existingReports.some((item) => item.id === detailedReport.id)
            ? existingReports.map((item) => (item.id === detailedReport.id ? mergedReport : item))
            : [mergedReport, ...existingReports];

          set({
            reports: normalizeReportList(nextReports),
            detailFetchingId: null,
            error: null,
            lastFetchedAt: Date.now(),
            cacheOwnerId: currentUserId,
          }, false, 'reports/detailSuccess');

          return mergedReport;
        } catch (error) {
          set({
            detailFetchingId: null,
            error: error?.response?.data?.error || error?.message || 'Unable to load report details',
          }, false, 'reports/detailError');

          return report ?? null;
        }
      },
      fetchReportStatus: async (reportId) => {
        if (!reportId || String(reportId).startsWith('local-')) {
          return null;
        }

        const existingReport = get().reports.find((item) => item.id === reportId);

        try {
          const response = await apiClient.get(`/reports/${reportId}/status`, { timeout: 12000 });
          const payload = response.data?.data?.report ?? response.data?.report ?? response.data?.data ?? response.data ?? {};
          const normalized = normalizeReport(payload);
          const merged = mergeReportPreservingLocalPreview(normalized, existingReport);
          const nextReports = get().reports.some((item) => item.id === merged.id)
            ? get().reports.map((item) => (item.id === merged.id ? merged : item))
            : [merged, ...get().reports];

          set({
            reports: normalizeReportList(nextReports),
            selectedReportId: get().selectedReportId === reportId ? merged.id : get().selectedReportId,
            error: null,
            lastFetchedAt: Date.now(),
            cacheOwnerId: getCurrentUserId(),
          }, false, 'reports/statusSuccess');

          return merged;
        } catch (error) {
          set({
            error: error?.response?.data?.error || error?.message || 'Unable to refresh report status',
          }, false, 'reports/statusError');

          return existingReport ?? null;
        }
      },
    }), { name: 'arogyaai-reports-store' }),
    {
      name: REPORTS_STORAGE_KEY,
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        reports: state.reports
          .filter((report) => !report.isOptimistic && !String(report.id).startsWith('local-'))
          .map(({ localPreviewUrl, uploadProgress, isOptimistic, statusMessage, ...report }) => report),
        selectedReportId: state.selectedReportId && !String(state.selectedReportId).startsWith('local-')
          ? state.selectedReportId
          : null,
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
