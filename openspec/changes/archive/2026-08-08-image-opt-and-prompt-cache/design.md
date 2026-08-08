# OpenSpec Design: image-opt-and-prompt-cache

## Architecture

### Prompt-Image Cache Flow
```
[ render_approved.py / _comic_lib.py ]
          │
          ▼
Compute SHA256 Hash(character_prompt + scene_prompt + style + seed)
          │
          ├── Check data/.cache/images/<hash>.png
          │     ├── FOUND -> Return cached PNG bytes (0.05s)
          │     └── NOT FOUND -> Call MiniMax API -> Save to data/.cache/images/<hash>.png
          ▼
Generate WebP copy (quality 82) -> Save to data/comics/<id>/panel_<N>.webp
```

## Decisions

1. **Storage Path**: Cache files are stored in `data/.cache/images/<hash>.png`. Directory `data/.cache/` is added to `.gitignore`.
2. **WebP Quality**: Pillow `quality=82` delivers 70-80% size reduction with visually lossless comic art quality.
3. **HTTP Cache Control**: WebP endpoints set `Cache-Control: public, max-age=31536000, immutable`.
4. **Fallback Mechanism**: If WebP creation fails or is missing, Web UI falls back to PNG without throwing errors.
