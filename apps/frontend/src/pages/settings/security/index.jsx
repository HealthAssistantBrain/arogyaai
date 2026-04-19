import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
    ShieldCheck, Key, Eye, EyeOff, CheckCircle2, Circle, RefreshCw,
    Laptop, Monitor, Smartphone as PhoneIcon, ArrowUpRight,
    AlertCircle, Shield, Clock, Download, ArrowRight, Lock
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

const SettingsSecurity = () => {
    const [twoFAEnabled, setTwoFAEnabled] = useState(true);
    const [isScanning, setIsScanning] = useState(false);
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

    // eslint-disable-next-line
    const newPass = watch("newPassword", "");

    const onSubmit = (data) => {
        console.log("Password updated successfully", data);
    };

    const handleRunScan = () => {
        setIsScanning(true);
        setTimeout(() => setIsScanning(false), 2000);
    };

    const activeSessions = [
        {
            device: 'MacBook Pro 16"', type: 'Laptop', icon: Laptop, browser: 'Chrome Browser',
            location: 'Mumbai, India', ip: '192.168.1.184', isCurrent: true,
            bg: 'bg-[#6143f4]/10', color: 'text-[#6143f4]'
        },
        {
            device: 'iPhone 15 Pro', type: 'Mobile', icon: PhoneIcon, browser: 'iOS App',
            location: 'New Delhi, India', ip: '104.22.11.89', lastActive: 'Active 2 hrs ago',
            bg: 'bg-[#009cde]/10', color: 'text-[#009cde]'
        }
    ];

    const loginHistory = [
        { date: 'Oct 24, 2026', time: '10:45 AM', device: 'MacBook Pro / Chrome', icon: Laptop, location: 'Mumbai, India', ip: '192.168.1.184', status: 'Successful', statusColor: 'emerald' },
        { date: 'Oct 23, 2026', time: '04:12 PM', device: 'iPhone 15 Pro / App', icon: PhoneIcon, location: 'New Delhi, India', ip: '104.22.11.89', status: 'Successful', statusColor: 'emerald' },
        { date: 'Oct 21, 2026', time: '03:22 AM', device: 'Unknown Windows / Firefox', icon: Monitor, location: 'St. Petersburg, Russia', ip: '95.161.222.10', status: 'Blocked', statusColor: 'red' },
        { date: 'Oct 20, 2026', time: '09:30 AM', device: 'MacBook Pro / Chrome', icon: Laptop, location: 'Mumbai, India', ip: '192.168.1.184', status: 'Successful', statusColor: 'emerald' },
    ];

    const Toggle = ({ active, onClick }) => (
        <button
            onClick={onClick}
            className={`relative inline-flex h-8 w-14 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 ${active ? 'bg-[#6143f4]' : 'bg-slate-200 dark:bg-slate-700'}`}
        >
            <span
                style={{ transform: active ? 'translateX(24px)' : 'translateX(0)' }}
                className="pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow-lg ring-0 mt-0.5 ml-0.5 transition-transform duration-200 ease-in-out"
            />
        </button>
    );

    return (
        <div className="max-w-6xl mx-auto space-y-12 pb-16">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                <div className="space-y-4">
                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Security</h2>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none max-w-2xl">Manage your passwords, active sessions, and multi-factor authentication securely.</p>
                </div>
                <div className="flex gap-4">
                    <button className="px-8 py-5 bg-white dark:bg-[#131022] border border-slate-200 dark:border-white/10 rounded-[1.5rem] font-black text-xs uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-white/5 transition-all flex items-center xl:hidden 2xl:flex gap-3 shadow-sm leading-none">
                        <Download size={18} /> Export Logs
                    </button>
                    <button
                        onClick={handleRunScan}
                        disabled={isScanning}
                        className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] shadow-2xl shadow-[#6143f4]/30 transition-all flex items-center gap-4 active:scale-95 leading-none disabled:opacity-50"
                    >
                        <RefreshCw size={18} className={isScanning ? 'animate-spin' : ''} /> {isScanning ? 'Scanning...' : 'Run Audit'}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 items-start">
                {/* Left/Main Column: Password & Sessions */}
                <div className="lg:col-span-2 space-y-12">

                    {/* Change Password Block */}
                    <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 overflow-hidden transition-all duration-500 hover:border-[#6143f4]/20 group/card">
                        <div className="px-10 py-10 border-b border-slate-100 dark:border-white/5 flex justify-between items-center bg-slate-50/30 dark:bg-transparent">
                            <div className="flex items-center gap-5">
                                <div className="size-14 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] group-hover/card:scale-110 transition-transform shadow-inner">
                                    <Key size={28} />
                                </div>
                                <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">Credential Update</h3>
                            </div>
                        </div>
                        <div className="p-10 lg:p-14">
                            <form className="space-y-10" onSubmit={handleSubmit(onSubmit)}>
                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1 leading-none block">Current Matrix</label>
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
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="w-full px-14 py-5 rounded-[1.5rem] text-[10px] font-black text-white bg-[#6143f4] uppercase tracking-[0.2em] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] hover:bg-[#4a34c1] hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed leading-none"
                                    >
                                        {isSubmitting ? 'UPDATING...' : 'UPDATE PASSWORD'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>

                    {/* Active Sessions */}
                    <div className="space-y-6">
                        <div className="flex items-center gap-4">
                            <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Active Sessions</h3>
                        </div>

                        <div className="space-y-4">
                            {activeSessions.map((session, idx) => {
                                const SessionIcon = session.icon;
                                return (
                                    <div key={idx} className="bg-white dark:bg-[#131022] rounded-[2.5rem] p-8 shadow-sm border border-[#6143f4]/5 flex flex-col sm:flex-row items-center gap-6 hover:border-[#6143f4]/20 transition-all group/card relative overflow-hidden">
                                        <div className={`size-16 rounded-[1.5rem] ${session.bg} flex items-center justify-center shrink-0 shadow-inner border border-[#6143f4]/5 group-hover/card:scale-110 transition-transform duration-500`}>
                                            <SessionIcon size={28} className={`${session.color} group-hover/card:rotate-6 transition-transform`} strokeWidth={2.5} />
                                        </div>
                                        <div className="flex-1 space-y-2 text-center sm:text-left">
                                            <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-center sm:justify-start">
                                                <h4 className="text-xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">{session.device}</h4>
                                                {session.isCurrent && (
                                                    <span className="bg-emerald-500/10 text-emerald-500 text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest border border-emerald-500/20 shadow-sm leading-none mt-1 sm:mt-0">Primary</span>
                                                )}
                                            </div>
                                            <p className="text-sm text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-70 leading-none">{session.browser} • {session.location}</p>
                                        </div>
                                        <button className="px-6 py-3 bg-white dark:bg-[#131022] border border-red-500/20 text-red-500 hover:bg-red-500 hover:text-white rounded-[1rem] font-black text-[10px] uppercase tracking-widest transition-all active:scale-95 shadow-sm leading-none shrink-0">
                                            Revoke
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                </div>

                {/* Right Column: Tips, 2FA, Security Rating */}
                <div className="space-y-10">

                    {/* Password Requirements Card */}
                    <div className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 border border-[#6143f4]/5 shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] space-y-8">
                        <div className="flex items-center gap-4">
                            <div className="size-1 bg-[#6143f4] rounded-full"></div>
                            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Security Thresholds</h4>
                        </div>
                        <ul className="space-y-6">
                            {[
                                { label: 'Minimum 8 char', active: newPass.length >= 8 },
                                { label: 'One uppercase', active: /[A-Z]/.test(newPass) },
                                { label: 'One number', active: /\d/.test(newPass) },
                                { label: 'One special (!@#$)', active: /[!@#$%^*]/.test(newPass) }
                            ].map((req, rid) => (
                                <li key={rid} className={`flex items-center gap-4 text-[11px] font-black uppercase tracking-tight transition-all duration-500 ${req.active ? 'text-emerald-500' : 'text-slate-400 opacity-60'}`}>
                                    <div className={`size-5 rounded-md flex items-center justify-center transition-all ${req.active ? 'bg-emerald-500 text-white rotate-0' : 'bg-slate-100 dark:bg-white/5 text-slate-300 dark:text-slate-500 rotate-45'}`}>
                                        {req.active ? <CheckCircle2 size={12} strokeWidth={3} /> : <Circle size={8} strokeWidth={4} />}
                                    </div>
                                    <span className="leading-none mt-0.5">{req.label}</span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* 2FA Card */}
                    <div className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 border border-[#6143f4]/5 shadow-sm space-y-6">
                        <div className="size-14 bg-[#6143f4] rounded-[1.5rem] flex items-center justify-center text-white shadow-xl">
                            <ShieldCheck size={28} strokeWidth={2.5} />
                        </div>
                        <div>
                            <h4 className="text-2xl font-black uppercase tracking-tighter italic text-[#13082a] dark:text-white leading-none mb-2">Two-Factor Auth</h4>
                            <p className="text-xs font-bold text-slate-500 dark:text-slate-400 leading-relaxed uppercase tracking-tight">Adaptive defense via SMS tokens for every access event.</p>
                        </div>
                        <div className="flex items-center gap-6 justify-between pt-4 border-t border-slate-50 dark:border-white/5">
                            <div>
                                <p className={`text-[10px] font-black uppercase tracking-widest leading-none ${twoFAEnabled ? 'text-emerald-500' : 'text-slate-400'}`}>{twoFAEnabled ? 'System Active' : 'Offline'}</p>
                            </div>
                            <Toggle active={twoFAEnabled} onClick={() => setTwoFAEnabled(!twoFAEnabled)} />
                        </div>
                    </div>

                </div>
            </div>

            {/* Access Logs */}
            <div className="space-y-6 pt-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Security Access Logs</h3>
                    </div>
                </div>
                <div className="bg-white dark:bg-[#131022] rounded-[3rem] shadow-sm border border-[#6143f4]/5 overflow-hidden">
                    <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-[#f6f5f8]/50 dark:bg-white/5 border-b border-[#6143f4]/5">
                                    <th className="px-8 py-6 text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Temporal Marker</th>
                                    <th className="px-8 py-6 text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Hardware</th>
                                    <th className="px-8 py-6 text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Location</th>
                                    <th className="px-8 py-6 text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50 dark:divide-white/5">
                                {loginHistory.map((log, idx) => {
                                    const LogIcon = log.icon;
                                    return (
                                        <tr key={idx} className="group/row transition-all hover:bg-[#6143f4]/[0.02]">
                                            <td className="px-8 py-6 whitespace-nowrap">
                                                <div className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">{log.date}</div>
                                                <div className="text-[9px] text-slate-400 font-black uppercase tracking-[0.2em] mt-1 opacity-60 leading-none">{log.time}</div>
                                            </td>
                                            <td className="px-8 py-6 whitespace-nowrap">
                                                <div className="flex items-center gap-4">
                                                    <div className="size-8 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 border border-slate-100 dark:border-white/5 group-hover/row:text-[#6143f4] transition-all">
                                                        <LogIcon size={16} />
                                                    </div>
                                                    <span className="text-xs font-black text-[#13082a] dark:text-white uppercase tracking-tight">{log.device}</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6 whitespace-nowrap text-[10px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest">{log.location}</td>
                                            <td className="px-8 py-6 whitespace-nowrap">
                                                <span className={`inline-flex items-center gap-2 py-1.5 px-4 rounded-full text-[9px] font-black uppercase tracking-widest leading-none ${log.statusColor === 'emerald' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
                                                    }`}>
                                                    {log.status === 'Blocked' ? <AlertCircle size={12} /> : <CheckCircle2 size={12} />}
                                                    {log.status}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes gradient-flow { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
                .animate-gradient-flow { animation: gradient-flow 15s ease infinite; }
            `}} />
        </div>
    );
};

export default SettingsSecurity;
