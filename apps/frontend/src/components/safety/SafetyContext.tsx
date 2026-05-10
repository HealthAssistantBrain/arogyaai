import React, { createContext, useContext, useState, type ReactNode } from 'react';

export type SafetyRiskLevel = 'safe' | 'caution' | 'elevated' | 'urgent' | 'emergency';

export interface SafetyState {
  riskLevel: SafetyRiskLevel;
  confidenceScore: number;
  confidenceReason: string;
  flags: string[];
  escalationRequired: boolean;
  escalationMessage: string | null;
  uncertaintyFlags: string[];
  rewritten?: boolean;
  processingTimeMs?: number;
}

export const defaultSafetyState: SafetyState = {
  riskLevel: 'safe',
  confidenceScore: 1,
  confidenceReason: '',
  flags: [],
  escalationRequired: false,
  escalationMessage: null,
  uncertaintyFlags: [],
  rewritten: false,
  processingTimeMs: 0,
};

const SafetyContext = createContext<{
  safety: SafetyState;
  setSafety: (next: SafetyState) => void;
}>({
  safety: defaultSafetyState,
  setSafety: () => undefined,
});

export function SafetyProvider({ children }: { children: ReactNode }) {
  const [safety, setSafety] = useState<SafetyState>(defaultSafetyState);
  return <SafetyContext.Provider value={{ safety, setSafety }}>{children}</SafetyContext.Provider>;
}

export function useSafety() {
  return useContext(SafetyContext);
}

export function parseSafetyFromResponse(payload: any): SafetyState {
  const safety = payload?.safety || payload?.data?.safety || {};
  return {
    riskLevel: safety.risk_level || 'safe',
    confidenceScore: typeof safety.confidence_score === 'number' ? safety.confidence_score : 1,
    confidenceReason: safety.confidence_reason || '',
    flags: Array.isArray(safety.flags) ? safety.flags : [],
    escalationRequired: Boolean(safety.escalation_required),
    escalationMessage: safety.escalation_message || null,
    uncertaintyFlags: Array.isArray(safety.uncertainty_flags) ? safety.uncertainty_flags : [],
    rewritten: Boolean(safety.rewritten),
    processingTimeMs: typeof safety.processing_time_ms === 'number' ? safety.processing_time_ms : 0,
  };
}
