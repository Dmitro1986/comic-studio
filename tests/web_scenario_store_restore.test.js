// T1 — ScenarioStore.restoreApproval cycle test
// Validates that revokeApproval → restoreApproval returns scenario to its original
// queue with status and metadata preserved.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

import { ScenarioStore } from '../web/lib/scenario_store.js';

function makeDataRoot() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'comic-store-'));
  for (const state of ['draft', 'approved', 'rendered', 'published', 'rejected']) {
    fs.mkdirSync(path.join(root, 'scenarios', state), { recursive: true });
  }
  return root;
}

function writeScenario(root, state, record) {
  const dir = path.join(root, 'scenarios', state);
  fs.writeFileSync(path.join(dir, `${record.id}.json`), JSON.stringify(record, null, 2));
}

function readScenario(root, state, id) {
  const file = path.join(root, 'scenarios', state, `${id}.json`);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, 'utf-8'));
}

function listQueue(root, state) {
  const dir = path.join(root, 'scenarios', state);
  return fs.readdirSync(dir).filter((f) => f.endsWith('.json'));
}

test('T1: revokeApproval preserves approved_at, panel_paths, render_revision', async () => {
  const root = makeDataRoot();
  const store = new ScenarioStore({ dataRoot: root, logger: null });
  const id = 'restore01';
  const record = {
    id,
    status: 'approved',
    title: 'Sentry Test',
    tone: 'epic',
    style: 'star',
    image_style: 'comic',
    layout: 'comic',
    aspect_ratio: '16:9',
    panels: [
      { n: 1, prompt: 'p1', caption: 'c1' },
      { n: 2, prompt: 'p2', caption: 'c2' },
      { n: 3, prompt: 'p3', caption: 'c3' },
    ],
    approved_at: '2026-09-15T10:00:00.000Z',
    feedback: [],
  };
  writeScenario(root, 'approved', record);

  await store.revokeApproval(id, { requestId: 'test-revoke' });

  const draft = readScenario(root, 'draft', id);
  assert.equal(draft.status, 'draft', 'moved to draft');
  assert.equal(draft.revision_source, 'approved', 'remembers source');
  assert.equal(draft.revision_status, 'revision_queued', 'queued status set');
  assert.equal(draft.approved_at, record.approved_at, 'approved_at preserved through revoke');
  assert.equal(fs.existsSync(path.join(root, 'scenarios', 'approved', `${id}.json`)), false, 'source file removed');
});

test('T1: restoreApproval returns scenario to approved with status cleaned', async () => {
  const root = makeDataRoot();
  const store = new ScenarioStore({ dataRoot: root, logger: null });
  const id = 'restore02';
  const record = {
    id,
    status: 'approved',
    title: 'Ramstein Test',
    tone: 'epic',
    style: 'star',
    image_style: 'comic',
    layout: 'comic',
    aspect_ratio: '16:9',
    panels: [
      { n: 1, prompt: 'p1', caption: 'c1' },
      { n: 2, prompt: 'p2', caption: 'c2' },
      { n: 3, prompt: 'p3', caption: 'c3' },
    ],
    approved_at: '2026-09-15T11:00:00.000Z',
    feedback: [],
  };
  writeScenario(root, 'approved', record);
  await store.revokeApproval(id, { requestId: 'rev-1' });

  const result = await store.restoreApproval(id, { requestId: 'res-1', reason: 'llm_fallback' });
  assert.equal(result.restored_to, 'approved', 'restored_to is approved');

  const restored = readScenario(root, 'approved', id);
  assert.equal(restored.status, 'approved', 'status back to approved');
  assert.equal(restored.revision_status, 'none', 'revision_status cleaned');
  assert.equal(restored.revision_source, undefined, 'revision_source removed');
  assert.equal(restored.approved_at, record.approved_at, 'approved_at preserved through full cycle');
  assert.ok(Array.isArray(restored.revision_history), 'revision_history exists');
  const lastEntry = restored.revision_history[restored.revision_history.length - 1];
  assert.equal(lastEntry.status, 'revision_restored', 'history entry marked as restored');
  assert.equal(lastEntry.reason, 'llm_fallback', 'history entry has reason');

  assert.equal(fs.existsSync(path.join(root, 'scenarios', 'draft', `${id}.json`)), false, 'draft file removed');
});

test('T1: restoreApproval from rendered source preserves render_revision and panel_paths', async () => {
  const root = makeDataRoot();
  const store = new ScenarioStore({ dataRoot: root, logger: null });
  const id = 'restore03';
  const record = {
    id,
    status: 'rendered',
    title: 'Puppet Test',
    tone: 'dark',
    style: 'gothic',
    image_style: 'realistic',
    layout: 'comic',
    aspect_ratio: '16:9',
    panels: [
      { n: 1, prompt: 'p1', caption: 'c1' },
      { n: 2, prompt: 'p2', caption: 'c2' },
      { n: 3, prompt: 'p3', caption: 'c3' },
    ],
    rendered_at: '2026-09-15T12:00:00.000Z',
    render_revision: 2,
    panel_paths: [`data/comics/${id}/panel_1.png`, `data/comics/${id}/panel_2.png`, `data/comics/${id}/panel_3.png`],
    feedback: [],
  };
  writeScenario(root, 'rendered', record);
  await store.revokeApproval(id, { requestId: 'rev-2' });
  await store.restoreApproval(id, { requestId: 'res-2', reason: 'panel_count_out_of_range' });

  const restored = readScenario(root, 'rendered', id);
  assert.equal(restored.status, 'rendered');
  assert.equal(restored.render_revision, 2, 'render_revision preserved');
  assert.deepEqual(restored.panel_paths, record.panel_paths, 'panel_paths preserved');
  assert.equal(restored.rendered_at, record.rendered_at, 'rendered_at preserved');
});

test('T1: restoreApproval refuses if scenario is not in draft', async () => {
  const root = makeDataRoot();
  const store = new ScenarioStore({ dataRoot: root, logger: null });
  const id = 'restore04';
  const record = {
    id,
    status: 'draft',
    title: 'Stuck Draft',
    tone: 'epic',
    style: 'star',
    image_style: 'comic',
    layout: 'comic',
    aspect_ratio: '16:9',
    panels: [{ n: 1, prompt: 'p', caption: 'c' }],
    feedback: [],
    // intentionally NO revision_source — legacy draft
  };
  writeScenario(root, 'draft', record);

  await assert.rejects(
    () => store.restoreApproval(id, { requestId: 'res-3' }),
    (err) => err.code === 'RESTORE_SOURCE_UNKNOWN',
  );
});

test('T1: full revision fallback cycle — approved → draft → approved', async () => {
  const root = makeDataRoot();
  const store = new ScenarioStore({ dataRoot: root, logger: null });
  const id = 'cycle05';

  const record = {
    id,
    status: 'approved',
    title: 'Full Cycle',
    tone: 'epic',
    style: 'star',
    image_style: 'comic',
    layout: 'comic',
    aspect_ratio: '16:9',
    panels: [
      { n: 1, prompt: 'p1', caption: 'c1' },
      { n: 2, prompt: 'p2', caption: 'c2' },
      { n: 3, prompt: 'p3', caption: 'c3' },
    ],
    approved_at: '2026-09-10T08:00:00.000Z',
    feedback: [],
  };
  writeScenario(root, 'approved', record);

  // Step 1: Operator triggers revision
  await store.revokeApproval(id, { requestId: 'req-1' });
  assert.deepEqual(listQueue(root, 'draft'), [`${id}.json`], 'file in draft after revoke');
  assert.deepEqual(listQueue(root, 'approved'), [], 'no file in approved after revoke');

  // Step 2: LLM fails → graceful fallback restores scenario
  await store.restoreApproval(id, { requestId: 'res-final', reason: 'llm_timeout' });
  assert.deepEqual(listQueue(root, 'draft'), [], 'no file in draft after restore');
  assert.deepEqual(listQueue(root, 'approved'), [`${id}.json`], 'file back in approved');

  // Step 3: Scenario is queryable again in approved state
  const candidate = store.find(id);
  assert.ok(candidate, 'scenario is findable');
  assert.equal(candidate.state, 'approved', 'state is approved');
  assert.equal(candidate.record.title, 'Full Cycle', 'content unchanged');
  assert.equal(candidate.record.panels.length, 3, 'panels unchanged');
  assert.equal(candidate.record.revision_status, 'none', 'revision_status reset');
});
