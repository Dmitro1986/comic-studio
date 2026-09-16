import fs from 'fs';
import path from 'path';
import { createLogger } from './logger.js';
import { ScenarioStore } from './scenario_store.js';
import { LifecycleService } from './lifecycle.js';
import { ProcessRunner } from './process_runner.js';
import { JobStore } from './job_store.js';
import { JobManager } from './job_manager.js';
import { AipultRunner } from './aipult/runner.js';
import { safeResolve } from './validation.js';

function defaultOnRevisionComplete({ config, store, logger }) {
  return async ({ job, parsed, success, error, interrupted = false }) => {
    try {
      if (interrupted) {
        logger.info('revision.interrupted', { scenario_id: job.scenario_id, job_id: job.id, request_id: job.request_id });
        return;
      }
      if (success && parsed && parsed.id) {
        // Graceful fallback path: LLM call failed or returned invalid output.
        // We do NOT apply revision and we do NOT mark failed. Instead, we restore
        // the scenario back to its original approved/rendered queue so the operator
        // sees no behavioural change.
        if (parsed.fallback === true) {
          try {
            await store.restoreApproval(parsed.id, {
              requestId: job.request_id,
              reason: parsed.reason || 'llm_fallback',
            });
            logger.warn('revision.fallback', {
              scenario_id: parsed.id,
              job_id: job.id,
              request_id: job.request_id,
              reason: parsed.reason,
              warnings: parsed.warnings,
              feedback_count: parsed.feedback_count,
            });
          } catch (restoreErr) {
            // If restore fails (e.g. legacy draft without revision_source), log loudly
            // but don't propagate — the scenario is at worst stuck in draft with a
            // clear revision.fallback log line.
            logger.error('revision.fallback.restore_failed', {
              scenario_id: parsed.id,
              job_id: job.id,
              request_id: job.request_id,
              code: restoreErr.code || 'RESTORE_FAILED',
              message: restoreErr.message,
            });
          }
          return;
        }
        const record = JSON.parse(fs.readFileSync(path.resolve(config.dataRoot, 'scenarios', 'draft', `${parsed.id}.json`), 'utf-8'));
        await store.applyRevision(parsed.id, record, { requestId: job.request_id, feedbackCount: parsed.feedback_count });
        logger.info('revision.succeeded', { scenario_id: parsed.id, job_id: job.id, request_id: job.request_id, revision_request_id: parsed.revision_at });
      } else if (error) {
        // Hard failure (Python process crashed, timeout, etc.). Restore scenario back
        // to its original queue rather than leaving it stuck in draft with a failed flag.
        try {
          await store.restoreApproval(job.scenario_id, {
            requestId: job.request_id,
            reason: error.code || 'process_failed',
          });
          logger.warn('revision.failed_restored', {
            scenario_id: job.scenario_id,
            job_id: job.id,
            request_id: job.request_id,
            code: error.code || 'REVISION_FAILED',
            message: error.message,
          });
        } catch (restoreErr) {
          // Last-resort: fall back to legacy markRevisionFailed only if restore is impossible.
          logger.error('revision.failed.restore_failed', {
            scenario_id: job.scenario_id,
            job_id: job.id,
            code: restoreErr.code || 'RESTORE_FAILED',
            message: restoreErr.message,
          });
          await store.markRevisionFailed(job.scenario_id, {
            requestId: job.request_id,
            errorCode: error.code || 'REVISION_FAILED',
            message: error.message || 'Revision failed',
          });
          logger.warn('revision.failed', { scenario_id: job.scenario_id, job_id: job.id, request_id: job.request_id, code: error.code || 'REVISION_FAILED' });
        }
      }
    } catch (inner) {
      logger.error('revision.apply.failed', { scenario_id: job.scenario_id, job_id: job.id, code: inner.code || 'REVISION_APPLY_FAILED', message: inner.message });
    }
  };
}

export function createRuntime(config, overrides = {}) {
  const logger = overrides.logger || createLogger({ dataRoot: config.dataRoot, projectRoot: config.projectRoot });
  const store = overrides.store || new ScenarioStore({ dataRoot: config.dataRoot, logger, maxRevisionHistory: config.maxRevisionHistory });
  const lifecycle = overrides.lifecycle || new LifecycleService({ store, logger, minSeed: config.minSeed, maxSeed: config.maxSeed, maxFeedbackCount: config.maxRevisionFeedbackCount });
  const runner = overrides.runner || new ProcessRunner({ logger });
  const jobStore = overrides.jobStore || new JobStore({ dataRoot: config.dataRoot, logger });
  const onRevisionComplete = overrides.onRevisionComplete || defaultOnRevisionComplete({ config, store, logger });
  const jobManager = overrides.jobManager || new JobManager({ config, jobStore, runner, logger, onRevisionComplete });
  const aipultRunner = overrides.aipultRunner || new AipultRunner({ config, logger, processRunner: runner });
  let stopping = false;

  function cleanupArtifacts() {
    const cutoff = Date.now() - config.artifactRetentionMs;
    for (const name of ['.staging']) {
      const root = safeResolve(config.dataRoot, name);
      fs.mkdirSync(root, { recursive: true });
      for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const target = safeResolve(root, entry.name);
        try {
          if (fs.statSync(target).mtimeMs < cutoff) fs.rmSync(target, { recursive: true, force: true });
        } catch {}
      }
    }
    store.cleanupLegacyStaging(config.legacyRetentionMs);
    return jobStore.cleanup(config.jobRetentionMs);
  }

  const recoveredTransitions = store.reconcileTransitions();
  const recoveredTrash = store.recoverTrash();
  const interruptedJobs = jobStore.markInterrupted();
  const removedJobs = cleanupArtifacts();
  logger.info('web.runtime.initialized', { recovered_transitions: recoveredTransitions, recovered_trash: recoveredTrash, interrupted_jobs: interruptedJobs, removed_jobs: removedJobs });

  return {
    config, logger, store, lifecycle, runner, jobStore, jobManager, aipultRunner,
    isShuttingDown: () => stopping,
    cleanupArtifacts,
    async shutdown() {
      stopping = true;
      await jobManager.shutdown(config.shutdownGraceMs);
    },
  };
}
