/**
 * SSE (Server-Sent Events) Broadcaster for real-time job status streaming.
 *
 * Manages HTTP event-stream connections for GET /api/jobs/:id/stream.
 */
import { EventEmitter } from 'events';

export class SseBroadcaster extends EventEmitter {
  constructor() {
    super();
    /** @type {Map<string, Set<import('express').Response>>} */
    this.subscribers = new Map();
  }

  /**
   * Subscribes an Express response stream to job events for the given jobId.
   *
   * @param {string} jobId
   * @param {import('express').Response} res
   */
  subscribe(jobId, res) {
    res.set({
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // Disable nginx buffering if proxied
    });
    res.flushHeaders?.();

    if (!this.subscribers.has(jobId)) {
      this.subscribers.set(jobId, new Set());
    }
    const clients = this.subscribers.get(jobId);
    clients.add(res);

    // Initial ping event
    this.sendEvent(res, 'connected', { job_id: jobId, timestamp: new Date().toISOString() });

    res.on('close', () => {
      clients.delete(res);
      if (clients.size === 0) {
        this.subscribers.delete(jobId);
      }
    });
  }

  /**
   * Broadcasts an SSE event to all connected subscribers of jobId.
   *
   * @param {string} jobId
   * @param {string} event
   * @param {object} data
   */
  broadcast(jobId, event, data) {
    const clients = this.subscribers.get(jobId);
    if (!clients || clients.size === 0) return;
    for (const res of clients) {
      this.sendEvent(res, event, data);
    }
  }

  /**
   * Formats and writes a single SSE message to a response stream.
   *
   * @param {import('express').Response} res
   * @param {string} event
   * @param {object} data
   */
  sendEvent(res, event, data) {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  }
}

export const sseBroadcaster = new SseBroadcaster();
