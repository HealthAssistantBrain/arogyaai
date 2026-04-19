import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloudUpload, ArrowLeft, Bell, HelpCircle, Search, FileText } from 'lucide-react';

import { ROUTES } from '../router/routes';
import { useReportUploadStore } from '../store/reportUploadStore';
import { openCommandPalette } from '../components/CommandPalette';

const UploadReport = () => {
    const navigate = useNavigate();
    const [isDragging, setIsDragging] = useState(false);
    const setPendingFile = useReportUploadStore((state) => state.setPendingFile);
    const clearReportFlow = useReportUploadStore((state) => state.clearReportFlow);

    const processFile = (file) => {
        const isPdf = file && (file.type === 'application/pdf' || file.name?.toLowerCase().endsWith('.pdf'));
        if (!isPdf) {
            window.alert('Please upload a valid PDF document.');
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

    const handleFileChange = (event) => {
        processFile(event.target.files?.[0]);
    };

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    

                    <div className="p-10 space-y-12 max-w-[1100px] mx-auto w-full relative z-10 pb-20">
                        <div className="flex flex-col gap-4">
                            <h2 className="text-5xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none uppercase italic">Upload Medical Report</h2>
                            <p className="text-slate-400 font-bold uppercase tracking-widest text-[11px] opacity-80 leading-none max-w-2xl">Upload a PDF report to extract text, run AI analysis, and generate structured medical insights.</p>
                        </div>

                        <label
                            className={`relative flex flex-col items-center justify-center py-20 px-10 rounded-[4rem] border-4 border-dashed transition-all cursor-pointer overflow-hidden ${
                                isDragging
                                    ? 'border-[#6143f4] bg-[#6143f4]/10 shadow-[0_0_80px_-20px_rgba(97,67,244,0.3)]'
                                    : 'border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-white/5 hover:border-[#6143f4]/40 hover:bg-[#6143f4]/5 hover:shadow-2xl'
                            }`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="size-32 bg-white dark:bg-[#131022] rounded-[2.5rem] flex items-center justify-center text-[#6143f4] mb-10 border border-slate-100 dark:border-white/10">
                                <CloudUpload size={56} strokeWidth={1.5} />
                            </div>

                            <h3 className="text-3xl font-black text-[#13082a] dark:text-white mb-4 tracking-tighter uppercase italic">
                                {isDragging ? 'Drop Report Pipeline' : 'Drag & Drop Medical Report PDF'}
                            </h3>

                            <p className="text-slate-400 mb-12 max-w-sm text-center text-[10px] font-black uppercase tracking-[0.3em] leading-relaxed">
                                Or <span className="text-[#6143f4] border-b-2 border-[#6143f4]/20 pb-1 mx-2">click to browse</span> local files.
                            </p>

                            <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest bg-white dark:bg-white/5 px-6 py-4 rounded-[1.25rem] border border-slate-100 dark:border-white/10 shadow-sm text-slate-500 dark:text-slate-400">
                                <FileText size={16} />
                                PDF only
                            </div>

                            <input type="file" className="hidden" accept=".pdf,application/pdf" onChange={handleFileChange} />
                        </label>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default UploadReport;
