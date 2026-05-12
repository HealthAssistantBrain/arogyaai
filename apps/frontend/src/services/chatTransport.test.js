import assert from 'node:assert/strict';
import test from 'node:test';

import {
  appendAssistantChunk,
  createInitialAssistantMessage,
  hydrateConversationState,
  parseStreamBuffer,
  resolveChatMessageUpdate,
  serializeConversationState,
} from './chatTransport.js';

test('conversation state round-trips through storage serialization', () => {
  const serialized = serializeConversationState({
    sessionId: 'session-42',
    continuitySummary: 'Tracking the elevated heart rate thread',
    messages: [
      createInitialAssistantMessage(),
      { id: 'user-1', role: 'user', content: 'My pulse is still high.', structured: null },
    ],
  });

  const hydrated = hydrateConversationState(serialized);
  assert.equal(hydrated.sessionId, 'session-42');
  assert.equal(hydrated.continuitySummary, 'Tracking the elevated heart rate thread');
  assert.equal(hydrated.messages.length, 2);
});

test('parseStreamBuffer emits completed events and retains partial remainder', () => {
  const events = [];
  const remainder = parseStreamBuffer(
    '{"event":"typing","data":{"label":"Arya is typing..."}}\n{"event":"chunk","data":{"content":"One"}}\n{"event":"chunk"',
    (event) => events.push(event),
  );

  assert.equal(events.length, 2);
  assert.equal(events[0].event, 'typing');
  assert.equal(events[1].event, 'chunk');
  assert.equal(remainder, '{"event":"chunk"');
});

test('appendAssistantChunk preserves progressive chunk spacing', () => {
  assert.equal(appendAssistantChunk('', 'First chunk.'), 'First chunk.');
  assert.equal(appendAssistantChunk('First chunk.', 'Second chunk.'), 'First chunk.\n\nSecond chunk.');
});

test('resolveChatMessageUpdate supports functional message updaters', () => {
  const nextMessages = resolveChatMessageUpdate(
    (current) => [
      ...current,
      { id: 'user-42', role: 'user', content: 'Explain the latest risk score.', structured: null },
    ],
    [createInitialAssistantMessage()],
  );

  assert.equal(nextMessages.length, 2);
  assert.equal(nextMessages[1].id, 'user-42');
  assert.equal(nextMessages[1].role, 'user');
});
