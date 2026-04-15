import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import React from 'react';
import { openCommandPalette } from '../components/CommandPalette';
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
  CloudDownload,
  PlusCircle,
  HelpCircle,
  RefreshCw,
  Lock,
  Smartphone,
  Hospital,
  Activity as VitalIcon,
  Gavel,
  ShieldAlert,
  Archive,
  ArrowRight,
  Info,
  Check,
  Key,
  Eye,
  EyeOff,
  Circle,
  ChevronRight,
  Verified
} from 'lucide-react';

const changePasswordSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'One uppercase letter required')
    .regex(/\d/, 'One number required')
    .regex(/[!@#$%^*]/, 'One special char (!@#$%) required'),
  confirmPassword: z.string()
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

const ChangePassword = () => {
    const navigate = useNavigate();
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
        watch
    } = useForm({
        resolver: zodResolver(changePasswordSchema),
        defaultValues: { currentPassword: '', newPassword: '', confirmPassword: '' },
    });

    const newPass = watch("newPassword", "");

    const onSubmit = (data) => {
        console.log("Password updated successfully", data);
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

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto no-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search security settings..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 group shadow-sm">
                                <HelpCircle size={20} />
                            </button>
                            
                        </div>
                    </header>

                    {/* Scrollable Content Area */}
                    <div className="flex-1 p-10 lg:p-12 custom-scrollbar overflow-y-auto">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">
                            
                            {/* Breadcrumbs */}
                            <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                                <button onClick={() => navigate(ROUTES.SETTINGS)} className="hover:text-[#6143f4] transition-colors">Settings</button>
                                <ChevronRight size={12} strokeWidth={3} />
                                <span className="text-slate-500">Security</span>
                                <ChevronRight size={12} strokeWidth={3} />
                                <span className="text-[#6143f4] italic">Change Password</span>
                            </div>

                            {/* Page Header */}
                            <div className="space-y-4 pb-4">
                                <h1 className="text-5xl lg:text-6xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Account Security</h1>
                                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug max-w-2xl">Update your login credentials and secure your health data with a strong, rotated password policy.</p>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 items-start">
                                {/* Left/Main Column: Form */}
                                <div className="lg:col-span-2">
                                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 overflow-hidden transition-all duration-500 hover:border-[#6143f4]/20 group/card">
                                        <div className="px-10 py-10 border-b border-slate-100 dark:border-white/5 flex justify-between items-center bg-slate-50/30 dark:bg-transparent">
                                            <div className="flex items-center gap-5">
                                                <div className="size-14 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] group-hover/card:scale-110 transition-transform shadow-inner">
                                                    <Key size={28} />
                                                </div>
                                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">Rotation & Update</h3>
                                            </div>
                                            <div className="flex items-center gap-3 px-6 py-2 bg-emerald-500/10 text-emerald-600 rounded-full font-black text-[10px] uppercase tracking-widest animate-pulse border border-emerald-500/20 shadow-sm leading-none">
                                                <div className="size-1.5 bg-emerald-500 rounded-full"></div>
                                                <span>Level: High Security</span>
                                            </div>
                                        </div>
                                        <div className="p-10 lg:p-14">
                                            <form className="space-y-10" onSubmit={handleSubmit(onSubmit)}>
                                                <div className="space-y-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1 leading-none block">Validation: Current Matrix</label>
                                                    <div className="relative group/input">
                                                        <Lock className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/input:text-[#6143f4] transition-colors" size={20} />
                                                        <input 
                                                            className={`w-full bg-slate-50 dark:bg-[#0B0819] border-2 rounded-[1.5rem] py-5 pl-16 pr-16 text-lg font-black uppercase tracking-widest focus:ring-8 focus:ring-[#6143f4]/5 outline-none transition-all dark:text-white placeholder:text-slate-300 ${errors.currentPassword ? 'border-red-500/50' : 'border-slate-100 dark:border-white/5 focus:border-[#6143f4]'}`}
                                                            placeholder="••••••••" 
                                                            type={showCurrent ? 'text' : 'password'} 
                                                            {...register('currentPassword')}
                                                        />
                                                        <button 
                                                            className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#6143f4] transition-colors" 
                                                            type="button"
                                                            onClick={() => setShowCurrent(!showCurrent)}
                                                        >
                                                            {showCurrent ? <EyeOff size={22} /> : <Eye size={22} />}
                                                        </button>
                                                    </div>
                                                    {errors.currentPassword && <p className="text-red-500 text-[10px] font-black uppercase tracking-widest mt-2 ml-4 animate-bounce">{errors.currentPassword.message}</p>}
                                                </div>

                                                <div className="h-px w-full bg-gradient-to-r from-transparent via-[#6143f4]/10 to-transparent"></div>

                                                <div className="space-y-10">
                                                    <div className="space-y-4">
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1 leading-none block">New Security Protocol</label>
                                                        <div className="relative group/input">
                                                            <Key className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/input:text-[#6143f4] transition-colors" size={20} />
                                                            <input 
                                                                className={`w-full bg-slate-50 dark:bg-[#0B0819] border-2 rounded-[1.5rem] py-5 pl-16 pr-16 text-lg font-black uppercase tracking-widest focus:ring-8 focus:ring-[#6143f4]/5 outline-none transition-all dark:text-white placeholder:text-slate-300 ${errors.newPassword ? 'border-red-500/50' : 'border-slate-100 dark:border-white/5 focus:border-[#6143f4]'}`}
                                                                placeholder="CREATE STRONG PASS..." 
                                                                type={showNew ? 'text' : 'password'} 
                                                                {...register('newPassword')}
                                                            />
                                                            <button 
                                                                className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#6143f4] transition-colors" 
                                                                type="button"
                                                                onClick={() => setShowNew(!showNew)}
                                                            >
                                                                {showNew ? <EyeOff size={22} /> : <Eye size={22} />}
                                                            </button>
                                                        </div>
                                                        {errors.newPassword && <p className="text-red-500 text-[10px] font-black uppercase tracking-widest mt-2 ml-4 animate-bounce">{errors.newPassword.message}</p>}
                                                    </div>

                                                    <div className="space-y-4">
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1 leading-none block">Re-Enter Matrix</label>
                                                        <div className="relative group/input">
                                                            <RefreshCw className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/input:text-[#6143f4] transition-colors" size={20} />
                                                            <input 
                                                                className={`w-full bg-slate-50 dark:bg-[#0B0819] border-2 rounded-[1.5rem] py-5 pl-16 pr-16 text-lg font-black uppercase tracking-widest focus:ring-8 focus:ring-[#6143f4]/5 outline-none transition-all dark:text-white placeholder:text-slate-300 ${errors.confirmPassword ? 'border-red-500/50' : 'border-slate-100 dark:border-white/5 focus:border-[#6143f4]'}`}
                                                                placeholder="CONFIRM NEW PASS..." 
                                                                type={showNew ? 'text' : 'password'} 
                                                                {...register('confirmPassword')}
                                                            />
                                                        </div>
                                                        {errors.confirmPassword && <p className="text-red-500 text-[10px] font-black uppercase tracking-widest mt-2 ml-4 animate-bounce">{errors.confirmPassword.message}</p>}
                                                    </div>
                                                </div>

                                                <div className="flex flex-col sm:flex-row items-center justify-end gap-6 pt-10 border-t border-slate-100 dark:border-white/5 mt-10">
                                                    <button 
                                                        type="button"
                                                        onClick={() => navigate(ROUTES.SETTINGS)}
                                                        className="w-full sm:w-auto px-10 py-5 rounded-[1.5rem] text-[10px] font-black text-slate-400 uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-white/5 transition-all"
                                                    >
                                                        Discard
                                                    </button>
                                                    <button 
                                                        type="submit"
                                                        disabled={isSubmitting}
                                                        className="w-full sm:w-auto px-14 py-5 rounded-[1.5rem] text-[10px] font-black text-white bg-[#6143f4] uppercase tracking-[0.2em] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] hover:bg-[#4a34c1] hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed leading-none"
                                                    >
                                                        {isSubmitting ? 'UPDATING...' : 'UPDATE PASSWORD'}
                                                    </button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column: Tips & Requirements */}
                                <div className="space-y-10">
                                    
                                    {/* Password Requirements Card */}
                                    <section className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 border border-[#6143f4]/5 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] space-y-8">
                                        <div className="flex items-center gap-4">
                                            <div className="size-1 bg-[#6143f4] rounded-full"></div>
                                            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Security Thresholds</h4>
                                        </div>
                                        <ul className="space-y-6">
                                            {[
                                                { label: 'Minimum 8 characters', active: newPass.length >= 8 },
                                                { label: 'One uppercase letter', active: /[A-Z]/.test(newPass) },
                                                { label: 'One number (0-9)', active: /\d/.test(newPass) },
                                                { label: 'One special char (!@#$)', active: /[!@#$%^*]/.test(newPass) }
                                            ].map((req, rid) => (
                                                <li key={rid} className={`flex items-center gap-4 text-xs font-black uppercase tracking-tight transition-all duration-500 ${req.active ? 'text-emerald-500' : 'text-slate-400 opacity-60'}`}>
                                                    <div className={`size-6 rounded-lg flex items-center justify-center transition-all ${req.active ? 'bg-emerald-500 text-white rotate-0' : 'bg-slate-100 text-slate-300 rotate-45'}`}>
                                                        {req.active ? <CheckCircle2 size={16} strokeWidth={3} /> : <Circle size={10} strokeWidth={4} />}
                                                    </div>
                                                    <span className="leading-none mt-0.5">{req.label}</span>
                                                </li>
                                            ))}
                                        </ul>
                                        <div className="mt-10 pt-10 border-t border-slate-100 dark:border-white/5 space-y-4">
                                            <div className="flex items-center justify-between">
                                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Matrix Strength</span>
                                                <span className={`text-[10px] font-black uppercase tracking-tighter italic leading-none ${newPass.length > 10 ? 'text-[#6143f4]' : 'text-amber-500 animate-pulse'}`}>
                                                    {newPass.length > 10 ? 'SECURE' : 'MEDIUM'}
                                                </span>
                                            </div>
                                            <div className="h-2.5 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                                                <motion.div 
                                                    initial={{ width: 0 }}
                                                    animate={{ width: newPass.length > 10 ? '100%' : newPass.length > 5 ? '60%' : '20%' }}
                                                    className={`h-full bg-gradient-to-r ${newPass.length > 10 ? 'from-[#6143f4] to-[#009cde]' : 'from-amber-400 to-orange-500'} rounded-full transition-all duration-1000 shadow-lg`}
                                                ></motion.div>
                                            </div>
                                        </div>
                                    </section>

                                    {/* 2FA Promo Card */}
                                    <section className="bg-gradient-to-br from-[#6143f4] via-[#009cde] to-[#6143f4] bg-[length:200%_200%] animate-gradient-flow rounded-[3rem] p-10 text-white shadow-[0_40px_100px_-20px_rgba(97,67,244,0.3)] relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 w-48 h-48 bg-white/10 rounded-full blur-[80px] -z-10 group-hover:scale-150 transition-transform duration-1000"></div>
                                        <motion.div 
                                            animate={{ rotate: [0, 10, 0, -10, 0] }}
                                            transition={{ duration: 5, repeat: Infinity }}
                                            className="size-16 bg-white/10 border border-white/20 rounded-2xl flex items-center justify-center mb-6 shadow-2xl backdrop-blur-md"
                                        >
                                            <ShieldCheck size={32} strokeWidth={2.5} />
                                        </motion.div>
                                        <h4 className="text-2xl font-black uppercase tracking-tighter italic leading-none mb-3">Two-Factor Auth</h4>
                                        <p className="text-sm font-bold text-white/80 leading-snug uppercase tracking-tight mb-8">Add an extra layer of security to your health records by enabling 2FA now.</p>
                                        <button className="w-full py-4 bg-white text-[#6143f4] rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-2xl hover:scale-105 active:scale-95 transition-all">
                                            Configure Now
                                        </button>
                                    </section>

                                    {/* Security Tip */}
                                    <section className="bg-white dark:bg-[#131022] rounded-[3rem] p-8 border border-slate-100 dark:border-white/5 shadow-sm flex gap-6 items-start">
                                        <div className="size-14 rounded-2xl bg-amber-50 dark:bg-amber-500/5 flex items-center justify-center text-amber-500 shrink-0 shadow-inner">
                                            <Info size={24} />
                                        </div>
                                        <div className="space-y-3">
                                            <h4 className="text-[10px] font-black text-[#13082a] dark:text-white uppercase tracking-[0.2em] leading-none">Forensic Tip</h4>
                                            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80">
                                                Avoid common words or birthdays. Use a unique passphrase for maximum resistance to brute force attacks.
                                            </p>
                                        </div>
                                    </section>

                                </div>
                            </div>

                        </div>
                    </div>

                    {/* Standardized HIPAA Footer */}
                    <footer className="h-24 shrink-0 border-t border-[#6143f4]/10 bg-white dark:bg-[#131022] flex flex-col md:flex-row items-center justify-between px-10 gap-4 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">
                        <div className="flex flex-wrap items-center justify-center md:justify-start gap-10 leading-none">
                            <p className="opacity-60 italic">© 2026 ArogyaAI Intelligence Platform</p>
                            <div className="flex gap-8">
                                <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Legal Terms</a>
                                <a className="hover:text-[#6143f4] transition-colors cursor-pointer" href="#">Security Portal</a>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-8 py-3 shadow-sm leading-none">
                            <div className="size-2 bg-emerald-500 rounded-full animate-pulse"></div>
                            <p className="text-emerald-600 dark:text-emerald-400 mt-0.5 tracking-widest">SECURE END-TO-END ENCRYPTED</p>
                        </div>
                    </footer>
                </main>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .leading-snug { line-height: 1.3 !important; }
                .italic { font-style: italic; }
                @keyframes gradient-flow {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }
                .animate-gradient-flow {
                    animation: gradient-flow 15s ease infinite;
                }
            `}} />
        </div>
    );
};

export default ChangePassword;

