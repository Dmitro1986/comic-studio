# OpenSpec Tasks: image-opt-and-prompt-cache

- [x] 1. Prompt-Image Cache (`py/lib/image_cache.py`)
  - [x] 1.1 Implement SHA256 prompt hashing function.
  - [x] 1.2 Implement `get_cached_image` and `save_cached_image`.
  - [x] 1.3 Add `data/.cache/` to `.gitignore`.
- [x] 2. Render Pipeline WebP & Cache Integration (`py/render/`)
  - [x] 2.1 Integrate `image_cache` in panel image generation site.
  - [x] 2.2 Add `.webp` output generation (quality 82) alongside `.png` for panels and preview comics.
- [x] 3. Web API Endpoints (`web/routes/comics.js`)
  - [x] 3.1 Implement `/comics/:id.webp` and `/comics/:id/:panel_name.webp` endpoints.
  - [x] 3.2 Add immutable cache headers for WebP responses.
- [x] 4. Web UI Responsive Picture Tags (`ui/app.js`, `ui/index.html`)
  - [x] 4.1 Update dashboard comic previews to use `<picture>` tags with `.webp` source and `.png` fallback.
- [x] 5. Testing & Verification
  - [x] 5.1 Add Python unit tests in `tests/test_image_cache.py`.
  - [x] 5.2 Add Node.js Web API tests in `web/tests/comics.test.js`.
  - [x] 5.3 Run full test suites.
