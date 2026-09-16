import { conflict, unavailable } from './errors.js';
import { parseJsonResult } from './process_runner.js';
import { serializeJob } from './job_store.js';
import { sseBroadcaster } from './sse_broadcaster.js';
import path from 'node:path';

function getRevisionScript() {
  return process.env.REVISION_SCRIPT || 'scripts/revise_scenario.py';
}

function getPublishScript() {
  return process.env.PUBLISH_SCRIPT || 'scripts/publish_rendered.js';
}

export class JobManager {
  constructor({ config, jobStore, runner, logger, onRevisionComplete, onPublishComplete } = {}) {
    this.config = config;
    this.jobStore = jobStore;
    this.runner = runner;
    this.logger = logger;
    this.onRevisionComplete = onRevisionComplete;
    this.onPublishComplete = onPublishComplete;
    this.promises = new Map();
    this.accepting = true;
  }

  enqueueRender({ scenarioId, mode, seed, requestId, provider, publish }) {
    if (!this.accepting) throw unavailable('SERVER_SHUTTING_DOWN', 'Server is shutting down');
    const active = this.jobStore.activeForScenario(scenarioId);
    if (active) throw conflict('BUSY', 'Another job is already active for this scenario', { job_id: active.id, type: active.type });
    const job = this.jobStore.create({
      type: 'render',
      scenarioId,
      mode,
      requestId,
      seed,
      provider: provider || 'minimax',
      publish: Boolean(publish),
    });
    const promise = this._runRender(job).finally(() => this.promises.delete(job.id));
    this.promises.set(job.id, promise);
    return job;
  }

  enqueuePublish({ scenarioId, requestId }) {
    if (!this.accepting) throw unavailable('SERVER_SHUTTING_DOWN', 'Server is shutting down');
    const active = this.jobStore.activeForScenario(scenarioId);
    if (active) throw conflict('BUSY', 'Another job is already active for this scenario', { job_id: active.id, type: active.type });
    const job = this.jobStore.create({
      type: 'publish',
      scenarioId,
      mode: 'initial',
      requestId,
    });
    const promise = this._runPublish(job).finally(() => this.promises.delete(job.id));
    this.promises.set(job.id, promise);
    return job;
  }

  enqueueRevision({ scenarioId, scenarioPath, feedback, sourceContext, sourceContextPreview, requestId, revisionKind = 'standard' }) {
    if (!this.accepting) throw unavailable('SERVER_SHUTTING_DOWN', 'Server is shutting down');
    const active = this.jobStore.activeForScenario(scenarioId);
    if (active) throw conflict('BUSY', 'Another job is already active for this scenario', { job_id: active.id, type: active.type });
    const job = this.jobStore.create({
      type: 'revision',
      scenarioId,
      mode: 'initial',
      requestId,
      revisionKind,
      sourceContextPreview,
      feedbackCount: Array.isArray(feedback) ? feedback.length : 0,
    });
    const promise = this._runRevision(job, { scenarioPath, feedback, sourceContext, revisionKind })
      .finally(() => this.promises.delete(job.id));
    this.promises.set(job.id, promise);
    return job;
  }

  _updateJob(id, patch) {
    const updated = this.jobStore.update(id, patch);
    if (updated) {
      const serialized = serializeJob(updated);
      sseBroadcaster.broadcast(id, 'job_updated', serialized);
      sseBroadcaster.broadcast('all', 'job_updated', serialized);
    }
    return updated;
  }

  async _runRender(job) {
    this._updateJob(job.id, { status: 'running', started_at: new Date().toISOString() });
    const args = ['scripts/render_approved.py', '--scenario-id', job.scenario_id, '--json-result'];
    if (job.provider && job.provider !== 'minimax') {
      args.push('--provider', job.provider);
    }
    if (job.mode === 'rerender') {
      args.push('--rerender', '--staging-dir', `${this.config.dataRoot}/.staging/${job.id}`);
      if (job.seed !== undefined) args.push('--seed', String(job.seed));
    }
    try {
      const processResult = await this.runner.run(this.config.pythonBin, args, {
        cwd: this.config.projectRoot,
        timeoutMs: this.config.renderTimeoutMs,
        outputLimit: this.config.processOutputLimit,
        requestId: job.request_id,
        operation: `render:${job.scenario_id}`,
      });
      const result = parseJsonResult(processResult.stdout);
      if (!result.ok) throw new Error(result.error || 'Renderer reported failure');
      this._updateJob(job.id, {
        status: 'succeeded',
        finished_at: new Date().toISOString(),
        result: {
          scenario_id: job.scenario_id,
          comic_path: result.comic_path,
          render_revision: result.render_revision,
          provider: job.provider || 'minimax',
        },
      });
      this.logger?.info('job.render.succeeded', {
        request_id: job.request_id,
        scenario_id: job.scenario_id,
        job_id: job.id,
        provider: job.provider || 'minimax',
        render_revision: result.render_revision,
      });

      // Auto-publish chain: if render was requested with publish: true, kick off
      // a publish job as a sibling (does NOT block the render job). This makes
      // the MCP `render_comic(id, provider='draw-things', publish=true)` flow a
      // single-shot operation: render then publish.
      if (job.publish) {
        try {
          this.enqueuePublish({ scenarioId: job.scenario_id, requestId: job.request_id });
          this.logger?.info('render.publish.queued', {
            request_id: job.request_id,
            scenario_id: job.scenario_id,
            source_job_id: job.id,
          });
        } catch (publishErr) {
          // Render already succeeded; publish enqueue failure is non-fatal for the render job.
          this.logger?.warn('render.publish.queue_failed', {
            request_id: job.request_id,
            scenario_id: job.scenario_id,
            code: publishErr.code || 'PUBLISH_QUEUE_FAILED',
            message: publishErr.message,
          });
        }
      }
    } catch (error) {
      const current = this.jobStore.get(job.id);
      if (current.status === 'interrupted') return;
      this._updateJob(job.id, {
        status: error.code === 'PROCESS_INTERRUPTED' ? 'interrupted' : 'failed',
        finished_at: new Date().toISOString(),
        error: { code: error.code || 'RENDER_FAILED', message: error.message || 'Render failed' },
      });
      this.logger?.error('job.render.failed', { request_id: job.request_id, scenario_id: job.scenario_id, job_id: job.id, code: error.code || 'RENDER_FAILED' });
    }
  }

  async _runRevision(job, { scenarioPath, feedback, sourceContext, revisionKind }) {
    this._updateJob(job.id, { status: 'running', started_at: new Date().toISOString() });
    const args = [
      getRevisionScript(),
      '--scenario-id', job.scenario_id,
      '--scenario-path', scenarioPath,
      '--json-result',
    ];
    if (Array.isArray(feedback) && feedback.length) {
      args.push('--feedback', JSON.stringify(feedback));
    }
    if (sourceContext) args.push('--source-context', sourceContext);
    let lastStderr = '';
    try {
      const processResult = await this.runner.run(this.config.pythonBin, args, {
        cwd: this.config.projectRoot,
        timeoutMs: this.config.revisionTimeoutMs,
        outputLimit: this.config.revisionOutputLimit,
        requestId: job.request_id,
        operation: `revision:${job.scenario_id}`,
      });
      lastStderr = processResult.stderr || '';
      const parsed = parseJsonResult(processResult.stdout);
      if (!parsed.ok) throw new Error(parsed.error || 'Revision process reported failure');
      // parsed.fallback === true signals graceful fallback (LLM unavailable / invalid output).
      // Job still succeeds — the runtime decides whether to apply, restore, or do nothing.
      const isFallback = parsed.fallback === true;
      this._updateJob(job.id, {
        status: 'succeeded',
        finished_at: new Date().toISOString(),
        result: {
          scenario_id: job.scenario_id,
          revision_at: parsed.revision_at,
          feedback_count: parsed.feedback_count,
          fallback: isFallback || undefined,
          fallback_reason: isFallback ? parsed.reason : undefined,
        },
      });
      this.logger?.info(
        isFallback ? 'job.revision.fallback' : 'job.revision.succeeded',
        {
          request_id: job.request_id,
          scenario_id: job.scenario_id,
          job_id: job.id,
          revision_kind: revisionKind,
          fallback_reason: isFallback ? parsed.reason : undefined,
        },
      );
      if (typeof this.onRevisionComplete === 'function') {
        await this.onRevisionComplete({ job, parsed, success: true });
      }
    } catch (error) {
      const current = this.jobStore.get(job.id);
      if (current.status === 'interrupted') {
        if (typeof this.onRevisionComplete === 'function') {
          await this.onRevisionComplete({ job, error, success: false, interrupted: true });
        }
        return;
      }
      // Capture stderr from process_runner for diagnostics (when available).
      const stderrExcerpt = (lastStderr || '').slice(0, 2000);
      this._updateJob(job.id, {
        status: error.code === 'PROCESS_INTERRUPTED' ? 'interrupted' : 'failed',
        finished_at: new Date().toISOString(),
        error: {
          code: error.code || 'REVISION_FAILED',
          message: error.message || 'Revision failed',
          stderr_excerpt: stderrExcerpt || undefined,
        },
      });
      this.logger?.error('job.revision.failed', {
        request_id: job.request_id,
        scenario_id: job.scenario_id,
        job_id: job.id,
        code: error.code || 'REVISION_FAILED',
        stderr_excerpt: stderrExcerpt || undefined,
        stderr_length: stderrExcerpt.length,
      });
      if (typeof this.onRevisionComplete === 'function') {
        await this.onRevisionComplete({ job, error, success: false, stderr_excerpt: stderrExcerpt });
      }
    }
  }

  async _runPublish(job) {
    this._updateJob(job.id, { status: 'running', started_at: new Date().toISOString() });
    const args = [getPublishScript(), '--scenario-id', job.scenario_id];
    try {
      const processResult = await this.runner.run(this.config.nodeBin, args, {
        cwd: this.config.projectRoot,
        timeoutMs: this.config.publishTimeoutMs || 180_000,
        outputLimit: this.config.processOutputLimit,
        requestId: job.request_id,
        operation: `publish:${job.scenario_id}`,
      });
      const stdout = processResult.stdout || '';
      // publish_rendered.js prints a summary on the last few lines but does not emit machine-readable JSON.
      // We parse the scenario file directly to extract published_url.
      const scenarioPath = path.join(this.config.dataRoot, 'scenarios', 'published', `${job.scenario_id}.json`);
      let publishedUrl = null;
      try {
        const fs = await import('node:fs');
        if (fs.existsSync(scenarioPath)) {
          const rec = JSON.parse(fs.readFileSync(scenarioPath, 'utf-8'));
          publishedUrl = rec.published_url || null;
        }
      } catch (fsErr) {
        this.logger?.warn('publish.read_state_failed', {
          request_id: job.request_id,
          scenario_id: job.scenario_id,
          message: fsErr.message,
        });
      }

      if (!publishedUrl) {
        throw new Error('Publish process completed but no published_url found on scenario');
      }

      this._updateJob(job.id, {
        status: 'succeeded',
        finished_at: new Date().toISOString(),
        result: {
          scenario_id: job.scenario_id,
          published_url: publishedUrl,
        },
      });
      this.logger?.info('job.publish.succeeded', {
        request_id: job.request_id,
        scenario_id: job.scenario_id,
        job_id: job.id,
        published_url: publishedUrl,
      });
      if (typeof this.onPublishComplete === 'function') {
        await this.onPublishComplete({ job, success: true, published_url: publishedUrl });
      }
    } catch (error) {
      const current = this.jobStore.get(job.id);
      if (current.status === 'interrupted') {
        if (typeof this.onPublishComplete === 'function') {
          await this.onPublishComplete({ job, error, success: false, interrupted: true });
        }
        return;
      }
      this._updateJob(job.id, {
        status: error.code === 'PROCESS_INTERRUPTED' ? 'interrupted' : 'failed',
        finished_at: new Date().toISOString(),
        error: { code: error.code || 'PUBLISH_FAILED', message: error.message || 'Publish failed' },
      });
      this.logger?.error('job.publish.failed', {
        request_id: job.request_id,
        scenario_id: job.scenario_id,
        job_id: job.id,
        code: error.code || 'PUBLISH_FAILED',
        message: error.message,
      });
      if (typeof this.onPublishComplete === 'function') {
        await this.onPublishComplete({ job, error, success: false });
      }
    }
  }

  stopAccepting() {
    this.accepting = false;
  }

  async shutdown(graceMs) {
    this.stopAccepting();
    const active = [...this.promises.values()];
    if (!active.length) return;
    let timer;
    await Promise.race([
      Promise.allSettled(active),
      new Promise(resolve => { timer = setTimeout(resolve, graceMs); }),
    ]);
    if (timer) clearTimeout(timer);
    if (this.promises.size) {
      this.runner.shutdown();
      for (const id of this.promises.keys()) {
        try {
          this.jobStore.update(id, {
            status: 'interrupted',
            finished_at: new Date().toISOString(),
            error: { code: 'PROCESS_INTERRUPTED', message: 'Server shut down during job' },
          });
        } catch {}
      }
    }
  }
}
