import { useState } from 'react';
import {
    Bell, Check, Mail, Sparkles, AlertTriangle, Calendar, Clock, CheckCircle2
} from 'lucide-react';

const SettingsNotifications = () => {
    // State for Global Channels
    const [globalChannels, setGlobalChannels] = useState({
        email: true,
        push: true,
    });

    // State for Category Preferences
    const [preferences, setPreferences] = useState([
        {
            id: 'ai_insights',
            title: 'AI Insights',
            description: 'Receive alerts when AI detects new health patterns or potential anomalies in your data.',
            icon: Sparkles,
            color: 'text-indigo-500',
            bgColor: 'bg-indigo-50',
            email: true,
            push: true,
        },
        {
            id: 'health_alerts',
            title: 'Health Alerts',
            description: 'Critical notifications regarding abnormal lab results or vital sign deviations.',
            icon: AlertTriangle,
            color: 'text-red-500',
            bgColor: 'bg-red-50',
            email: true,
            push: true,
        },
        {
            id: 'appointment_reminders',
            title: 'Appointment Reminders',
            description: 'Notifications about upcoming visits, screenings, and follow-ups.',
            icon: Calendar,
            color: 'text-blue-500',
            bgColor: 'bg-blue-50',
            email: false,
            push: true,
        },
    ]);

    // State for Reminders
    const [reminders, setReminders] = useState({
        medication: true,
        sync: true,
        sleep: false,
    });

    // State for Frequency
    const [frequency, setFrequency] = useState({
        aiDigest: 'Immediate',
        healthReport: 'Weekly',
    });

    const handleGlobalToggle = (channel) => {
        setGlobalChannels((prev) => ({ ...prev, [channel]: !prev[channel] }));
    };

    const handlePreferenceToggle = (id, channel) => {
        setPreferences((prev) =>
            prev.map((pref) =>
                pref.id === id ? { ...pref, [channel]: !pref[channel] } : pref
            )
        );
    };

    const handleReminderToggle = (reminder) => {
        setReminders((prev) => ({ ...prev, [reminder]: !prev[reminder] }));
    };

    const handleFrequencyChange = (category, value) => {
        setFrequency((prev) => ({ ...prev, [category]: value }));
    };

    const Toggle = ({ active, onClick, color = 'bg-[#6143f4]' }) => (
        <button
            onClick={onClick}
            className={`relative inline-flex h-8 w-14 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 ${active ? color : 'bg-slate-200 dark:bg-slate-700'}`}
        >
            <span
                style={{ transform: active ? 'translateX(24px)' : 'translateX(0)' }}
                className="pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow-lg ring-0 mt-0.5 ml-0.5 transition-transform duration-200 ease-in-out"
            />
        </button>
    );

    return (
        <div className="max-w-5xl mx-auto space-y-12 pb-16">

            {/* Page Header */}
            <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
                <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Notification Settings</h2>
                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug">Configure how and when you want to receive updates from ArogyaAI. Customizing these alerts ensures you receive critical health insights without information overload.</p>
            </div>

            {/* Section 1: Global Channels */}
            <section className="space-y-8">
                <div className="flex items-center gap-4">
                    <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Global Broadcast Channels</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="bg-white/80 dark:bg-[#131022]/80 backdrop-blur-xl p-8 rounded-[3rem] flex items-center justify-between shadow-sm border border-slate-100 dark:border-white/5 hover:border-[#6143f4]/20 transition-all duration-500 group">
                        <div className="flex items-center gap-6">
                            <div className="size-16 bg-[#6143f4]/10 rounded-2xl flex items-center justify-center text-[#6143f4] group-hover:scale-110 transition-transform shadow-inner shrink-0">
                                <Mail size={32} />
                            </div>
                            <div>
                                <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white mb-2">Email Alerts</p>
                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none">Weekly reports & summaries</p>
                            </div>
                        </div>
                        <div className="shrink-0"><Toggle active={globalChannels.email} onClick={() => handleGlobalToggle('email')} /></div>
                    </div>
                    <div className="bg-white/80 dark:bg-[#131022]/80 backdrop-blur-xl p-8 rounded-[3rem] flex items-center justify-between shadow-sm border border-slate-100 dark:border-white/5 hover:border-[#009cde]/20 transition-all duration-500 group">
                        <div className="flex items-center gap-6">
                            <div className="size-16 bg-[#009cde]/10 rounded-2xl flex items-center justify-center text-[#009cde] group-hover:scale-110 transition-transform shadow-inner shrink-0">
                                <Bell size={32} />
                            </div>
                            <div>
                                <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white mb-2">Push Notifications</p>
                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none">Real-time web & mobile alerts</p>
                            </div>
                        </div>
                        <div className="shrink-0"><Toggle active={globalChannels.push} onClick={() => handleGlobalToggle('push')} color="bg-[#009cde]" /></div>
                    </div>
                </div>
            </section>

            {/* Section 2: Category Preferences */}
            <section className="space-y-8">
                <div className="flex items-center gap-4">
                    <div className="size-1.5 bg-[#009cde] rounded-full"></div>
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Clinical Intelligence Subscriptions</h3>
                </div>
                <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] border border-[#6143f4]/5 overflow-hidden">
                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                        {preferences.map((item) => {
                            const PrefIcon = item.icon;
                            return (
                                <div key={item.id} className="p-8 sm:p-10 flex flex-col sm:flex-row items-start sm:items-center justify-between hover:bg-[#6143f4]/[0.02] transition-all gap-8 group/row">
                                    <div className="flex items-start gap-6">
                                        <div className={`size-16 ${item.bgColor} dark:bg-white/5 rounded-2xl flex items-center justify-center ${item.color} shrink-0 shadow-inner group-hover/row:scale-110 transition-transform`}>
                                            <PrefIcon size={32} />
                                        </div>
                                        <div className="space-y-2 max-w-xl">
                                            <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">{item.title}</p>
                                            <p className="text-sm text-slate-500 dark:text-slate-400 font-bold leading-snug uppercase tracking-tight opacity-70">{item.description}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-6 sm:gap-12 shrink-0 self-start sm:self-center w-full sm:w-auto">
                                        <div className="flex items-center gap-4 group/box cursor-pointer" onClick={() => handlePreferenceToggle(item.id, 'email')}>
                                            <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Email</span>
                                            <div className={`size-6 rounded-lg border-2 transition-all flex items-center justify-center ${item.email ? 'bg-[#6143f4] border-[#6143f4] text-white' : 'border-slate-200 dark:border-white/10'}`}>
                                                {item.email && <Check size={14} strokeWidth={4} />}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4 group/box cursor-pointer" onClick={() => handlePreferenceToggle(item.id, 'push')}>
                                            <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Push</span>
                                            <div className={`size-6 rounded-lg border-2 transition-all flex items-center justify-center ${item.push ? 'bg-[#6143f4] border-[#6143f4] text-white' : 'border-slate-200 dark:border-white/10'}`}>
                                                {item.push && <Check size={14} strokeWidth={4} />}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Section 3: Frequency & Reminders Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
                {/* Frequency Controls */}
                <section className="space-y-8">
                    <div className="flex items-center gap-4">
                        <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Diagnostic Schedule</h3>
                    </div>
                    <div className="bg-white dark:bg-[#131022] p-8 sm:p-10 rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 space-y-10">
                        <div className="space-y-6">
                            <label className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-slate-400 leading-none">
                                <Clock size={14} className="text-[#6143f4]" /> AI Insights Digest
                            </label>
                            <div className="grid grid-cols-3 gap-3">
                                {['Immediate', 'Daily', 'Weekly'].map((opt) => (
                                    <button
                                        key={opt}
                                        onClick={() => handleFrequencyChange('aiDigest', opt)}
                                        className={`py-4 px-2 sm:px-4 rounded-2xl text-[9px] sm:text-[10px] font-black uppercase tracking-widest transition-all shadow-sm ${frequency.aiDigest === opt
                                                ? 'bg-[#6143f4] text-white shadow-[#6143f4]/30 border-transparent'
                                                : 'bg-slate-50 dark:bg-white/5 text-slate-500 border border-slate-100 dark:border-white/5 hover:bg-slate-100 dark:hover:bg-white/10'
                                            }`}
                                    >
                                        {opt}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="space-y-6">
                            <label className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-slate-400 leading-none">
                                <CheckCircle2 size={14} className="text-[#009cde]" /> Health Performance Reports
                            </label>
                            <div className="grid grid-cols-3 gap-3">
                                {['Daily', 'Weekly', 'Monthly'].map((opt) => (
                                    <button
                                        key={opt}
                                        onClick={() => handleFrequencyChange('healthReport', opt)}
                                        className={`py-4 px-2 sm:px-4 rounded-2xl text-[9px] sm:text-[10px] font-black uppercase tracking-widest transition-all shadow-sm ${frequency.healthReport === opt
                                                ? 'bg-[#6143f4] text-white shadow-[#6143f4]/30 border-transparent'
                                                : 'bg-slate-50 dark:bg-white/5 text-slate-500 border border-slate-100 dark:border-white/5 hover:bg-slate-100 dark:hover:bg-white/10'
                                            }`}
                                    >
                                        {opt}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>

                {/* Reminder Preferences */}
                <section className="space-y-8">
                    <div className="flex items-center gap-4">
                        <div className="size-1.5 bg-[#009cde] rounded-full"></div>
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Adherence Triggers</h3>
                    </div>
                    <div className="bg-white dark:bg-[#131022] p-8 sm:p-10 rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 space-y-6 sm:space-y-8">
                        {[
                            { id: 'medication', title: 'Medication Reminders', desc: 'Adherence prompts via mobile app' },
                            { id: 'sync', title: 'Sync Reminders', desc: "Alert if wearable hasn't synced for 24h" },
                            { id: 'sleep', title: 'Sleep Goal Alerts', desc: 'Gentle reminders to wind down' },
                        ].map((rem, idx, arr) => (
                            <div key={rem.id} className={`flex items-center justify-between pb-6 sm:pb-8 ${idx !== arr.length - 1 ? 'border-b border-slate-100 dark:border-white/5' : ''}`}>
                                <div className="space-y-2 pr-4">
                                    <p className="text-xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">{rem.title}</p>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest opacity-60 leading-none">{rem.desc}</p>
                                </div>
                                <div className="shrink-0"><Toggle active={reminders[rem.id]} onClick={() => handleReminderToggle(rem.id)} /></div>
                            </div>
                        ))}
                    </div>
                </section>
            </div>

            {/* Section 4: Action Footer */}
            <div className="pt-12 flex flex-col sm:flex-row items-center justify-end gap-6 border-t border-[#6143f4]/15">
                <button className="w-full sm:w-auto px-12 py-5 rounded-[1.5rem] border-2 border-slate-200 dark:border-white/10 font-black text-xs uppercase tracking-[0.2em] text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-all shadow-sm leading-none">
                    Discard Changes
                </button>
                <button className="w-full sm:w-auto px-16 py-5 rounded-[1.5rem] bg-[#6143f4] text-white font-black text-xs uppercase tracking-[0.2em] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] hover:bg-[#4a34c1] hover:scale-105 active:scale-95 transition-all leading-none">
                    Save Preferences
                </button>
            </div>
        </div>
    );
};

export default SettingsNotifications;
