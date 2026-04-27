import SkeletonBox from './SkeletonBox';

const SkeletonTable = ({ rows = 4, cols = 4, className = '' }) => (
    <div className={`bg-white dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm overflow-hidden ${className}`}>
        {/* Header row */}
        <div className="flex gap-4 px-6 py-4 bg-slate-50 dark:bg-slate-800/30 border-b border-slate-100 dark:border-slate-800">
            {Array.from({ length: cols }).map((_, i) => (
                <SkeletonBox key={i} className="h-3 flex-1 rounded" />
            ))}
        </div>
        {/* Data rows */}
        {Array.from({ length: rows }).map((_, r) => (
            <div key={r} className="flex gap-4 px-6 py-5 border-b border-slate-50 dark:border-slate-800/50 last:border-0">
                {Array.from({ length: cols }).map((_, c) => (
                    <SkeletonBox key={c} className="h-4 flex-1 rounded" />
                ))}
            </div>
        ))}
    </div>
);

export default SkeletonTable;
