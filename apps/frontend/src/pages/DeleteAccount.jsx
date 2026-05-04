import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { useAuthStore } from '../store/authStore';
import api from '../lib/axios';
import toast from 'react-hot-toast';
import React from 'react';
import {
    LayoutDashboard,
    Brain,
    FlaskConical,
    History,
    Activity,
    FileText,
    Settings,
    ShieldCheck,
    Bell,
    Search,
    MoreVertical,
    Waves,
    Shield,
    CheckCircle2,
    HelpCircle,
    AlertTriangle,
    Trash2,
    Database,
    Smartphone,
    Watch,
    WifiOff,
    ChevronRight,
    Info,
    Check,
    ShieldAlert
} from 'lucide-react';

const DeleteAccount = () => {
    const navigate = useNavigate();
    const { reset } = useAuthStore();
    const [isConfirmed, setIsConfirmed] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    // Call real DELETE /users/me, then hard-reset everything
    const handleDelete = async () => {
        if (!isConfirmed || isDeleting) return;
        setIsDeleting(true);
        try {
            await api.delete('/users/me');
        } catch (err) {
            // Backend was not reached — abort and inform the user.
            // Do NOT clear state here: that would mislead the user into thinking
            // the account was deleted when it was not.
            console.error('[DeleteAccount] API error:', err);
            toast.error('Could not reach the server. Please try again.');
            setIsDeleting(false);
            return;
        }
        // API call succeeded — now wipe local state and redirect.
        reset();
        navigate('/', { replace: true });
    };

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management', active: true },
        { icon: ShieldCheck, label: 'Security Audit', path: ROUTES.SECURITY_AUDIT, group: 'Management' },
        { icon: Bell, label: 'Notifications', path: ROUTES.SETTINGS_NOTIFICATIONS, group: 'Management' },
    ];

    const consequences = [
        {
            icon: Database,
            title: 'Data Loss',
            desc: 'All biometric logs and medical records wiped from secure servers.',
            color: 'text-amber-500',
            bg: 'bg-amber-500/10'
        },
        {
            icon: Brain,
            title: 'AI Models',
            desc: 'Personalized models and predictive insights permanently erased.',
            color: 'text-primary',
            bg: 'bg-primary/10'
        },
        {
            icon: WifiOff,
            title: 'Device Link',
            desc: 'Connections to wearables and smart sensors will be severed.',
            color: 'text-secondary',
            bg: 'bg-secondary/10'
        }
    ];

    return (
        <div className="bg-background dark:bg-background text-text-primary dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-background dark:bg-background">
                    {/* Top Navigation Bar */}


                    {/* Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-5xl mx-auto space-y-12 pb-16">

                            {/* Breadcrumbs */}
                            <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-text-muted">
                                <button onClick={() => navigate(ROUTES.SETTINGS)} className="hover:text-primary transition-colors">Settings</button>
                                <ChevronRight size={12} strokeWidth={3} />
                                <span className="text-text-primary dark:text-text-primary italic">Delete Account</span>
                            </div>

                            {/* Header */}
                            <div className="space-y-4">
                                <h1 className="text-5xl lg:text-6xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">Delete Your Account</h1>
                                <p className="text-lg text-slate-500 dark:text-text-muted font-bold uppercase tracking-tight opacity-80 leading-snug max-w-2xl">
                                    We're sorry to see you go. This process handles the permanent removal of your ArogyaAI profile, health insights, and personal history.
                                </p>
                            </div>

                            {/* IRREVERSIBLE WARNING CARD */}
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="bg-[#fff1f2] dark:bg-red-500/5 border-2 border-red-200 dark:border-red-500/20 rounded-[3rem] p-10 flex flex-col md:flex-row gap-8 items-start relative overflow-hidden group shadow-[0_20px_50px_-10px_rgba(239,68,68,0.1)]"
                            >
                                <div className="absolute top-0 right-0 size-48 bg-red-500/5 rounded-full blur-[80px] -mr-16 -mt-16 group-hover:scale-110 transition-transform duration-1000"></div>
                                <div className="bg-[#ef4444] text-text-primary rounded-2xl p-5 shrink-0 shadow-2xl shadow-red-500/30 group-hover:rotate-12 transition-transform">
                                    <AlertTriangle size={36} strokeWidth={2.5} />
                                </div>
                                <div className="space-y-4">
                                    <h3 className="text-[#ef4444] text-2xl font-black uppercase tracking-tight italic leading-none">Warning: Irreversible Action</h3>
                                    <p className="text-[#ef4444]/80 dark:text-red-400/80 font-bold leading-relaxed text-[15px] uppercase tracking-tight">
                                        Deleting your account will permanently remove all your health data from our secure servers. This action is final. Once confirmed, you will lose access to all your insights and history immediately.
                                    </p>
                                </div>
                            </motion.div>

                            {/* CONSEQUENCES GRID */}
                            <div className="bg-surface rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-slate-100 dark:border-stroke/50 overflow-hidden group/consequences">
                                <div className="px-12 py-8 border-b border-slate-50 dark:border-stroke/50 bg-slate-50/30 dark:bg-transparent">
                                    <h3 className="text-[11px] font-black text-text-muted uppercase tracking-[0.3em] leading-none">Forensic Impact Analysis</h3>
                                </div>
                                <div className="p-10 lg:p-14 grid grid-cols-1 md:grid-cols-3 gap-12 lg:gap-16">
                                    {consequences.map((item, idx) => (
                                        <div key={idx} className="space-y-6 group/item">
                                            <div className={`${item.bg} ${item.color} size-16 rounded-[1.5rem] flex items-center justify-center shadow-inner group-hover/item:scale-110 group-hover/item:rotate-6 transition-all duration-500`}>
                                                <item.icon size={32} strokeWidth={2.5} />
                                            </div>
                                            <div className="space-y-3">
                                                <h4 className="font-black text-lg uppercase tracking-tight text-text-primary dark:text-text-primary italic leading-none">{item.title}</h4>
                                                <p className="text-slate-500 dark:text-text-muted text-xs font-bold leading-relaxed uppercase tracking-tight opacity-70">{item.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* CONFIRMATION CARD */}
                            <div className="bg-surface rounded-[3.5rem] border border-slate-100 dark:border-stroke/50 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] p-10 lg:p-14 space-y-12 relative group/confirm">
                                <div className="flex items-start gap-8 group/toggle cursor-pointer select-none" onClick={() => setIsConfirmed(!isConfirmed)}>
                                    <div className="pt-1.5 shrink-0">
                                        <div className={`size-8 rounded-xl border-2 transition-all duration-500 flex items-center justify-center ${isConfirmed ? 'bg-[#ef4444] border-[#ef4444] shadow-2xl shadow-red-500/40 rotate-0' : 'border-slate-200 dark:border-stroke rotate-45 group-hover/toggle:border-red-500 group-hover/toggle:rotate-0'}`}>
                                            <Check size={20} strokeWidth={4} className={`text-text-primary transition-opacity ${isConfirmed ? 'opacity-100' : 'opacity-0'}`} />
                                        </div>
                                    </div>
                                    <p className="text-slate-600 dark:text-text-muted text-[15px] font-bold leading-relaxed uppercase tracking-tight group-hover/confirm:text-text-primary dark:group-hover/confirm:text-text-primary transition-colors">
                                        I understand that this action is permanent and my data cannot be recovered. I agree to the permanent deletion of my ArogyaAI account and all associated personal information from the health ecosystem.
                                    </p>
                                </div>

                                <div className="flex flex-col md:flex-row gap-6">
                                    <button
                                        disabled={!isConfirmed}
                                        onClick={handleDelete}
                                        className={`flex-1 group/btn flex items-center justify-center gap-4 py-6 px-10 rounded-[2rem] font-black text-xs uppercase tracking-[0.25em] transition-all duration-500 relative overflow-hidden ${isConfirmed
                                            ? 'bg-[#ef4444] text-text-primary shadow-[0_25px_50px_-12px_rgba(239,68,68,0.5)] hover:scale-[1.02] active:scale-95'
                                            : 'bg-slate-100 dark:bg-white/5 text-text-muted cursor-not-allowed opacity-50 grayscale'
                                            }`}
                                    >
                                        <Trash2 size={20} className="group-hover/btn:animate-bounce" />
                                        <span>Permanently Delete Account</span>
                                    </button>
                                    <button
                                        onClick={() => navigate(ROUTES.SETTINGS)}
                                        className="flex-1 py-6 px-10 rounded-[2rem] bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-stroke text-slate-500 dark:text-text-secondary font-black text-xs uppercase tracking-[0.25em] hover:bg-slate-200 dark:hover:bg-white/10 hover:text-text-primary dark:hover:text-text-primary transition-all active:scale-95"
                                    >
                                        Cancel and Keep Account
                                    </button>
                                </div>
                            </div>

                            {/* SUPPORT BLOCK */}
                            <div className="pt-8 text-center space-y-6">
                                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-text-muted leading-none">
                                    Need help before you go?
                                    <button onClick={() => navigate(ROUTES.HELP)} className="text-secondary hover:underline ml-2 transition-all">
                                        Contact our support intelligence
                                    </button>
                                </p>
                            </div>

                        </div>
                    </div>
                </main>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .leading-snug { line-height: 1.3 !important; }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default DeleteAccount;


