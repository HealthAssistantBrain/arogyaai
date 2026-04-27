const widths = ['w-full', 'w-5/6', 'w-4/6', 'w-3/4', 'w-2/3'];

const SkeletonText = ({ lines = 3, className = '' }) => (
    <div className={`space-y-2.5 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
            <div
                key={i}
                className={`h-3.5 animate-pulse bg-slate-200 dark:bg-slate-800 rounded ${widths[i % widths.length]}`}
            />
        ))}
    </div>
);

export default SkeletonText;
