import { CloudUpload, FileText, Loader2 } from 'lucide-react';

const UploadReportUI = ({
    onFileSelect,
    isDragging,
    onDragOver,
    onDragLeave,
    onDrop,
    uploading,
    disabled = false,
}) => {
    return (
        <label
            className={`relative flex flex-col items-center justify-center p-12 rounded-[1.5rem] transition-all overflow-hidden group ${disabled ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'} ${isDragging && !disabled
                ? 'border-primary border-4 border-dashed bg-primary/10 shadow-[0_0_80px_-20px_rgba(97,67,244,0.3)]'
                : 'border-slate-200 dark:border-stroke border-4 border-dashed bg-surface hover:bg-primary/5 hover:shadow-2xl'
                }`}
            onDragOver={disabled ? undefined : onDragOver}
            onDragLeave={disabled ? undefined : onDragLeave}
            onDrop={disabled ? undefined : onDrop}
        >
            <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>

            <div className="size-24 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-6 group-hover:scale-110 transition-transform">
                {uploading ? <Loader2 size={48} strokeWidth={1.5} className="animate-spin" /> : <CloudUpload size={48} strokeWidth={1.5} />}
            </div>

            <h3 className="text-2xl font-bold text-text-primary dark:text-text-primary mb-2 tracking-tighter">
                {uploading ? 'Analyzing report...' : isDragging ? 'Drop Report Pipeline' : 'Drag and drop your medical report here'}
            </h3>

            <p className="text-gray-500 dark:text-text-muted mb-8 max-w-md text-center text-sm font-medium">
                {uploading ? 'Your current upload is being processed. You can preview it in Reports.' : (
                    <>Or <span className="text-primary font-bold underline">click to browse</span> your local files. Your data is encrypted and HIPAA compliant.</>
                )}
            </p>

            <div className="flex items-center gap-6">
                <div className="flex items-center gap-2 text-xs font-bold text-text-muted uppercase tracking-widest bg-gray-100 dark:bg-white/5 px-4 py-2 rounded-lg">
                    <FileText size={16} />
                    PDF / JPG / PNG
                </div>
            </div>

            <input
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                disabled={disabled}
                onChange={(e) => {
                    const selectedFile = e.target.files?.[0];
                    if (selectedFile) {
                        onFileSelect(selectedFile);
                    }
                }}
            />

            {uploading && <div className="mt-4 text-sm text-primary font-bold animate-pulse">Uploading...</div>}
        </label>
    );
};

export default UploadReportUI;

