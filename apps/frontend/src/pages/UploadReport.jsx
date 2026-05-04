import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloudUpload, ArrowLeft, Bell, HelpCircle, Search, FileText } from 'lucide-react';

import { ROUTES } from '../router/routes';
import { useReportUploadStore } from '../store/reportUploadStore';
import UploadReportUI from '../components/upload/UploadReportUI';

const UploadReport = () => {
    const navigate = useNavigate();
    const [isDragging, setIsDragging] = useState(false);
    const setPendingFile = useReportUploadStore((state) => state.setPendingFile);
    const clearReportFlow = useReportUploadStore((state) => state.clearReportFlow);

    const processFile = (file) => {
        const supportedTypes = new Set(['application/pdf', 'image/jpeg', 'image/png']);
        const supportedExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
        const fileName = file?.name?.toLowerCase() || '';
        const isSupported = file && (supportedTypes.has(file.type) || supportedExtensions.some((extension) => fileName.endsWith(extension)));
        if (!isSupported) {
            window.alert('Please upload a valid PDF, JPG, or PNG medical report.');
            return;
        }

        clearReportFlow();
        setPendingFile(file);
        navigate(ROUTES.REPORT_PROCESSING);
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
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">


                    <div className="p-10 space-y-12 max-w-[1100px] mx-auto w-full relative z-10 pb-20">
                        <div className="flex flex-col gap-4">
                            <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none uppercase italic">Upload Medical Report</h2>
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none max-w-2xl">Upload a PDF or image report to extract OCR text, run AI analysis, and generate structured medical insights.</p>
                        </div>

                        <UploadReportUI
                            onFileSelect={processFile}
                            isDragging={isDragging}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        />
                    </div>
                </main>
            </div>
        </div>
    );
};

export default UploadReport;
