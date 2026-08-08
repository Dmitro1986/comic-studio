# OpenSpec Design: export-endpoints-and-rate-limiting

## Architecture

```
                 [ Web UI / MCP / HTTP Client ]
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
     GET /export/pdf                 GET /export/zip
               │                               │
               ▼                               ▼
    [ Pillow Image.save PDF ]       [ ZipFile Archive ]
```

## Decisions
1. **Pillow Multi-page PDF**: Compiles panel images directly into a PDF document using Pillow's `Image.save(pdf_path, save_all=True, append_images=...)`.
2. **Standard ZipFile**: Uses Python standard library `zipfile` module.
3. **In-Memory Rate Limiting**: Uses Express rate limiting middleware with windowed IP tracking (max 30 requests / 15 mins).
