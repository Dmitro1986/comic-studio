// T3 — JobManager.enqueueRender with provider + publish chain + enqueuePublish

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { JobManager } from '../web/lib/job_manager.js';

function makeDataRoot() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'comic-jm-'));
  for (const dir of ['draft', 'approved', 'rendered', 'published', 'rejected', 'jobs']) {
    fs.mkdirSync(path.join(root, dir === 'jobs' ? 'jobs' : `scenarios/${dir}`), { recursive: true });
  }
  // Also create dataRoot/scenarios tree
  fs.mkdirSync(path.join(root, 'scenarios'), { recursive: true });
  return root;
}

function makeConfig(dataRoot) {
  return {
    projectRoot: dataRoot,
    dataRoot,
    pythonBin: 'python3',
    nodeBin: 'node',
    renderTimeoutMs: 60000,
    revisionTimeoutMs: 60000,
    revisionOutputLimit: 65536,
    publishTimeoutMs: 60000,
    processOutputLimit: 65536,
  };
}

class FakeRunner {
  constructor() {
    this.calls = [];
    this.responses = [];
  }
  setNext(response) { this.responses.push(response); }
  async run(executable, args, opts) {
    this.calls.push({ executable, args, opts });
    if (this.responses.length === 0) {
      return { code: 0, stdout: '{"ok": true}', stderr: '' };
    }
    return this.responses.shift();
  }
}

class FakeJobStore {
  constructor(dataRoot) {
    this.dataRoot = dataRoot;
    this.jobs = new Map();
    this.activeJobs = [];
  }
  create(job) {
    const id = 'job-' + Math.random().toString(36).slice(2, 10);
    // Match real JobStore: store snake_case `scenario_id`, not camelCase `scenarioId`.
    const stored = {
      ...job,
      scenario_id: job.scenarioId ?? job.scenario_id,
      id,
      status: 'queued',
      created_at: new Date().toISOString(),
    };
    delete stored.scenarioId;
    this.jobs.set(id, stored);
    this.activeJobs.push(stored);
    return stored;
  }
  update(id, patch) {
    const current = this.jobs.get(id);
    if (!current) throw new Error('not found');
    const next = { ...current, ...patch };
    this.jobs.set(id, next);
    if (['succeeded', 'failed', 'interrupted'].includes(patch.status)) {
      this.activeJobs = this.activeJobs.filter(j => j.id !== id);
    }
    return next;
  }
  get(id) {
    return this.jobs.get(id);
  }
  list() {
    return [...this.jobs.values()];
  }
  activeForScenario(scenarioId) {
    return this.activeJobs.find(j => j.scenario_id === scenarioId) || null;
  }
}

test('T3: enqueueRender passes --provider to render script', async () => {
  const dataRoot = makeDataRoot();
  const config = makeConfig(dataRoot);
  const jobStore = new FakeJobStore(dataRoot);
  const runner = new FakeRunner();
  runner.setNext({ code: 0, stdout: '{"ok": true, "comic_path": "/x.png", "render_revision": 1}', stderr: '' });

  const jm = new JobManager({ config, jobStore, runner, logger: null });
  const job = jm.enqueueRender({ scenarioId: 'aabbccdd', mode: 'initial', requestId: 'r1', provider: 'draw-things', publish: false });

  // Wait for job to finish
  await new Promise((resolve) => setTimeout(resolve, 50));

  // The runner should have been called with --provider draw-things
  const renderCall = runner.calls.find(c => c.executable === 'python3');
  assert.ok(renderCall, 'python3 was invoked');
  assert.ok(renderCall.args.includes('--provider'), '--provider flag passed');
  const idx = renderCall.args.indexOf('--provider');
  assert.equal(renderCall.args[idx + 1], 'draw-things', 'provider value is draw-things');
});

test('T3: enqueueRender omits --provider when default minimax', async () => {
  const dataRoot = makeDataRoot();
  const config = makeConfig(dataRoot);
  const jobStore = new FakeJobStore(dataRoot);
  const runner = new FakeRunner();
  runner.setNext({ code: 0, stdout: '{"ok": true, "comic_path": "/x.png", "render_revision": 1}', stderr: '' });

  const jm = new JobManager({ config, jobStore, runner, logger: null });
  jm.enqueueRender({ scenarioId: 'aabbccdd', mode: 'initial', requestId: 'r1', provider: 'minimax', publish: false });
  await new Promise((resolve) => setTimeout(resolve, 50));

  const renderCall = runner.calls.find(c => c.executable === 'python3');
  assert.ok(renderCall, 'python3 invoked');
  assert.ok(!renderCall.args.includes('--provider'), '--provider NOT passed for default minimax');
});

test('T3: render with publish=true enqueues publish after render success', async () => {
  const dataRoot = makeDataRoot();
  const config = makeConfig(dataRoot);
  const jobStore = new FakeJobStore(dataRoot);
  const runner = new FakeRunner();
  // Render success
  runner.setNext({ code: 0, stdout: '{"ok": true, "comic_path": "/x.png", "render_revision": 1}', stderr: '' });
  // Pre-create the published scenario file so publish can read it
  fs.writeFileSync(
    path.join(dataRoot, 'scenarios', 'published', 'aabbccdd.json'),
    JSON.stringify({ id: 'aabbccdd', status: 'published', published_url: 'https://example.com/comics/aabbccdd.html' })
  );
  // Publish success (no JSON output expected, just stdout)
  runner.setNext({ code: 0, stdout: '=== Publication Summary ===\n  ✅ Succeeded: 1\n', stderr: '' });

  const jm = new JobManager({ config, jobStore, runner, logger: null });
  jm.enqueueRender({ scenarioId: 'aabbccdd', mode: 'initial', requestId: 'r1', provider: 'draw-things', publish: true });

  // Wait long enough for both jobs to be enqueued and run
  await new Promise((resolve) => setTimeout(resolve, 200));

  const calls = runner.calls;
  assert.equal(calls.length, 2, 'two process calls (render + publish)');
  assert.equal(calls[0].executable, 'python3', 'first call is python (render)');
  assert.equal(calls[1].executable, 'node', 'second call is node (publish)');
  assert.ok(calls[1].args.includes('--scenario-id'));
  assert.equal(calls[1].args[calls[1].args.indexOf('--scenario-id') + 1], 'aabbccdd');
});

test('T3: render with publish=false does NOT enqueue publish', async () => {
  const dataRoot = makeDataRoot();
  const config = makeConfig(dataRoot);
  const jobStore = new FakeJobStore(dataRoot);
  const runner = new FakeRunner();
  runner.setNext({ code: 0, stdout: '{"ok": true, "comic_path": "/x.png", "render_revision": 1}', stderr: '' });

  const jm = new JobManager({ config, jobStore, runner, logger: null });
  jm.enqueueRender({ scenarioId: 'aabbccdd', mode: 'initial', requestId: 'r1', provider: 'minimax', publish: false });
  await new Promise((resolve) => setTimeout(resolve, 100));

  assert.equal(runner.calls.length, 1, 'only one process call (render)');
  assert.equal(runner.calls[0].executable, 'python3', 'render is python');
});

test('T3: enqueuePublish standalone spawns node script and returns published_url', async () => {
  const dataRoot = makeDataRoot();
  const config = makeConfig(dataRoot);
  const jobStore = new FakeJobStore(dataRoot);
  const runner = new FakeRunner();
  runner.setNext({ code: 0, stdout: 'Published\n', stderr: '' });

  // Pre-create published scenario file
  fs.writeFileSync(
    path.join(dataRoot, 'scenarios', 'published', 'cccc1122.json'),
    JSON.stringify({ id: 'cccc1122', status: 'published', published_url: 'https://example.com/comics/cccc1122.html' })
  );

  const jm = new JobManager({ config, jobStore, runner, logger: null });
  const job = jm.enqueuePublish({ scenarioId: 'cccc1122', requestId: 'r2' });
  await new Promise((resolve) => setTimeout(resolve, 100));

  const publishCall = runner.calls.find(c => c.executable === 'node');
  assert.ok(publishCall, 'node was invoked');
  assert.ok(publishCall.args.includes('--scenario-id'));
  assert.equal(publishCall.args[publishCall.args.indexOf('--scenario-id') + 1], 'cccc1122');

  const finalJob = jobStore.get(job.id);
  assert.equal(finalJob.status, 'succeeded');
  assert.equal(finalJob.result.published_url, 'https://example.com/comics/cccc1122.html');
});

test('T3: publish fails when published_url not found', async () => {
  const dataRoot = makeDataRoot();
  const config = makeConfig(dataRoot);
  const jobStore = new FakeJobStore(dataRoot);
  const runner = new FakeRunner();
  runner.setNext({ code: 0, stdout: 'OK\n', stderr: '' });
  // No published scenario file written

  const jm = new JobManager({ config, jobStore, runner, logger: null });
  const job = jm.enqueuePublish({ scenarioId: 'notpub01', requestId: 'r3' });
  await new Promise((resolve) => setTimeout(resolve, 100));

  const finalJob = jobStore.get(job.id);
  assert.equal(finalJob.status, 'failed');
  assert.match(finalJob.error.message, /no published_url/);
});
