import React from 'react';
import { CloudUpload, FileText } from 'lucide-react';

const UploadReportUI = ({
    onFileSelect,
    isDragging,
    onDragOver,
    onDragLeave,
    onDrop,
    uploading
}) => {
    return (
        <label
            className={`relative flex flex-col items-center justify-center p-12 rounded-[1.5rem] transition-all cursor-pointer overflow-hidden group ${isDragging
                ? 'border-[#6143f4] border-4 border-dashed bg-[#6143f4]/10 shadow-[0_0_80px_-20px_rgba(97,67,244,0.3)]'
                : 'border-slate-200 dark:border-slate-800 border-4 border-dashed bg-white dark:bg-[#131022] hover:bg-[#6143f4]/5 hover:shadow-2xl'
                }`}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
        >
            <div className="absolute inset-0 bg-[#6143f4]/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>

            <div className="size-24 bg-[#6143f4]/10 rounded-full flex items-center justify-center text-[#6143f4] mb-6 group-hover:scale-110 transition-transform">
                <CloudUpload size={48} strokeWidth={1.5} />
            </div>

            <h3 className="text-2xl font-bold text-[#13082a] dark:text-white mb-2 tracking-tighter">
                {isDragging ? 'Drop Report Pipeline' : 'Drag and drop your medical report here'}
            </h3>

            <p className="text-gray-500 dark:text-slate-400 mb-8 max-w-md text-center text-sm font-medium">
                Or <span className="text-[#6143f4] font-bold underline">click to browse</span> your local files. Your data is encrypted and HIPAA compliant.
            </p>

            <div className="flex items-center gap-6">
                <div className="flex items-center gap-2 text-xs font-bold text-gray-400 uppercase tracking-widest bg-gray-100 dark:bg-white/5 px-4 py-2 rounded-lg">
                    <FileText size={16} />
                    PDF
                </div>
            </div>

            <input
                type="file"
                className="hidden"
                accept=".pdf,application/pdf"
                onChange={(e) => {
                    const selectedFile = e.target.files?.[0];
                    if (selectedFile) {
                        onFileSelect(selectedFile);
                    }
                }}
            />

            {uploading && <div className="mt-4 text-sm text-[#6143f4] font-bold animate-pulse">Uploading...</div>}
        </label>
    );
};

export default UploadReportUI;
