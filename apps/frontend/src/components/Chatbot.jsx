import { createElement, useEffect, useMemo, useRef, useState } from 'react';
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

const normalizeRiskLevel = (level) => {
  const raw = String(level || 'low').toLowerCase();
  if (raw.includes('high') || raw.includes('critical')) return { key: 'high', label: 'High' };
  if (raw.includes('moderate') || raw.includes('medium')) return { key: 'medium', label: 'Medium' };
  return { key: 'low', label: 'Low' };
};

const RiskBadge = ({ level }) => {
  const normalized = normalizeRiskLevel(level);
  const palette = {
    high: 'bg-rose-500/15 text-rose-700 border-rose-200 dark:bg-rose-500/15 dark:text-rose-200 dark:border-rose-500/20',
    medium: 'bg-amber-500/15 text-amber-700 border-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:border-amber-500/20',
    low: 'bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:border-emerald-500/20',
  };

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${palette[normalized.key] || palette.low}`}>
      {normalized.label} Risk
    </span>
  );
};

const ConfidenceBadge = ({ value }) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  const normalized = Math.max(0, Math.min(1, numeric > 1 ? numeric / 100 : numeric));
  const percent = Math.round(normalized * 100);
  const tone =
    normalized >= 0.75
      ? 'bg-emerald-500/15 text-emerald-700 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:border-emerald-500/20'
      : normalized >= 0.5
        ? 'bg-sky-500/15 text-sky-700 border-sky-200 dark:bg-sky-500/15 dark:text-sky-200 dark:border-sky-500/20'
        : 'bg-amber-500/15 text-amber-700 border-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:border-amber-500/20';

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${tone}`}>
      {percent}% Confidence
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
  const iconElement = Icon ? createElement(Icon, { size: 15, className: 'text-[#6143f4] dark:text-[#b9abff]' }) : null;

  return (
    <section className={`rounded-2xl border p-3 ${toneClasses[tone] || toneClasses.default}`}>
      <div className="mb-2 flex items-center gap-2">
        {iconElement}
        <h5 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-300">{title}</h5>
      </div>
      <ul className="list-disc space-y-2 pl-5">
        {items.map((item) => (
          <li key={`${title}-${item}`} className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {sanitizeDisplayText(item)}
          </li>
        ))}
      </ul>
    </section>
  );
};

const sectionItems = (content) => {
  if (Array.isArray(content)) return content.filter(Boolean);
  return content ? [content] : [];
};

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

const QuestionChips = ({ questions, onSelect, disabled }) => {
  if (!questions?.length) return null;

  return (
    <section className="rounded-2xl border border-[#6143f4]/15 bg-[#6143f4]/5 p-3 dark:border-[#6143f4]/25 dark:bg-[#6143f4]/10">
      <div className="mb-2 flex items-center gap-2">
        <MessageSquareMore size={15} className="text-[#6143f4] dark:text-[#b9abff]" />
        <h5 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-300">Follow-up Questions</h5>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSelect?.(question)}
            disabled={disabled}
            className="rounded-full border border-[#6143f4]/20 bg-white px-3 py-1.5 text-left text-xs font-bold leading-relaxed text-[#4c35c9] transition-colors hover:bg-[#6143f4]/10 disabled:cursor-not-allowed disabled:opacity-60 dark:border-[#b9abff]/20 dark:bg-white/5 dark:text-[#d7d0ff] dark:hover:bg-white/10"
          >
            {sanitizeDisplayText(question)}
          </button>
        ))}
      </div>
    </section>
  );
};

const AssistantStructuredCard = ({ payload, onQuestionClick, disabled }) => {
  if (!payload) return null;

  const sources = Array.isArray(payload.sources) ? payload.sources.slice(0, 3) : [];
  const context = payload.used_context || {};
  const riskLevel = normalizeRiskLevel(payload.risk_level).key;
  const structured = payload.structured_response || payload;
  const understanding = sectionItems(structured.understanding || payload.understanding).slice(0, 1);
  const clinicalInterpretation = sectionItems(structured.clinical_interpretation || payload.clinical_interpretation || payload.interpretation).slice(0, 2);
  const followUps = sectionItems(payload.follow_up_questions).slice(0, 2);
  const recommendations = sectionItems(structured.recommendations || payload.recommendations).slice(0, 4);
  const safetyNotes = sectionItems(payload.safety_notes || payload.safety_note).slice(0, 2);
  const possibleCauses = sectionItems(structured.possible_causes || payload.possible_causes || payload.possible_conditions).slice(0, 3);

  return (
    <div className="space-y-3 overflow-hidden rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#13082A]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3 dark:border-white/10">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.22em] text-slate-500 dark:text-slate-300">
            <Sparkles size={14} className="text-[#6143f4] dark:text-[#b9abff]" />
            Clinical Response
          </div>
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {sanitizeDisplayText(payload.risk_summary || structured.clinical_interpretation || payload.summary || payload.insight)}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <RiskBadge level={payload.risk_level} />
          <ConfidenceBadge value={payload.confidence_score ?? structured.confidence_score} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <ContextBadge active={Boolean(context.has_ml_prediction)} label="Risk Data" />
        <ContextBadge active={Boolean(context.has_vitals)} label="Wearables" />
        <ContextBadge active={Boolean(context.has_labs)} label="Labs" />
        <ContextBadge active={Boolean(context.session_messages_used)} label="Memory" />
        <ContextBadge active={Boolean(sources.length || context.retrieval_source)} label="Medical Guide" />
      </div>

      <Section icon={MessageSquareMore} title="Understanding" items={understanding} />
      <Section icon={Stethoscope} title="Clinical Interpretation" items={clinicalInterpretation} />
      <Section icon={HeartPulse} title="Symptoms Considered" items={payload.symptoms} />
      <Section icon={Sparkles} title="Possible Causes" items={possibleCauses} />
      <Section icon={Sparkles} title="What To Monitor" items={payload.what_to_monitor} />
      <QuestionChips questions={followUps} onSelect={onQuestionClick} disabled={disabled} />
      <Section icon={ShieldAlert} title="Recommendations" items={recommendations} tone={riskLevel === 'high' ? 'caution' : 'default'} />
      <Section icon={AlertTriangle} title="Safety" items={safetyNotes} tone={riskLevel === 'high' ? 'alert' : 'default'} />

      {sources.length ? (
        <section className="rounded-2xl bg-slate-50 p-3 dark:bg-white/5">
          <h5 className="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-300">Knowledge Sources</h5>
          <div className="space-y-2">
            {sources.map((source) => (
              <div key={`${source.title}-${source.source}`} className="rounded-xl border border-slate-200 bg-white p-2.5 dark:border-white/10 dark:bg-white/5">
                <div className="text-sm font-bold text-[#13082A] dark:text-white">{sanitizeDisplayText(source.title)}</div>
                <div className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">{sanitizeDisplayText(source.excerpt)}</div>
                <div className="mt-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">
                  {sanitizeDisplayText(source.source)} {source.category ? `• ${sanitizeDisplayText(source.category)}` : ''}
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
              Share a symptom, report change, or concern. ArogyaAI will keep the thread in mind and respond carefully.
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
                    <MessageContent text={message.content} />
                  </div>

                  {message.role === 'assistant' && message.structured ? (
                    <AssistantStructuredCard payload={message.structured} onQuestionClick={sendMessage} disabled={isSending} />
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
