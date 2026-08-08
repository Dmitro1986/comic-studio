# web-webp-rendering Capability Spec

## Requirements

### REQ-1: WebP Artifact Generation
WHEN a comic or panel image is rendered, the system SHALL output both `.png` and `.webp` (quality 82) versions.

### REQ-2: WebP HTTP Serving
WHEN `GET /comics/<id>.webp` or `GET /comics/<id>/<panel_name>.webp` is requested, the system SHALL respond with `200 OK`, `Content-Type: image/webp`, and long-term cache headers `Cache-Control: public, max-age=31536000, immutable`.
WHEN the `.webp` artifact does not exist, the system SHALL respond with `404 Not Found`.

### REQ-3: Web UI Responsive Picture Rendering
The Web UI SHALL render comic previews using `<picture>` elements specifying `.webp` as primary source and `.png` as fallback.
