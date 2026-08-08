# OpenSpec Tasks: sse-realtime-and-pure-python-fuzzy

- [x] 1. Pure-Python Fuzzy Resolver (`py/lib/scenario_resolver.py`)
  - [x] 1.1 Implement pure-Python Levenshtein distance and ratio calculation.
  - [x] 1.2 Replace `RuntimeError` with pure-python fallback.
  - [x] 1.3 Add unit test `tests/test_pure_python_fuzzy.py`.
- [x] 2. SSE Broadcaster & Express Route (`web/lib/sse_broadcaster.js`, `web/routes/jobs.js`)
  - [x] 2.1 Implement `SseBroadcaster` class.
  - [x] 2.2 Add `GET /api/jobs/:id/stream` endpoint with `text/event-stream`.
  - [x] 2.3 Connect jobManager state transitions to broadcaster.
- [x] 3. Web UI EventSource Integration (`ui/app.js`)
  - [x] 3.1 Subscribe to active job SSE streams in Web UI.
- [x] 4. Verification
  - [x] 4.1 Run Python unit test suite.
  - [x] 4.2 Run Node.js test suite with new SSE tests.
