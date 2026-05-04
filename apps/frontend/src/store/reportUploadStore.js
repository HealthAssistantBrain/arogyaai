import { create } from 'zustand';

export const useReportUploadStore = create((set) => ({
    pendingFile: null,
    pendingPreviewUrl: '',
    pendingReportId: '',
    reportResult: null,
    uploadedFileName: '',
    isProcessing: false,
    errorMessage: '',
    setPendingFile: (file, options = {}) => set({
        pendingFile: file,
        pendingPreviewUrl: options.localPreviewUrl || '',
        pendingReportId: options.reportId || '',
        reportResult: null,
        uploadedFileName: file?.name || '',
        errorMessage: '',
    }),
    setReportResult: (reportResult, uploadedFileName = '') => set({
        reportResult,
        uploadedFileName,
        errorMessage: '',
    }),
    setProcessing: (isProcessing) => set({ isProcessing }),
    setErrorMessage: (errorMessage) => set({ errorMessage }),
    clearReportFlow: () => set({
        pendingFile: null,
        pendingPreviewUrl: '',
        pendingReportId: '',
        reportResult: null,
        uploadedFileName: '',
        isProcessing: false,
        errorMessage: '',
    }),
}));
