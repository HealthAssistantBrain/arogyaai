import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

import { ROUTES } from '../router/routes';
import { useReportUploadStore } from '../store/reportUploadStore';
import useReportsStore from '../store/reportsStore';
import UploadReportUI from '../components/upload/UploadReportUI';
import { resolveReportType } from '../lib/reportUpload';

const UploadReport = () => {
    const navigate = useNavigate();
    const [isDragging, setIsDragging] = useState(false);
    const setPendingFile = useReportUploadStore((state) => state.setPendingFile);
    const clearReportFlow = useReportUploadStore((state) => state.clearReportFlow);
    const setProcessing = useReportUploadStore((state) => state.setProcessing);
    const isProcessing = useReportUploadStore((state) => state.isProcessing);
    const addOptimisticReport = useReportsStore((state) => state.addOptimisticReport);

    const processFile = (file) => {
        if (isProcessing) {
            return;
        }

        const supportedTypes = new Set(['application/pdf', 'image/jpeg', 'image/png']);
        const supportedExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
        const fileName = file?.name?.toLowerCase() || '';
        const isSupported = file && (supportedTypes.has(file.type) || supportedExtensions.some((extension) => fileName.endsWith(extension)));
        if (!isSupported) {
            window.alert('Please upload a valid PDF, JPG, or PNG medical report.');
            return;
        }

        clearReportFlow();
        const reportId = `local-${globalThis.crypto?.randomUUID?.() || Date.now()}`;
        const localPreviewUrl = URL.createObjectURL(file);
        setPendingFile(file, { localPreviewUrl, reportId });
        setProcessing(true);
        addOptimisticReport({
            id: reportId,
            fileName: file.name,
            file_name: file.name,
            originalFilename: file.name,
            original_filename: file.name,
            fileSize: file.size,
            file_size: file.size,
            reportType: resolveReportType(file),
            report_type: resolveReportType(file),
            status: 'PROCESSING',
            localPreviewUrl,
            summarySource: 'local-preview',
            summary_source: 'local-preview',
            summaryView: {
                title: file.name,
                patientInfo: [],
                keyFindings: [],
                biomarkers: [],
                abnormalValues: [],
                notes: [],
                source: 'local-preview',
            },
            statusMessage: 'Analyzing report...',
        });
        navigate(ROUTES.MEDICAL_REPORTS, { state: { startUpload: true, reportId } });
    };

    const handleDragOver = (event) => {
        event.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (event) => {
        event.preventDefault();
        setIsDragging(false);
        processFile(event.dataTransfer?.files?.[0]);
    };

    return (
        <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-background dark:bg-background">


                    <div className="p-10 space-y-12 max-w-[1100px] mx-auto w-full relative z-10 pb-20">
                        <div className="flex flex-col gap-4">
                            <h2 className="text-5xl font-black tracking-tighter text-text-primary dark:text-text-primary leading-none uppercase italic">Upload Medical Report</h2>
                            <p className="text-text-muted font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none max-w-2xl">Upload a PDF or image report to extract OCR text, run AI analysis, and generate structured medical insights.</p>
                        </div>

                        <UploadReportUI
                            onFileSelect={processFile}
                            isDragging={isDragging}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            uploading={isProcessing}
                            disabled={isProcessing}
                        />

                        {isProcessing ? (
                            <div className="flex items-center justify-center gap-3 text-primary text-[11px] font-black uppercase tracking-[0.25em]">
                                <Loader2 size={16} className="animate-spin" />
                                Analyzing report...
                            </div>
                        ) : null}
                    </div>
                </main>
            </div>
        </div>
    );
};

export default UploadReport;

