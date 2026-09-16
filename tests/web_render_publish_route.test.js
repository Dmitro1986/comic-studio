// T3 — POST /api/scenarios/:id/render with provider+publish
//   and POST /api/scenarios/:id/publish
//
// These tests bypass the JobManager queue (using stubs) so the routes can be
// verified without spawning real Python or Node processes.

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

// In-memory store stub
const inMemoryScenarios = {
  'approved01': {
    id: 'approved01',
    status: 'approved',
    title: 'Approved Test',
    seed: 42,
    panels: [{ n: 1, prompt: 'p', caption: 'c' }],
  },
  'rendered01': {
    id: 'rendered01',
    status: 'rendered',
    title: 'Rendered Test',
    seed: 7,
    panels: [{ n: 1, prompt: 'p', caption: 'c' }],
  },
  'draft01': {
    id: 'draft01',
    status: 'draft',
    title: 'Draft Test',
    panels: [{ n: 1, prompt: 'p', caption: 'c' }],
  },
  'published01': {
    id: 'published01',
    status: 'published',
    title: 'Published Test',
    published_url: 'https://example.com/comics/published01.html',
  },
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

const lifecycle = {
  renderPolicy: (id, mode) => {
    const rec = inMemoryScenarios[id];
    if (!rec) throw new Error('not found');
    return { state: rec.status, record: rec };
  },
  setSeed: async () => ({ record: {} }),
};

let lastJobEnqueued = null;

const jobManager = {
  jobStore: {
    activeForScenario: () => null,
  },
  enqueueRender: (params) => {
    lastJobEnqueued = { type: 'render', ...params };
    return { id: 'job-test', status: 'queued', ...params };
  },
  enqueuePublish: (params) => {
    lastJobEnqueued = { type: 'publish', ...params };
    return { id: 'job-test', status: 'queued', ...params };
  },
};

const { scenariosRouter } = await import('../web/routes/scenarios.js');
import { errorMiddleware } from '../web/lib/errors.js';
import { serializeJob } from '../web/lib/job_store.js';

function makeApp() {
  const app = express();
  app.use((req, _res, next) => {
    req.id = 'test-req-' + Math.random().toString(36).slice(2, 8);
    next();
  });
  app.use(express.json());
  app.use('/api/scenarios', scenariosRouter({ config, store, lifecycle, runner: { run: async () => ({ stdout: '{}' }) }, jobManager }));
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

test('T3: POST /:id/render with provider=draw-things forwards provider to jobManager', async () => {
  lastJobEnqueued = null;
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/render', {
    provider: 'draw-things',
  });
  assert.equal(res.status, 202);
  assert.equal(res.body.provider, 'draw-things');
  assert.equal(lastJobEnqueued.type, 'render');
  assert.equal(lastJobEnqueued.provider, 'draw-things');
});

test('T3: POST /:id/render with publish=true enqueues render with publish flag', async () => {
  lastJobEnqueued = null;
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/render', {
    publish: true,
  });
  assert.equal(res.status, 202);
  assert.equal(res.body.publish, true);
  assert.equal(lastJobEnqueued.publish, true);
});

test('T3: POST /:id/render defaults provider to minimax', async () => {
  lastJobEnqueued = null;
  const app = makeApp();
  await request(app, 'POST', '/api/scenarios/approved01/render', {});
  assert.equal(lastJobEnqueued.provider, 'minimax');
});

test('T3: POST /:id/render rejects invalid provider', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/render', {
    provider: 'openai',
  });
  assert.equal(res.status, 400);
  assert.equal(res.body.error.code, 'INVALID_RENDER_PROVIDER');
});

test('T3: POST /:id/render with both provider and publish', async () => {
  lastJobEnqueued = null;
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/render', {
    provider: 'draw-things',
    publish: true,
  });
  assert.equal(res.status, 202);
  assert.equal(res.body.provider, 'draw-things');
  assert.equal(res.body.publish, true);
  assert.equal(lastJobEnqueued.provider, 'draw-things');
  assert.equal(lastJobEnqueued.publish, true);
});

test('T3: POST /:id/publish from rendered state returns 202', async () => {
  lastJobEnqueued = null;
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/rendered01/publish');
  assert.equal(res.status, 202);
  assert.equal(lastJobEnqueued.type, 'publish');
  assert.equal(lastJobEnqueued.scenarioId, 'rendered01');
});

test('T3: POST /:id/publish from published state is idempotent (still allowed)', async () => {
  lastJobEnqueued = null;
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/published01/publish');
  assert.equal(res.status, 202);
});

test('T3: POST /:id/publish from draft state rejected', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/draft01/publish');
  assert.equal(res.status, 409);
  assert.equal(res.body.error.code, 'PUBLISH_REQUIRES_RENDERED');
});

test('T3: POST /:id/publish from approved state rejected', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/approved01/publish');
  assert.equal(res.status, 409);
  assert.equal(res.body.error.code, 'PUBLISH_REQUIRES_RENDERED');
});

test('T3: POST /:id/publish rejects unknown scenario', async () => {
  const app = makeApp();
  const res = await request(app, 'POST', '/api/scenarios/unknown123/publish');
  assert.equal(res.status, 404);
  assert.equal(res.body.error.code, 'SCENARIO_NOT_FOUND');
});
