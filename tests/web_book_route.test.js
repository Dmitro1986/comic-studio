// T4 — POST /api/scenarios/:id/book route tests (mock-based)

import { test } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import http from 'node:http';

process.env.WEB_DATA_ROOT = '/tmp/comic-test-' + Date.now();
process.env.WEB_PROJECT_ROOT = process.cwd();

const config = {
  dataRoot: process.env.WEB_DATA_ROOT,
  projectRoot: process.env.WEB_PROJECT_ROOT,
  pythonBin: 'python3',
  nodeBin: 'node',
  ingestTimeoutMs: 30000,
  renderTimeoutMs: 60000,
  publishTimeoutMs: 60000,
  revisionTimeoutMs: 60000,
  revisionOutputLimit: 65536,
  processOutputLimit: 65536,
  maxContentChars: 8000,
  minSeed: 0,
  maxSeed: 2_147_483_647,
  maxRevisionFeedbackCount: 20,
  maxRevisionHistory: 10,
};

const inMemoryScenarios = {
  rendered01: { id: 'rendered01', status: 'rendered', title: 'Rendered Test', panels: [{ n: 1, prompt: 'p', caption: 'c' }] },
  published01: { id: 'published01', status: 'published', title: 'Published Test', panels: [{ n: 1, prompt: 'p', caption: 'c' }] },
  approved01: { id: 'approved01', status: 'approved', title: 'Approved Test', panels: [{ n: 1, prompt: 'p', caption: 'c' }] },
  draft01: { id: 'draft01', status: 'draft', title: 'Draft Test', panels: [{ n: 1, prompt: 'p', caption: 'c' }] },
};

const store = {
  find: (id) => {
    const rec = inMemoryScenarios[id];
    if (!rec) return null;
    return { state: rec.status, record: rec };
  },
  get: (id) => {
    const rec = inMemoryScenarios[id];
    if (!rec) throw new Error('not found');
    return { state: rec.status, record: rec };
  },
};

let nextRunnerResult = null;
let lastRunnerArgs = null;

const runner = {
  run: async (bin, args, opts) => {
    lastRunnerArgs = { bin, args, opts };
    return nextRunnerResult;
  },
};

const { scenariosRouter } = await import('../web/routes/scenarios.js');
import { errorMiddleware } from '../web/lib/errors.js';

function makeApp() {
  const app = express();
  app.use((req, _res, next) => {
    req.id = 'test-req-' + Math.random().toString(36).slice(2, 8);
    next();
  });
  app.use(express.json());
  app.use('/api/scenarios', scenariosRouter({ config, store, lifecycle: {}, runner, jobManager: { enqueueRender: () => ({}), enqueueRevision: () => ({}), enqueuePublish: () => ({}) } }));
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
      req.on('error', (err) => { server.close(); reject(err); });
      if (data) req.write(data);
      req.end();
    });
  });
}

test('T4: POST /:id/book with valid style returns 201 + path/size', async () => {
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: true, scenario_id: 'rendered01', style: 'sentry', path: 'data/comics/rendered01-book.html', size_bytes: 27175, size_kb: 26.5 }),
    stderr: '',
  };
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/rendered01/book', { style: 'sentry' });
  assert.equal(res.status, 201);
  assert.equal(res.body.style, 'sentry');
  assert.equal(res.body.size_kb, 26.5);
});

test('T4: POST /:id/book validates style enum', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/rendered01/book', { style: 'no-such-style' });
  assert.equal(res.status, 400);
  assert.equal(res.body.error.code, 'INVALID_BOOK_STYLE');
});

test('T4: POST /:id/book rejects draft state', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/draft01/book', { style: 'sentry' });
  assert.equal(res.status, 409);
  assert.equal(res.body.error.code, 'BOOK_REQUIRES_RENDERED');
});

test('T4: POST /:id/book rejects approved state', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/book', { style: 'sentry' });
  assert.equal(res.status, 409);
  assert.equal(res.body.error.code, 'BOOK_REQUIRES_RENDERED');
});

test('T4: POST /:id/book allows published state', async () => {
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: true, scenario_id: 'published01', style: 'ramstein', path: 'data/comics/published01-book.html', size_bytes: 26759, size_kb: 26.1 }),
    stderr: '',
  };
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/published01/book', { style: 'ramstein' });
  assert.equal(res.status, 201);
  assert.equal(res.body.style, 'ramstein');
});

test('T4: POST /:id/book rejects unknown scenario', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/unknown00/book', { style: 'sentry' });
  assert.equal(res.status, 404);
  assert.equal(res.body.error.code, 'SCENARIO_NOT_FOUND');
});

test('T4: POST /:id/book forwards title/subtitle/provider to Python', async () => {
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: true, scenario_id: 'rendered01', style: 'sentry', path: 'data/comics/rendered01-book.html', size_bytes: 27000, size_kb: 26.4 }),
    stderr: '',
  };
  const app = makeApp();
  await request(app, 'POST', '/api/scenarios/rendered01/book', {
    style: 'sentry',
    title: 'Custom Title',
    subtitle: 'Sub',
    provider: 'draw-things',
  });
  assert.ok(lastRunnerArgs.args.includes('--title'));
  const titleIdx = lastRunnerArgs.args.indexOf('--title');
  assert.equal(lastRunnerArgs.args[titleIdx + 1], 'Custom Title');
  assert.ok(lastRunnerArgs.args.includes('--provider'));
  const providerIdx = lastRunnerArgs.args.indexOf('--provider');
  assert.equal(lastRunnerArgs.args[providerIdx + 1], 'draw-things');
});

test('T4: POST /:id/book propagates Python error', async () => {
  nextRunnerResult = {
    code: 0,
    stdout: JSON.stringify({ ok: false, error: 'No panels', code: 'RENDER_BOOK_FAILED' }),
    stderr: '',
  };
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/rendered01/book', { style: 'sentry' });
  assert.equal(res.status, 500);
});
