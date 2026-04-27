import { motion } from 'framer-motion';
import {
  Bot,
  ChevronDown,
  HeartPulse,
  Mic,
  Send,
  ShieldAlert,
  Sparkles,
  User,
} from 'lucide-react';

const promptChips = [
  'Explain my health score',
  'Recent lab results',
];

const preventativeSuggestions = [
  'Avoid blue light exposure 90 minutes before bed.',
  'Maintain a consistent cooling temperature (65-68°F).',
  'Consider a magnesium supplement post-consultation.',
];

const AssistantOverlay = ({ onClose }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className="absolute inset-x-0 top-0 bottom-20 z-[900] pointer-events-none lg:bottom-0"
      aria-hidden={false}
    >
      <div className="absolute inset-0 bg-slate-950/10 backdrop-blur-[4px] dark:bg-slate-950/25" />

      <div className="relative flex h-full w-full items-stretch justify-end p-3 sm:p-4 lg:p-6">
        <div className="hidden 2xl:flex flex-1 items-end pr-6">
          <div className="w-full max-w-4xl rounded-[2rem] border border-white/20 bg-white/15 p-6 shadow-2xl shadow-[#6143f4]/10 backdrop-blur-2xl dark:border-white/10 dark:bg-white/5">
            <div className="space-y-4 opacity-50">
              <div className="h-3 w-32 rounded-full bg-white/60" />
              <div className="grid grid-cols-3 gap-4">
                <div className="h-40 rounded-[1.5rem] bg-white/30" />
                <div className="h-40 rounded-[1.5rem] bg-white/25" />
                <div className="h-40 rounded-[1.5rem] bg-white/20" />
              </div>
              <div className="h-56 rounded-[1.75rem] bg-white/20" />
            </div>
          </div>
        </div>

        <motion.aside
          initial={{ x: 28, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 28, opacity: 0 }}
          transition={{ duration: 0.26, ease: 'easeOut' }}
          className="pointer-events-auto flex h-full w-full max-w-[36rem] flex-col overflow-hidden rounded-[2rem] border border-white/20 bg-white/90 shadow-[0_28px_80px_rgba(19,8,42,0.22)] backdrop-blur-xl dark:border-white/10 dark:bg-[#13082A]/95"
        >
          <header className="flex items-center justify-between gap-4 bg-gradient-to-r from-[#6143f4] to-[#009CDE] p-4 text-white">
            <div className="flex min-w-0 items-center gap-3">
              <div className="relative">
                <div className="flex size-11 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
                  <Bot size={20} strokeWidth={2.5} />
                </div>
                <span className="absolute bottom-0 right-0 size-3 rounded-full border-2 border-[#6143f4] bg-emerald-400" />
              </div>

              <div className="min-w-0">
                <h3 className="text-lg font-bold leading-tight">ArogyaAI Assistant</h3>
                <div className="mt-1 flex items-center gap-2 text-[11px] font-medium text-white/90">
                  <span className="size-2 rounded-full bg-emerald-300 shadow-[0_0_0_6px_rgba(110,231,183,0.15)]" />
                  <span>Online</span>
                  <span className="text-white/60">Ask about your health insights</span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-white transition-colors hover:bg-white/10"
              aria-label="Minimize assistant"
            >
              <ChevronDown size={20} strokeWidth={2.5} />
            </button>
          </header>

          <div className="flex-1 overflow-y-auto bg-[#F7F7FB] p-4 dark:bg-[#0f0b20]">
            <div className="space-y-5">
              <section className="mb-2 space-y-3 text-center">
                <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-[#6143f4]/10 text-[#6143f4] dark:bg-[#6143f4]/20">
                  <HeartPulse size={20} strokeWidth={2.5} />
                </div>
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  Hello! I&apos;m your ArogyaAI Assistant. How can I help you understand your health data today?
                </p>
                <div className="flex flex-wrap justify-center gap-2 pt-1">
                  {promptChips.map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-[0.18em] text-slate-700 transition-colors hover:bg-slate-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </section>

              <div className="flex justify-end">
                <div className="flex max-w-[85%] flex-row-reverse gap-2">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[#009CDE]/15 text-[#009CDE]">
                    <User size={15} strokeWidth={2.5} />
                  </div>
                  <div className="rounded-2xl rounded-tr-none bg-[#6143f4] px-3 py-3 text-sm text-white shadow-sm">
                    What does my recent sleep analysis indicate?
                  </div>
                </div>
              </div>

              <div className="flex justify-start">
                <div className="flex max-w-[90%] gap-2">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-[#6143f4]/20 bg-white text-[#6143f4] shadow-sm dark:bg-white/5 dark:text-[#b9abff]">
                    <Sparkles size={14} strokeWidth={2.5} />
                  </div>
                  <div className="space-y-3">
                    <div className="rounded-2xl rounded-tl-none border border-slate-200 bg-white p-3 text-sm text-slate-700 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-200">
                      Based on your latest biometric sync, your sleep architecture shows significant fragmentation. Let&apos;s look at the specific insight.
                    </div>

                    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#13082A]">
                      <div className="flex items-center justify-between border-b border-slate-200 bg-rose-50 px-3 py-2 dark:border-white/10 dark:bg-rose-950/30">
                        <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.22em] text-rose-700 dark:text-rose-200">
                          <ShieldAlert size={14} />
                          Risk Insight
                        </span>
                        <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.18em] text-rose-700 dark:text-rose-200">
                          Elevated
                        </span>
                      </div>

                      <div className="p-3">
                        <h4 className="mb-1 text-sm font-bold text-[#13082A] dark:text-white">
                          REM Sleep Deficiency
                        </h4>
                        <p className="mb-3 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                          Your REM cycles are 24% below the optimal zone for the past 72 hours, potentially impacting cognitive recovery.
                        </p>

                        <div className="rounded-xl bg-slate-50 p-2.5 dark:bg-white/5">
                          <h5 className="mb-2 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
                            Preventative Suggestions
                          </h5>
                          <ul className="space-y-1.5 pl-4 text-xs leading-relaxed text-slate-700 marker:text-[#6143f4] dark:text-slate-200">
                            {preventativeSuggestions.map((item) => (
                              <li key={item} className="list-disc">
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <footer className="border-t border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-[#13082A]">
            <div className="relative flex items-center">
              <input
                type="text"
                placeholder="Ask about your health, reports, or predictions..."
                className="w-full rounded-xl border-0 bg-slate-100 py-3 pl-4 pr-24 text-sm text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-2 focus:ring-[#6143f4] dark:bg-white/5 dark:text-white dark:placeholder:text-slate-500 dark:focus:bg-white/10"
              />
              <div className="absolute right-2 flex items-center gap-1">
                <button
                  type="button"
                  aria-label="Voice input"
                  className="rounded-full p-2 text-slate-500 transition-colors hover:text-[#6143f4] dark:text-slate-400"
                >
                  <Mic size={18} strokeWidth={2.2} />
                </button>
                <button
                  type="button"
                  aria-label="Send message"
                  className="rounded-full p-2 text-[#6143f4] transition-colors hover:bg-[#6143f4]/10"
                >
                  <Send size={18} strokeWidth={2.3} />
                </button>
              </div>
            </div>
          </footer>
        </motion.aside>
      </div>
    </motion.div>
  );
};

export default AssistantOverlay;
