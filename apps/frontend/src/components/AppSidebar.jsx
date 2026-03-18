// ── Shared AppSidebar component (Step 4 — config-driven, Step 3 — profile click)
// Renders from sidebarConfig.js — NO hardcoded nav items.
// Profile card bottom navigates to ROUTES.SETTINGS_PROFILE (Patch 3 fix).
// Usage: <AppSidebar activePath={ROUTES.DASHBOARD} />

import { useNavigate, useLocation } from 'react-router-dom'
import { Waves, MoreVertical }       from 'lucide-react'
import { ROUTES }                    from '../router/routes'
import sidebarConfig                 from '../config/sidebarConfig'

export default function AppSidebar({ activePath }) {
  const navigate = useNavigate()
  const location = useLocation()

  // Determine active route — prefer explicit prop, fall back to current location
  const currentPath = activePath ?? location.pathname

  return (
    <aside className="w-72 bg-white dark:bg-[#131022] border-r border-[#6143f4]/5 dark:border-white/5 flex flex-col h-full overflow-y-auto no-scrollbar hidden lg:flex shrink-0">

      {/* Logo / Brand */}
      <div
        className="p-8 flex items-center gap-4 cursor-pointer group"
        onClick={() => navigate(ROUTES.DASHBOARD)}
      >
        <div className="size-11 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
          <Waves size={24} strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mt-1">Healthcare OS</p>
        </div>
      </div>

      {/* Navigation — rendered from sidebarConfig */}
      <nav className="flex-1 px-5 space-y-1.5 overflow-y-auto pb-6 custom-scrollbar">
        {sidebarConfig.map((group) => (
          <div key={group.section} className="py-2">
            <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em] px-4 mb-3 mt-4 leading-none">
              {group.section}
            </div>
            {group.items.map((link) => {
              const isActive = currentPath === link.path
              return (
                <button
                  key={link.label}
                  onClick={() => navigate(link.path)}
                  className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-[1.25rem] transition-all group ${
                    isActive
                      ? 'bg-[#6143f4] text-white shadow-2xl shadow-[#6143f4]/30 font-black'
                      : 'text-slate-500 dark:text-slate-400 hover:bg-[#6143f4]/5 hover:text-[#6143f4] font-bold'
                  }`}
                >
                  <link.icon
                    size={18}
                    className={isActive ? 'text-white' : 'text-slate-400 group-hover:text-[#6143f4]'}
                  />
                  <span className="text-[11px] uppercase tracking-widest leading-none">
                    {link.label}
                  </span>
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Profile Bottom Card — FIX: clicking navigates to ROUTES.SETTINGS_PROFILE */}
      <div className="p-6 border-t border-slate-100 dark:border-white/5">
        <div
          onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}
          className="flex items-center gap-3 p-3 rounded-[1.5rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/30 transition-colors cursor-pointer group"
        >
          <div className="size-11 rounded-xl bg-[#6143f4]/10 overflow-hidden flex items-center justify-center text-[#6143f4] text-xs font-black border-2 border-transparent group-hover:border-[#6143f4] transition-all">
            AJ
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-black truncate text-[#13082a] dark:text-white uppercase">Alex Johnson</p>
            <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Premium Member</p>
          </div>
          <MoreVertical size={14} className="text-slate-400" />
        </div>
      </div>
    </aside>
  )
}
