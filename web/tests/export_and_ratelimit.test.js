import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { listen, makeTestRuntime } from './helpers.js';

test('GET /api/scenarios/:id/export/pdf returns 404 for non-rendered scenario', async () => {
  const ctx = makeTestRuntime();
  const dir = path.join(ctx.project.dataRoot, 'scenarios', 'draft');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'draft-001.json'), JSON.stringify({ id: 'draft-001', status: 'draft' }));

  const server = await listen(ctx.app);
  try {
    const response = await fetch(`${server.baseUrl}/api/scenarios/draft-001/export/pdf`);
    assert.equal(response.status, 404);
  } finally {
    await server.close();
    ctx.project.cleanup();
  }
});

test('Rate limiter returns HTTP 429 when mutation quota is exceeded', async () => {
  process.env.ENABLE_RATE_LIMIT = 'true';
  const ctx = makeTestRuntime();
  const server = await listen(ctx.app);
  try {
    let lastRes;
    for (let i = 0; i < 62; i++) {
      lastRes = await fetch(`${server.baseUrl}/api/scenarios/test-001/approve`, { method: 'POST' });
    }
    assert.equal(lastRes.status, 429);
    const body = await lastRes.json();
    assert.equal(body.error.code, 'TOO_MANY_REQUESTS');
  } finally {
    delete process.env.ENABLE_RATE_LIMIT;
    await server.close();
    ctx.project.cleanup();
  }
});
