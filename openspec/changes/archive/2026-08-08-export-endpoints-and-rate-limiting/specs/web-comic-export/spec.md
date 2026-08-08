# web-comic-export Capability Spec

## Requirements

### REQ-1: PDF Export
WHEN `GET /api/scenarios/:id/export/pdf` is requested for a rendered or published scenario, the system SHALL compile its panel images into a PDF document and return `200 OK` with `Content-Type: application/pdf` and `Content-Disposition: attachment; filename="<id>.pdf"`.

### REQ-2: Social ZIP Export
WHEN `GET /api/scenarios/:id/export/zip` is requested for a rendered or published scenario, the system SHALL package its panels, fonts, and HTML into a ZIP archive and return `200 OK` with `Content-Type: application/zip` and `Content-Disposition: attachment; filename="<id>.zip"`.
