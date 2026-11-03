import assert from "node:assert/strict";
import test from "node:test";

import { parseSSE } from "./sse.mjs";

test("reads complete events and keeps the unfinished rest", () => {
  const { events, rest } = parseSSE('event: token\ndata: {"text":"Hi"}\n\nevent: token\ndata: {"te');
  assert.deepEqual(events, [{ name: "token", data: { text: "Hi" } }]);
  assert.equal(rest, 'event: token\ndata: {"te');
});

test("events split across chunks are completed later", () => {
  const first = parseSSE('event: done\ndata: {"balance":0');
  assert.equal(first.events.length, 0);
  const second = parseSSE(first.rest + '}\n\n');
  assert.deepEqual(second.events, [{ name: "done", data: { balance: 0 } }]);
});

test("handles Windows line endings", () => {
  const { events } = parseSSE('event: meta\r\ndata: {"question_id":1}\r\n\r\n');
  assert.equal(events[0].data.question_id, 1);
});
