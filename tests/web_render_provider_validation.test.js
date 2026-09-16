// T3 — renderProvider + renderProvider validation tests
import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  renderProvider,
  RENDER_PROVIDERS,
  DEFAULT_RENDER_PROVIDER,
} from '../web/lib/validation.js';

test('T3: renderProvider returns string when valid', () => {
  assert.equal(renderProvider('minimax'), 'minimax');
  assert.equal(renderProvider('draw-things'), 'draw-things');
});

test('T3: renderProvider defaults to DEFAULT_RENDER_PROVIDER when undefined', () => {
  assert.equal(renderProvider(undefined), DEFAULT_RENDER_PROVIDER);
  assert.equal(renderProvider(null), DEFAULT_RENDER_PROVIDER);
});

test('T3: renderProvider normalises case', () => {
  assert.equal(renderProvider('MiniMax'), 'minimax');
  assert.equal(renderProvider('Draw-Things'), 'draw-things');
});

test('T3: renderProvider rejects unknown provider', () => {
  assert.throws(() => renderProvider('openai'), (err) => err.code === 'INVALID_RENDER_PROVIDER');
  assert.throws(() => renderProvider('midjourney'), (err) => err.code === 'INVALID_RENDER_PROVIDER');
});

test('T3: renderProvider rejects empty string', () => {
  assert.throws(() => renderProvider(''), (err) => err.code === 'INVALID_RENDER_PROVIDER');
});

test('T3: RENDER_PROVIDERS exports frozen list', () => {
  assert.deepEqual([...RENDER_PROVIDERS], ['minimax', 'draw-things']);
  assert.equal(DEFAULT_RENDER_PROVIDER, 'minimax');
});
