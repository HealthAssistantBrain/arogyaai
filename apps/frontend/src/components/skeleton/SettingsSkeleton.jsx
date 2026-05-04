import { SkeletonBox } from './index';

/**
 * SettingsSkeleton — mimics the Settings page layout (sidebar nav + content)
 * while any user/profile data is loading.
 */
const SettingsSkeleton = () => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-pulse">
        {/* Sidebar nav */}
        <div className="lg:col-span-1 bg-white dark:bg-background rounded-xl border border-slate-100 dark:border-stroke p-6 space-y-3">
            {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl">
                    <SkeletonBox className="size-4 rounded" />
                    <SkeletonBox className="h-4 w-24 rounded" />
                </div>
            ))}
        </div>

        {/* Content */}
        <div className="lg:col-span-2 bg-white dark:bg-background rounded-xl border border-slate-100 dark:border-stroke p-8 space-y-8">
            <SkeletonBox className="h-4 w-28 rounded" />
            <div className="space-y-4">
                {[1, 2, 3].map(i => (
                    <div key={i} className="flex items-center justify-between p-3 rounded-xl">
                        <SkeletonBox className="h-4 w-36 rounded" />
                        <SkeletonBox className="h-6 w-12 rounded-full" />
                    </div>
                ))}
            </div>
            <div className="pt-6 border-t border-slate-100 dark:border-stroke space-y-4">
                <SkeletonBox className="h-4 w-20 rounded" />
                <div className="flex items-center justify-between p-3 rounded-xl">
                    <SkeletonBox className="h-4 w-24 rounded" />
                    <SkeletonBox className="h-3 w-40 rounded" />
                </div>
            </div>
        </div>
    </div>
);

export default SettingsSkeleton;

