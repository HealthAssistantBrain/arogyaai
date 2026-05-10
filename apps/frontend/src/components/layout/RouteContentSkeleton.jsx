export default function RouteContentSkeleton({ label = 'Loading workspace…' }) {
  return (
    <div className="min-h-[calc(100vh-5rem)] bg-background dark:bg-background px-6 py-8 sm:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-3">
            <div className="h-3 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-white/10" />
            <div className="h-10 w-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-white/10" />
          </div>
          <div className="hidden h-10 w-36 animate-pulse rounded-2xl bg-slate-200 dark:bg-white/10 sm:block" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
          <div className="space-y-6">
            <div className="h-64 animate-pulse rounded-[2rem] bg-white/75 shadow-sm dark:bg-white/[0.04]" />
            <div className="grid gap-6 md:grid-cols-2">
              <div className="h-56 animate-pulse rounded-[2rem] bg-white/75 shadow-sm dark:bg-white/[0.04]" />
              <div className="h-56 animate-pulse rounded-[2rem] bg-white/75 shadow-sm dark:bg-white/[0.04]" />
            </div>
          </div>
          <div className="h-[30rem] animate-pulse rounded-[2rem] bg-white/75 shadow-sm dark:bg-white/[0.04]" />
        </div>
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-text-muted dark:text-slate-500">
          {label}
        </p>
      </div>
    </div>
  );
}
