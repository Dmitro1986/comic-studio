// T2 — panelCount validation tests
import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  panelCount,
  PANEL_COUNTS,
  MIN_PANEL_COUNT,
  MAX_PANEL_COUNT,
  DEFAULT_PANEL_COUNT,
} from '../web/lib/validation.js';

test('T2: panelCount returns integer when valid', () => {
  assert.equal(panelCount(3), 3);
  assert.equal(panelCount(4), 4);
  assert.equal(panelCount(5), 5);
  assert.equal(panelCount(6), 6);
});

test('T2: panelCount defaults to DEFAULT_PANEL_COUNT when undefined', () => {
  assert.equal(panelCount(undefined), DEFAULT_PANEL_COUNT);
  assert.equal(panelCount(null), DEFAULT_PANEL_COUNT);
});

test('T2: panelCount rejects 0', () => {
  assert.throws(() => panelCount(0), (err) => err.code === 'INVALID_PANEL_COUNT');
});

test('T2: panelCount rejects 2', () => {
  assert.throws(() => panelCount(2), (err) => err.code === 'INVALID_PANEL_COUNT');
});

test('T2: panelCount rejects 7', () => {
  assert.throws(() => panelCount(7), (err) => err.code === 'INVALID_PANEL_COUNT');
});

test('T2: panelCount rejects non-integer (3.5)', () => {
  assert.throws(() => panelCount(3.5), (err) => err.code === 'INVALID_PANEL_COUNT');
});

test('T2: panelCount rejects negative', () => {
  assert.throws(() => panelCount(-1), (err) => err.code === 'INVALID_PANEL_COUNT');
});

test('T2: panelCount accepts string "5" (coerced)', () => {
  assert.equal(panelCount('5'), 5);
});

test('T2: PANEL_COUNTS exports frozen [3,4,5,6]', () => {
  assert.deepEqual([...PANEL_COUNTS], [3, 4, 5, 6]);
  assert.equal(MIN_PANEL_COUNT, 3);
  assert.equal(MAX_PANEL_COUNT, 6);
  assert.equal(DEFAULT_PANEL_COUNT, 3);
});
