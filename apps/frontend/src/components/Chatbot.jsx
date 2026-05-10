import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  HeartPulse,
  LoaderCircle,
  Mic,
  Send,
} from 'lucide-react';
import api from '../lib/axios';
import ChatMessage from './chat/ChatMessage';
import useChatStore from '../store/chatStore';
import { parseSafetyFromResponse } from './safety/SafetyContext';

const promptChips = [
  'Why is my heart rate high?',
  'What does chest pain mean?',
  'Explain my latest risk score',
];

const initialAssistantMessage = {
  id: 'assistant-welcome',
  role: 'assistant',
  content: "Hey! What would you like help with today?",
  structured: {
    mode: 'casual',
    depth: 'micro',
    quick_replies: ['Check symptoms', 'View my risk score', 'Upload a report'],
  },
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
  return payload.summary_preview || payload.message || payload.summary || payload.understanding || payload.clinical_interpretation || payload.insight || payload.risk_summary || 'I reviewed your question using the available health context.';
};

const quickReplyToQuery = {
  'Check symptoms': 'I want to check my symptoms.',
  'View my risk score': 'Explain my risk score.',
  'Upload a report': 'I want to upload a report.',
};

const typingConfig = {
  micro: { minMs: 500, label: 'Arya is typing...' },
  short: { minMs: 800, label: 'Arya is typing...' },
  medium: { minMs: 1500, label: 'Thinking this through...' },
  detailed: { minMs: 1400, label: 'Thinking this through...' },
  expert: { minMs: 1500, label: 'Analyzing your data...' },
};

const predictPendingDepth = (value) => {
  const query = String(value || '').trim().toLowerCase();
  if (!query) return 'short';
  if (/(can't breathe|cannot breathe|heart attack|stroke|crushing chest pain|severe)/.test(query)) return 'short';
  if (/(hi|hello|hey|thanks|thank you|bye|okay|ok|got it)/.test(query) && query.split(/\s+/).length <= 4) return 'micro';
  if (/(report|blood test|lab report|analyze this report)/.test(query)) return 'expert';
  if (/(risk score|what should i do|recommend|advice)/.test(query)) return 'detailed';
  if (/(pain|hurts|headache|dizzy|breath|fever|palpitations|symptom)/.test(query)) return 'medium';
  return 'short';
};

const waitForMinimum = async (startedAt, depth) => {
  const minimum = typingConfig[depth]?.minMs ?? 800;
  const elapsed = Date.now() - startedAt;
  if (elapsed >= minimum) return;
  await new Promise((resolve) => window.setTimeout(resolve, minimum - elapsed));
};

const Chatbot = () => {
  const [messages, setMessages] = useState([initialAssistantMessage]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const [typingDepth, setTypingDepth] = useState('short');
  const endRef = useRef(null);
  const { currentMode, escalation, setMode, setEscalation, setCurrentSafety, recordSafetyForMessage } = useChatStore();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);

  const canSend = useMemo(() => input.trim().length > 0 && !isSending, [input, isSending]);

  const sendMessage = async (presetValue) => {
    const query = String(presetValue ?? input).trim();
    if (!query || isSending) return;
    const requestDepth = predictPendingDepth(query);
    const requestStartedAt = Date.now();

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
    setTypingDepth(requestDepth);

    try {
      const response = await api.post('/chat', {
        query,
        history: historyPayload,
      });

      const payload = response?.data?.data || null;
      const safety = parseSafetyFromResponse(payload);
      await waitForMinimum(requestStartedAt, payload?.depth || requestDepth);
      setMode(response?.data?.mode || payload?.mode || 'casual');
      setEscalation(payload?.escalation || null);
      setCurrentSafety(safety);
      const assistantMessageId = `assistant-${Date.now()}`;
      recordSafetyForMessage(assistantMessageId, safety);
      setMessages((current) => [
        ...current,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: buildAssistantSummary(payload),
          structured: { ...payload, safety },
        },
      ]);
    } catch (requestError) {
      await waitForMinimum(requestStartedAt, requestDepth);
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

  const handleQuickReply = async (reply) => {
    await sendMessage(quickReplyToQuery[reply] || reply);
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
              Share a symptom, report change, or concern. Arya will keep the thread in mind and respond naturally.
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
            <ChatMessage
              key={message.id}
              message={message}
              disabled={isSending}
              onQuickReply={handleQuickReply}
            />
          ))}

          {isSending ? (
            <div className="flex justify-start">
              <div className="flex max-w-[85%] gap-2">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-white text-primary shadow-sm dark:bg-white/5 dark:text-[#b9abff]">
                  <HeartPulse size={14} strokeWidth={2.5} />
                </div>
                <div className="space-y-2 rounded-2xl rounded-tl-none border border-slate-200 bg-white px-3 py-3 text-sm text-slate-600 shadow-sm dark:border-stroke dark:bg-white/5 dark:text-text-secondary">
                  <div className="flex items-center gap-2">
                    <LoaderCircle size={16} className="animate-spin" />
                    {typingConfig[typingDepth]?.label || 'Thinking this through...'}
                  </div>
                  {typingDepth === 'expert' ? (
                    <div className="h-1.5 w-44 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                      <div className="h-full w-1/2 animate-pulse rounded-full bg-primary/70" />
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          {escalation?.severity === 'emergency' ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
              <div className="flex items-center gap-2 font-semibold">
                <AlertCircle size={16} />
                Emergency guidance is active for this conversation.
              </div>
            </div>
          ) : null}

          {!isSending && currentMode !== 'expert' && escalation?.severity === 'medical' ? (
            <div className="text-xs font-medium uppercase tracking-[0.18em] text-amber-600 dark:text-amber-300">
              Clinical mode active
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

