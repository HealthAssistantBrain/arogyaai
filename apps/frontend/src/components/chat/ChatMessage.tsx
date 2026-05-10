import { Sparkles, User } from 'lucide-react';
import AnalysisToggle from './AnalysisToggle';
import QuickReplies from './QuickReplies';
import { AIInterpretationLabel } from '../safety/AIInterpretationLabel';
import { ConfidenceIndicator } from '../safety/ConfidenceIndicator';
import { EscalationNotice } from '../safety/EscalationNotice';
import { SafetyBanner } from '../safety/SafetyBanner';
import type { SafetyState } from '../safety/SafetyContext';

type StructuredPayload = {
  depth?: string;
  mode?: string;
  summary_preview?: string;
  full_analysis?: string;
  expert_sections?: Array<{ title?: string; content?: string }>;
  quick_replies?: string[];
  safety?: SafetyState | null;
  memory?: {
    token_count?: number;
    episodic_count?: number;
    has_health_trends?: boolean;
    continuity_tags?: string[];
  } | null;
};

type ChatMessageProps = {
  message: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    structured?: StructuredPayload | null;
  };
  disabled?: boolean;
  onQuickReply?: (reply: string) => void;
};

const sanitizeDisplayText = (value: string) =>
  String(value || '')
    .replace(/#{1,6}\s*/g, '')
    .replace(/[*`_]+/g, '')
    .replace(/\s+\n/g, '\n')
    .trim();

const splitParagraphs = (value: string) =>
  sanitizeDisplayText(value)
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);

const MessageContent = ({ text }: { text: string }) => {
  const paragraphs = splitParagraphs(text);
  if (!paragraphs.length) return null;

  return (
    <div className="space-y-2">
      {paragraphs.map((paragraph) => (
        <p key={paragraph} className="leading-relaxed">
          {paragraph}
        </p>
      ))}
    </div>
  );
};

const bubbleSpacing = (depth?: string) => {
  if (depth === 'micro') return 'px-3 py-2';
  if (depth === 'short') return 'px-3 py-2.5';
  return 'px-3 py-3';
};

const ChatMessage = ({ message, disabled = false, onQuickReply }: ChatMessageProps) => {
  const depth = message?.structured?.depth;
  const quickReplies = Array.isArray(message?.structured?.quick_replies)
    ? message.structured?.quick_replies || []
    : [];
  const isExpert = message?.role === 'assistant' && message?.structured?.mode === 'expert';
  const safety = message?.role === 'assistant' ? message?.structured?.safety || null : null;
  const memory = message?.role === 'assistant' ? message?.structured?.memory || null : null;
  const memoryTags = Array.isArray(memory?.continuity_tags) ? memory?.continuity_tags : [];

  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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

        <div className="space-y-2">
          {message.role === 'assistant' ? <AIInterpretationLabel /> : null}
          {message.role === 'assistant' ? <SafetyBanner safety={safety} /> : null}

          <div
            className={`rounded-2xl text-sm shadow-sm ${
              bubbleSpacing(depth)
            } ${
              message.role === 'user'
                ? 'rounded-tr-none bg-primary text-white'
                : 'rounded-tl-none border border-slate-200 bg-white text-slate-700 dark:border-stroke dark:bg-white/5 dark:text-text-primary'
            }`}
          >
            <MessageContent text={message.content} />
          </div>

          {isExpert ? (
            <AnalysisToggle
              fullAnalysis={message?.structured?.full_analysis}
              sections={message?.structured?.expert_sections}
            />
          ) : null}

          {message.role === 'assistant' && quickReplies.length && onQuickReply ? (
            <QuickReplies replies={quickReplies} disabled={disabled} onSelect={onQuickReply} />
          ) : null}

          {message.role === 'assistant' && memory && (memory.episodic_count || memory.has_health_trends) ? (
            <div className="inline-flex flex-wrap items-center gap-2 rounded-full border border-primary/10 bg-primary/5 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-primary dark:border-primary/20 dark:bg-primary/10 dark:text-[#c9bfff]">
              <span>Personal memory used</span>
              {memory.episodic_count ? <span>{memory.episodic_count} recall{memory.episodic_count > 1 ? 's' : ''}</span> : null}
              {memory.has_health_trends ? <span>trend context</span> : null}
              {memoryTags.slice(0, 2).map((tag) => (
                <span key={tag}>{tag.replace(/_/g, ' ')}</span>
              ))}
            </div>
          ) : null}

          {message.role === 'assistant' ? <ConfidenceIndicator safety={safety} /> : null}
          {message.role === 'assistant' ? <EscalationNotice safety={safety} /> : null}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
