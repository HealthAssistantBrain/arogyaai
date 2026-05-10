import type { SafetyState } from './SafetyContext';

export function EscalationNotice({ safety }: { safety: SafetyState | null | undefined }) {
  if (!safety?.escalationRequired || !safety.escalationMessage) return null;

  return (
    <div className="mt-4 flex items-start gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sky-900 dark:border-sky-400/30 dark:bg-sky-500/10 dark:text-sky-100">
      <span className="text-lg">⚕️</span>
      <div>
        <p className="mb-0.5 text-sm font-semibold">Clinical Evaluation Recommended</p>
        <p className="text-sm leading-relaxed">{safety.escalationMessage}</p>
      </div>
    </div>
  );
}
