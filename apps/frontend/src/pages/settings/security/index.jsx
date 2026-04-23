import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Key, Eye, EyeOff, CheckCircle2, Circle, Lock } from 'lucide-react';
import api from '../../../lib/axios';
import { useAuthStore } from '../../../store/authStore';

const SettingsSecurity = () => {
    const { user } = useAuthStore();

    const isPasswordMissing = !user?.has_password;

    // Conditionally require currentPassword if the user has a password
    const changePasswordSchema = z.object({
        currentPassword: isPasswordMissing
            ? z.string().optional()
            : z.string().min(1, 'Current password is required'),
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

    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);
    const [submitError, setSubmitError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const {
        register,
        handleSubmit,
        formState: { errors, isSubmitting },
        watch,
        reset
    } = useForm({
        resolver: zodResolver(changePasswordSchema),
        defaultValues: { currentPassword: '', newPassword: '', confirmPassword: '' },
    });

    const newPass = watch("newPassword", "");

    const onSubmit = async (data) => {
        setSubmitError('');
        setSuccessMessage('');
        try {
            const payload = {
                password: data.newPassword,
                confirm_password: data.confirmPassword
            };

            await api.put("/auth/update-password", payload);
            setSuccessMessage("Password updated successfully.");
            reset();
        } catch (error) {
            setSubmitError(error.response?.data?.detail || "Failed to update password");
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-12 pb-16">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                <div className="space-y-4">
                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Security</h2>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none max-w-2xl">
                        Manage your account credentials securely.
                    </p>
                </div>
            </div>

            {/* Change Password Block */}
            <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 overflow-hidden transition-all duration-500 hover:border-[#6143f4]/20 group/card">
                <div className="px-10 py-10 border-b border-slate-100 dark:border-white/5 flex justify-between items-center bg-slate-50/30 dark:bg-transparent">
                    <div className="flex items-center gap-5">
                        <div className="size-14 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] group-hover/card:scale-110 transition-transform shadow-inner">
                            <Key size={28} />
                        </div>
                        <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none">
                            {isPasswordMissing ? 'Add Password' : 'Credential Update'}
                        </h3>
                    </div>
                </div>
                <div className="p-10 lg:p-14">
                    <form className="space-y-10" onSubmit={handleSubmit(onSubmit)}>

                        {!isPasswordMissing && (
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
                        )}

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

                            {/* Password validations */}
                            <ul className="space-y-3 px-2">
                                {[
                                    { label: 'Minimum 8 char', active: newPass.length >= 8 },
                                    { label: 'One uppercase', active: /[A-Z]/.test(newPass) },
                                    { label: 'One number', active: /\d/.test(newPass) },
                                    { label: 'One special (!@#$)', active: /[!@#$%^*]/.test(newPass) }
                                ].map((req, rid) => (
                                    <li key={rid} className={`flex items-center gap-3 text-[10px] font-black uppercase tracking-tight transition-all duration-500 ${req.active ? 'text-emerald-500' : 'text-slate-400 opacity-60'}`}>
                                        <div className={`size-4 rounded-full flex items-center justify-center transition-all ${req.active ? 'bg-emerald-500 text-white rotate-0' : 'bg-slate-100 dark:bg-white/5 text-slate-300 dark:text-slate-500 rotate-45'}`}>
                                            {req.active ? <CheckCircle2 size={10} strokeWidth={3} /> : <Circle size={6} strokeWidth={4} />}
                                        </div>
                                        <span className="leading-none mt-0.5">{req.label}</span>
                                    </li>
                                ))}
                            </ul>

                            <div className="space-y-4">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] ml-1 leading-none block">Re-Enter Matrix</label>
                                <div className="relative group/input">
                                    <Key className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/input:text-[#6143f4] transition-colors" size={20} />
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

                        {submitError && (
                            <p className="text-red-500 text-[10px] font-black uppercase tracking-widest mt-4 text-center">{submitError}</p>
                        )}
                        {successMessage && (
                            <p className="text-emerald-500 text-[10px] font-black uppercase tracking-widest mt-4 text-center">{successMessage}</p>
                        )}

                        <div className="flex flex-col sm:flex-row items-center justify-end gap-6 pt-10 border-t border-slate-100 dark:border-white/5 mt-10">
                            <button
                                type="submit"
                                disabled={isSubmitting}
                                className="w-full px-14 py-5 rounded-[1.5rem] text-[10px] font-black text-white bg-[#6143f4] uppercase tracking-[0.2em] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] hover:bg-[#4a34c1] hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed leading-none"
                            >
                                {isSubmitting ? 'UPDATING...' : (isPasswordMissing ? 'SET PASSWORD' : 'UPDATE PASSWORD')}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default SettingsSecurity;
