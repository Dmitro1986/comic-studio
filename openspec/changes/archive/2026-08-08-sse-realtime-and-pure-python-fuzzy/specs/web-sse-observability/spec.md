# web-sse-observability Capability Spec

## Requirements

### REQ-1: SSE Streaming Endpoint
WHEN `GET /api/jobs/:id/stream` is requested, the system SHALL respond with `200 OK`, `Content-Type: text/event-stream`, `Cache-Control: no-cache`, and `Connection: keep-alive`.

### REQ-2: Job State Event Broadcast
WHEN a job state transitions (e.g. `active`, `completed`, `failed`), the system SHALL send an SSE event formatted as `event: job_updated\ndata: <json>\n\n`.
