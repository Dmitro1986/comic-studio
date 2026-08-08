# OpenSpec Proposal: export-endpoints-and-rate-limiting

## Why
1. **Portable Sharing**: Users need to export rendered comics into PDF (for printing/document sharing) and Social ZIP bundles (containing PNG/WebP panels and `index.html` for direct uploading to social media and external CMS platforms).
2. **API Protection**: Heavy mutation endpoints (scenario creation, rendering, AI chat) need protection against rate abuse (`express-rate-limit`) to prevent API key quota exhaustion.

## What Changes
1. **Python Export Helper (`py/lib/export_helper.py`)**:
   - `export_to_pdf(scenario_id)`: compiles rendered panel images into a multi-page PDF using Pillow.
   - `export_to_zip(scenario_id)`: packages panels, fonts, and `index.html` into a ZIP archive.
2. **Web API Export Routes (`web/routes/scenarios.js`)**:
   - `GET /api/scenarios/:id/export/pdf` and `GET /api/scenarios/:id/export/zip` with `Content-Disposition: attachment`.
3. **MCP Export Tools (`mcp-server/index.js`)**:
   - Registered `export_comic_pdf` and `export_comic_zip` MCP tools.
4. **API Rate Limiting (`web/app.js`)**:
   - Integrated windowed rate-limiting middleware for mutation routes.
5. **Web UI Buttons (`ui/app.js`)**:
   - Added PDF and ZIP download links to comic cards.

## Out of Scope
- Paid cloud storage uploads (local file streaming only).
