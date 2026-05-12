import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  HeartPulse,
  LoaderCircle,
  Mic,
  Send,
} from 'lucide-react';
import api from '../lib/axios';
import { useAuthStore } from '../store/authStore';
import ChatMessage from './chat/ChatMessage';
import useChatStore from '../store/chatStore';
import { parseSafetyFromResponse } from './safety/SafetyContext';
import { streamChatResponse } from '../services/chatStreamService';
import { appendAssistantChunk } from '../services/chatTransport';
import { useAppStore } from '../store/useAppStore';
import useDashboardStore from '../store/dashboardStore';
import {
  createChatActionDispatcher,
  logAssistantDevEvent,
} from '../services/chat/chatActionDispatcher';

const promptChips = [
  'Why is my heart rate high?',
  'What does chest pain mean?',
  'Explain my latest risk score',
];

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

const buildMessageId = (role = 'message') =>
  `${role}-${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`}`;

const Chatbot = () => {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const [typingDepth, setTypingDepth] = useState('short');
  const [typingLabel, setTypingLabel] = useState(typingConfig.short.label);
  const endRef = useRef(null);
  const abortRef = useRef(null);
  const activeAssistantMessageIdRef = useRef(null);
  const userId = useAuthStore((state) => state.user?.id || state.session?.user?.id || 'anonymous');
  const closeAssistant = useAppStore((state) => state.closeAssistant);
  const {
    messages,
    sessionId,
    continuitySummary,
    hydratedForUserId,
    hydrateConversation,
    persistConversation,
    appendMessage,
    patchMessage,
    setSessionMeta,
    currentMode,
    escalation,
    setMode,
    setEscalation,
    setCurrentSafety,
    recordSafetyForMessage,
  } = useChatStore();

  useEffect(() => {
    hydrateConversation(userId);
  }, [hydrateConversation, userId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSending]);

  useEffect(() => {
    if (hydratedForUserId !== userId) return;
    persistConversation(userId);
  }, [continuitySummary, hydratedForUserId, messages, persistConversation, sessionId, userId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const canSend = useMemo(() => input.trim().length > 0 && !isSending, [input, isSending]);

  const persistLatestConversation = () => {
    if (hydratedForUserId !== userId) return;
    persistConversation(userId);
  };

  const appendLocalAssistantActionMessage = (message, metadata = {}) => {
    const role = message?.role === 'assistant' ? 'assistant' : 'user';
    const content = String(message?.content || '').trim();
    if (!content) return;

    appendMessage({
      id: buildMessageId(role),
      role,
      content,
      structured: {
        ...(message?.structured || {}),
        assistant_action: metadata.actionId || null,
        assistant_source: metadata.source || 'assistant',
        local_action: true,
      },
    });
  };

  const interruptStreaming = async ({ actionId, source } = {}) => {
    if (!abortRef.current) return false;

    const activeAssistantMessageId = activeAssistantMessageIdRef.current;
    if (activeAssistantMessageId) {
      const existing = useChatStore.getState().messages.find((message) => message.id === activeAssistantMessageId);
      if (existing?.content) {
        patchMessage(activeAssistantMessageId, {
          structured: {
            interrupted: true,
            interrupted_by: actionId || 'assistant-action',
            interrupted_source: source || 'assistant',
          },
        });
      }
    }

    logAssistantDevEvent('[CHAT_ACTION]', {
      phase: 'abort_requested',
      actionId: actionId || 'assistant-action',
      source: source || 'assistant',
    });

    abortRef.current.abort();
    return true;
  };

  const sendMessage = async (presetValue, options = {}) => {
    const query = String(presetValue ?? input).trim();
    const displayText = String(options.displayText ?? presetValue ?? input).trim() || query;

    if (!query || isSending) return;

    const {
      messages: currentMessages,
      sessionId: currentSessionId,
      continuitySummary: currentContinuitySummary,
      currentMode: currentConversationMode,
    } = useChatStore.getState();
    const requestDepth = predictPendingDepth(query);
    const requestStartedAt = Date.now();
    const historyPayload = toHistoryPayload(currentMessages);
    const nextUserMessage = {
      id: buildMessageId('user'),
      role: 'user',
      content: displayText,
      structured: options.metadata || null,
    };

    appendMessage(nextUserMessage);
    setInput('');
    setError('');
    setIsSending(true);
    setTypingDepth(requestDepth);
    setTypingLabel(typingConfig[requestDepth]?.label || 'Thinking this through...');
    logAssistantDevEvent('[ASSISTANT_TRIGGER]', {
      phase: 'message_started',
      prompt: displayText,
      transport: options.metadata?.assistant_action ? 'assistant-action' : 'manual',
    });

    try {
      const assistantMessageId = buildMessageId('assistant');
      activeAssistantMessageIdRef.current = assistantMessageId;
      let sawStreamChunk = false;
      let finalPayload = null;

      const finalizeAssistantMessage = async (payload, sourceMode = 'stream') => {
        const safety = parseSafetyFromResponse(payload);
        await waitForMinimum(requestStartedAt, payload?.depth || requestDepth);
        setMode(payload?.mode || 'casual');
        setEscalation(payload?.escalation || null);
        setCurrentSafety(safety);
        recordSafetyForMessage(assistantMessageId, safety);
        setSessionMeta({
          sessionId: payload?.session_id || useChatStore.getState().sessionId || currentSessionId || null,
          continuitySummary:
            payload?.conversation_state?.continuity_summary ||
            payload?.context_compression?.summary ||
            useChatStore.getState().continuitySummary ||
            currentContinuitySummary,
        });
        const finalizedContent = buildAssistantSummary(payload);
        const existing = useChatStore.getState().messages.find((message) => message.id === assistantMessageId);
        if (existing) {
          patchMessage(assistantMessageId, {
            content: finalizedContent,
            structured: { ...payload, safety, transport: sourceMode },
          });
          return;
        }
        appendMessage({
          id: assistantMessageId,
          role: 'assistant',
          content: finalizedContent,
          structured: { ...payload, safety, transport: sourceMode },
        });
      };

      const fallbackToBufferedResponse = async () => {
        const response = await api.post('/chat', {
          query,
          history: historyPayload,
          session_id: currentSessionId,
        });
        const payload = response?.data?.data || null;
        await finalizeAssistantMessage(payload, 'buffered');
      };

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChatResponse({
          query,
          history: historyPayload,
          sessionId: currentSessionId,
          signal: controller.signal,
          onEvent: (event) => {
            if (!event || typeof event !== 'object') return;
            if (event.event === 'meta') {
              setSessionMeta({
                sessionId: event?.data?.session_id || useChatStore.getState().sessionId || currentSessionId,
              });
              return;
            }
            if (event.event === 'typing') {
              setTypingDepth(event?.data?.depth || requestDepth);
              setTypingLabel(event?.data?.label || typingConfig[requestDepth]?.label || 'Thinking this through...');
              return;
            }
            if (event.event === 'chunk') {
              const chunkContent = String(event?.data?.content || '').trim();
              if (!chunkContent) return;
              sawStreamChunk = true;
              const existing = useChatStore.getState().messages.find((message) => message.id === assistantMessageId);
              if (!existing) {
                appendMessage({
                  id: assistantMessageId,
                  role: 'assistant',
                  content: chunkContent,
                  structured: {
                    mode: useChatStore.getState().currentMode || currentConversationMode,
                    depth: requestDepth,
                    quick_replies: [],
                  },
                });
                return;
              }
              patchMessage(assistantMessageId, {
                content: appendAssistantChunk(existing.content, chunkContent),
                structured: {
                  ...(existing.structured || {}),
                  depth: requestDepth,
                },
              });
              return;
            }
            if (event.event === 'final') {
              finalPayload = event?.data?.payload || null;
              return;
            }
            if (event.event === 'error') {
              throw new Error(event?.data?.message || 'Streaming chat failed.');
            }
          },
        });

        if (finalPayload) {
          await finalizeAssistantMessage(finalPayload, 'stream');
        } else if (!sawStreamChunk) {
          await fallbackToBufferedResponse();
        } else {
          throw new Error('The assistant stream ended before the final message was completed.');
        }
      } catch (streamError) {
        if (streamError?.name === 'AbortError') {
          logAssistantDevEvent('[CHAT_ACTION]', {
            phase: 'aborted',
            prompt: displayText,
          });
          return;
        }
        if (!sawStreamChunk) {
          await fallbackToBufferedResponse();
        } else {
          await waitForMinimum(requestStartedAt, requestDepth);
          const message = extractErrorMessage(streamError);
          setError(message);
          appendMessage({
            id: buildMessageId('assistant-error'),
            role: 'assistant',
            content: message,
            structured: null,
          });
        }
      }
    } catch (requestError) {
      await waitForMinimum(requestStartedAt, requestDepth);
      const message = extractErrorMessage(requestError);
      setError(message);
      appendMessage({
        id: buildMessageId('assistant-error'),
        role: 'assistant',
        content: message,
        structured: null,
      });
    } finally {
      activeAssistantMessageIdRef.current = null;
      abortRef.current = null;
      setIsSending(false);
      setTypingLabel(typingConfig.short.label);
    }
  };

  const getDashboardSnapshot = () => {
    const dashboardState = useDashboardStore.getState();
    return {
      score: dashboardState.healthScore?.data?.score ?? null,
      label: dashboardState.healthScore?.data?.label ?? '',
      updatedAt:
        dashboardState.healthScore?.last_updated ||
        dashboardState.healthScore?.lastUpdated ||
        dashboardState.healthScore?.data?.last_updated ||
        null,
      alerts: dashboardState.alerts?.data?.alerts || [],
    };
  };

  const handleActionError = (actionError, action) => {
    const isBusyError = actionError?.code === 'assistant_busy';
    const message = isBusyError
      ? actionError.message
      : action?.effect === 'route'
        ? 'I could not open that workflow right now. Please try again.'
        : 'I could not run that assistant action right now. Please try again.';

    setError(message);

    if (isBusyError) {
      return;
    }

    appendMessage({
      id: buildMessageId('assistant-error'),
      role: 'assistant',
      content: message,
      structured: {
        mode: 'casual',
        depth: 'micro',
        quick_replies: [],
      },
    });
  };

  const chatActionDispatcher = createChatActionDispatcher({
    navigate,
    closeAssistant,
    sendMessage,
    appendLocalExchange: appendLocalAssistantActionMessage,
    interruptStreaming,
    persistContext: persistLatestConversation,
    getDashboardSnapshot,
    isBusy: () => isSending,
    onError: handleActionError,
  });

  const handleQuickReply = async (reply) => {
    await chatActionDispatcher.execute(reply, { source: 'quick-reply' });
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
            {continuitySummary ? (
              <div className="mx-auto max-w-xl rounded-full border border-primary/10 bg-primary/5 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary dark:border-primary/20 dark:bg-primary/10 dark:text-[#cdbfff]">
                Continuing thread: {continuitySummary}
              </div>
            ) : null}
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              {promptChips.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => chatActionDispatcher.execute(chip, { source: 'suggested-chip' })}
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
              disabled={false}
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
                    {typingLabel || typingConfig[typingDepth]?.label || 'Thinking this through...'}
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
