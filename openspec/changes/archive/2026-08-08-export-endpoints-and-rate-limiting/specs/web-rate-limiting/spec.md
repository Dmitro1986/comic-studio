# web-rate-limiting Capability Spec

## Requirements

### REQ-1: Rate Limiting on Mutation Endpoints
WHEN heavy mutation endpoints (`/api/scenarios`, `/render`, `/revise`, `/aipult/chat`) exceed the allowed request quota per window from an IP address, the system SHALL respond with HTTP `429 Too Many Requests`.
