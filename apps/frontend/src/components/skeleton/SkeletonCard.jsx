import SkeletonBox from './SkeletonBox';
import SkeletonText from './SkeletonText';

const SkeletonCard = ({ className = '', headerHeight = 'h-5' }) => (
    <div className={`bg-white dark:bg-background p-6 rounded-xl border border-slate-100 dark:border-stroke shadow-sm ${className}`}>
        <SkeletonBox className={`${headerHeight} w-32 mb-5 rounded`} />
        <SkeletonText lines={3} />
    </div>
);

export default SkeletonCard;

