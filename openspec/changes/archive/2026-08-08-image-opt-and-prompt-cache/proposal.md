# OpenSpec Proposal: image-opt-and-prompt-cache

## Why
Generating comic panel images via MiniMax Image API takes 3-5 minutes and incurs API costs. When a user requests a scenario revision or re-renders a comic where certain panels or character prompts have not changed, re-invoking the MiniMax API creates unnecessary latency and API cost. Furthermore, serving full uncompressed PNG images (1-3 MB each) over Web UI and Telegram MiniApp creates heavy network bandwidth usage on mobile devices.

## What Changes
1. **Prompt-Image Caching**: Hash-based caching (`sha256(character_prompt + scene_prompt + style + seed)`) stored in `data/.cache/images/`. Subsequent renders with identical parameters skip MiniMax API calls and return the cached panel in <0.1s.
2. **WebP Image Generation**: Python render pipeline generates `.webp` copies (Pillow quality 82) alongside `.png` for all rendered panels and preview comics.
3. **Web API & Web UI Integration**: Serve `/comics/<id>.webp` and `/comics/<id>/<panel_name>.webp` with long-term cache headers and use responsive `<picture>` HTML tags in the Web UI dashboard.

## Out of Scope
- Notion live sync (stubbed for future expansion in main branch).
- Removal of PNG files (PNG retained for backward-compatibility).
