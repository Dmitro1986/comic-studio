"""Knowledge book HTML renderer.

Generates a styled HTML book from a published Comic Studio scenario with:
  - cover page (title, tagline, epigraph)
  - glossary section (per-style named entities)
  - navigation bar
  - narrative blocks (extracted from source context)
  - pages with embedded panel renders (data-act-N anchors)
  - sources / epilogue / footer
  - modal lightbox for full-screen image viewing

The book uses one canonical CSS (`py/render/book/static/book.css`) with
CSS custom properties (--primary, --accent, --paper, --ink, ...) injected
from `STYLE_PALETTES` in `palettes.py`. Per-style glossaries live in
`glossaries.py` (defaults; can be overridden per-render).

Public API:
    render_book_html(scenario_id, style, *, output_dir=None,
                     custom_glossary=None, custom_title=None,
                     custom_subtitle=None) -> Path
"""
from __future__ import annotations

from .renderer import render_book_html, RenderBookError

__all__ = ["render_book_html", "RenderBookError"]
