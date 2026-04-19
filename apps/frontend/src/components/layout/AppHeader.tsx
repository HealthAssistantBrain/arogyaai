import { Bell, Search, Settings, Menu } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ROUTES } from '../../router/routes';
import { openCommandPalette } from '../CommandPalette';
import UserProfile from '../common/UserProfile';
import useNotificationStore from '../../store/notificationStore';

export default function AppHeader() {
    const navigate = useNavigate();
    // @ts-ignore
    const unreadCount = useNotificationStore((state) => state.unreadCount);

    return (
        <header className="h-16 sm:h-20 bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6 sm:px-8 shrink-0 sticky top-0 z-30 backdrop-blur-md">
            <div className="flex items-center gap-4 flex-1">
                <button className="lg:hidden p-2 -ml-2 text-slate-500" onClick={openCommandPalette} title="Menu" aria-label="Menu">
                    <Menu className="w-5 h-5" />
                </button>
                <div className="hidden sm:block max-w-md w-full">
                    <div className="relative group">
                        <Search
                            onClick={openCommandPalette}
                            style={{ cursor: "pointer", pointerEvents: "auto" }}
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6043F4] transition-colors"
                            size={18}
                        />
                        <input
                            className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-none rounded-xl focus:ring-2 focus:ring-[#6043F4]/20 text-sm font-medium transition-all outline-none"
                            placeholder="Search analytics or records..."
                            type="text"
                            onClick={openCommandPalette}
                            readOnly
                        />
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-3 sm:gap-4 ml-auto">
                <button
                    className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors relative"
                    type="button"
                    onClick={() => navigate(ROUTES.NOTIFICATIONS)}
                    title="Notifications"
                    aria-label="Notifications"
                >
                    <Bell size={20} />
                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2 size-2 bg-red-500 rounded-full border-2 border-white dark:border-slate-800" />
                    )}
                </button>
                <button
                    className="hidden sm:flex size-10 rounded-xl bg-slate-100 dark:bg-slate-800 items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors"
                    type="button"
                    onClick={() => navigate(ROUTES.SETTINGS)}
                    title="Settings"
                    aria-label="Settings"
                >
                    <Settings size={20} />
                </button>
                <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-800 mx-1 sm:mx-2" />
                <UserProfile />
            </div>
        </header>
    );
}
