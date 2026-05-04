import SkeletonBox from './SkeletonBox';

const BAR_HEIGHTS = [65, 40, 80, 55, 90, 35, 70];

const SkeletonChart = ({ className = '', bars = 7 }) => (
    <div className={`bg-white dark:bg-background p-6 rounded-xl border border-slate-100 dark:border-stroke shadow-sm ${className}`}>
        <SkeletonBox className="h-4 w-28 rounded mb-6" />
        <div className="flex items-end gap-2 h-32">
            {Array.from({ length: bars }).map((_, i) => (
                <div
                    key={i}
                    className="flex-1 animate-pulse bg-slate-200 dark:bg-card rounded-t"
                    style={{ height: `${BAR_HEIGHTS[i % BAR_HEIGHTS.length]}%` }}
                />
            ))}
        </div>
    </div>
);

export default SkeletonChart;

