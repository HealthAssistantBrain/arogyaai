import { motion } from 'framer-motion';
import { SkeletonBox, SkeletonText } from './index';

/**
 * RiskReportSkeleton — mimics the AI Risk Prediction / Report page
 * layout while data is loading.
 */
const RiskReportSkeleton = () => (
    <motion.div
        key="risk-skeleton"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display antialiased"
    >
        <div className="flex flex-1 overflow-hidden">
            <main className="flex-1 overflow-y-auto p-6 lg:p-10">
                <div className="max-w-7xl mx-auto space-y-12 pb-20">
                    {/* Profile header */}
                    <div className="flex items-center gap-8">
                        <SkeletonBox className="size-28 lg:size-32 rounded-3xl" />
                        <div className="space-y-4 flex-1">
                            <SkeletonBox className="h-10 w-64 rounded-lg" />
                            <div className="flex gap-6">
                                <SkeletonBox className="h-3 w-28 rounded" />
                                <SkeletonBox className="h-3 w-32 rounded" />
                                <SkeletonBox className="h-3 w-36 rounded" />
                            </div>
                        </div>
                        <div className="flex gap-4">
                            <SkeletonBox className="h-12 w-36 rounded-2xl" />
                            <SkeletonBox className="h-12 w-36 rounded-2xl" />
                        </div>
                    </div>

                    {/* 3-card stat row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="p-8 rounded-[2.5rem] bg-white dark:bg-[#1a1433] border border-slate-100 dark:border-white/5 shadow-sm">
                                <SkeletonBox className="h-3 w-28 rounded mb-4" />
                                <SkeletonBox className="h-14 w-24 rounded-lg mb-6" />
                                <SkeletonBox className="h-6 w-36 rounded-xl" />
                            </div>
                        ))}
                    </div>

                    {/* Table + sidebar */}
                    <div className="grid grid-cols-12 gap-10">
                        <div className="col-span-12 lg:col-span-8">
                            {/* Disease table */}
                            <div className="bg-white dark:bg-[#1a1433] rounded-[2.5rem] border border-slate-100 dark:border-white/5 shadow-sm overflow-hidden">
                                <div className="px-10 py-8 border-b border-slate-50 dark:border-white/5">
                                    <SkeletonBox className="h-6 w-72 rounded" />
                                </div>
                                <div className="px-10 py-4">
                                    {[1, 2, 3, 4].map(i => (
                                        <div key={i} className="flex gap-8 py-6 border-b border-slate-50 dark:border-white/5 last:border-0">
                                            <div className="flex-1 space-y-2">
                                                <SkeletonBox className="h-5 w-40 rounded" />
                                                <SkeletonBox className="h-3 w-52 rounded" />
                                            </div>
                                            <SkeletonBox className="h-6 w-24 rounded-full" />
                                            <SkeletonBox className="h-4 w-20 rounded" />
                                            <SkeletonBox className="h-6 w-16 rounded" />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Side panel */}
                        <div className="col-span-12 lg:col-span-4">
                            <div className="bg-white dark:bg-[#1a1433] rounded-[2.5rem] border border-slate-100 dark:border-white/5 shadow-sm p-10">
                                <SkeletonBox className="h-4 w-44 rounded mb-10" />
                                <div className="space-y-10">
                                    {[1, 2, 3].map(i => (
                                        <div key={i} className="space-y-3">
                                            <div className="flex justify-between">
                                                <SkeletonBox className="h-3 w-28 rounded" />
                                                <SkeletonBox className="h-4 w-16 rounded-full" />
                                            </div>
                                            <SkeletonBox className="h-3 w-full rounded-full" />
                                            <SkeletonBox className="h-3 w-4/5 rounded" />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </motion.div>
);

export default RiskReportSkeleton;
