import { NavLink, useNavigate } from 'react-router-dom';
import { Waves } from 'lucide-react';
import { navConfig } from '../../config/navConfig';
import { ROUTES } from '../../router/routes';
import useNotificationStore from '../../store/notificationStore';

export default function Sidebar() {
    const navigate = useNavigate();
    const unreadCount = useNotificationStore((state) => state.unreadCount);

    return (
        <aside className="w-[260px] bg-white dark:bg-[#131022] border-r border-slate-100 dark:border-white/5 flex flex-col h-screen sticky top-0 z-30 shrink-0 hidden lg:flex">
            {/* Logo / Brand */}
            <div
                className="px-6 py-6 flex items-center gap-3 cursor-pointer group"
                onClick={() => navigate(ROUTES.DASHBOARD)}
            >
                <div className="w-10 h-10 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-md shadow-[#6143f4]/20 group-hover:scale-105 transition-transform">
                    <Waves size={22} strokeWidth={2.5} />
                </div>
                <div>
                    <h1 className="text-lg font-black tracking-tight leading-none">ArogyaAI</h1>
                    <p className="text-[9px] text-slate-400 font-bold uppercase tracking-[0.2em] mt-1 leading-none">
                        Healthcare AI
                    </p>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 overflow-y-auto custom-scrollbar">
                {navConfig.map((group, gIdx) => (
                    <div key={gIdx} className={gIdx > 0 ? 'mt-6 pt-6 border-t border-slate-100 dark:border-white/5' : ''}>
                        {group.section && (
                            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.25em] px-3 mb-3 leading-none">
                                {group.section}
                            </div>
                        )}
                        <div className="space-y-1">
                            {group.items.map((link) => {
                                const Icon = link.icon;
                                return (
                                    <NavLink
                                        key={link.label}
                                        to={link.path}
                                        className={({ isActive }) => `w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left ${
                                            isActive
                                                ? 'bg-[#6143f4] text-white font-bold shadow-md shadow-[#6143f4]/20'
                                                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 hover:text-[#6143f4] font-medium'
                                        }`}
                                    >
                                        {({ isActive }) => (
                                            <>
                                                {Icon && (
                                                    <span className="relative inline-flex">
                                                        <Icon
                                                            size={18}
                                                            className={isActive ? 'text-white' : 'text-slate-400 group-hover:text-[#6143f4]'}
                                                        />
                                                        {link.path === ROUTES.NOTIFICATIONS && unreadCount > 0 && (
                                                            <span className="absolute -top-1 -right-1 size-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-[#131022]" />
                                                        )}
                                                    </span>
                                                )}
                                                <span className="text-[13px] tracking-tight leading-none">
                                                    {link.label}
                                                </span>
                                            </>
                                        )}
                                    </NavLink>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </nav>
        </aside>
    );
}
