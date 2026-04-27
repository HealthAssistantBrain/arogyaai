import { useState } from 'react';
import { EyeOff, Eye, CheckCircle2, Circle, Key, ShieldCheck, Info } from 'lucide-react';

const PasswordUpdateV2 = ({
    register,
    isPasswordMissing,
    newPass = "",
    errors,
    isSubmitting,
    isResetEmailSending = false,
    submitError,
    successMessage,
    onSubmit,
    onCancel,
    onForgotPassword,
}) => {
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);

    const passwordReqs = [
        { label: 'Minimum 8 characters', active: newPass.length >= 8 },
        { label: 'At least one uppercase letter', active: /[A-Z]/.test(newPass) },
        { label: 'At least one number (0-9)', active: /\d/.test(newPass) },
        { label: 'At least one special character (!@#$)', active: /[!@#$%^*]/.test(newPass) }
    ];

    const activeCount = passwordReqs.filter(req => req.active).length;
    let strengthLabel = 'Weak';
    let strengthWidth = '25%';
    let strengthColor = 'bg-red-500';
    let strengthTextColor = 'text-red-500';

    if (activeCount === 4) {
        strengthLabel = 'Strong';
        strengthWidth = '100%';
        strengthColor = 'bg-emerald-500';
        strengthTextColor = 'text-emerald-500';
    } else if (activeCount >= 2) {
        strengthLabel = 'Medium';
        strengthWidth = '60%';
        strengthColor = 'bg-[#009CDE]';
        strengthTextColor = 'text-[#009CDE]';
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Card */}
            <div className="lg:col-span-2">
                <div className="bg-white dark:bg-slate-900 rounded-xl shadow-[0_4px_20px_-2px_rgba(19,8,42,0.05)] overflow-hidden border border-slate-100 dark:border-slate-800">
                    <div className="px-8 py-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center">
                        <h3 className="font-bold text-[#13082a] dark:text-white flex items-center gap-2">
                            <Key className="text-[#6143f4]" size={20} />
                            {isPasswordMissing ? 'Add Password' : 'Change Password'}
                        </h3>
                        <span className="text-[11px] px-2 py-1 bg-green-100 text-green-700 rounded-full font-bold uppercase tracking-tight">Level: High Security</span>
                    </div>

                    <div className="p-8">
                        <form className="space-y-6" onSubmit={onSubmit}>
                            {isPasswordMissing && (
                                <div className="rounded-2xl border border-[#6143f4]/15 bg-[#6143f4]/5 px-4 py-3 text-sm font-medium text-slate-600 dark:border-[#6143f4]/20 dark:bg-[#6143f4]/10 dark:text-slate-300">
                                    You are using Google login. Set a password to enable manual login, or send yourself a reset email to finish setup securely.
                                </div>
                            )}

                            {!isPasswordMissing && (
                                <>
                                    <div className="space-y-2">
                                        <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Current Password</label>
                                        <div className="relative group">
                                            <input
                                                className={`w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-800 py-3 px-4 focus:ring-2 focus:ring-[#6143f4] focus:border-[#6143f4] outline-none transition-all ${errors.currentPassword ? 'border-red-500' : ''}`}
                                                placeholder="••••••••"
                                                type={showCurrent ? 'text' : 'password'}
                                                {...register('currentPassword')}
                                            />
                                            <button
                                                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                                                type="button"
                                                onClick={() => setShowCurrent(!showCurrent)}
                                            >
                                                {showCurrent ? <EyeOff size={20} /> : <Eye size={20} />}
                                            </button>
                                        </div>
                                        {errors.currentPassword && <p className="text-red-500 text-xs font-bold mt-1">{errors.currentPassword.message}</p>}
                                    </div>
                                    <div className="h-[1px] w-full bg-slate-100 dark:bg-slate-800 my-4"></div>
                                </>
                            )}

                            <div className="space-y-2">
                                <label className="text-sm font-bold text-slate-700 dark:text-slate-300">New Password</label>
                                <div className="relative group">
                                    <input
                                        className={`w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-800 py-3 px-4 focus:ring-2 focus:ring-[#6143f4] focus:border-[#6143f4] outline-none transition-all ${errors.newPassword ? 'border-red-500' : ''}`}
                                        placeholder="Create a strong password"
                                        type={showNew ? 'text' : 'password'}
                                        {...register('newPassword')}
                                    />
                                    <button
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                                        type="button"
                                        onClick={() => setShowNew(!showNew)}
                                    >
                                        {showNew ? <EyeOff size={20} /> : <Eye size={20} />}
                                    </button>
                                </div>
                                {errors.newPassword && <p className="text-red-500 text-xs font-bold mt-1">{errors.newPassword.message}</p>}
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Confirm New Password</label>
                                <div className="relative group">
                                    <input
                                        className={`w-full rounded-xl border-slate-200 dark:border-slate-700 dark:bg-slate-800 py-3 px-4 focus:ring-2 focus:ring-[#6143f4] focus:border-[#6143f4] outline-none transition-all ${errors.confirmPassword ? 'border-red-500' : ''}`}
                                        placeholder="Re-enter your new password"
                                        type={showNew ? 'text' : 'password'}
                                        {...register('confirmPassword')}
                                    />
                                </div>
                                {errors.confirmPassword && <p className="text-red-500 text-xs font-bold mt-1">{errors.confirmPassword.message}</p>}
                            </div>

                            {submitError && (
                                <p className="text-red-500 text-sm font-bold mt-4">{submitError}</p>
                            )}
                            {successMessage && (
                                <p className="text-emerald-500 text-sm font-bold mt-4">{successMessage}</p>
                            )}

                            <div className="flex items-center justify-end gap-4 pt-6 border-t border-slate-100 dark:border-slate-800 mt-8">
                                <button
                                    className="px-6 py-3 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-100 transition-all dark:hover:bg-slate-800 dark:text-slate-300"
                                    type="button"
                                    onClick={onCancel}
                                >
                                    Cancel
                                </button>
                                <button
                                    className="px-1 py-3 text-sm font-bold text-[#6143f4] transition-all hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                                    type="button"
                                    onClick={onForgotPassword}
                                    disabled={isResetEmailSending}
                                >
                                    {isResetEmailSending ? 'Sending reset link...' : 'Forgot Password?'}
                                </button>
                                <button
                                    className="px-8 py-3 rounded-xl text-sm font-bold text-white bg-[#6143f4] hover:opacity-90 shadow-[0_4px_14px_rgba(97,67,244,0.3)] transition-all disabled:opacity-50"
                                    type="submit"
                                    disabled={isSubmitting || isResetEmailSending}
                                >
                                    {isSubmitting ? 'Updating...' : (isPasswordMissing ? 'Set Password' : 'Update Password')}
                                </button>
                            </div>

                        </form>
                    </div>
                </div>
            </div>

            {/* Sidebar Tips/Requirements */}
            <div className="space-y-6">
                <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl shadow-[0_4px_20px_-2px_rgba(19,8,42,0.05)] p-6">
                    <h4 className="text-sm font-bold text-[#13082a] dark:text-white mb-4">Password Requirements</h4>
                    <ul className="space-y-3">
                        {passwordReqs.map((req, rid) => (
                            <li key={rid} className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-400">
                                {req.active ?
                                    <CheckCircle2 className="text-emerald-500 shrink-0 mt-0.5" size={18} /> :
                                    <Circle className="text-slate-300 shrink-0 mt-0.5" size={15} />
                                }
                                <span className="leading-tight">{req.label}</span>
                            </li>
                        ))}
                    </ul>

                    <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
                        <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-tight mb-2">
                            <span>Strength Score</span>
                            <span className={strengthTextColor}>{strengthLabel}</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                            <div className={`h-full ${strengthColor} rounded-full transition-all duration-300`} style={{ width: strengthWidth }}></div>
                        </div>
                    </div>
                </div>

                <div className="bg-gradient-to-br from-[#6143f4] to-[#009CDE] rounded-xl p-6 text-white shadow-[0_4px_20px_-2px_rgba(19,8,42,0.05)]">
                    <ShieldCheck className="mb-3" size={32} />
                    <h4 className="font-bold text-lg mb-2 leading-tight">Two-Factor Authentication</h4>
                    <p className="text-sm text-white/80 mb-4">Add an extra layer of security to your health records by enabling 2FA.</p>
                    <button className="w-full py-2.5 bg-white/20 hover:bg-white/30 backdrop-blur-sm border border-white/20 text-white text-xs font-bold rounded-lg transition-all" type="button">
                        Configure Now
                    </button>
                </div>

                <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl shadow-[0_4px_20px_-2px_rgba(19,8,42,0.05)] p-6">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="size-10 rounded-full bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center text-amber-500">
                            <Info size={20} />
                        </div>
                        <h4 className="text-sm font-bold text-[#13082a] dark:text-white">Security Tip</h4>
                    </div>
                    <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">Avoid using common words, birthdays, or names. A mix of unrelated words (passphrase) is often more secure and easier to remember.</p>
                </div>
            </div>
        </div>
    );
};

export default PasswordUpdateV2;
