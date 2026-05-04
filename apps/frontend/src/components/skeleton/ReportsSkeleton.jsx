import { motion } from 'framer-motion';
import { SkeletonBox, SkeletonText } from './index';

/**
 * ReportsSkeleton — mimics the Medical Reports Hub page layout while
 * the report list is loading.
 */
const ReportsSkeleton = () => (
    <motion.div
        key="reports-skeleton"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-background dark:bg-card text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased"
    >
        <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between px-10 py-10 shrink-0 gap-6">
                    <div className="space-y-4">
                        <SkeletonBox className="h-10 w-72 rounded-lg" />
                        <SkeletonBox className="h-3 w-96 rounded" />
                    </div>
                    <SkeletonBox className="h-14 w-52 rounded-[1.5rem]" />
                </div>

                {/* Content split */}
                <div className="flex flex-1 gap-10 px-10 pb-10 overflow-hidden">
                    {/* Sidebar list */}
                    <div className="w-full md:w-[35%] flex flex-col gap-4">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="p-6 rounded-[2.25rem] bg-white/60 dark:bg-white/5 border border-transparent flex items-center gap-5 animate-pulse">
                                <div className="size-14 rounded-[1.25rem] bg-slate-200 dark:bg-card shrink-0" />
                                <div className="flex-1 space-y-2">
                                    <SkeletonBox className="h-4 w-40 rounded" />
                                    <SkeletonBox className="h-3 w-28 rounded" />
                                </div>
                                <SkeletonBox className="h-6 w-20 rounded-full" />
                            </div>
                        ))}
                    </div>

                    {/* Preview panel */}
                    <div className="flex-1 flex min-w-0">
                        <div className="flex-1 bg-white/40 dark:bg-white/5 backdrop-blur-2xl rounded-[3rem] overflow-hidden flex flex-col border border-white/40 dark:border-stroke">
                            <div className="p-7 border-b border-stroke dark:border-stroke flex items-center gap-4">
                                <SkeletonBox className="size-8 rounded-lg" />
                                <SkeletonBox className="h-3 w-48 rounded" />
                            </div>
                            <div className="flex-1 flex items-center justify-center p-10">
                                <div className="text-center space-y-4">
                                    <SkeletonBox className="size-16 mx-auto rounded-[1.75rem]" />
                                    <SkeletonBox className="h-3 w-44 mx-auto rounded" />
                                    <SkeletonBox className="h-3 w-64 mx-auto rounded" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </motion.div>
);

export default ReportsSkeleton;

