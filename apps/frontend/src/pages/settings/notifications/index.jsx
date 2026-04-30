import { useEffect, useMemo, useRef } from 'react';
import { AlertTriangle, Bell, Check, LoaderCircle, Mail, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';

import useNotificationPreferencesStore from '../../../store/notificationPreferencesStore';
import { ensurePushSubscription, removeCurrentPushSubscription } from '../../../services/pushSubscriptionService';

const PREFERENCE_LABELS = {
  email_enabled: 'Email notifications',
  push_enabled: 'Push notifications',
  ai_insights_email: 'AI insights email',
  ai_insights_push: 'AI insights push',
  health_alerts_email: 'Health alerts email',
  health_alerts_push: 'Health alerts push',
  reminders_email: 'Reminders email',
  reminders_push: 'Reminders push',
};

const SECTIONS = [
  {
    id: 'ai_insights',
    title: 'AI Insights',
    description: 'Updates when new model-driven analysis, risk explanations, and recommendation bundles are ready.',
    icon: Sparkles,
    color: 'text-[#6143f4]',
    bgColor: 'bg-[#6143f4]/10',
    emailKey: 'ai_insights_email',
    pushKey: 'ai_insights_push',
  },
  {
    id: 'health_alerts',
    title: 'Health Alerts',
    description: 'Critical notifications tied to abnormal vitals, elevated risk states, and abnormal lab detections.',
    icon: AlertTriangle,
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    emailKey: 'health_alerts_email',
    pushKey: 'health_alerts_push',
  },
  {
    id: 'reminders',
    title: 'Reminders',
    description: 'Appointment-style reminders and scheduled nudges routed through the same delivery pipeline.',
    icon: Bell,
    color: 'text-[#009cde]',
    bgColor: 'bg-[#009cde]/10',
    emailKey: 'reminders_email',
    pushKey: 'reminders_push',
  },
];

function Toggle({ active, pending, onClick, color = 'bg-[#6143f4]' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative inline-flex h-8 w-14 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 ${active ? color : 'bg-slate-200 dark:bg-slate-700'}`}
    >
      {pending ? (
        <span className="absolute inset-0 flex items-center justify-center">
          <LoaderCircle size={14} className="animate-spin text-white" />
        </span>
      ) : null}
      <span
        style={{ transform: active ? 'translateX(24px)' : 'translateX(0)' }}
        className="pointer-events-none inline-block h-6 w-6 rounded-full bg-white shadow-lg ring-0 mt-0.5 ml-0.5 transition-transform duration-200 ease-in-out"
      />
    </button>
  );
}

function ChannelCheckbox({ checked, pending, label, onClick }) {
  return (
    <button type="button" onClick={onClick} className="flex items-center gap-4">
      <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">{label}</span>
      <div className={`flex size-6 items-center justify-center rounded-lg border-2 transition-all ${checked ? 'border-[#6143f4] bg-[#6143f4] text-white' : 'border-slate-200 dark:border-white/10'}`}>
        {pending ? <LoaderCircle size={13} className="animate-spin" /> : checked ? <Check size={14} strokeWidth={4} /> : null}
      </div>
    </button>
  );
}

const SettingsNotifications = () => {
  const {
    preferences,
    pendingKeys,
    isLoading,
    error,
    fetchPreferences,
    applyOptimisticPreferences,
    restoreServerPreferences,
    commitPreferences,
  } = useNotificationPreferencesStore();

  const debounceTimerRef = useRef(null);
  const latestVersionRef = useRef(0);
  const isSavingRef = useRef(false);
  const latestSnapshotRef = useRef(preferences);
  const latestKeysRef = useRef([]);

  useEffect(() => {
    latestSnapshotRef.current = preferences;
  }, [preferences]);

  useEffect(() => {
    void fetchPreferences().catch(() => {});
  }, [fetchPreferences]);

  useEffect(() => () => {
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }
  }, []);

  const statusSummary = useMemo(() => {
    const enabledChannels = [];
    if (preferences.email_enabled) enabledChannels.push('email');
    if (preferences.push_enabled) enabledChannels.push('push');
    return enabledChannels.length > 0 ? enabledChannels.join(' + ') : 'delivery paused';
  }, [preferences.email_enabled, preferences.push_enabled]);

  const flushLatestPreferences = async () => {
    if (isSavingRef.current) {
      return;
    }

    const version = latestVersionRef.current;
    const snapshot = latestSnapshotRef.current;
    const changedKeys = [...new Set(latestKeysRef.current)];
    isSavingRef.current = true;

    try {
      await commitPreferences(snapshot, changedKeys);
      if (changedKeys.length === 1) {
        toast.success(`${PREFERENCE_LABELS[changedKeys[0]]} updated.`);
      } else {
        toast.success('Notification preferences saved.');
      }
      latestKeysRef.current = [];
    } catch (saveError) {
      toast.error(saveError?.response?.data?.error || saveError?.message || 'Unable to save notification preferences.');
    } finally {
      isSavingRef.current = false;
      if (latestVersionRef.current !== version) {
        void flushLatestPreferences();
      }
    }
  };

  const queueSave = (nextPreferences, changedKeys) => {
    latestVersionRef.current += 1;
    latestSnapshotRef.current = nextPreferences;
    latestKeysRef.current = [...new Set([...latestKeysRef.current, ...changedKeys])];

    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = window.setTimeout(() => {
      void flushLatestPreferences();
    }, 300);
  };

  const handleToggle = async (key) => {
    const currentPreferences = useNotificationPreferencesStore.getState().preferences;
    const nextValue = !currentPreferences[key];
    const nextPreferences = { ...currentPreferences, [key]: nextValue };
    applyOptimisticPreferences({ [key]: nextValue }, [key]);

    if (key === 'push_enabled') {
      try {
        if (nextValue) {
          await ensurePushSubscription();
        } else {
          await removeCurrentPushSubscription().catch(() => false);
        }
      } catch (pushError) {
        restoreServerPreferences([key]);
        toast.error(pushError?.message || 'Unable to configure push notifications.');
        return;
      }
    }

    queueSave(nextPreferences, [key]);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-12 pb-16">
      <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
        <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Notification Settings</h2>
        <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug">
          Control how ArogyaAI delivers real alerts, AI insight summaries, and reminder traffic across email and browser push.
        </p>
      </div>

      {error ? (
        <div className="rounded-[2rem] border border-red-500/15 bg-red-500/10 px-6 py-5 text-sm font-bold uppercase tracking-tight text-red-500">
          {error}
        </div>
      ) : null}

      <section className="space-y-8">
        <div className="flex items-center gap-4">
          <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
          <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Global Delivery Channels</h3>
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <div className="flex items-center justify-between rounded-[3rem] border border-slate-100 bg-white/80 p-8 shadow-sm transition-all duration-500 hover:border-[#6143f4]/20 dark:border-white/5 dark:bg-[#131022]/80">
            <div className="flex items-center gap-6">
              <div className="flex size-16 items-center justify-center rounded-2xl bg-[#6143f4]/10 text-[#6143f4] shadow-inner">
                <Mail size={30} />
              </div>
              <div>
                <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">Email Alerts</p>
                <p className="mt-2 text-[10px] font-black uppercase tracking-widest text-slate-400">SMTP or SendGrid backed delivery</p>
              </div>
            </div>
            <Toggle
              active={preferences.email_enabled}
              pending={Boolean(pendingKeys.email_enabled)}
              onClick={() => void handleToggle('email_enabled')}
            />
          </div>

          <div className="flex items-center justify-between rounded-[3rem] border border-slate-100 bg-white/80 p-8 shadow-sm transition-all duration-500 hover:border-[#009cde]/20 dark:border-white/5 dark:bg-[#131022]/80">
            <div className="flex items-center gap-6">
              <div className="flex size-16 items-center justify-center rounded-2xl bg-[#009cde]/10 text-[#009cde] shadow-inner">
                <Bell size={30} />
              </div>
              <div>
                <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">Push Notifications</p>
                <p className="mt-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Service worker + backend web push</p>
              </div>
            </div>
            <Toggle
              active={preferences.push_enabled}
              pending={Boolean(pendingKeys.push_enabled)}
              onClick={() => void handleToggle('push_enabled')}
              color="bg-[#009cde]"
            />
          </div>
        </div>
      </section>

      <section className="space-y-8">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="size-1.5 bg-[#009cde] rounded-full"></div>
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Event-Level Delivery Matrix</h3>
          </div>
          <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">Active: {statusSummary}</p>
        </div>

        <div className="overflow-hidden rounded-[3.5rem] border border-[#6143f4]/5 bg-white shadow-[0_40px_80px_-20px_rgba(19,8,42,0.05)] dark:bg-[#131022]">
          <div className="divide-y divide-slate-100 dark:divide-white/5">
            {SECTIONS.map((section) => {
              const SectionIcon = section.icon;

              return (
                <div key={section.id} className="flex flex-col gap-8 p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10">
                  <div className="flex items-start gap-6">
                    <div className={`flex size-16 items-center justify-center rounded-2xl ${section.bgColor} ${section.color}`}>
                      <SectionIcon size={30} />
                    </div>
                    <div className="max-w-2xl space-y-2">
                      <p className="text-2xl font-black uppercase tracking-tighter italic leading-none text-[#13082a] dark:text-white">{section.title}</p>
                      <p className="text-sm font-bold uppercase tracking-tight text-slate-500 dark:text-slate-400 opacity-75">{section.description}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-8">
                    <ChannelCheckbox
                      checked={preferences[section.emailKey]}
                      pending={Boolean(pendingKeys[section.emailKey])}
                      label="Email"
                      onClick={() => void handleToggle(section.emailKey)}
                    />
                    <ChannelCheckbox
                      checked={preferences[section.pushKey]}
                      pending={Boolean(pendingKeys[section.pushKey])}
                      label="Push"
                      onClick={() => void handleToggle(section.pushKey)}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {isLoading ? (
        <div className="flex items-center gap-4 rounded-[2rem] border border-[#6143f4]/10 bg-white/70 px-6 py-5 dark:border-white/5 dark:bg-[#131022]/70">
          <LoaderCircle size={18} className="animate-spin text-[#6143f4]" />
          <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Loading notification preferences</span>
        </div>
      ) : null}
    </div>
  );
};

export default SettingsNotifications;
