import { motion } from 'framer-motion';
import { SkeletonBox, SkeletonText } from './index';

/**
 * AQISkeleton — mimics the Air Quality Risk Monitor page layout
 * while environmental data is loading.
 */
const AQISkeleton = () => (
    <motion.div
        key="aqi-skeleton"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display antialiased"
    >
        <div className="flex h-screen overflow-hidden">
            <main className="flex-1 overflow-y-auto p-8">
                <div className="max-w-7xl mx-auto space-y-8">
                    {/* Header */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div className="space-y-3">
                            <SkeletonBox className="h-9 w-72 rounded-lg" />
                            <SkeletonBox className="h-4 w-48 rounded" />
                        </div>
                        <div className="flex gap-3">
                            <SkeletonBox className="h-10 w-10 rounded-xl" />
                            <SkeletonBox className="h-10 w-36 rounded-xl" />
                        </div>
                    </div>

                    {/* AQI Hero Gauge */}
                    <div className="bg-white dark:bg-slate-900 p-10 rounded-[2rem] border border-slate-100 dark:border-slate-800 shadow-sm flex flex-col items-center">
                        <SkeletonBox className="size-40 rounded-full mb-6" />
                        <SkeletonBox className="h-5 w-32 rounded mb-3" />
                        <SkeletonBox className="h-3 w-48 rounded" />
                    </div>

                    {/* Pollutant grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                        {[1, 2, 3, 4, 5, 6].map(i => (
                            <div key={i} className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm">
                                <SkeletonBox className="h-3 w-12 rounded mb-3" />
                                <SkeletonBox className="h-7 w-16 rounded mb-2" />
                                <SkeletonBox className="h-2.5 w-20 rounded" />
                            </div>
                        ))}
                    </div>

                    {/* Trend chart + Alerts */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm">
                            <SkeletonBox className="h-4 w-32 rounded mb-6" />
                            <div className="flex items-end gap-3 h-36">
                                {[1, 2, 3, 4, 5, 6, 7].map(i => (
                                    <div key={i} className="flex-1 animate-pulse bg-slate-200 dark:bg-slate-800 rounded-t" style={{ height: `${[65, 40, 80, 55, 90, 35, 70][i % 7]}%` }} />
                                ))}
                            </div>
                        </div>
                        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm">
                            <SkeletonBox className="h-4 w-36 rounded mb-6" />
                            <div className="space-y-4">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="flex items-start gap-3">
                                        <SkeletonBox className="size-8 rounded-lg shrink-0" />
                                        <div className="flex-1 space-y-2">
                                            <SkeletonBox className="h-4 w-40 rounded" />
                                            <SkeletonBox className="h-3 w-full rounded" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </motion.div>
);

export default AQISkeleton;
