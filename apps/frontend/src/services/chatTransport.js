export const CHAT_STORAGE_VERSION = 1;

export const createInitialAssistantMessage = () => ({
  id: 'assistant-welcome',
  role: 'assistant',
  content: 'What would you like help with today?',
  structured: {
    mode: 'casual',
    depth: 'micro',
    quick_replies: ['Check symptoms', 'View my risk score', 'Upload a report'],
  },
});

const sanitizeStructuredPayload = (value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value;
};

export const normalizeChatMessages = (messages) => {
  const normalized = Array.isArray(messages)
    ? messages
        .filter((message) => message && typeof message === 'object')
        .map((message) => ({
          id: String(message.id || `${message.role || 'message'}-${Date.now()}`),
          role: message.role === 'assistant' ? 'assistant' : 'user',
          content: String(message.content || '').trim(),
          structured: sanitizeStructuredPayload(message.structured),
        }))
        .filter((message) => message.content || message.role === 'assistant')
    : [];

  return normalized.length ? normalized : [createInitialAssistantMessage()];
};

export const resolveChatMessageUpdate = (messagesOrUpdater, currentMessages = []) => {
  const baseline = normalizeChatMessages(currentMessages);
  const nextMessages =
    typeof messagesOrUpdater === 'function'
      ? messagesOrUpdater(baseline)
      : messagesOrUpdater;

  return normalizeChatMessages(nextMessages);
};

export const buildChatStorageKey = (userId = 'anonymous') => `arogyaai-chat:${userId || 'anonymous'}`;

export const serializeConversationState = ({
  sessionId = null,
  continuitySummary = '',
  messages = [],
} = {}) =>
  JSON.stringify({
    version: CHAT_STORAGE_VERSION,
    sessionId: sessionId || null,
    continuitySummary: String(continuitySummary || ''),
    messages: normalizeChatMessages(messages).slice(-30),
    savedAt: new Date().toISOString(),
  });

export const hydrateConversationState = (rawValue) => {
  if (!rawValue) {
    return {
      sessionId: null,
      continuitySummary: '',
      messages: [createInitialAssistantMessage()],
    };
  }

  try {
    const payload = typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue;
    return {
      sessionId: payload?.sessionId || null,
      continuitySummary: String(payload?.continuitySummary || ''),
      messages: normalizeChatMessages(payload?.messages),
    };
  } catch {
    return {
      sessionId: null,
      continuitySummary: '',
      messages: [createInitialAssistantMessage()],
    };
  }
};

export const appendAssistantChunk = (existingContent = '', chunk = '') => {
  const current = String(existingContent || '').trim();
  const next = String(chunk || '').trim();
  if (!next) return current;
  if (!current) return next;
  return `${current}\n\n${next}`;
};

export const parseStreamBuffer = (buffer, onEvent) => {
  const chunks = String(buffer || '').split('\n');
  const remainder = chunks.pop() || '';

  chunks.forEach((line) => {
    const normalized = line.trim();
    if (!normalized) return;
    try {
      const payload = JSON.parse(normalized);
      if (typeof onEvent === 'function') {
        onEvent(payload);
      }
    } catch {
      // Ignore malformed partial lines and continue parsing the stream.
    }
  });

  return remainder;
};
