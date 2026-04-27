import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ROUTES } from '../router/routes';
import { useAuthStore } from '../store/authStore';
import {
    LogOut,
    ArrowRight,
    LayoutDashboard,
    Waves
} from 'lucide-react';

const initialsFromName = (value) =>
    String(value || 'ArogyaAI')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() || '')
        .join('') || 'AI';

const LogoutConfirmation = () => {
    const navigate = useNavigate();
    const logout = useAuthStore((state) => state.logout);
    const user = useAuthStore((state) => state.user);
    const profile = useAuthStore((state) => state.profile);
    const [isLoggingOut, setIsLoggingOut] = useState(false);

    const displayName = profile?.full_name || user?.full_name || 'Your profile';
    const avatarUrl = profile?.avatar_url || user?.avatar_url || user?.user_metadata?.avatar_url || null;
    const avatarInitials = useMemo(() => initialsFromName(displayName), [displayName]);

    const handleLogout = async () => {
        setIsLoggingOut(true);

        try {
            await logout();
            navigate(ROUTES.HOME, { replace: true });
        } catch (err) {
            console.error('Logout failed:', err);
            setIsLoggingOut(false);
        }
    };

    return (
        <div className="bg-[#13082a] min-h-screen font-display antialiased flex items-center justify-center relative overflow-hidden text-[14px]">
            {/* Background & Overlay Strategy */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#6143f4]/20 rounded-full blur-[120px] opacity-50 animate-pulse"></div>
                <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"></div>
            </div>

            <div className="w-full max-w-xl px-6 py-12 z-10 flex flex-col items-center">
                {/* Logo Section - High Fidelity Centering */}
                <div className="flex flex-col items-center mb-16 transition-transform hover:scale-105 duration-500 cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                    <div className="bg-gradient-to-br from-[#6143f4] to-[#009cde] p-[2px] rounded-2xl shadow-2xl shadow-[#6143f4]/20 group-hover:rotate-12 transition-transform duration-500">
                        <div className="bg-[#13082a] size-14 rounded-[0.9rem] flex items-center justify-center text-white">
                            <Waves size={32} strokeWidth={2.5} />
                        </div>
                    </div>
                    <div className="mt-4 text-center">
                        <h1 className="text-3xl font-black tracking-tighter uppercase leading-none text-white italic">ArogyaAI</h1>
                        <p className="text-[10px] text-[#6143f4] font-black uppercase tracking-[0.3em] mt-2 opacity-80 leading-none">Intelligence Ecosystem</p>
                    </div>
                </div>

                {/* Logout Card - Focused High Fidelity Modal */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 30 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    className="w-full bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_80px_160px_-40px_rgba(0,0,0,0.6)] border border-white/10 overflow-hidden relative group/modal"
                >
                    {/* Inner Lavender Background Section */}
                    <div className="bg-gradient-to-b from-[#f6f5f8] to-white dark:from-[#1e1a3d] dark:to-[#131022] p-12 lg:p-16 flex flex-col items-center text-center">

                        {/* Avatar & Badge Section */}
                        <div className="mb-10 relative group/avatar">
                            <div className="size-32 rounded-[2.5rem] bg-gradient-to-br from-[#6143f4]/20 to-[#009cde]/20 p-1 transition-transform duration-700 group-hover/avatar:scale-110 group-hover/avatar:rotate-3 shadow-2xl">
                                <div className="size-full rounded-[2.2rem] overflow-hidden border-4 border-white dark:border-[#131022] bg-white flex items-center justify-center">
                                    {avatarUrl ? (
                                        <img
                                            className="w-full h-full object-cover grayscale opacity-80 group-hover/avatar:grayscale-0 group-hover/avatar:opacity-100 transition-all duration-700"
                                            alt={displayName}
                                            src={avatarUrl}
                                        />
                                    ) : (
                                        <span className="text-4xl font-black text-slate-300 dark:text-slate-600 grayscale opacity-80 group-hover/avatar:grayscale-0 group-hover/avatar:opacity-100 transition-all duration-700">
                                            {avatarInitials}
                                        </span>
                                    )}
                                </div>
                            </div>
                            <motion.div
                                animate={{ y: [0, -5, 0], rotate: [0, 5, -5, 0] }}
                                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                                className="absolute -bottom-2 -right-2 size-12 bg-[#ef4444] rounded-2xl flex items-center justify-center shadow-[0_10px_30px_-5px_rgba(239,68,68,0.5)] border-4 border-white dark:border-[#131022] text-white"
                            >
                                <LogOut size={22} strokeWidth={3} />
                            </motion.div>
                        </div>

                        {/* Text Content - Italicized High Impact Header */}
                        <div className="space-y-4 mb-12">
                            <h2 className="text-4xl font-black text-[#13082a] dark:text-white leading-none uppercase tracking-tighter italic">Log Out</h2>
                            <p className="text-slate-500 dark:text-slate-400 text-[15px] font-bold leading-relaxed uppercase tracking-tight max-w-sm px-4">
                                Are you sure you want to log out of your ArogyaAI account? You will need to sign back in to access your health data.
                            </p>
                        </div>

                        {/* Action Buttons - Premium Standardized Styling */}
                        <div className="w-full flex flex-col gap-4">
                            <button
                                onClick={handleLogout}
                                disabled={isLoggingOut}
                                className="w-full py-6 bg-[#6143f4] hover:bg-[#4a34c1] text-white font-black text-xs uppercase tracking-[0.25em] rounded-[2rem] transition-all shadow-[0_25px_50px_-15px_rgba(97,67,244,0.4)] flex items-center justify-center gap-4 group/btn active:scale-95 leading-none"
                            >
                                <span>{isLoggingOut ? 'Logging Out...' : 'Log Out'}</span>
                                <ArrowRight size={18} strokeWidth={3} className="group-hover/btn:translate-x-2 transition-transform duration-300" />
                            </button>
                            <button
                                onClick={() => navigate(-1)}
                                disabled={isLoggingOut}
                                className="w-full py-6 bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 text-slate-400 dark:text-slate-500 hover:text-[#13082a] dark:hover:text-white font-black text-xs uppercase tracking-[0.25em] rounded-[2rem] transition-all active:scale-95 leading-none"
                            >
                                Discard & Stay
                            </button>
                        </div>
                    </div>
                </motion.div>

                {/* Footer Link - Standardized Iconography */}
                <div className="mt-12 text-center">
                    <button
                        onClick={() => navigate(ROUTES.DASHBOARD)}
                        className="inline-flex items-center gap-4 text-slate-400 dark:text-slate-500 hover:text-white transition-all text-[11px] font-black uppercase tracking-[0.3em] group py-2"
                    >
                        <LayoutDashboard size={18} className="group-hover:rotate-12 group-hover:scale-110 transition-all text-[#6143f4]" />
                        <span className="opacity-80 group-hover:opacity-100">Return to Dashboard</span>
                    </button>
                </div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .leading-none { line-height: 1 !important; }
                .italic { font-style: italic; }
                @keyframes float {
                    0% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
                    50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.7; }
                    100% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
                }
                .animate-pulse {
                    animation: float 8s ease-in-out infinite;
                }
            `}} />
        </div>
    );
};

export default LogoutConfirmation;
