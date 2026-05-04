import { useEffect, useMemo, useRef, useState } from 'react';
import {
  HeartPulse,
  LoaderCircle,
  Mic,
  Send,
  Sparkles,
  User,
} from 'lucide-react';
import api from '../lib/axios';

const promptChips = [
  'Why is my heart rate high?',
  'What does chest pain mean?',
  'Explain my latest risk score',
];

const initialAssistantMessage = {
  id: 'assistant-welcome',
  role: 'assistant',
  content: "Hello. Tell me what's going on, even if it feels vague. I'll ask the next useful question and interpret your health data cautiously.",
  structured: null,
};

const extractErrorMessage = (error) =>
  error?.response?.data?.error ||
  error?.response?.data?.detail ||
  error?.message ||
  'Unable to reach the assistant right now.';

const toHistoryPayload = (messages) =>
  messages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .slice(-5)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));

const buildAssistantSummary = (payload) => {
  if (!payload) return 'I reviewed your question using the available health context.';
  return payload.message || payload.understanding || payload.clinical_interpretation || payload.insight || payload.risk_summary || 'I reviewed your question using the available health context.';
};

const sanitizeDisplayText = (value) =>
  String(value || '')
    .replace(/#{1,6}\s*/g, '')
    .replace(/[*`_]+/g, '')
    .replace(/\s+\n/g, '\n')
    .trim();

const splitParagraphs = (value) =>
  sanitizeDisplayText(value)
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);

const MessageContent = ({ text }) => {
  const paragraphs = splitParagraphs(text);

  if (!paragraphs.length) return null;

  return (
    <div className="space-y-2">
      {paragraphs.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
    </div>
  );
};

const Chatbot = () => {
  const [messages, setMessages] = useState([initialAssistantMessage]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);

  const canSend = useMemo(() => input.trim().length > 0 && !isSending, [input, isSending]);

  const sendMessage = async (presetValue) => {
    const query = String(presetValue ?? input).trim();
    if (!query || isSending) return;

    const nextUserMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      structured: null,
    };

    const historyPayload = toHistoryPayload(messages);

    setMessages((current) => [...current, nextUserMessage]);
    setInput('');
    setError('');
    setIsSending(true);

    try {
      const response = await api.post('/chat', {
        query,
        history: historyPayload,
      });

      const payload = response?.data?.data || null;
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: buildAssistantSummary(payload),
          structured: payload,
        },
      ]);
    } catch (requestError) {
      const message = extractErrorMessage(requestError);
      setError(message);
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: message,
          structured: null,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await sendMessage();
  };

  return (
    <>
      <div className="flex-1 overflow-y-auto bg-[#F7F7FB] p-4 dark:bg-[#0f0b20]">
        <div className="space-y-5">
          <section className="mb-2 space-y-3 text-center">
            <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary dark:bg-primary/20">
              <HeartPulse size={20} strokeWidth={2.5} />
            </div>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-text-secondary">
              Share a symptom, report change, or concern. ArogyaAI will keep the thread in mind and respond carefully.
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              {promptChips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => sendMessage(chip)}
                  disabled={isSending}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-[0.18em] text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stroke dark:bg-white/5 dark:text-text-primary dark:hover:bg-white/10"
                >
                  {chip}
                </button>
              ))}
            </div>
          </section>

          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex ${message.role === 'user' ? 'max-w-[85%] flex-row-reverse gap-2' : 'max-w-[92%] gap-2'}`}>
                <div
                  className={`flex size-8 shrink-0 items-center justify-center rounded-full ${
                    message.role === 'user'
                      ? 'bg-secondary/15 text-secondary'
                      : 'border border-primary/20 bg-white text-primary shadow-sm dark:bg-white/5 dark:text-[#b9abff]'
                  }`}
                >
                  {message.role === 'user' ? <User size={15} strokeWidth={2.5} /> : <Sparkles size={14} strokeWidth={2.5} />}
                </div>

                <div className="space-y-3">
                  <div
                    className={`rounded-2xl px-3 py-3 text-sm shadow-sm ${
                      message.role === 'user'
                        ? 'rounded-tr-none bg-primary text-white'
                        : 'rounded-tl-none border border-slate-200 bg-white text-slate-700 dark:border-stroke dark:bg-white/5 dark:text-text-primary'
                    }`}
                  >
                    <MessageContent text={message.content} />
                  </div>
                </div>
              </div>
            </div>
          ))}

          {isSending ? (
            <div className="flex justify-start">
              <div className="flex max-w-[85%] gap-2">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-white text-primary shadow-sm dark:bg-white/5 dark:text-[#b9abff]">
                  <Sparkles size={14} strokeWidth={2.5} />
                </div>
                <div className="flex items-center gap-2 rounded-2xl rounded-tl-none border border-slate-200 bg-white px-3 py-3 text-sm text-slate-600 shadow-sm dark:border-stroke dark:bg-white/5 dark:text-text-secondary">
                  <LoaderCircle size={16} className="animate-spin" />
                  Reviewing this carefully...
                </div>
              </div>
            </div>
          ) : null}

          <div ref={endRef} />
        </div>
      </div>

      <footer className="border-t border-slate-200 bg-white p-4 dark:border-stroke dark:bg-card">
        <form onSubmit={handleSubmit} className="space-y-2">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about your health, reports, symptoms, or predictions..."
              className="w-full rounded-xl border-0 bg-slate-100 py-3 pl-4 pr-24 text-sm text-slate-800 placeholder:text-text-muted focus:bg-white focus:ring-2 focus:ring-[var(--color-primary)] dark:bg-white/5 dark:text-text-primary dark:placeholder:text-slate-500 dark:focus:bg-white/10"
            />
            <div className="absolute right-2 flex items-center gap-1">
              <button
                type="button"
                aria-label="Voice input"
                className="rounded-full p-2 text-slate-500 transition-colors hover:text-primary dark:text-text-muted"
              >
                <Mic size={18} strokeWidth={2.2} />
              </button>
              <button
                type="submit"
                disabled={!canSend}
                aria-label="Send message"
                className="rounded-full p-2 text-primary transition-colors hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send size={18} strokeWidth={2.3} />
              </button>
            </div>
          </div>

          {error ? (
            <div className="rounded-xl bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 dark:bg-rose-500/10 dark:text-rose-200">
              {error}
            </div>
          ) : null}
        </form>
      </footer>
    </>
  );
};

export default Chatbot;

