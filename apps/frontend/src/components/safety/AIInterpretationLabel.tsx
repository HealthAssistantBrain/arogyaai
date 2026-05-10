export function AIInterpretationLabel({ visible = true }: { visible?: boolean }) {
  if (!visible) return null;

  return (
    <div className="mb-2 inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-sky-600/70 dark:text-sky-300/70">
      <span className="size-1.5 rounded-full bg-sky-500/70" />
      AI Interpretation · Not a clinical diagnosis
    </div>
  );
}
