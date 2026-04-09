import { create } from 'zustand';

export const useReportUploadStore = create((set) => ({
    pendingFile: null,
    reportResult: null,
    uploadedFileName: '',
    isProcessing: false,
    errorMessage: '',
    setPendingFile: (file) => set({
        pendingFile: file,
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
        reportResult: null,
        uploadedFileName: '',
        isProcessing: false,
        errorMessage: '',
    }),
}));
