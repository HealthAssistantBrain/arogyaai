import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/routes';
import { useAuthStore } from '../../store/authStore';

const initialsFromName = (value: string | undefined | null) =>
    String(value || 'ArogyaAI')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() || '')
        .join('') || 'AI';

export default function UserProfile() {
    const navigate = useNavigate();
    // @ts-ignore
    const user = useAuthStore((state) => state.user);
    // @ts-ignore
    const profile = useAuthStore((state) => state.profile);

    const displayName = profile?.full_name || user?.full_name || 'Your profile';
    const avatarUrl = profile?.avatar_url || user?.avatar_url || null;
    const avatarInitials = useMemo(() => initialsFromName(displayName), [displayName]);

    return (
        <div
            className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(ROUTES.SETTINGS_PROFILE);
                }
            }}
        >
            <div className="text-right hidden sm:block">
                <p className="text-xs font-bold text-[#13082A] dark:text-white leading-none">{displayName}</p>
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-1">Live profile</p>
            </div>
            {avatarUrl ? (
                <img className="size-10 rounded-full border-2 border-[#6043F4]/20 p-0.5 object-cover" src={avatarUrl} alt={displayName} />
            ) : (
                <div className="size-10 rounded-full border-2 border-[#6043F4]/20 p-0.5 flex items-center justify-center bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-white font-bold">
                    {avatarInitials}
                </div>
            )}
        </div>
    );
}
