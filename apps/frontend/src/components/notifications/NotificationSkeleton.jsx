import React from 'react';
import Skeleton from '../ui/Skeleton';

const NotificationSkeleton = () => {
    return (
        <div className="bg-white/50 dark:bg-white/5 backdrop-blur-sm rounded-[2rem] p-6 lg:p-8 border border-white dark:border-stroke/50 border-l-8 border-slate-200 animate-pulse">
            <div className="flex flex-col md:flex-row gap-6 items-start">
                <div className="size-14 rounded-[1.25rem] bg-slate-200 dark:bg-white/10 shrink-0" />
                <div className="flex-1 space-y-4">
                    <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2">
                            <Skeleton width={200} height={24} />
                            <div className="flex gap-2">
                                <Skeleton width={80} height={12} />
                            </div>
                        </div>
                        <Skeleton width={100} height={12} />
                    </div>
                    <div className="space-y-2">
                        <Skeleton width="90%" height={16} />
                        <Skeleton width="70%" height={16} />
                    </div>
                    <div className="flex gap-3 pt-2">
                        <Skeleton width={80} height={32} />
                        <Skeleton width={120} height={32} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default NotificationSkeleton;

