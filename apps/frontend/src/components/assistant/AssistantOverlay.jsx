import { motion } from 'framer-motion';
import { Bot, ChevronDown } from 'lucide-react';
import Chatbot from '../Chatbot';

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
                  <span className="text-white/60">Clinical reasoning with ML + RAG</span>
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

          <Chatbot />
        </motion.aside>
      </div>
    </motion.div>
  );
};

export default AssistantOverlay;
