import { apiClient } from './apiClient';

const STORAGE_KEY = 'arogyaai-report-upload';
const HISTORY_KEY = 'arogyaai-report-history';

const reportTypeMap = {
  pdf: 'BLOOD_TEST',
  jpg: 'XRAY',
  jpeg: 'XRAY',
  png: 'CLINICAL_NOTE',
};

export const resolveReportType = (file) => {
  const extension = file?.name?.split('.').pop()?.toLowerCase() ?? '';
  return reportTypeMap[extension] ?? 'OTHER';
};

export const saveUploadedReportSession = (payload) => {
  if (typeof window !== 'undefined') {
    // Only keep session state for immediate transition; NO long-term caching
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }
};

export const getUploadedReportSession = () => {
  if (typeof window === 'undefined') return null;
  const raw = sessionStorage.getItem(STORAGE_KEY);

  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn('[reportUpload] Failed to parse session payload', error);
    return null;
  }
};

export const getUploadedReportHistory = () => {
  // Legacy function - History is now 100% DB driven
  return [];
};

export const clearUploadedReportSession = () => {
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(STORAGE_KEY);
  }
};

const normalizeResponse = (response, file, reportType) => {
  const payload = response?.data?.data ?? response?.data ?? {};
  const fileName = payload.name ?? payload.file_name ?? file.name;
  const fileUrl = payload.file_url ?? payload.fileUrl ?? null;
  const summary = payload.summary ?? payload.patient_summary ?? [];
  const summaryView = payload.summary_view ?? payload.summaryView ?? null;

  return {
    id: payload.id ?? null,
    name: fileName,
    fileName,
    file_name: fileName,
    fileSize: file.size,
    fileUrl,
    file_url: fileUrl,
    reportType: payload.report_type ?? reportType,
    status: payload.status ?? 'PENDING',
    createdAt: payload.created_at ?? new Date().toISOString(),
    title: payload.title ?? file.name,
    summary,
    summaryView,
    ocrText: payload.ocr_text ?? '',
    parsedText: payload.parsed_text ?? payload.parsedText ?? payload.ocr_text ?? '',
    markers: Array.isArray(payload.markers) ? payload.markers : [],
    abnormalValues: Array.isArray(payload.abnormal_values) ? payload.abnormal_values : [],
    patientSummary: payload.patient_summary ?? '',
    risks: Array.isArray(payload.risks) ? payload.risks : [],
    recommendations: Array.isArray(payload.recommendations) ? payload.recommendations : [],
    summarySource: payload.summary_source ?? 'unknown',
  };
};

export const uploadMedicalReport = async (file) => {
  const reportType = resolveReportType(file);
  const formData = new FormData();

  formData.append('file', file);
  formData.append('report_type', reportType);

  try {
    const response = await apiClient.post('/reports/upload', formData, {
      timeout: 90000,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    const normalized = normalizeResponse(response, file, reportType);
    saveUploadedReportSession(normalized);
    return normalized;
  } catch (error) {
    const status = error?.response?.status;
    const message =
      error?.response?.data?.error ||
      error?.response?.data?.detail ||
      error?.message ||
      'Upload failed.';

    if (status === 404) {
      throw new Error('Upload endpoint is not available on the backend yet.');
    }

    if (status === 401) {
      throw new Error('Your session expired. Please log in again and retry the upload.');
    }

    throw new Error(message);
  }
};
