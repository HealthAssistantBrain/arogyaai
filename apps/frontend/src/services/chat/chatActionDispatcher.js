import { ROUTES } from '../../router/routes.js';

const isDevelopment = Boolean(import.meta.env && import.meta.env.DEV);

const toActionKey = (value = '') =>
  String(value || '')
    .trim()
    .toLowerCase();

const slugifyActionId = (value = '') =>
  toActionKey(value)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'assistant-action';

const formatAlertSummary = (alerts = []) =>
  alerts
    .map((alert) => {
      if (typeof alert === 'string') return alert.trim();
      if (!alert || typeof alert !== 'object') return '';
      return String(alert.title || alert.message || alert.label || '').trim();
    })
    .filter(Boolean)
    .slice(0, 2);

export const logAssistantDevEvent = (tag, payload = {}) => {
  if (!isDevelopment) return;
  console.info(tag, payload);
};

export const buildRiskScorePrompt = (dashboardSnapshot = {}) => {
  const score = Number(dashboardSnapshot?.score);
  const hasScore = Number.isFinite(score);
  const label = String(dashboardSnapshot?.label || '').trim();
  const updatedAt = dashboardSnapshot?.updatedAt
    ? new Date(dashboardSnapshot.updatedAt).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : '';
  const activeAlerts = formatAlertSummary(dashboardSnapshot?.alerts);

  return [
    'Please explain my current health risk score using my latest ArogyaAI context.',
    hasScore ? `Current score shown on my dashboard: ${Math.round(score)}/100${label ? ` (${label})` : ''}.` : '',
    updatedAt ? `Latest dashboard update: ${updatedAt}.` : '',
    activeAlerts.length ? `Active alerts on the dashboard: ${activeAlerts.join('; ')}.` : '',
    'Focus on the main drivers, what changed recently, and the safest next actions in clear patient-friendly language.',
  ]
    .filter(Boolean)
    .join('\n');
};

const buildRouteAction = ({
  actionId,
  label,
  prompt,
  route,
  routeState,
  workflowId,
  assistantMessage,
}) => ({
  actionId,
  label,
  effect: 'route',
  route,
  routeState: {
    ...(routeState || {}),
    assistantPrompt: prompt,
    assistantWorkflow: workflowId,
  },
  workflowId,
  interruptsStreaming: true,
  localMessages: [
    {
      role: 'user',
      content: prompt,
    },
    {
      role: 'assistant',
      content: assistantMessage,
      structured: {
        mode: 'casual',
        depth: 'micro',
        quick_replies: [],
      },
    },
  ],
});

const buildChatAction = ({
  actionId,
  label,
  prompt,
  displayText,
}) => ({
  actionId,
  label,
  effect: 'chat',
  prompt,
  displayText: displayText || label || prompt,
  interruptsStreaming: false,
});

export const resolveAssistantAction = (rawAction, { dashboardSnapshot } = {}) => {
  if (rawAction && typeof rawAction === 'object' && !Array.isArray(rawAction) && rawAction.effect) {
    return rawAction;
  }

  const label = String(
    (rawAction && typeof rawAction === 'object'
      ? rawAction.label || rawAction.prompt || rawAction.actionId
      : rawAction) || '',
  ).trim();
  const key = toActionKey(label);

  if (key === 'check symptoms') {
    return buildRouteAction({
      actionId: 'check-symptoms',
      label,
      prompt: 'I want to check my symptoms.',
      route: ROUTES.SYMPTOM_ANALYSIS,
      workflowId: 'symptom-analysis',
      assistantMessage: 'Opening the symptom analysis workspace so we can structure your symptoms clearly.',
    });
  }

  if (key === 'upload a report') {
    return buildRouteAction({
      actionId: 'upload-report',
      label,
      prompt: 'I want to upload a report.',
      route: ROUTES.UPLOAD,
      workflowId: 'report-upload',
      assistantMessage: 'Opening the report upload flow so you can add a PDF or image for analysis.',
    });
  }

  if (
    key === 'view my risk score' ||
    key === 'explain my latest risk score' ||
    key === 'explain my risk score'
  ) {
    return buildChatAction({
      actionId: 'view-risk-score',
      label: label || 'View my risk score',
      prompt: buildRiskScorePrompt(dashboardSnapshot),
      displayText: label || 'View my risk score',
    });
  }

  return buildChatAction({
    actionId: slugifyActionId(label),
    label,
    prompt: label,
    displayText: label,
  });
};

export const createChatActionDispatcher = ({
  navigate,
  closeAssistant,
  sendMessage,
  appendLocalExchange,
  interruptStreaming,
  persistContext,
  getDashboardSnapshot,
  isBusy,
  onError,
} = {}) => ({
  async execute(rawAction, metadata = {}) {
    const action = resolveAssistantAction(rawAction, {
      dashboardSnapshot: getDashboardSnapshot?.(),
    });
    const source = metadata.source || 'assistant';
    const basePayload = {
      actionId: action.actionId,
      effect: action.effect,
      label: action.label,
      source,
    };

    logAssistantDevEvent('[BUTTON_ACTION]', {
      phase: 'received',
      ...basePayload,
    });

    try {
      if (action.effect === 'chat' && isBusy?.()) {
        const busyError = new Error('Arya is still finishing the current response. Please try again in a moment.');
        busyError.code = 'assistant_busy';
        throw busyError;
      }

      if (action.interruptsStreaming && interruptStreaming) {
        const interrupted = await interruptStreaming({
          actionId: action.actionId,
          source,
        });
        logAssistantDevEvent('[CHAT_ACTION]', {
          phase: 'interrupt_checked',
          interrupted,
          ...basePayload,
        });
      }

      if (Array.isArray(action.localMessages) && action.localMessages.length && appendLocalExchange) {
        action.localMessages.forEach((message) =>
          appendLocalExchange(message, {
            actionId: action.actionId,
            source,
          }),
        );
        persistContext?.();
        logAssistantDevEvent('[CHAT_CONTEXT_SYNC]', {
          phase: 'local_messages_appended',
          count: action.localMessages.length,
          ...basePayload,
        });
      }

      if (action.effect === 'route') {
        if (typeof navigate !== 'function') {
          throw new Error('Assistant route navigation is unavailable.');
        }

        logAssistantDevEvent('[WORKFLOW_LAUNCH]', {
          phase: 'start',
          route: action.route,
          workflowId: action.workflowId || null,
          ...basePayload,
        });

        closeAssistant?.();
        navigate(action.route, {
          state: {
            ...(action.routeState || {}),
            assistantActionId: action.actionId,
            assistantSource: source,
          },
        });

        logAssistantDevEvent('[CHAT_ROUTE]', {
          phase: 'complete',
          route: action.route,
          workflowId: action.workflowId || null,
          ...basePayload,
        });

        return { ok: true, action };
      }

      if (action.effect === 'chat') {
        if (typeof sendMessage !== 'function') {
          throw new Error('Assistant message dispatch is unavailable.');
        }

        logAssistantDevEvent('[ASSISTANT_TRIGGER]', {
          phase: 'dispatch',
          prompt: action.displayText,
          ...basePayload,
        });

        await sendMessage(action.prompt, {
          displayText: action.displayText,
          metadata: {
            assistant_action: action.actionId,
            assistant_source: source,
          },
        });

        return { ok: true, action };
      }

      throw new Error(`Unsupported assistant action effect: ${action.effect}`);
    } catch (error) {
      logAssistantDevEvent('[CHAT_ACTION]', {
        phase: 'failed',
        error: error?.message || 'Unknown assistant action error',
        ...basePayload,
      });
      onError?.(error, action);
      return { ok: false, action, error };
    }
  },
});
