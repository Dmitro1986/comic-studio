# python-image-cache Capability Spec

## Requirements

### REQ-1: Prompt Hash Computation
The system SHALL compute a deterministic SHA256 hex string from character prompt, scene prompt, image style, and seed values.

### REQ-2: Prompt Cache Retrieval and Storage
WHEN a prompt hash exists in `data/.cache/images/<hash>.png`, the system SHALL return the cached image bytes without invoking the MiniMax API.
WHEN an image is generated via MiniMax API, the system SHALL save the result to `data/.cache/images/<hash>.png`.
