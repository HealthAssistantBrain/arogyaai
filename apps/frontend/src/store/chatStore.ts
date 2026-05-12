import { create } from 'zustand';
import type { SafetyState } from '../components/safety/SafetyContext';
import {
  buildChatStorageKey,
  createInitialAssistantMessage,
  hydrateConversationState,
  normalizeChatMessages,
  resolveChatMessageUpdate,
  serializeConversationState,
} from '../services/chatTransport';

export type ConversationMode = 'casual' | 'medical' | 'expert';

export type EscalationState = {
  escalated: boolean;
  severity: 'none' | 'medical' | 'emergency';
  reason: string;
  critical: boolean;
};

export type ChatStructuredPayload = {
  depth?: string;
  mode?: string;
  summary_preview?: string;
  full_analysis?: string;
  quick_replies?: string[];
  safety?: SafetyState | null;
  session_id?: string | null;
  conversation_state?: {
    continuity_summary?: string;
  } | null;
  [key: string]: unknown;
};

export type ChatMessageRecord = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  structured?: ChatStructuredPayload | null;
};

type ChatState = {
  currentMode: ConversationMode;
  escalation: EscalationState;
  currentSafety: SafetyState | null;
  safetyHistory: Array<{ messageId: string; safety: SafetyState }>;
  messages: ChatMessageRecord[];
  sessionId: string | null;
  continuitySummary: string;
  hydratedForUserId: string | null;
  setMode: (mode?: string | null) => void;
  setEscalation: (value?: Partial<EscalationState> | null) => void;
  setCurrentSafety: (value: SafetyState | null) => void;
  recordSafetyForMessage: (messageId: string, value: SafetyState) => void;
  hydrateConversation: (userId?: string | null) => void;
  persistConversation: (userId?: string | null) => void;
  setMessages: (messages: ChatMessageRecord[] | ((messages: ChatMessageRecord[]) => ChatMessageRecord[])) => void;
  appendMessage: (message: ChatMessageRecord) => void;
  patchMessage: (messageId: string, patch: Partial<ChatMessageRecord>) => void;
  setSessionMeta: (value?: { sessionId?: string | null; continuitySummary?: string | null } | null) => void;
  clearConversation: (userId?: string | null) => void;
  resetChatRouting: () => void;
};

const defaultEscalation: EscalationState = {
  escalated: false,
  severity: 'none',
  reason: '',
  critical: false,
};

export const useChatStore = create<ChatState>((set) => ({
  currentMode: 'casual',
  escalation: defaultEscalation,
  currentSafety: null,
  safetyHistory: [],
  messages: [createInitialAssistantMessage()],
  sessionId: null,
  continuitySummary: '',
  hydratedForUserId: null,
  setMode: (mode) =>
    set({
      currentMode: mode === 'expert' || mode === 'medical' ? mode : 'casual',
    }),
  setEscalation: (value) =>
    set({
      escalation: {
        ...defaultEscalation,
        ...(value || {}),
        severity:
          value?.severity === 'emergency' || value?.severity === 'medical'
            ? value.severity
            : 'none',
        escalated: Boolean(value?.escalated),
        critical: Boolean(value?.critical),
      },
    }),
  setCurrentSafety: (value) =>
    set({
      currentSafety: value,
    }),
  recordSafetyForMessage: (messageId, value) =>
    set((state) => ({
      safetyHistory: [...state.safetyHistory.slice(-49), { messageId, safety: value }],
    })),
  hydrateConversation: (userId) => {
    if (typeof window === 'undefined') return;
    const key = buildChatStorageKey(userId || 'anonymous');
    const hydrated = hydrateConversationState(window.localStorage.getItem(key));
    set({
      messages: normalizeChatMessages(hydrated.messages),
      sessionId: hydrated.sessionId,
      continuitySummary: hydrated.continuitySummary,
      hydratedForUserId: userId || 'anonymous',
    });
  },
  persistConversation: (userId) => {
    if (typeof window === 'undefined') return;
    const state = useChatStore.getState();
    window.localStorage.setItem(
      buildChatStorageKey(userId || state.hydratedForUserId || 'anonymous'),
      serializeConversationState({
        sessionId: state.sessionId,
        continuitySummary: state.continuitySummary,
        messages: state.messages,
      }),
    );
  },
  setMessages: (messages) =>
    set((state) => ({
      messages: resolveChatMessageUpdate(messages, state.messages),
    })),
  appendMessage: (message) =>
    set((state) => ({
      messages: normalizeChatMessages([...state.messages, message]),
    })),
  patchMessage: (messageId, patch) =>
    set((state) => ({
      messages: normalizeChatMessages(
        state.messages.map((message) =>
          message.id !== messageId
            ? message
            : {
                ...message,
                ...patch,
                structured:
                  patch.structured === undefined
                    ? message.structured
                    : {
                        ...(message.structured || {}),
                        ...(patch.structured || {}),
                      },
              },
        ),
      ),
    })),
  setSessionMeta: (value) =>
    set((state) => ({
      sessionId: value?.sessionId === undefined ? state.sessionId : value?.sessionId || null,
      continuitySummary:
        value?.continuitySummary === undefined ? state.continuitySummary : String(value?.continuitySummary || ''),
    })),
  clearConversation: (userId) => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(buildChatStorageKey(userId || useChatStore.getState().hydratedForUserId || 'anonymous'));
    }
    set({
      messages: [createInitialAssistantMessage()],
      sessionId: null,
      continuitySummary: '',
    });
  },
  resetChatRouting: () =>
    set({
      currentMode: 'casual',
      escalation: defaultEscalation,
      currentSafety: null,
      safetyHistory: [],
    }),
}));

export default useChatStore;
