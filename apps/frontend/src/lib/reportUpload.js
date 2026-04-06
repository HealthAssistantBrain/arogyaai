import { apiClient } from './apiClient';

const STORAGE_KEY = 'arogyaai-report-upload';

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
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
};

export const getUploadedReportSession = () => {
  const raw = sessionStorage.getItem(STORAGE_KEY);

  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn('[reportUpload] Failed to parse session payload', error);
    return null;
  }
};

export const clearUploadedReportSession = () => {
  sessionStorage.removeItem(STORAGE_KEY);
};

const normalizeResponse = (response, file, reportType) => {
  const payload = response?.data?.data ?? response?.data ?? {};

  return {
    id: payload.id ?? null,
    fileName: file.name,
    fileSize: file.size,
    fileUrl: payload.file_url ?? null,
    reportType: payload.report_type ?? reportType,
    status: payload.status ?? 'PENDING',
    createdAt: payload.created_at ?? new Date().toISOString(),
    title: payload.title ?? file.name,
    summary: Array.isArray(payload.summary) ? payload.summary : [],
    ocrText: payload.ocr_text ?? '',
    markers: Array.isArray(payload.markers) ? payload.markers : [],
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
