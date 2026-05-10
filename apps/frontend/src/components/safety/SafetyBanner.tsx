import type { SafetyState } from './SafetyContext';

const BANNER_CONFIG: Record<
  SafetyState['riskLevel'],
  { bg: string; border: string; icon: string; label: string; text: string } | null
> = {
  emergency: {
    bg: 'bg-red-600',
    border: 'border-red-800',
    icon: '🚨',
    label: 'Emergency',
    text: 'text-white',
  },
  urgent: {
    bg: 'bg-orange-500',
    border: 'border-orange-700',
    icon: '⚠️',
    label: 'Medical Attention Recommended',
    text: 'text-white',
  },
  elevated: {
    bg: 'bg-amber-50',
    border: 'border-amber-300',
    icon: '💡',
    label: 'Important Context',
    text: 'text-amber-950',
  },
  caution: null,
  safe: null,
};

export function SafetyBanner({ safety }: { safety: SafetyState | null | undefined }) {
  const config = safety ? BANNER_CONFIG[safety.riskLevel] : null;
  if (!config) return null;

  return (
    <div
      className={`mb-3 flex items-start gap-3 rounded-xl border px-4 py-3 ${config.bg} ${config.border} ${config.text}`}
      role="alert"
      aria-live="assertive"
    >
      <span className="mt-0.5 text-lg">{config.icon}</span>
      <div className="space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em]">{config.label}</p>
        {safety?.escalationMessage ? <p className="text-sm leading-relaxed">{safety.escalationMessage}</p> : null}
      </div>
    </div>
  );
}
