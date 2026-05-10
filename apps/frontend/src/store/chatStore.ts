import { create } from 'zustand';
import type { SafetyState } from '../components/safety/SafetyContext';

export type ConversationMode = 'casual' | 'medical' | 'expert';

export type EscalationState = {
  escalated: boolean;
  severity: 'none' | 'medical' | 'emergency';
  reason: string;
  critical: boolean;
};

type ChatState = {
  currentMode: ConversationMode;
  escalation: EscalationState;
  currentSafety: SafetyState | null;
  safetyHistory: Array<{ messageId: string; safety: SafetyState }>;
  setMode: (mode?: string | null) => void;
  setEscalation: (value?: Partial<EscalationState> | null) => void;
  setCurrentSafety: (value: SafetyState | null) => void;
  recordSafetyForMessage: (messageId: string, value: SafetyState) => void;
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
  resetChatRouting: () =>
    set({
      currentMode: 'casual',
      escalation: defaultEscalation,
      currentSafety: null,
      safetyHistory: [],
    }),
}));

export default useChatStore;
