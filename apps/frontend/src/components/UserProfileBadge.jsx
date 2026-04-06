import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import { getUserProfile } from '../lib/userProfile';

const VARIANTS = {
  standard: {
    wrapper: 'flex items-center gap-4 ml-2 cursor-pointer group',
    textWrap: 'text-right hidden sm:block',
    name: 'text-xs font-black text-[#13082a] dark:text-white uppercase leading-none group-hover:text-[#6143f4] transition-colors',
    subtitle: 'text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1',
    avatarWrap: 'size-12 rounded-2xl border-2 border-[#6143f4]/20 p-1 bg-white overflow-hidden shadow-xl shadow-[#6143f4]/10 transition-all group-hover:scale-105 active:scale-95',
    avatar: 'size-full rounded-xl object-cover',
  },
  compact: {
    wrapper: 'flex items-center gap-3 cursor-pointer group',
    textWrap: 'text-right hidden sm:block',
    name: 'text-sm font-bold text-[#13082A] dark:text-white leading-none group-hover:text-[#6043F4] transition-colors',
    subtitle: 'text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold tracking-widest mt-1',
    avatarWrap: 'size-10 rounded-full border-2 border-[#6043F4]/20 overflow-hidden shadow-md transition-transform group-hover:scale-110',
    avatar: 'w-full h-full object-cover',
  },
  sidebar: {
    wrapper: 'flex items-center gap-3 p-3 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/30 transition-colors cursor-pointer group w-[212px]',
    textWrap: 'flex-1 min-w-0',
    name: 'text-xs font-black truncate text-[#13082a] dark:text-white uppercase',
    subtitle: 'text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1',
    avatarWrap: 'size-11 rounded-xl bg-[#6143f4]/10 overflow-hidden flex items-center justify-center border-2 border-transparent group-hover:border-[#6143f4] transition-all shrink-0',
    avatar: 'size-full rounded-[10px] object-cover',
  },
  small: {
    wrapper: 'flex items-center gap-2.5 cursor-pointer group',
    textWrap: 'text-right',
    name: 'text-[12px] font-bold text-[#13082a] dark:text-white leading-tight group-hover:text-[#6143f4] transition-colors',
    subtitle: 'text-[8px] text-[#6143f4] uppercase font-bold tracking-wider mt-0.5 opacity-80',
    avatarWrap: 'w-9 h-9 rounded-lg bg-[#6143f4]/10 overflow-hidden border-2 border-transparent group-hover:border-[#6143f4] transition-all shrink-0',
    avatar: 'w-full h-full object-cover',
  },
};

export default function UserProfileBadge({
  className = '',
  variant = 'standard',
  userOverride = null,
}) {
  const navigate = useNavigate();
  const authUser = useAuthStore((state) => state.user);
  const role = useAuthStore((state) => state.role);
  const config = VARIANTS[variant] ?? VARIANTS.standard;
  const profile = useMemo(
    () => getUserProfile(userOverride ?? authUser, role),
    [authUser, role, userOverride]
  );
  const [avatarSrc, setAvatarSrc] = useState(profile.avatar);

  useEffect(() => {
    setAvatarSrc(profile.avatar);
  }, [profile.avatar]);

  return (
    <div
      className={`${config.wrapper} ${className}`.trim()}
      onClick={() => navigate(ROUTES.PROFILE)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          navigate(ROUTES.PROFILE);
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className={config.textWrap}>
        <p className={config.name}>{profile.name}</p>
        <p className={config.subtitle}>{profile.subtitle}</p>
      </div>
      <div className={config.avatarWrap}>
        <img
          className={config.avatar}
          src={avatarSrc}
          alt={profile.name}
          onError={() => setAvatarSrc(profile.fallbackAvatar)}
        />
      </div>
    </div>
  );
}
