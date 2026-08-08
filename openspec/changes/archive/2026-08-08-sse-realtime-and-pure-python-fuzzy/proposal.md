# OpenSpec Proposal: sse-realtime-and-pure-python-fuzzy

## Why
1. **Real-time Observability**: Web UI currently polls `/api/scenarios` every 10 seconds. When a user launches a scenario creation or render job, waiting for poll intervals creates latency and redundant HTTP traffic. SSE (Server-Sent Events) allows real-time pushing of job state changes directly to Web UI and AiPULT.
2. **Hermetic Python Dependencies**: `scenario_resolver.py` previously failed with `RuntimeError` if external C++ libraries `rapidfuzzy` or `thefuzz` were absent in `.venv`. Implementing a native pure-Python fuzzy matching algorithm guarantees 100% test passing and scenario resolution on any Python 3.10+ environment without external C-compilers.

## What Changes
1. **Pure-Python Fuzzy Matching**: Implement a pure-Python Levenshtein/ratio fallback in `py/lib/scenario_resolver.py`.
2. **SSE Event Broadcaster**: Add `web/lib/sse_broadcaster.js` to manage SSE client connections.
3. **SSE HTTP Stream Endpoint**: Expose `GET /api/jobs/:id/stream` (`text/event-stream`) in `web/routes/jobs.js`.
4. **Web UI Live Updates**: Connect `EventSource` in `ui/app.js` when jobs are active.

## Out of Scope
- WebSockets bidirectional protocol (SSE is unidirectional server-to-client, matching requirements).
