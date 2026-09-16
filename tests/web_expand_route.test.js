// T2 — POST /api/scenarios/:id/expand route test (mocks Python process)
// Validates that:
//   - panel_count validation is applied at HTTP layer
//   - expand endpoint forwards target_count and scene_hints to Python
//   - fallback response shape is preserved (200 + fallback: true)
//   - happy path returns 201 with panel_count + added_panels

import { test } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import http from 'node:http';

// Provide config stub before requiring routes
process.env.WEB_DATA_ROOT = '/tmp/comic-test-' + Date.now();
process.env.WEB_PROJECT_ROOT = process.cwd();
process.env.NODE_ENV = 'test';

const config = {
  dataRoot: process.env.WEB_DATA_ROOT,
  projectRoot: process.env.WEB_PROJECT_ROOT,
  pythonBin: process.env.PYTHON_BIN || 'python3',
  ingestTimeoutMs: 30000,
  revisionTimeoutMs: 60000,
  revisionOutputLimit: 65536,
  processOutputLimit: 65536,
  maxContentChars: 8000,
  minSeed: 0,
  maxSeed: 2_147_483_647,
  maxRevisionFeedbackCount: 20,
  maxRevisionHistory: 10,
};

// In-memory store stub
const inMemoryDraft = {
  integ01: {
    id: 'integ01',
    status: 'draft',
    title: 'Expand Test',
    panels: [
      { n: 1, prompt: 'p1', caption: 'c1' },
      { n: 2, prompt: 'p2', caption: 'c2' },
      { n: 3, prompt: 'p3', caption: 'c3' },
    ],
  },
};

const store = {
  find: (id) => {
    const rec = inMemoryDraft[id];
    if (!rec) return null;
    return { state: rec.status, record: rec };
  },
  get: (id) => {
    const rec = inMemoryDraft[id];
    if (!rec) throw new Error('not found');
    return { state: rec.status, record: rec };
  },
};

let lastRunnerArgs = null;
let nextRunnerResult = null;

const runner = {
  run: async (bin, args, opts) => {
    lastRunnerArgs = { bin, args, opts };
    return nextRunnerResult;
  },
};

const noopJobManager = { enqueueRender: () => ({}), enqueueRevision: () => ({}) };

// Stub parseJsonResult to use our controlled stdout
import { parseJsonResult } from '../web/lib/process_runner.js';
import { errorMiddleware } from '../web/lib/errors.js';

const { scenariosRouter } = await import('../web/routes/scenarios.js');

function makeApp() {
  const app = express();
  app.use((req, _res, next) => {
    req.id = 'test-req-' + Math.random().toString(36).slice(2, 8);
    next();
  });
  app.use(express.json());
  app.use('/api/scenarios', scenariosRouter({ config, store, lifecycle: {}, runner, jobManager: noopJobManager }));
  app.use(errorMiddleware(null));
  return app;
}

function request(app, method, path, body = null) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, () => {
      const port = server.address().port;
      const data = body ? JSON.stringify(body) : null;
      const opts = {
        method,
        hostname: '127.0.0.1',
        port,
        path,
        headers: data ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {},
      };
      const req = http.request(opts, (res) => {
        let chunks = '';
        res.on('data', (c) => (chunks += c));
        res.on('end', () => {
          server.close();
          try {
            resolve({ status: res.statusCode, body: chunks ? JSON.parse(chunks) : null });
          } catch (err) {
            resolve({ status: res.statusCode, body: chunks });
          }
        });
      });
      req.on('error', (err) => {
        server.close();
        reject(err);
      });
      if (data) req.write(data);
      req.end();
    });
  });
}

test('T2: POST /api/scenarios/:id/expand with valid target_count returns 201 + panel_count', async () => {
  const app = makeApp();
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: true, id: 'integ01', status: 'draft', panel_count: 5, added_panels: [4, 5] }),
    stderr: '',
  };
  const res = await request(app, 'POST', '/api/scenarios/integ01/expand', { target_count: 5 });
  assert.equal(res.status, 201);
  assert.equal(res.body.ok, true);
  assert.equal(res.body.panel_count, 5);
  assert.deepEqual(res.body.added_panels, [4, 5]);
  // Verify Python was called with --target-count 5
  assert.ok(lastRunnerArgs.args.includes('--target-count'));
  const idx = lastRunnerArgs.args.indexOf('--target-count');
  assert.equal(lastRunnerArgs.args[idx + 1], '5');
});

test('T2: POST /api/scenarios/:id/expand with scene_hints forwards them', async () => {
  const app = makeApp();
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: true, id: 'integ01', status: 'draft', panel_count: 5, added_panels: [4, 5] }),
    stderr: '',
  };
  await request(app, 'POST', '/api/scenarios/integ01/expand', {
    target_count: 5,
    scene_hints: ['Rooftop chase', 'Face-off in rain'],
  });
  assert.ok(lastRunnerArgs.args.includes('--scene-hint'));
  const hintIdx = lastRunnerArgs.args.indexOf('--scene-hint');
  assert.equal(lastRunnerArgs.args[hintIdx + 1], 'Rooftop chase');
  assert.equal(lastRunnerArgs.args[hintIdx + 3], 'Face-off in rain');
});

test('T2: POST /api/scenarios/:id/expand with fallback returns 200 + fallback: true', async () => {
  const app = makeApp();
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: true, fallback: true, id: 'integ01', panels_unchanged: true, reason: 'llm_rate_limited', warnings: ['test warning'] }),
    stderr: '',
  };
  const res = await request(app, 'POST', '/api/scenarios/integ01/expand', { target_count: 5 });
  assert.equal(res.status, 200);
  assert.equal(res.body.fallback, true);
  assert.equal(res.body.fallback_reason, 'llm_rate_limited');
  assert.equal(res.body.panel_count, 3, 'panel_count unchanged');
  assert.deepEqual(res.body.warnings, ['test warning']);
});

test('T2: POST /api/scenarios/:id/expand rejects target_count=2 (below minimum)', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/integ01/expand', { target_count: 2 });
  assert.equal(res.status, 400);
  assert.equal(res.body.error.code, 'INVALID_PANEL_COUNT');
});

test('T2: POST /api/scenarios/:id/expand rejects target_count=7 (above maximum)', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/integ01/expand', { target_count: 7 });
  assert.equal(res.status, 400);
  assert.equal(res.body.error.code, 'INVALID_PANEL_COUNT');
});

test('T2: POST /api/scenarios/:id/expand rejects non-integer target_count', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/integ01/expand', { target_count: 3.5 });
  assert.equal(res.status, 400);
  assert.equal(res.body.error.code, 'INVALID_PANEL_COUNT');
});

test('T2: POST /api/scenarios/:id/expand rejects target not greater than current', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/integ01/expand', { target_count: 3 });
  assert.equal(res.status, 400);
  assert.equal(res.body.error.code, 'TARGET_NOT_GREATER');
});

test('T2: POST /api/scenarios/:id/expand rejects non-draft scenario', async () => {
  inMemoryDraft.approved01 = { id: 'approved01', status: 'approved', panels: [{ n: 1, prompt: 'p', caption: 'c' }] };
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/expand', { target_count: 4 });
  assert.equal(res.status, 409);
  assert.equal(res.body.error.code, 'EXPANSION_REQUIRES_DRAFT');
  delete inMemoryDraft.approved01;
});

test('T2: POST /api/scenarios/:id/expand rejects unknown scenario', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/unknown123/expand', { target_count: 4 });
  assert.equal(res.status, 404);
  assert.equal(res.body.error.code, 'SCENARIO_NOT_FOUND');
});
