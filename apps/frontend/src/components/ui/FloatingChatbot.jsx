import { Bot } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

const FloatingChatbot = () => {
  const isAssistantOpen = useAppStore((s) => s.isAssistantOpen);
  const openAssistant = useAppStore((s) => s.openAssistant);
  const closeAssistant = useAppStore((s) => s.closeAssistant);

  const toggleChat = () => {
    if (isAssistantOpen) {
      closeAssistant();
      return;
    }

    console.log('Open AI Chat');
    openAssistant();
  };

  return (
    <div className="fixed bottom-[6rem] right-4 z-[1000] sm:right-5 md:bottom-6 md:right-6">
      {isAssistantOpen ? null : (
        <div className="group relative">
          <button
            type="button"
            onClick={toggleChat}
            aria-label="Open AI assistant"
            aria-expanded={false}
            className="relative flex size-14 items-center justify-center overflow-hidden rounded-full border border-white/30 bg-gradient-to-br from-[#6143f4] via-[#7a5cf6] to-[#009CDE] text-white shadow-[0_18px_40px_rgba(97,67,244,0.35)] transition-[transform,opacity,box-shadow] duration-300 hover:scale-105 hover:shadow-[0_22px_50px_rgba(97,67,244,0.45)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#009CDE] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
          >
            <span className="absolute inset-0 bg-white/10 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-white/20" />
            <span className="absolute -inset-1 rounded-full bg-white/20 opacity-0 blur-xl transition-opacity duration-500 group-hover:opacity-100" />

            <Bot size={22} strokeWidth={2.4} />

            <span className="absolute -right-0.5 -top-0.5 size-3 rounded-full border-2 border-white bg-emerald-400 shadow-[0_0_0_0_rgba(52,211,153,0.45)] animate-pulse" />
          </button>

          <div className="pointer-events-none absolute right-0 top-full hidden pt-3 lg:block">
            <div className="rounded-full border border-white/20 bg-slate-950 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.28em] text-white opacity-0 shadow-lg shadow-black/20 transition-all duration-200 group-hover:opacity-100">
              AI Assistant
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FloatingChatbot;
