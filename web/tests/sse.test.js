import test from 'node:test';
import assert from 'node:assert/strict';
import { SseBroadcaster } from '../lib/sse_broadcaster.js';

test('SseBroadcaster formats and sends SSE events to connected subscribers', () => {
  const broadcaster = new SseBroadcaster();
  const written = [];
  const fakeRes = {
    set() {},
    flushHeaders() {},
    write(chunk) { written.push(chunk); },
    on(event, handler) { this.closeHandler = handler; },
  };

  broadcaster.subscribe('job-100', fakeRes);
  assert.equal(written.length, 1);
  assert.match(written[0], /event: connected/);

  broadcaster.broadcast('job-100', 'job_updated', { status: 'running' });
  assert.equal(written.length, 2);
  assert.match(written[1], /event: job_updated/);
  assert.match(written[1], /"status":"running"/);

  // Close connection
  fakeRes.closeHandler();
  broadcaster.broadcast('job-100', 'job_updated', { status: 'succeeded' });
  assert.equal(written.length, 2); // No new writes after close
});
