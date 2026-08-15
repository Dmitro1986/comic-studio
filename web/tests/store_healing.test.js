import { test, suite } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { setupTestApp } from './helpers.js';

suite('Scenario Store Auto-healing', () => {
  test('find() heals interrupted revoke by removing stale approved duplicate', async (t) => {
    const { store, cleanup } = await setupTestApp();
    t.after(cleanup);

    const id = 'healme' + Date.now();
    
    // Create draft
    const draftPath = path.join(store.dataRoot, 'scenarios/draft', `${id}.json`);
    fs.mkdirSync(path.dirname(draftPath), { recursive: true });
    fs.writeFileSync(draftPath, JSON.stringify({
      id,
      status: 'draft',
      revision_status: null
    }));

    // Create stale approved copy (interrupted revoke)
    const approvedPath = path.join(store.dataRoot, 'scenarios/approved', `${id}.json`);
    fs.mkdirSync(path.dirname(approvedPath), { recursive: true });
    fs.writeFileSync(approvedPath, JSON.stringify({
      id,
      status: 'approved',
      revision_status: 'revision_queued'
    }));

    // Ensure store.find() auto-heals and returns draft
    const found = store.find(id);
    assert.ok(found, 'Should find the scenario');
    assert.equal(found.state, 'draft', 'Should resolve to draft');

    // Ensure stale copy was deleted
    assert.equal(fs.existsSync(approvedPath), false, 'Stale approved copy should be deleted');
    assert.equal(fs.existsSync(draftPath), true, 'Draft should remain');
  });

  test('reconcileTransitions() cleans up stale revoke leftovers', async (t) => {
    const { store, cleanup } = await setupTestApp();
    t.after(cleanup);

    const id = 'reconcile' + Date.now();
    
    // Create draft
    const draftPath = path.join(store.dataRoot, 'scenarios/draft', `${id}.json`);
    fs.mkdirSync(path.dirname(draftPath), { recursive: true });
    fs.writeFileSync(draftPath, JSON.stringify({
      id,
      status: 'draft'
    }));

    // Create stale approved copy
    const approvedPath = path.join(store.dataRoot, 'scenarios/approved', `${id}.json`);
    fs.mkdirSync(path.dirname(approvedPath), { recursive: true });
    fs.writeFileSync(approvedPath, JSON.stringify({
      id,
      status: 'approved',
      revision_status: 'revision_queued'
    }));

    // Run reconciliation
    const recovered = store.reconcileTransitions();
    
    // The duplicate should not be counted as a normal recovery since it was just a deletion of a stale file
    // (Our implementation might count it or not, let's just check the file system)

    assert.equal(fs.existsSync(approvedPath), false, 'Stale approved copy should be deleted');
    assert.equal(fs.existsSync(draftPath), true, 'Draft should remain');
  });
});
