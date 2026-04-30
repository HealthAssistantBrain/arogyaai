import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  HeartPulse,
  LoaderCircle,
  MessageSquareMore,
  Mic,
  Send,
  ShieldAlert,
  Sparkles,
  Stethoscope,
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
  content: "Hello! I'm your ArogyaAI clinical assistant. Ask about symptoms, wearable changes, labs, or your risk predictions and I'll reason with your health data plus retrieved medical guidance.",
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
    .slice(-3)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));

const buildAssistantSummary = (payload) => {
  if (!payload) return 'I reviewed your question using the available health context.';
  return payload.insight || payload.risk_summary || 'I reviewed your question using the available health context.';
};

const RiskBadge = ({ level }) => {
  const normalized = String(level || 'LOW').toUpperCase();
  const palette = {
    HIGH: 'bg-rose-500/15 text-rose-700 border-rose-200 dark:bg-rose-500/15 dark:text-rose-200 dark:border-rose-500/20',
    MODERATE: 'bg-amber-500/15 text-amber-700 border-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:border-amber-500/20',
    LOW: 'bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:border-emerald-500/20',
  };

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${palette[normalized] || palette.LOW}`}>
      {normalized} Risk
    </span>
  );
};

const ContextBadge = ({ active, label }) => (
  <span
    className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${
      active
        ? 'bg-[#6143f4]/10 text-[#6143f4] dark:bg-[#6143f4]/20 dark:text-[#c7bcff]'
        : 'bg-slate-200/80 text-slate-500 dark:bg-white/10 dark:text-slate-400'
    }`}
  >
    {label}
  </span>
);

const Section = ({ icon: Icon, title, items, tone = 'default' }) => {
  if (!items?.length) return null;

  const toneClasses = {
    default: 'bg-slate-50 border-slate-200 dark:bg-white/5 dark:border-white/10',
    caution: 'bg-amber-50 border-amber-200 dark:bg-amber-500/10 dark:border-amber-500/20',
    alert: 'bg-rose-50 border-rose-200 dark:bg-rose-500/10 dark:border-rose-500/20',
  };

  return (
    <section className={`rounded-2xl border p-3 ${toneClasses[tone] || toneClasses.default}`}>
      <div className="mb-2 flex items-center gap-2">
        <Icon size={15} className="text-[#6143f4] dark:text-[#b9abff]" />
        <h5 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-300">{title}</h5>
      </div>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={`${title}-${item}`} className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
};

const AssistantStructuredCard = ({ payload }) => {
  if (!payload) return null;

  const sources = Array.isArray(payload.sources) ? payload.sources.slice(0, 3) : [];
  const context = payload.used_context || {};

  return (
    <div className="space-y-3 overflow-hidden rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#13082A]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 dark:border-white/10">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-300">
            <Sparkles size={14} className="text-[#6143f4] dark:text-[#b9abff]" />
            Clinical Response
          </div>
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">{payload.risk_summary}</p>
        </div>
        <RiskBadge level={payload.risk_level} />
      </div>

      <div className="flex flex-wrap gap-2">
        <ContextBadge active={Boolean(context.has_ml_prediction)} label="ML Data" />
        <ContextBadge active={Boolean(context.has_vitals)} label="Wearables" />
        <ContextBadge active={Boolean(context.has_labs)} label="Labs" />
        <ContextBadge active={true} label="RAG Knowledge" />
      </div>

      <Section icon={MessageSquareMore} title="Insight" items={[payload.insight].filter(Boolean)} />
      <Section icon={HeartPulse} title="Symptoms" items={payload.symptoms} />
      <Section icon={Stethoscope} title="Possible Causes" items={payload.possible_causes || payload.possible_conditions} />
      <Section icon={Sparkles} title="What To Monitor" items={payload.what_to_monitor} />
      <Section icon={MessageSquareMore} title="Follow-up Questions" items={payload.follow_up_questions} />
      <Section icon={ShieldAlert} title="Recommendations" items={payload.recommendations} tone={payload.risk_level === 'HIGH' ? 'caution' : 'default'} />
      <Section icon={AlertTriangle} title="Safety" items={payload.safety_notes} tone={payload.risk_level === 'HIGH' ? 'alert' : 'default'} />

      {sources.length ? (
        <section className="rounded-2xl bg-slate-50 p-3 dark:bg-white/5">
          <h5 className="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-300">Knowledge Sources</h5>
          <div className="space-y-2">
            {sources.map((source) => (
              <div key={`${source.title}-${source.source}`} className="rounded-xl border border-slate-200 bg-white p-2.5 dark:border-white/10 dark:bg-white/5">
                <div className="text-sm font-bold text-[#13082A] dark:text-white">{source.title}</div>
                <div className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">{source.excerpt}</div>
                <div className="mt-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">
                  {source.source} {source.category ? `• ${source.category}` : ''}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
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
            <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-[#6143f4]/10 text-[#6143f4] dark:bg-[#6143f4]/20">
              <HeartPulse size={20} strokeWidth={2.5} />
            </div>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              Ask about symptoms, vitals, labs, or risk outputs. The assistant combines your health data with retrieved medical knowledge and responds in a safe clinical style.
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              {promptChips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => sendMessage(chip)}
                  disabled={isSending}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-[0.18em] text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
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
                      ? 'bg-[#009CDE]/15 text-[#009CDE]'
                      : 'border border-[#6143f4]/20 bg-white text-[#6143f4] shadow-sm dark:bg-white/5 dark:text-[#b9abff]'
                  }`}
                >
                  {message.role === 'user' ? <User size={15} strokeWidth={2.5} /> : <Sparkles size={14} strokeWidth={2.5} />}
                </div>

                <div className="space-y-3">
                  <div
                    className={`rounded-2xl px-3 py-3 text-sm shadow-sm ${
                      message.role === 'user'
                        ? 'rounded-tr-none bg-[#6143f4] text-white'
                        : 'rounded-tl-none border border-slate-200 bg-white text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200'
                    }`}
                  >
                    {message.content}
                  </div>

                  {message.role === 'assistant' && message.structured ? (
                    <AssistantStructuredCard payload={message.structured} />
                  ) : null}
                </div>
              </div>
            </div>
          ))}

          {isSending ? (
            <div className="flex justify-start">
              <div className="flex max-w-[85%] gap-2">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-[#6143f4]/20 bg-white text-[#6143f4] shadow-sm dark:bg-white/5 dark:text-[#b9abff]">
                  <Sparkles size={14} strokeWidth={2.5} />
                </div>
                <div className="flex items-center gap-2 rounded-2xl rounded-tl-none border border-slate-200 bg-white px-3 py-3 text-sm text-slate-600 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                  <LoaderCircle size={16} className="animate-spin" />
                  Reviewing your data and medical knowledge...
                </div>
              </div>
            </div>
          ) : null}

          <div ref={endRef} />
        </div>
      </div>

      <footer className="border-t border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-[#13082A]">
        <form onSubmit={handleSubmit} className="space-y-2">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about your health, reports, symptoms, or predictions..."
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
                type="submit"
                disabled={!canSend}
                aria-label="Send message"
                className="rounded-full p-2 text-[#6143f4] transition-colors hover:bg-[#6143f4]/10 disabled:cursor-not-allowed disabled:opacity-50"
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
