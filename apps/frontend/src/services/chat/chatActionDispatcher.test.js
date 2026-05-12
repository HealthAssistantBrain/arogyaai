import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildRiskScorePrompt,
  createChatActionDispatcher,
  resolveAssistantAction,
} from './chatActionDispatcher.js';

test('resolveAssistantAction maps symptom workflow quick action to a route launch', () => {
  const action = resolveAssistantAction('Check symptoms');

  assert.equal(action.actionId, 'check-symptoms');
  assert.equal(action.effect, 'route');
  assert.equal(action.workflowId, 'symptom-analysis');
  assert.equal(action.routeState.assistantWorkflow, 'symptom-analysis');
  assert.equal(action.localMessages.length, 2);
});

test('buildRiskScorePrompt enriches the risk explanation prompt with dashboard context', () => {
  const prompt = buildRiskScorePrompt({
    score: 68,
    label: 'Elevated',
    updatedAt: '2026-05-11T12:30:00.000Z',
    alerts: [{ title: 'Resting heart rate is elevated' }],
  });

  assert.match(prompt, /68\/100/);
  assert.match(prompt, /Elevated/);
  assert.match(prompt, /Resting heart rate is elevated/);
});

test('dispatcher launches upload workflow actions with local continuity messages', async () => {
  const appended = [];
  const navigations = [];
  const interrupts = [];
  let persisted = 0;
  let closed = 0;

  const dispatcher = createChatActionDispatcher({
    appendLocalExchange: (message, metadata) => appended.push({ message, metadata }),
    closeAssistant: () => {
      closed += 1;
    },
    getDashboardSnapshot: () => ({}),
    interruptStreaming: async (payload) => {
      interrupts.push(payload);
      return true;
    },
    navigate: (route, options) => navigations.push({ route, options }),
    persistContext: () => {
      persisted += 1;
    },
  });

  const result = await dispatcher.execute('Upload a report', { source: 'quick-reply' });

  assert.equal(result.ok, true);
  assert.equal(interrupts.length, 1);
  assert.equal(appended.length, 2);
  assert.equal(appended[0].message.role, 'user');
  assert.equal(appended[1].message.role, 'assistant');
  assert.equal(persisted, 1);
  assert.equal(closed, 1);
  assert.equal(navigations.length, 1);
  assert.equal(navigations[0].route, '/upload');
  assert.equal(navigations[0].options.state.assistantActionId, 'upload-report');
});

test('dispatcher sends contextual risk score prompts through the chat transport', async () => {
  const sent = [];
  const dispatcher = createChatActionDispatcher({
    getDashboardSnapshot: () => ({
      score: 74,
      label: 'High',
      alerts: ['Blood pressure trend is rising'],
    }),
    sendMessage: async (prompt, options) => {
      sent.push({ prompt, options });
    },
  });

  const result = await dispatcher.execute('View my risk score', { source: 'quick-reply' });

  assert.equal(result.ok, true);
  assert.equal(sent.length, 1);
  assert.equal(sent[0].options.displayText, 'View my risk score');
  assert.equal(sent[0].options.metadata.assistant_action, 'view-risk-score');
  assert.match(sent[0].prompt, /74\/100/);
  assert.match(sent[0].prompt, /Blood pressure trend is rising/);
});
