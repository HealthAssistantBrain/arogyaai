const SkeletonBox = ({ className = '', style }) => (
    <div
        className={`animate-pulse bg-slate-200 dark:bg-slate-800 rounded-xl ${className}`}
        style={style}
    />
);

export default SkeletonBox;
