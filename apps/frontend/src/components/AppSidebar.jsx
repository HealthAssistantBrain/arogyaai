// ── Shared AppSidebar component (Step 4 — config-driven, Step 3 — profile click)
// Renders from sidebarConfig.js — NO hardcoded nav items.
// Profile card bottom navigates to ROUTES.SETTINGS_PROFILE (Patch 3 fix).
// Usage: <AppSidebar activePath={ROUTES.DASHBOARD} />

import { useNavigate, useLocation } from 'react-router-dom'
import { Waves, MoreVertical } from 'lucide-react'
import { ROUTES } from '../router/routes'
import sidebarConfig from '../config/sidebarConfig'

export default function AppSidebar({ activePath }) {
  const navigate = useNavigate()
  const location = useLocation()

  // Determine active route — prefer explicit prop, fall back to current location
  const currentPath = activePath ?? location.pathname

  return (
    <aside className="w-72 bg-surface border-r border-primary/5 dark:border-stroke/50 flex flex-col h-full overflow-y-auto no-scrollbar hidden lg:flex shrink-0">

      {/* Logo / Brand */}
      <div
        className="p-8 flex items-center gap-4 cursor-pointer group"
        onClick={() => navigate(ROUTES.DASHBOARD)}
      >
        <div className="size-11 bg-primary rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary/20 transition-transform group-hover:scale-110">
          <Waves size={24} strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
          <p className="text-[10px] text-text-muted font-bold uppercase tracking-[0.2em] mt-1">Healthcare OS</p>
        </div>
      </div>

      {/* Navigation — rendered from sidebarConfig */}
      <nav className="flex-1 px-5 space-y-1.5 overflow-y-auto pb-6 custom-scrollbar">
        {sidebarConfig.map((group) => (
          <div key={group.section} className="py-2">
            <div className="text-[10px] font-black text-text-muted uppercase tracking-[0.25em] px-4 mb-3 mt-4 leading-none">
              {group.section}
            </div>
            {group.items.map((link) => {
              const isActive = currentPath === link.path
              return (
                <button
                  key={link.label}
                  onClick={() => navigate(link.path)}
                  className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-[1.25rem] transition-all group ${isActive
                      ? 'bg-primary text-white shadow-2xl shadow-primary/30 font-black'
                      : 'text-slate-500 dark:text-text-muted hover:bg-primary/5 hover:text-primary font-bold'
                    }`}
                >
                  <link.icon
                    size={18}
                    className={isActive ? 'text-text-primary' : 'text-text-muted group-hover:text-primary'}
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

    </aside>
  )
}

