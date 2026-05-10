import type { SafetyState } from './SafetyContext';

function getConfidenceLabel(score: number): { label: string; color: string; bar: string } {
  if (score >= 0.8) return { label: 'High confidence', color: 'text-emerald-600', bar: 'bg-emerald-500' };
  if (score >= 0.55) return { label: 'Moderate confidence', color: 'text-amber-600', bar: 'bg-amber-400' };
  if (score >= 0.35) return { label: 'Low confidence', color: 'text-orange-500', bar: 'bg-orange-400' };
  return { label: 'Very low confidence', color: 'text-red-500', bar: 'bg-red-500' };
}

export function ConfidenceIndicator({ safety }: { safety: SafetyState | null | undefined }) {
  if (!safety) return null;
  if (safety.riskLevel === 'safe' && safety.confidenceScore >= 0.8) return null;

  const pct = Math.max(0, Math.min(100, Math.round((safety.confidenceScore || 0) * 100)));
  const meta = getConfidenceLabel(safety.confidenceScore || 0);

  return (
    <div className="mt-2 flex items-center gap-2 text-xs text-slate-500 dark:text-text-secondary">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
        <div className={`h-full rounded-full transition-all duration-500 ${meta.bar}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`font-medium ${meta.color}`}>{meta.label}</span>
      {safety.confidenceReason ? (
        <span className="cursor-help underline decoration-dotted" title={safety.confidenceReason}>
          ⓘ
        </span>
      ) : null}
    </div>
  );
}
