import { motion } from 'framer-motion';
import { SkeletonBox, SkeletonText, SkeletonCard } from './index';

/**
 * InsightsSkeleton — mimics the AI Insights / Preventive Recommendations page
 * layout while data is loading.
 */
const InsightsSkeleton = () => (
    <motion.div
        key="insights-skeleton"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-background dark:bg-card text-text-primary dark:text-slate-100 min-h-screen font-display antialiased"
    >
        <div className="flex h-screen overflow-hidden">
            <main className="flex-1 flex flex-col overflow-y-auto">
                <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
                    {/* Page header */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                        <div className="space-y-3">
                            <SkeletonBox className="h-9 w-64 rounded-lg" />
                            <SkeletonBox className="h-4 w-48 rounded" />
                        </div>
                    </div>

                    {/* Risk score cards row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="bg-white dark:bg-background p-6 rounded-2xl border border-slate-100 dark:border-stroke shadow-sm">
                                <SkeletonBox className="h-3 w-24 rounded mb-4" />
                                <SkeletonBox className="h-10 w-20 rounded-lg mb-3" />
                                <SkeletonBox className="h-3 w-32 rounded" />
                            </div>
                        ))}
                    </div>

                    {/* SHAP drivers section */}
                    <div className="bg-white dark:bg-background p-8 rounded-2xl border border-slate-100 dark:border-stroke shadow-sm">
                        <SkeletonBox className="h-5 w-44 rounded mb-6" />
                        <div className="space-y-4">
                            {[1, 2, 3, 4, 5].map(i => (
                                <div key={i} className="flex items-center gap-4">
                                    <SkeletonBox className="h-4 w-32 rounded" />
                                    <SkeletonBox className="h-3 flex-1 rounded-full" />
                                    <SkeletonBox className="h-4 w-12 rounded" />
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Recommendations area */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <SkeletonCard className="rounded-2xl" />
                        <SkeletonCard className="rounded-2xl" />
                    </div>

                    {/* Bottom CTA bar */}
                    <SkeletonBox className="h-24 w-full rounded-xl" />
                </div>
            </main>
        </div>
    </motion.div>
);

export default InsightsSkeleton;

