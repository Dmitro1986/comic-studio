# OpenSpec Tasks: export-endpoints-and-rate-limiting

- [x] 1. Python Export Helpers (`py/lib/export_helper.py`)
  - [x] 1.1 Implement `export_to_pdf(scenario_id, output_path)`.
  - [x] 1.2 Implement `export_to_zip(scenario_id, output_path)`.
  - [x] 1.3 Add unit tests in `tests/test_export_helper.py`.
- [x] 2. Web API Endpoints & Rate Limiting (`web/routes/scenarios.js`, `web/app.js`)
  - [x] 2.1 Implement `GET /api/scenarios/:id/export/pdf`.
  - [x] 2.2 Implement `GET /api/scenarios/:id/export/zip`.
  - [x] 2.3 Add rate-limiting middleware for mutation routes in `web/app.js`.
- [x] 3. MCP Server Tools (`mcp-server/index.js`)
  - [x] 3.1 Register `export_comic_pdf` tool.
  - [x] 3.2 Register `export_comic_zip` tool.
- [x] 4. Web UI Download Buttons (`ui/app.js`)
  - [x] 4.1 Add PDF and ZIP buttons to comic cards.
- [x] 5. Verification
  - [x] 5.1 Run Python unit test suite.
  - [x] 5.2 Run Node.js test suite.
