import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { useAuthStore } from '../../../store/authStore';
import { getSupabaseClient, supabase } from '../../../lib/supabaseClient';
import { ROUTES } from '../../../router/routes';
import PasswordUpdateV2 from '../../../components/security/PasswordUpdateV2';

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

    const [submitError, setSubmitError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [isResetEmailSending, setIsResetEmailSending] = useState(false);

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
            const client = getSupabaseClient() ?? supabase;
            if (!client) throw new Error('Supabase Auth is not configured');

            const { error } = await client.auth.updateUser({
                password: data.newPassword,
            });

            if (error) throw error;
            setSuccessMessage("Password updated successfully.");
            reset();
        } catch (error) {
            setSubmitError(error?.message || "Failed to update password");
        }
    };

    const handleCancel = () => {
        setSubmitError('');
        setSuccessMessage('');
        reset();
    };

    const handleForgotPassword = async () => {
        if (!user?.email) {
            toast.error('No account email is available for password reset.');
            return;
        }

        setIsResetEmailSending(true);
        setSubmitError('');
        setSuccessMessage('');

        try {
            const client = getSupabaseClient() ?? supabase;
            if (!client) throw new Error('Supabase Auth is not configured');

            const { error } = await client.auth.resetPasswordForEmail(user.email, {
                redirectTo: `${window.location.origin}${ROUTES.RESET_PASSWORD}`,
            });

            if (error) throw error;

            toast.success('Password reset link sent to your email.');
        } catch (error) {
            console.error(error);
            toast.error(error?.message || 'Failed to send reset email.');
        } finally {
            setIsResetEmailSending(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-12 pb-16">
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
            <PasswordUpdateV2
                register={register}
                isPasswordMissing={isPasswordMissing}
                newPass={newPass}
                errors={errors}
                isSubmitting={isSubmitting}
                isResetEmailSending={isResetEmailSending}
                submitError={submitError}
                successMessage={successMessage}
                onSubmit={handleSubmit(onSubmit)}
                onCancel={handleCancel}
                onForgotPassword={handleForgotPassword}
            />
        </div>
    );
};

export default SettingsSecurity;
