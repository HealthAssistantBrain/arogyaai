import { useLocation, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/routes';
import {
    User, ShieldCheck, Smartphone, Database, HeartPulse, BellRing, Brain, Activity, LogOut, ArrowLeft, Trash2, MoonStar, SunMedium, Laptop
} from 'lucide-react';
import { useThemeStore } from '../../store/themeStore';

const SettingsSidebar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const theme = useThemeStore((state) => state.theme);
    const resolvedTheme = useThemeStore((state) => state.resolvedTheme);
    const setTheme = useThemeStore((state) => state.setTheme);

    const handleLogout = () => {
        navigate(ROUTES.LOGOUT);
    };
    const isDarkMode = resolvedTheme === 'dark';
    const isFollowingSystem = theme === 'system';

    const handleThemeToggle = () => {
        setTheme(isDarkMode ? 'light' : 'dark');
    };

    const menuItems = [
        { label: 'Profile', icon: User, path: ROUTES.SETTINGS_PROFILE, desc: 'Personal details' },
        { label: 'Security', icon: ShieldCheck, path: ROUTES.SETTINGS_SECURITY, desc: 'Passwords & Sessions' },
        { label: 'Devices', icon: Smartphone, path: ROUTES.SETTINGS_DEVICES, desc: 'Wearables sync' },
        { label: 'Data & Privacy', icon: Database, path: ROUTES.SETTINGS_DATA, desc: 'Export & delete' },
        { label: 'Integrations', icon: HeartPulse, path: ROUTES.SETTINGS_INTEGRATIONS, desc: 'Connected apps' },
        { label: 'Notifications', icon: BellRing, path: ROUTES.SETTINGS_NOTIFICATIONS, desc: 'Alerts & emails' },
        { label: 'AI Preferences', icon: Brain, path: ROUTES.SETTINGS_AI, desc: 'Model settings' },
        { label: 'System', icon: Activity, path: ROUTES.SETTINGS_SYSTEM, desc: 'Status & health' }
    ];

    return (
        <aside className="w-64 md:w-72 lg:w-80 shrink-0 border-r border-primary/10 bg-white dark:bg-background flex flex-col h-full z-20">
            <div className="p-8 border-b border-primary/5">
                <button onClick={() => navigate(ROUTES.DASHBOARD)} className="flex items-center gap-2 text-text-muted hover:text-primary transition-colors mb-6 group text-xs font-black uppercase tracking-widest">
                    <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform" />
                    Back to App
                </button>
                <h2 className="text-2xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">Settings</h2>
                <p className="text-xs text-text-muted font-bold uppercase tracking-widest mt-2 hidden md:block">System Control Panel</p>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-2">
                {menuItems.map((item) => {
                    const isActive = location.pathname.startsWith(item.path);
                    return (
                        <button
                            key={item.label}
                            onClick={() => navigate(item.path)}
                            className={`w-full flex items-center gap-4 px-4 py-3 rounded-2xl transition-all group ${isActive
                                ? 'bg-primary/10 text-primary border border-primary/20'
                                : 'text-slate-500 hover:bg-slate-50 hover:text-text-primary dark:text-text-muted dark:hover:bg-white/5 dark:hover:text-text-primary border border-transparent'
                                }`}
                        >
                            <item.icon size={18} className={isActive ? 'text-primary' : 'text-text-muted group-hover:text-primary'} />
                            <div className="text-left">
                                <p className="text-sm font-black uppercase tracking-tight leading-none">{item.label}</p>
                            </div>
                        </button>
                    )
                })}
            </div>

            <div className="p-6 border-t border-primary/5 space-y-2">
                <div className="rounded-[1.75rem] border border-primary/10 bg-primary/[0.04] dark:bg-white/[0.03] px-4 py-4 shadow-sm">
                    <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                            <p className="text-[10px] font-black uppercase tracking-[0.22em] text-text-muted">Theme</p>
                            <p className="text-sm font-black uppercase tracking-tight text-text-primary dark:text-text-primary">
                                {isDarkMode ? 'Dark Mode' : 'Light Mode'}
                            </p>
                            <p className="text-[11px] font-semibold text-slate-500 dark:text-text-muted leading-snug">
                                {isFollowingSystem
                                    ? `Following system preference: ${isDarkMode ? 'dark' : 'light'}.`
                                    : 'Applies instantly across the whole app.'}
                            </p>
                        </div>
                        <div className="mt-0.5 flex size-10 items-center justify-center rounded-2xl bg-white/90 text-primary shadow-sm dark:bg-white/5 dark:text-[#b9abff]">
                            {isFollowingSystem ? <Laptop size={18} /> : isDarkMode ? <MoonStar size={18} /> : <SunMedium size={18} />}
                        </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between gap-3">
                        <span className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-text-muted">
                            Dark Mode
                        </span>
                        <button
                            type="button"
                            onClick={handleThemeToggle}
                            aria-label="Toggle dark mode"
                            aria-pressed={isDarkMode}
                            className={`flex h-7 w-14 items-center rounded-full border p-1 transition-all ${isDarkMode
                                ? 'justify-end border-primary bg-primary shadow-lg shadow-primary/25'
                                : 'justify-start border-slate-300 bg-slate-200 dark:border-slate-600 dark:bg-slate-700'
                                }`}
                        >
                            <span className="size-5 rounded-full bg-white shadow-sm" />
                        </button>
                    </div>

                    <button
                        type="button"
                        onClick={() => setTheme('system')}
                        className={`mt-3 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] transition-all ${isFollowingSystem
                            ? 'border-primary/25 bg-primary/10 text-primary'
                            : 'border-slate-200 text-slate-500 hover:bg-white dark:border-stroke dark:text-text-secondary dark:hover:bg-white/5'
                            }`}
                    >
                        <Laptop size={12} />
                        Use System
                    </button>
                </div>

                <button
                    onClick={handleLogout}
                    className="w-full flex items-center justify-between px-4 py-3 rounded-2xl text-rose-500 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all group"
                >
                    <span className="text-xs font-black uppercase tracking-widest">Log Out</span>
                    <LogOut size={16} className="group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                    onClick={() => navigate(ROUTES.SETTINGS_DELETE_ACCOUNT)}
                    className="w-full flex items-center justify-between px-4 py-3 rounded-2xl text-red-400 hover:bg-red-500/8 border border-transparent hover:border-red-400/20 transition-all group"
                >
                    <span className="text-xs font-black uppercase tracking-widest">Delete Account</span>
                    <Trash2 size={15} className="group-hover:scale-110 transition-transform" />
                </button>
            </div>
        </aside>
    );
};

export default SettingsSidebar;

