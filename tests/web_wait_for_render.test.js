// T5 — waitForRender polling logic tests
// Mocks the API and verifies polling behavior, terminal detection, timeout handling.

import { test } from 'node:test';
import assert from 'node:assert/strict';

// Re-implement the polling logic for testing without spinning up the MCP server.
// This mirrors the waitForRender method in mcp-server/index.js but accepts an
// injectable fetch function for deterministic testing.

function makeWaiter({ fetchJobs, scenarioId = 'aabbccdd', timeoutSeconds = 10, pollInterval = 1, sleep = (ms) => new Promise((r) => setTimeout(r, ms)) }) {
  const terminal = new Set(['succeeded', 'failed', 'interrupted']);
  const deadline = Date.now() + timeoutSeconds * 1000;
  const start = Date.now();
  let polls = 0;
  let lastStatus = 'no_job_found';
  let lastJob = null;

  return (async () => {
    while (Date.now() < deadline) {
      polls += 1;
      try {
        const data = await fetchJobs();
        const items = Array.isArray(data.items) ? data.items : [];
        const matches = items
          .filter((j) => j && j.scenario_id === scenarioId && (j.type === 'render' || j.type === 'publish'))
          .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));

        if (matches.length > 0) {
          lastJob = matches[0];
          lastStatus = lastJob.status || 'unknown';
          if (terminal.has(lastStatus)) {
            return {
              ok: true,
              timeout: false,
              job_id: lastJob.id,
              type: lastJob.type,
              status: lastStatus,
              duration_seconds: Math.round(((Date.now() - start) / 1000) * 10) / 10,
              polls,
              result: lastJob.result,
              error: lastJob.error,
            };
          }
        }
      } catch (pollErr) {
        // ignore
      }
      const remaining = deadline - Date.now();
      if (remaining <= 0) break;
      await sleep(Math.min(pollInterval * 1000, remaining));
    }

    return {
      ok: false,
      timeout: true,
      last_status: lastStatus,
      job_id: lastJob ? lastJob.id : null,
      duration_seconds: Math.round(((Date.now() - start) / 1000) * 10) / 10,
      polls,
      timeout_seconds: timeoutSeconds,
    };
  })();
}

test('T5: waitForRender returns immediately when latest job is succeeded', async () => {
  const jobs = {
    items: [
      { id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:00:00Z', result: { comic_path: '/x.png' } },
    ],
  };
  const result = await makeWaiter({
    fetchJobs: async () => jobs,
    timeoutSeconds: 30,
    pollInterval: 1,
    sleep: async () => {}, // no-op
  });
  assert.equal(result.ok, true);
  assert.equal(result.timeout, false);
  assert.equal(result.status, 'succeeded');
  assert.equal(result.job_id, 'j1');
  assert.equal(result.polls, 1);
  assert.deepEqual(result.result, { comic_path: '/x.png' });
});

test('T5: waitForRender detects failed status', async () => {
  const jobs = {
    items: [
      { id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'failed', created_at: '2026-09-16T10:00:00Z', error: { code: 'RENDER_FAILED', message: 'OOM' } },
    ],
  };
  const result = await makeWaiter({ fetchJobs: async () => jobs, sleep: async () => {} });
  assert.equal(result.status, 'failed');
  assert.equal(result.error.message, 'OOM');
});

test('T5: waitForRender detects interrupted status', async () => {
  const jobs = { items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'interrupted', created_at: '2026-09-16T10:00:00Z' }] };
  const result = await makeWaiter({ fetchJobs: async () => jobs, sleep: async () => {} });
  assert.equal(result.status, 'interrupted');
});

test('T5: waitForRender picks latest job by created_at when multiple exist', async () => {
  const jobs = {
    items: [
      { id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:00:00Z' },
      { id: 'j2', scenario_id: 'aabbccdd', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:05:00Z' },
      { id: 'j3', scenario_id: 'aabbccdd', type: 'render', status: 'running', created_at: '2026-09-16T10:10:00Z' },
    ],
  };
  const result = await makeWaiter({ fetchJobs: async () => jobs, sleep: async () => {} });
  assert.equal(result.job_id, 'j3', 'latest job (running) wins until terminal');
});

test('T5: waitForRender waits for queued → running → succeeded transition', async () => {
  let pollCount = 0;
  const fetchJobs = async () => {
    pollCount += 1;
    if (pollCount === 1) return { items: [] };
    if (pollCount === 2) return { items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'queued', created_at: '2026-09-16T10:00:00Z' }] };
    if (pollCount === 3) return { items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'running', created_at: '2026-09-16T10:00:00Z' }] };
    return { items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:00:00Z', result: { comic_path: '/x.png' } }] };
  };
  const result = await makeWaiter({
    fetchJobs,
    timeoutSeconds: 10,
    pollInterval: 1,
    sleep: async () => {}, // no real sleep
  });
  assert.equal(result.ok, true);
  assert.equal(result.status, 'succeeded');
  assert.equal(result.polls, 4);
});

test('T5: waitForRender times out when job stays running', async () => {
  const fetchJobs = async () => ({
    items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'running', created_at: '2026-09-16T10:00:00Z' }],
  });
  const result = await makeWaiter({
    fetchJobs,
    timeoutSeconds: 2,
    pollInterval: 1,
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  });
  assert.equal(result.ok, false);
  assert.equal(result.timeout, true);
  assert.equal(result.last_status, 'running');
  assert.equal(result.job_id, 'j1');
  assert.ok(result.polls >= 1, 'should have polled at least once');
});

test('T5: waitForRender times out when no job ever appears', async () => {
  const result = await makeWaiter({
    fetchJobs: async () => ({ items: [] }),
    timeoutSeconds: 1,
    pollInterval: 1,
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  });
  assert.equal(result.ok, false);
  assert.equal(result.timeout, true);
  assert.equal(result.last_status, 'no_job_found');
  assert.equal(result.job_id, null);
});

test('T5: waitForRender filters out jobs for other scenarios', async () => {
  const jobs = {
    items: [
      { id: 'j1', scenario_id: 'OTHERONE', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:00:00Z' },
      { id: 'j2', scenario_id: 'OTHER2', type: 'render', status: 'failed', created_at: '2026-09-16T10:00:00Z' },
    ],
  };
  const result = await makeWaiter({
    fetchJobs: async () => jobs,
    timeoutSeconds: 1,
    pollInterval: 1,
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  });
  assert.equal(result.ok, false);
  assert.equal(result.timeout, true);
  assert.equal(result.last_status, 'no_job_found');
});

test('T5: waitForRender includes publish-type jobs in addition to render', async () => {
  // Scenario: render completes, publish job is enqueued (auto-publish chain from T3)
  const fetchJobs = async () => ({
    items: [
      { id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:00:00Z' },
      { id: 'j2', scenario_id: 'aabbccdd', type: 'publish', status: 'succeeded', created_at: '2026-09-16T10:05:00Z', result: { published_url: 'https://example.com/x.html' } },
    ],
  });
  const result = await makeWaiter({ fetchJobs, sleep: async () => {} });
  // Latest is publish job (most recent), terminal, returns immediately
  assert.equal(result.type, 'publish');
  assert.equal(result.status, 'succeeded');
  assert.equal(result.job_id, 'j2');
});

test('T5: waitForRender continues polling when fetch throws transient error', async () => {
  let count = 0;
  const fetchJobs = async () => {
    count += 1;
    if (count === 1) throw new Error('ECONNRESET');
    return { items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'succeeded', created_at: '2026-09-16T10:00:00Z' }] };
  };
  const result = await makeWaiter({ fetchJobs, sleep: async () => {} });
  assert.equal(result.ok, true);
  assert.equal(result.status, 'succeeded');
});

test('T5: waitForRender stops polling after deadline even if job is running', async () => {
  const startTime = Date.now();
  const result = await makeWaiter({
    fetchJobs: async () => ({ items: [{ id: 'j1', scenario_id: 'aabbccdd', type: 'render', status: 'running', created_at: '2026-09-16T10:00:00Z' }] }),
    timeoutSeconds: 1,
    pollInterval: 10, // larger than timeout — should be capped
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  });
  const elapsed = Date.now() - startTime;
  assert.equal(result.timeout, true);
  assert.ok(elapsed < 3000, `should return shortly after deadline, took ${elapsed}ms`);
});
