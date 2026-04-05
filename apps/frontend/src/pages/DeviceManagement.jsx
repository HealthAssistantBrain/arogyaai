import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Bell,
  Plus,
  Watch,
  Circle,
  Monitor,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  ChevronRight,
  Settings,
  Wifi,
} from 'lucide-react';
import { ROUTES } from '../router/routes';

/* ═══════════════════════════════════════════════════════════════
   DeviceCard — Rectangular card with settings gear icon
   ═══════════════════════════════════════════════════════════════ */
function DeviceCard({ device }) {
  return (
    <div className="bg-white dark:bg-[#131022] rounded-xl p-5 border border-slate-200/60 dark:border-white/5 hover:shadow-md transition-all relative flex flex-col min-h-[240px]">
      {/* Row 1: Icon + Status badge */}
      <div className="flex items-start justify-between mb-3.5">
        <div
          className="w-11 h-11 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: device.iconBg }}
        >
          {device.iconElement}
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: device.statusDotColor }}
          />
          <span
            className="text-[11px] font-semibold"
            style={{ color: device.statusTextColor }}
          >
            {device.statusLabel}
          </span>
        </div>
      </div>


      {/* Row 3: Device name */}
      <h4 className="text-[14px] font-bold text-[#13082a] dark:text-white mb-1.5 tracking-tight leading-snug">
        {device.name}
      </h4>

      {/* Row 4: Battery + Last synced */}
      <div className="flex items-center gap-2.5 text-[11px] text-slate-400 font-medium mb-4">
        {device.battery && (
          <span className="flex items-center gap-1">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="6" width="18" height="12" rx="2" /><line x1="23" y1="13" x2="23" y2="11" /></svg>
            {device.battery}
          </span>
        )}
        {device.lastSynced && (
          <span className="flex items-center gap-1">
            <RotateCw size={11} />
            {device.lastSynced}
          </span>
        )}
      </div>

      {/* Row 5: Action button + Settings gear */}
      <div className="flex items-center gap-2 mt-auto">
        <button
          className={`flex-1 py-2.5 rounded-lg text-[12px] font-semibold transition-all ${
            device.actionVariant === 'solidBlue'
              ? 'bg-[#0ea5a8] text-white hover:bg-[#0d9496]'
              : 'bg-[#e8f4f8] text-[#0ea5a8] hover:bg-[#d5eef3]'
          }`}
        >
          {device.actionLabel}
        </button>
        <button
          className="w-10 h-10 rounded-lg border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-400 hover:text-[#6143f4] hover:border-[#6143f4]/30 transition-all shrink-0"
          title="Device Settings"
        >
          <Settings size={16} />
        </button>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   DeviceGrid — 2×2 symmetric grid of DeviceCards
   ═══════════════════════════════════════════════════════════════ */
function DeviceGrid({ devices }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {devices.map((device, i) => (
        <DeviceCard key={i} device={device} />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   SyncPanel — Right-side Sync Health panel
   ═══════════════════════════════════════════════════════════════ */
function SyncPanel() {
  const integrations = [
    { name: 'Apple Health', emoji: '🍎', status: 'Enabled', statusColor: '#6143f4', statusBg: 'rgba(97,67,244,0.08)' },
    { name: 'Google Fit', emoji: '💚', status: 'ACTIVE', statusColor: '#22c55e', statusBg: 'rgba(34,197,94,0.08)' },
    { name: 'Dexcom CGM', emoji: '🔵', status: 'ACTIVE', statusColor: '#22c55e', statusBg: 'rgba(34,197,94,0.08)' },
  ];

  const circumference = 2 * Math.PI * 52;

  return (
    <div className="bg-white dark:bg-[#131022] rounded-xl p-6 border border-slate-200/60 dark:border-white/5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-[15px] font-bold text-[#13082a] dark:text-white tracking-tight">
          Sync Health
        </h3>
        <div className="w-6 h-6 rounded-full bg-[#22c55e] flex items-center justify-center">
          <CheckCircle2 size={14} className="text-white" />
        </div>
      </div>

      {/* Circular progress — 94% */}
      <div className="flex justify-center mb-4">
        <div className="relative w-[130px] h-[130px]">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
            {/* Background track */}
            <circle
              cx="60" cy="60" r="52"
              fill="none"
              stroke="#f0eff4"
              strokeWidth="10"
            />
            {/* Progress arc */}
            <circle
              cx="60" cy="60" r="52"
              fill="none"
              stroke="#6143f4"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${circumference * 0.94} ${circumference * 0.06}`}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[28px] font-black text-[#6143f4] leading-none">94%</span>
            <span className="text-[8px] uppercase tracking-[0.15em] text-slate-400 font-bold mt-1">
              Optimized
            </span>
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-[11px] text-slate-400 text-center leading-relaxed mb-5 px-2">
        Your health data is synchronized across 12 different metrics with high fidelity.
      </p>

      {/* Integrations list */}
      <div className="space-y-3 border-t border-slate-100 dark:border-white/5 pt-4">
        {integrations.map((item) => (
          <div key={item.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="text-[14px]">{item.emoji}</span>
              <span className="text-[12px] font-semibold text-[#13082a] dark:text-white">
                {item.name}
              </span>
            </div>
            <span
              className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md"
              style={{ color: item.statusColor, backgroundColor: item.statusBg }}
            >
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   TroubleshootingSection — Two cards side-by-side
   ═══════════════════════════════════════════════════════════════ */
function TroubleshootingSection() {
  const issues = [
    {
      icon: <RotateCw size={18} className="text-amber-500" />,
      iconBg: 'rgba(245,158,11,0.1)',
      dotColor: '#f59e0b',
      title: 'Firmware Update Available',
      desc: 'Oura Ring Gen 3 (v2.4.1) includes stability improvements.',
      action: 'Update Now',
      actionColor: '#f59e0b',
    },
    {
      icon: <Wifi size={18} className="text-blue-500" />,
      iconBg: 'rgba(59,130,246,0.1)',
      dotColor: '#3b82f6',
      title: 'Connection Alert',
      desc: 'Withings Scale signal strength is low. Move closer to router.',
      action: 'Run Diagnostics',
      actionColor: '#6143f4',
    },
  ];

  return (
    <div className="bg-white dark:bg-[#131022] rounded-xl p-6 border border-slate-200/60 dark:border-white/5">
      <h3 className="text-[15px] font-bold text-[#13082a] dark:text-white tracking-tight mb-4">
        Troubleshooting & Updates
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {issues.map((issue, i) => (
          <div
            key={i}
            className="flex gap-3 p-4 rounded-xl bg-slate-50/80 dark:bg-white/[0.03] border border-slate-100 dark:border-white/5"
          >
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
              style={{ backgroundColor: issue.iconBg }}
            >
              {issue.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ backgroundColor: issue.dotColor }}
                />
                <p className="text-[12px] font-bold text-[#13082a] dark:text-white leading-tight">
                  {issue.title}
                </p>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                {issue.desc}
              </p>
              <button
                className="text-[11px] font-bold hover:underline underline-offset-4 transition-colors"
                style={{ color: issue.actionColor }}
              >
                {issue.action}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PremiumCareCard — Dark themed CTA card
   ═══════════════════════════════════════════════════════════════ */
function PremiumCareCard() {
  return (
    <div className="bg-[#13082a] dark:bg-[#1a1035] rounded-xl p-6 text-white relative overflow-hidden">
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-[#6143f4] rounded-full blur-[60px] opacity-30" />
      <h3 className="text-[16px] font-bold mb-2 relative z-10">Premium Care</h3>
      <p className="text-[11px] text-slate-300 leading-relaxed mb-5 relative z-10">
        Automated device monitoring and priority troubleshooting is active for your account.
      </p>
      <button className="w-full py-2.5 bg-[#6143f4] hover:bg-[#5235dc] text-white text-[12px] font-bold rounded-lg transition-colors relative z-10">
        Manage Service Plan
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   DeviceManagement — Main Page
   ═══════════════════════════════════════════════════════════════ */
const DeviceManagement = () => {
  const navigate = useNavigate();

  const devices = [
    {
      name: 'Google Pixel Watch 3',
      iconElement: <Watch size={22} className="text-[#6143f4]" />,
      iconBg: 'rgba(97,67,244,0.08)',
      statusLabel: 'Connected',
      statusDotColor: '#22c55e',
      statusTextColor: '#22c55e',
      battery: '95%',
      lastSynced: 'Last synced 5m ago',
      actionLabel: 'Sync Now',
      actionVariant: 'lightBlue',
    },
    {
      name: 'Oura Ring Gen 3',
      iconElement: <Circle size={22} className="text-[#6143f4]" />,
      iconBg: 'rgba(97,67,244,0.08)',
      statusLabel: 'Syncing',
      statusDotColor: '#3b82f6',
      statusTextColor: '#3b82f6',
      battery: '22%',
      lastSynced: 'Syncing data...',
      actionLabel: 'Sync Now',
      actionVariant: 'lightBlue',
    },
    {
      name: 'Withings Body Scan',
      iconElement: <Monitor size={22} className="text-slate-500" />,
      iconBg: 'rgba(100,116,139,0.08)',
      statusLabel: 'Connected',
      statusDotColor: '#22c55e',
      statusTextColor: '#22c55e',
      battery: '62%',
      lastSynced: 'Last synced 2h ago',
      actionLabel: 'Sync Now',
      actionVariant: 'lightBlue',
    },
    {
      name: 'Google Fit',
      iconElement: <Activity size={22} className="text-[#22c55e]" />,
      iconBg: 'rgba(34,197,94,0.08)',
      statusLabel: 'Connected',
      statusDotColor: '#22c55e',
      statusTextColor: '#22c55e',
      battery: '100% Battery',
      lastSynced: 'Last synced 12m ago',
      actionLabel: 'Sync Now',
      actionVariant: 'lightBlue',
    },
  ];

  return (
    <>
      {/* ── Top Header Bar ────────────────────────────────────── */}
      <header className="h-[64px] bg-white/90 dark:bg-[#0B0819]/70 backdrop-blur-xl border-b border-slate-100 dark:border-white/5 flex items-center justify-between px-8 sticky top-0 z-20">
        {/* Search */}
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              className="w-full h-10 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg pl-9 pr-4 text-[13px] font-medium placeholder:text-slate-400 outline-none focus:ring-2 focus:ring-[#6143f4]/20 focus:border-[#6143f4]/30 transition-all dark:text-white"
              placeholder="Search medical data, devices, or insights..."
              type="text"
            />
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-3">
          <button className="h-9 bg-[#6143f4] text-white px-4 rounded-lg font-bold text-[11px] flex items-center gap-1.5 hover:bg-[#5235dc] shadow-md shadow-[#6143f4]/20 transition-all active:scale-95">
            <Plus size={14} strokeWidth={2.5} />
            Quick Action
          </button>
          <button className="w-9 h-9 flex items-center justify-center rounded-lg bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-400 hover:text-[#6143f4] transition-all relative">
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-[1.5px] border-white dark:border-[#0B0819]" />
          </button>
          <div className="h-5 w-px bg-slate-200 dark:bg-white/10 mx-0.5" />
          <div
            className="flex items-center gap-2.5 cursor-pointer group"
            onClick={() => navigate(ROUTES.SETTINGS_PROFILE)}
          >
            <div className="text-right">
              <p className="text-[12px] font-bold text-[#13082a] dark:text-white leading-tight group-hover:text-[#6143f4] transition-colors">
                Alex Rivera
              </p>
              <p className="text-[8px] text-[#6143f4] uppercase font-bold tracking-wider mt-0.5 opacity-80">
                Premium User
              </p>
            </div>
            <div className="w-9 h-9 rounded-lg bg-[#6143f4]/10 overflow-hidden border-2 border-transparent group-hover:border-[#6143f4] transition-all">
              <img
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBPXRQiJMy2AjUx1s7i8PF4VDCzzfdMwtRfXLHjRrgzSIQ81oYqk6GcXc_Tm6Ib463MN9qj5KL1eXMwKaIUQqZyLXkCGGM0RK7qH6_iMVzNLpTGdw_hpYS5eDo18scXpzHZLuA8PvMMwFaC9CelQUkXVlVugIOSU1LjxQxNnTgdaAoSC7uRYkemunPnF3SOoLmjXYVC4OpM1LtTBr1anc-24LOv7M9ZO_rUwQce_duaAsBqEKaY9ovz3riujUqxQDIK68cUxpyCDQox"
                alt="Alex Rivera"
              />
            </div>
          </div>
        </div>
      </header>

      {/* ── Page Content ──────────────────────────────────────── */}
      <div className="p-8 max-w-[1440px] mx-auto w-full pb-16">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-7">
          <div>
            <h2 className="text-[28px] font-black tracking-tight text-[#13082a] dark:text-white mb-1.5 leading-tight">
              Device Manager
            </h2>
            <p className="text-slate-400 text-[13px] font-medium">
              Manage and sync your connected wearable devices and health sensors.
            </p>
          </div>
          <button className="h-10 px-5 bg-[#6143f4] text-white rounded-lg text-[12px] font-bold flex items-center gap-2 hover:bg-[#5235dc] shadow-md shadow-[#6143f4]/20 transition-all active:scale-95 shrink-0">
            <Plus size={15} strokeWidth={2.5} />
            Add New Device
          </button>
        </div>

        {/* Main grid: content left (2/3) + sync panel right (1/3) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Connected Devices section header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <h3 className="text-[14px] font-bold text-[#13082a] dark:text-white">
                  Connected Devices
                </h3>
                <span className="text-[10px] font-bold text-[#6143f4] bg-[#6143f4]/[0.06] px-2 py-0.5 rounded-md border border-[#6143f4]/10">
                  4 Active
                </span>
              </div>
              <button className="text-[12px] font-semibold text-[#6143f4] hover:underline underline-offset-4 flex items-center gap-0.5">
                View History
                <ChevronRight size={14} />
              </button>
            </div>

            {/* 2×2 Device Grid */}
            <DeviceGrid devices={devices} />

            {/* Troubleshooting & Updates */}
            <TroubleshootingSection />
          </div>

          {/* Right column */}
          <div className="space-y-5">
            <SyncPanel />
            <PremiumCareCard />
          </div>
        </div>
      </div>
    </>
  );
};

export default DeviceManagement;
