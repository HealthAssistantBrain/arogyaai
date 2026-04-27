import React from 'react';
import { motion } from 'framer-motion';
import {
    Bell,
    AlertTriangle,
    Sparkles,
    Watch,
    FlaskConical,
    CheckCircle2,
    Clock
} from 'lucide-react';

const NotificationCardV2 = ({
    id,
    title,
    description,
    type,
    priority,
    timestamp,
    is_read,
    onMarkRead,
    onArchive,
    onView
}) => {
    // Map notification types/priorities to icons and colors
    const getStyleForType = () => {
        if (priority === 'high' || type === 'critical') {
            return {
                icon: AlertTriangle,
                accent: 'border-l-red-500',
                iconColor: 'text-red-500',
                bg: 'bg-red-500/10',
                priorityLabel: 'HIGH PRIORITY'
            };
        }

        switch (type) {
            case 'ai_insight':
                return {
                    icon: Sparkles,
                    accent: 'border-l-[#6143f4]',
                    iconColor: 'text-[#6143f4]',
                    bg: 'bg-[#6143f4]/10'
                };
            case 'lab_result':
                return {
                    icon: FlaskConical,
                    accent: 'border-l-[#009cde]',
                    iconColor: 'text-[#009cde]',
                    bg: 'bg-[#009cde]/10'
                };
            case 'system':
                return {
                    icon: Watch,
                    accent: 'border-l-slate-400',
                    iconColor: 'text-slate-500',
                    bg: 'bg-slate-100'
                };
            default:
                return {
                    icon: Bell,
                    accent: 'border-l-primary',
                    iconColor: 'text-primary',
                    bg: 'bg-primary/10'
                };
        }
    };

    const style = getStyleForType();
    const Icon = style.icon;

    const formattedTime = timestamp ? new Date(timestamp).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }) : '';

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`bg-white/80 dark:bg-white/5 backdrop-blur-xl rounded-[2rem] p-6 lg:p-8 shadow-[0_20px_40px_-10px_rgba(19,8,42,0.05)] border border-white dark:border-white/5 border-l-8 ${style.accent} relative overflow-hidden group hover:scale-[1.01] transition-all duration-300 ${!is_read ? 'ring-2 ring-[#6143f4]/20' : ''}`}
        >
            <div className="flex flex-col md:flex-row gap-6 items-start">
                <div className={`size-14 rounded-[1.25rem] ${style.bg} ${style.iconColor} flex items-center justify-center shrink-0 shadow-inner group-hover:rotate-12 group-hover:scale-110 transition-all duration-500`}>
                    <Icon size={28} strokeWidth={2.5} />
                </div>
                <div className="flex-1 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex flex-wrap items-center gap-3">
                            <h3 className={`text-lg lg:text-xl font-black ${is_read ? 'text-slate-500 dark:text-slate-400' : 'text-[#13082a] dark:text-white'} uppercase tracking-tight italic leading-none`}>
                                {title}
                            </h3>
                            {style.priorityLabel && (
                                <span className="bg-red-500 text-white text-[8px] font-black px-2 py-1 rounded-full uppercase tracking-widest shadow-lg shadow-red-500/20">
                                    {style.priorityLabel}
                                </span>
                            )}
                            {!is_read && <span className="size-2 rounded-full bg-[#6143f4] animate-pulse"></span>}
                        </div>
                        <div className="flex items-center gap-1 text-[10px] font-black uppercase tracking-widest text-slate-400 shrink-0 mt-1">
                            <Clock size={12} />
                            {formattedTime}
                        </div>
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 text-sm lg:text-base font-bold leading-relaxed uppercase tracking-tight max-w-4xl opacity-80">
                        {description}
                    </p>
                    <div className="flex flex-wrap items-center gap-3 pt-2">
                        {onView && (
                            <button
                                onClick={() => onView(id)}
                                className="px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] bg-[#6143f4] text-white hover:bg-[#4a34c1] transition-all active:scale-95 shadow-lg"
                            >
                                View
                            </button>
                        )}
                        {!is_read && onMarkRead && (
                            <button
                                onClick={() => onMarkRead(id)}
                                className="px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 text-slate-500 dark:text-slate-400 hover:text-[#6143f4] transition-all active:scale-95 flex items-center gap-2"
                            >
                                <Check size={14} strokeWidth={3} />
                                Mark Read
                            </button>
                        )}
                        {onArchive && (
                            <button
                                onClick={() => onArchive(id)}
                                className="px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 hover:text-red-500 transition-all active:scale-95"
                            >
                                Archive
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

// Check Lucide dependency
const Check = ({ size, strokeWidth }) => (
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
    >
        <polyline points="20 6 9 17 4 12" />
    </svg>
);

export default NotificationCardV2;
