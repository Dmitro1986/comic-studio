# OpenSpec Design: sse-realtime-and-pure-python-fuzzy

## Architecture

### SSE Event Streaming Architecture
```
[ Job State Mutation (render / revise) ]
                     │
                     ▼
          [ sseBroadcaster.emit(job) ]
                     │
                     ▼
     [ HTTP GET /api/jobs/:id/stream ]
         Content-Type: text/event-stream
                     │
                     ▼
             [ EventSource in UI ]
```

### Pure-Python Fuzzy Matching Fallback
```
[ py/lib/scenario_resolver.py ]
          │
          ├── Try import rapidfuzzy
          ├── Try import thefuzz
          └── Fallback to pure_python_ratio() (Levenshtein matrix / token sort)
```

## Decisions
1. **Pure Python Fallback**: Standard Levenshtein distance implementation using DP matrix, normalized to [0.0, 1.0] similarity ratio.
2. **SSE Format**: Events formatted as standard SSE `event: <name>\ndata: <json>\n\n`.
3. **Connection Cleanup**: Clients disconnected after `job_completed` / `job_failed` or HTTP client connection drop (`req.on('close')`).
