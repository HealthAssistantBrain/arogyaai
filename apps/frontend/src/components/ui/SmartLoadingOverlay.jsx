const SmartLoadingOverlay = ({ label = 'Refreshing data...', className = '' }) => (
  <div className={`pointer-events-none absolute inset-0 z-20 overflow-hidden ${className}`}>
    <div className="absolute inset-0 bg-white/45 backdrop-blur-[2px] dark:bg-slate-950/30" />
    <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-white/10 via-white/40 to-white/10 dark:from-white/5 dark:via-white/10 dark:to-white/5" />
    <div className="absolute right-4 top-4 rounded-full border border-white/60 bg-white/85 px-4 py-2 text-[10px] font-black uppercase tracking-[0.24em] text-slate-500 shadow-lg dark:border-white/10 dark:bg-slate-900/85 dark:text-slate-300">
      {label}
    </div>
  </div>
);

export default SmartLoadingOverlay;
