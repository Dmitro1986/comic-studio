import express from 'express';
import { asyncRoute, badRequest, conflict, notFound } from '../lib/errors.js';
import * as validate from '../lib/validation.js';
import { parseJsonResult } from '../lib/process_runner.js';
import { serializeScenario } from '../lib/scenario_store.js';
import { serializeJob } from '../lib/job_store.js';

export function scenariosRouter({ config, store, lifecycle, runner, jobManager }) {
  const router = express.Router();

  router.get('/', (req, res) => {
    const selected = validate.status(String(req.query.status || 'all'), { allowAll: true });
    const { items, invalidCount } = store.list(selected);
    res.json({ items: items.map(item => serializeScenario(item)), invalid_count: invalidCount, request_id: req.id });
  });

  router.post('/', asyncRoute(async (req, res) => {
    const body = req.body || {};
    const content = validate.boundedText(body.content, { field: 'content', max: config.maxContentChars, code: 'INVALID_CONTENT' });
    const imageStyle = validate.imageStyle(body.image_style || 'comic');
    const captionStyle = validate.captionStyle(body.caption_style || 'bubble');
    const source = validate.classifyContent(content);
    const args = [
      'scripts/ingest_and_draft.py', '--skip-notify', '--json-result',
      '--image-style', imageStyle, '--style', captionStyle,
      source.flag, source.value,
    ];
    const processResult = await runner.run(config.pythonBin, args, {
      cwd: config.projectRoot,
      timeoutMs: config.ingestTimeoutMs,
      outputLimit: config.processOutputLimit,
      requestId: req.id,
      operation: 'scenario.create',
    });
    const result = parseJsonResult(processResult.stdout);
    if (!result.ok || !result.id) throw new Error('Draft process returned an unsuccessful result');
    const id = validate.scenarioId(result.id);
    const candidate = store.get(id);
    if (candidate.state !== 'draft') throw conflict('INVALID_DRAFT_RESULT', 'Created scenario is not in draft state');
    res.status(201).json({ ok: true, id, status: 'draft', request_id: req.id });
  }));

  router.get('/:id', (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const candidate = store.get(id);
    res.json({ ...serializeScenario(candidate.record, { detail: true }), request_id: req.id });
  });

  router.get('/:id/export/:format', asyncRoute(async (req, res, next) => {
    const id = validate.scenarioId(req.params.id);
    const fmt = (req.params.format || '').toLowerCase();
    if (!['pdf', 'zip'].includes(fmt)) return next();

    const candidate = store.find(id);
    if (!candidate || !['rendered', 'published'].includes(candidate.state)) {
      return next(notFound('EXPORT_NOT_READY', 'Scenario must be rendered or published to export'));
    }

    const outPath = validate.safeResolve(config.dataRoot, 'comics', `${id}.${fmt}`);
    const args = ['scripts/export_comic.py', '--scenario-id', id, '--format', fmt, '--output', outPath, '--json-result'];
    const processResult = await runner.run(config.pythonBin, args, {
      cwd: config.projectRoot,
      timeoutMs: 30000,
      outputLimit: config.processOutputLimit,
      requestId: req.id,
      operation: `scenario.export.${fmt}`,
    });
    const result = parseJsonResult(processResult.stdout);
    if (!result.ok) throw new Error(result.error || 'Export process failed');

    res.set('Content-Type', fmt === 'pdf' ? 'application/pdf' : 'application/zip');
    res.set('Content-Disposition', `attachment; filename="${id}.${fmt}"`);
    return res.sendFile(outPath);
  }));

  router.post('/:id/approve', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const result = await lifecycle.approve(id);
    res.json({ ok: true, id, status: 'approved', idempotent: result.idempotent, request_id: req.id });
  }));

  router.post('/:id/reject', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const result = await lifecycle.reject(id);
    res.json({ ok: true, id, status: 'rejected', idempotent: result.idempotent, request_id: req.id });
  }));

  router.post('/:id/render', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const mode = validate.renderMode(req.body?.mode || 'initial');
    const active = jobManager.jobStore?.activeForScenario?.(id);
    if (active) throw conflict('BUSY', 'Another job is already active for this scenario', { job_id: active.id, type: active.type });
    const candidate = lifecycle.renderPolicy(id, mode);
    let renderSeed = candidate.record.seed;
    if (req.body?.seed !== undefined) {
      renderSeed = validate.seed(req.body.seed, { min: config.minSeed, max: config.maxSeed });
      if (candidate.state === 'approved') await lifecycle.setSeed(id, renderSeed);
    }
    const job = jobManager.enqueueRender({ scenarioId: id, mode, seed: renderSeed, requestId: req.id });
    res.status(202).json({ ok: true, job: serializeJob(job), request_id: req.id });
  }));

  router.post('/:id/seed', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const value = validate.seed(req.body?.seed, { min: config.minSeed, max: config.maxSeed });
    const result = await lifecycle.setSeed(id, value);
    res.json({ ok: true, id, seed: result.record.seed, request_id: req.id });
  }));

  // HTML preview — fast, no MiniMax call, shows panel structure + captions
  router.get('/:id/preview', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const candidate = lifecycle.store.find(id);
    if (!candidate) throw notFound('SCENARIO_NOT_FOUND', `Scenario ${id} not found`);
    const scenario = candidate.record;
    const panels = scenario.panels || [];

    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const title = scenario.title || 'Без названия';
    const style = scenario.style || 'star';
    const imageStyle = scenario.image_style || 'comic';
    const tone = scenario.tone || 'epic';

    // Build simple HTML preview with panel structure and captions
    const panelsHtml = panels.map((p, i) => {
      const n = p.n || (i + 1);
      const caption = esc(p.caption || '');
      return `
      <div class="panel">
        <div class="panel-number">Панель ${n}</div>
        <div class="panel-placeholder">⏳ Ожидает рендера</div>
        <div class="panel-caption">${caption}</div>
      </div>`;
    }).join('\n');

    const html = `<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Превью: ${esc(title)}</title>
  <style>
    body { font-family: sans-serif; background: #1a1a2e; color: #eee; padding: 2rem; }
    h1 { color: #ffd700; margin-bottom: 0.5rem; }
    .meta { color: #888; margin-bottom: 2rem; }
    .preview-badge { background: #ff6b35; color: white; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.85rem; display: inline-block; margin-bottom: 1.5rem; }
    .panels { display: flex; flex-direction: column; gap: 1.5rem; max-width: 800px; margin: 0 auto; }
    .panel { background: #16213e; border-radius: 8px; padding: 1rem; border: 1px solid #0f3460; }
    .panel-number { color: #e94560; font-size: 0.85rem; margin-bottom: 0.5rem; }
    .panel-placeholder { background: #0f3460; border-radius: 4px; height: 120px; display: flex; align-items: center; justify-content: center; color: #555; margin-bottom: 0.75rem; }
    .panel-caption { color: #ffd700; font-size: 1.1rem; text-align: center; padding: 0.5rem; background: #0f3460; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>${esc(title)}</h1>
  <div class="meta">Стиль: ${esc(style)} · Рисунок: ${esc(imageStyle)} · Тон: ${esc(tone)}</div>
  <div class="preview-badge">⚡ Превью — без рендера</div>
  <div class="panels">${panelsHtml}</div>
</body>
</html>`;

    res.set('Content-Type', 'text/html; charset=utf-8');
    res.send(html);
  }));

  router.post('/:id/feedback', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    await lifecycle.recordFeedback(id, req.body?.text || '');
    res.status(409).json({ error: { code: 'REVISION_REQUIRED', message: 'Use /revise endpoint', request_id: req.id } });
  }));

  router.post('/:id/revise', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const body = req.body || {};
    const feedback = Array.isArray(body.feedback) ? body.feedback : [];
    if (!feedback.length) throw badRequest('REVISION_FEEDBACK_REQUIRED', 'Revision request requires non-empty feedback list');
    if (feedback.length > config.maxRevisionFeedbackCount) {
      throw badRequest('REVISION_FEEDBACK_LIMIT', `Revision supports at most ${config.maxRevisionFeedbackCount} feedback items`);
    }
    const sourceContext = typeof body.source_context === 'string' ? body.source_context : '';
    const imageStyle = body.image_style ? validate.imageStyle(body.image_style) : undefined;
    const existing = lifecycle.store.find(id);
    if (existing && ['revision_queued', 'revision_running'].includes(existing.record.revision_status)) {
      const active = jobManager.jobStore.activeForScenario(id);
      throw conflict('REVISION_ALREADY_RUNNING', 'Revision is already queued or running for this scenario', { job_id: active?.id, revision_status: existing.record.revision_status });
    }
    const result = await lifecycle.revise({ id, requestId: req.id, feedback, sourceContext, imageStyle, jobManager });
    res.status(202).json({
      ok: true,
      id,
      status: 'draft',
      job: serializeJob(result.job),
      revision_endpoint: `/api/scenarios/${id}/revise`,
      request_id: req.id,
    });
  }));

  router.post('/:id/restyle', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const style = req.body?.style ? validate.captionStyle(req.body.style) : undefined;
    const captions = Array.isArray(req.body?.captions) ? req.body.captions : undefined;
    
    const existing = store.get(id);
    if (!['draft', 'approved', 'rendered', 'published'].includes(existing.state)) {
      throw conflict('INVALID_STATE', 'Restyle works only for active scenarios');
    }
    
    if (captions || style) {
      await store.update(id, async (record) => {
        if (style) record.style = style;
        if (captions) {
          if (captions.length !== record.panels.length) {
            const err = new Error('Captions length must match panels length');
            err.code = 'INVALID_CAPTIONS';
            throw err;
          }
          record.panels.forEach((p, i) => {
            if (typeof captions[i] === 'string') p.caption = captions[i];
          });
        }
        return record;
      });
    }

    const currentStyle = style || existing.record.style || 'bubble';

    // Only run python restyle script if comic has rendered image artifacts
    if (['rendered', 'published'].includes(existing.state)) {
      const args = ['scripts/restyle.py', '--scenario-id', id, '--style', currentStyle];
      await runner.run(config.pythonBin, args, {
        cwd: config.projectRoot,
        timeoutMs: 30000,
        outputLimit: config.processOutputLimit,
        requestId: req.id,
        operation: 'scenario.restyle',
      });
    }

    res.json({ ok: true, id, status: existing.state, style: currentStyle, request_id: req.id });
  }));

  router.post('/:id/remix', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const overrides = {};
    const body = req.body || {};
    if (body.title) overrides.title = validate.boundedText(body.title, { field: 'title', max: 200, code: 'INVALID_TITLE' });
    if (body.image_style) overrides.image_style = validate.imageStyle(body.image_style);
    if (body.style) overrides.style = validate.captionStyle(body.style);
    if (body.tone) overrides.tone = body.tone;
    if (body.seed !== undefined) overrides.seed = validate.seed(body.seed, { min: 0, max: 2_147_483_647 });
    const result = lifecycle.remix(id, overrides, { requestId: req.id });
    res.status(201).json({
      ok: true,
      id: result.record.id,
      status: 'draft',
      remix_of: result.record.remix_of,
      revision_endpoint: `/api/scenarios/${result.record.id}/revise`,
      request_id: req.id,
    });
  }));

  router.delete('/:id', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    if (req.query.confirm !== 'true') throw conflict('DELETE_CONFIRMATION_REQUIRED', 'Explicit delete confirmation is required');
    const artifacts = await store.deleteMutable(id);
    res.json({ ok: true, id, artifacts, request_id: req.id });
  }));

  router.post('/:id/publish', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const existing = store.get(id);
    if (existing.state !== 'rendered') {
      throw conflict('INVALID_STATE', 'Only rendered scenarios can be published');
    }
    const args = ['scripts/publish_rendered.js', '--scenario-id', id];
    await runner.run(process.execPath, args, {
      cwd: config.projectRoot,
      timeoutMs: 60000,
      outputLimit: config.processOutputLimit,
      requestId: req.id,
      operation: 'scenario.publish',
    });
    // The script moves the file, so it should now be in 'published' state
    const updated = store.get(id);
    res.json({ ok: true, id, status: updated.state, request_id: req.id });
  }));



  // POST /api/scenarios/:id/unpublish — вернуть в rendered (снять с публикации)
  router.post('/:id/unpublish', asyncRoute(async (req, res) => {
    const id = validate.scenarioId(req.params.id);
    const existing = store.get(id);
    
    if (existing.state !== 'published') {
      throw conflict('INVALID_STATE', 'Only published scenarios can be unpublished');
    }
    
    // Transition the state using the store to ensure data consistency
    await store.transition(id, 'published', 'rendered');
    
    // Remove comic HTML/webp artifacts
    const htmlPath = path.join(config.dataRoot, 'comics', `${id}.html`);
    const webpPath = path.join(config.dataRoot, 'comics', `${id}.webp`);
    
    await Promise.all([
      require('fs').promises.unlink(htmlPath).catch(() => {}),
      require('fs').promises.unlink(webpPath).catch(() => {}),
    ]);
    
    res.json({ ok: true, id, status: 'rendered', request_id: req.id });
  }));

  return router;
}
