import express from 'express';
import { serializeJob } from '../lib/job_store.js';
import { sseBroadcaster } from '../lib/sse_broadcaster.js';

export function jobsRouter({ jobStore }) {
  const router = express.Router();
  router.get('/', (req, res) => {
    res.json({ items: jobStore.list().map(serializeJob), request_id: req.id });
  });
  router.get('/:id/stream', (req, res) => {
    const job = jobStore.get(req.params.id);
    if (!job) return res.status(404).json({ error: { code: 'JOB_NOT_FOUND', message: 'Job not found' } });
    sseBroadcaster.subscribe(req.params.id, res);
  });
  router.get('/:id', (req, res) => {
    res.json({ job: serializeJob(jobStore.get(req.params.id)), request_id: req.id });
  });
  return router;
}
