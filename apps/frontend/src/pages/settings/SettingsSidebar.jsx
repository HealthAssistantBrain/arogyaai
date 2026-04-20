import { useLocation, useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/routes';
import { useAuthStore } from '../../store/authStore';
import {
    User, ShieldCheck, Smartphone, Database, HeartPulse, BellRing, Brain, Activity, LogOut, ArrowLeft, Trash2
} from 'lucide-react';

const SettingsSidebar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const logout = useAuthStore((s) => s.logout);

    const handleLogout = () => {
        logout();
        navigate(ROUTES.HOME, { replace: true });
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
        <aside className="w-64 md:w-72 lg:w-80 shrink-0 border-r border-[#6143f4]/10 bg-white dark:bg-[#0B0819] flex flex-col h-full z-20">
            <div className="p-8 border-b border-[#6143f4]/5">
                <button onClick={() => navigate(ROUTES.DASHBOARD)} className="flex items-center gap-2 text-slate-400 hover:text-[#6143f4] transition-colors mb-6 group text-xs font-black uppercase tracking-widest">
                    <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform" />
                    Back to App
                </button>
                <h2 className="text-2xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Settings</h2>
                <p className="text-xs text-slate-400 font-bold uppercase tracking-widest mt-2 hidden md:block">System Control Panel</p>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-2">
                {menuItems.map((item) => {
                    const isActive = location.pathname.startsWith(item.path);
                    return (
                        <button
                            key={item.label}
                            onClick={() => navigate(item.path)}
                            className={`w-full flex items-center gap-4 px-4 py-3 rounded-2xl transition-all group ${isActive
                                ? 'bg-[#6143f4]/10 text-[#6143f4] border border-[#6143f4]/20'
                                : 'text-slate-500 hover:bg-slate-50 hover:text-[#13082a] dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-white border border-transparent'
                                }`}
                        >
                            <item.icon size={18} className={isActive ? 'text-[#6143f4]' : 'text-slate-400 group-hover:text-[#6143f4]'} />
                            <div className="text-left">
                                <p className="text-sm font-black uppercase tracking-tight leading-none">{item.label}</p>
                            </div>
                        </button>
                    )
                })}
            </div>

            <div className="p-6 border-t border-[#6143f4]/5 space-y-2">
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
