"""Knowledge book HTML renderer — assemble + render the Jinja template.

Pipeline:
  1. Resolve scenario by ID (must exist in `data/scenarios/published/<id>.json`).
  2. Build panel descriptors (image URL, page_title, alt_text).
  3. Resolve narrative paragraphs (from context or custom override).
  4. Inject palette CSS variables into `book.css`.
  5. Render `book.html.j2` with autoescape (CLAUDE.md rule #9).
  6. Write to `data/comics/<id>-book.html` atomically.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from py.lib.config import data_dir, scenarios_dir, comics_dir
from py.lib.logging_setup import setup

from .palettes import STYLE_PALETTES, get_palette, to_css_vars
from .glossaries import get_default_glossary, Glossary

logger = setup("render.book.renderer")


class RenderBookError(Exception):
    """Raised when book rendering fails (scenario missing, no panels, invalid style, etc.)."""


@dataclass
class BookPanel:
    n: int
    image_url: str
    page_title: str
    alt_text: str


@dataclass
class RenderBookInput:
    scenario_id: str
    style: str
    scenario: dict
    panels: List[BookPanel] = field(default_factory=list)
    css_block: str = ""
    glossary: Glossary = field(default_factory=list)
    title: str = ""
    subtitle: str = ""
    tagline: str = "Knowledge comic"
    epigraph: str = ""
    narrative_paragraphs: List[str] = field(default_factory=list)
    epilogue_text: str = ""
    epilogue_author: str = ""
    epilogue_title: str = "Контекст"
    provider: str = "minimax"
    style_name: str = ""
    meta_lines: List[str] = field(default_factory=list)


# ── Roman numerals for page numbers ─────────────────────────────────────────

_ROMAN_VALUES = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
    (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),
]


def _to_roman(n: int) -> str:
    if n <= 0 or n > 3999:
        return str(n)
    result = []
    for value, sym in _ROMAN_VALUES:
        while n >= value:
            result.append(sym)
            n -= value
    return ''.join(result)


# ── Paths ───────────────────────────────────────────────────────────────────

def _module_root() -> Path:
    return Path(__file__).resolve().parent


def _template_dir() -> Path:
    return _module_root() / "templates"


def _css_path() -> Path:
    return _module_root() / "static" / "book.css"


def _load_css_template(palette_style: str) -> str:
    """Load book.css and inject palette CSS variables."""
    palette = get_palette(palette_style)
    css_text = _css_path().read_text(encoding="utf-8")
    palette_block = to_css_vars(palette)
    return css_text.replace("{{palette_vars}}", palette_block)


# ── Scenario resolution ─────────────────────────────────────────────────────

def _load_scenario(scenario_id: str) -> dict:
    """Load scenario from the published queue, falling back to rendered."""
    candidates = [
        scenarios_dir("published") / f"{scenario_id}.json",
        scenarios_dir("rendered") / f"{scenario_id}.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise RenderBookError(
        f"Scenario {scenario_id!r} not found in published/ or rendered/ queues"
    )


def _panel_image_path(scenario_id: str, panel_index: int, scenario: dict) -> Path:
    """Resolve absolute path to a panel PNG."""
    # Try panel_paths first (relative or absolute)
    panel_paths = scenario.get("panel_paths") or []
    if 0 <= panel_index < len(panel_paths):
        path = Path(panel_paths[panel_index])
        if path.is_absolute() and path.exists():
            return path
        # Relative to project root
        project_root = Path(__file__).resolve().parents[2]
        resolved = (project_root / path).resolve()
        if resolved.exists():
            return resolved
    # Default convention: data/comics/<id>/panel_<n>.png
    return comics_dir() / scenario_id / f"panel_{panel_index + 1}.png"


def _panel_image_url(scenario_id: str, panel_index: int, scenario: dict) -> str:
    """Public URL for the panel image (served by web UI)."""
    # Always use the canonical /comics/<id>/panel_<n>.png path the web server serves.
    return f"/comics/{scenario_id}/panel_{panel_index + 1}.png"


def _page_title_for_panel(panel: dict, fallback_index: int) -> str:
    """Derive a human-readable page title from panel caption or fallback."""
    caption = panel.get("caption") if isinstance(panel, dict) else None
    if caption and isinstance(caption, str) and caption.strip():
        # Capitalise only the FIRST letter, preserving the rest verbatim.
        # str.capitalize() lowercases everything else — which turns "Акт I" into
        # "Акт i" (lowercase Roman numerals) and breaks the book's typography.
        text = caption.strip().rstrip('.')
        return text[:1].upper() + text[1:] if text else text
    return f"Акт {fallback_index + 1}"


def _alt_text_for_panel(panel: dict, scenario_id: str, fallback_index: int) -> str:
    prompt = panel.get("prompt") if isinstance(panel, dict) else None
    if prompt and isinstance(prompt, str) and prompt.strip():
        # Strip CHARACTERS prefix, take first 100 chars
        cleaned = re.sub(r"^CHARACTERS:[^.]*\.\s*", "", prompt.strip())
        return cleaned[:200]
    return f"Панель {fallback_index + 1}"


def _split_paragraphs(text: str, max_chars: int = 1500) -> List[str]:
    """Split long context into reasonable narrative paragraphs."""
    if not text:
        return []
    text = text.strip()
    # Already split by \n\n
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 1 and len(text) > max_chars:
        # Split by sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current = ""
        chunks = []
        for sentence in sentences:
            if len(current) + len(sentence) > max_chars:
                if current:
                    chunks.append(current.strip())
                current = sentence
            else:
                current += " " + sentence
        if current:
            chunks.append(current.strip())
        return chunks
    return paragraphs


# ── Main entry point ────────────────────────────────────────────────────────

def render_book_html(
    scenario_id: str,
    style: str,
    *,
    output_dir: Optional[Path] = None,
    custom_glossary: Optional[Glossary] = None,
    custom_title: Optional[str] = None,
    custom_subtitle: Optional[str] = None,
    custom_epigraph: Optional[str] = None,
    custom_narrative: Optional[str] = None,
    custom_epilogue: Optional[str] = None,
    custom_epilogue_author: Optional[str] = None,
    custom_tagline: Optional[str] = None,
    custom_author: Optional[str] = None,
    source_url: Optional[str] = None,
    lang: Optional[str] = None,
    provider: str = "minimax",
) -> Path:
    """Render a knowledge book HTML for a published scenario.

    Args:
        scenario_id: 8-char hex scenario ID (must be in published/ or rendered/).
        style: One of STYLE_PALETTES keys (sentry, ramstein, hornsdale, ...).
        output_dir: Override output directory (default: data/comics/).
        custom_glossary: Replace default glossary (list of (term, definition)).
        custom_title / subtitle / tagline / epigraph / narrative / epilogue: text overrides.
        provider: Render provider name shown in footer.

    Returns:
        Path to the rendered book HTML file.
    """
    if style not in STYLE_PALETTES:
        raise RenderBookError(
            f"Unknown book style {style!r}. Available: {sorted(STYLE_PALETTES.keys())}"
        )

    scenario = _load_scenario(scenario_id)
    panels_raw = scenario.get("panels") or []
    if not isinstance(panels_raw, list) or not panels_raw:
        raise RenderBookError(
            f"Scenario {scenario_id!r} has no panels; cannot render book"
        )

    # Resolve language: explicit arg → scenario field → default 'ru'
    resolved_lang = lang or scenario.get("language") or "ru"
    # Resolve source URL: explicit arg → scenario field → ""
    resolved_source_url = source_url or scenario.get("source_url") or ""

    # Localized UI strings per language
    glossary_title_ru = "Кто есть кто"
    glossary_title_uk = "Хто є хто"
    epilogue_title_ru = "Контекст"
    epilogue_title_uk = "Контекст"  # generic, suits both
    sources_title_ru = "Ключевые источники"
    sources_title_uk = "Ключові джерела"
    if resolved_lang == "uk":
        glossary_title = glossary_title_uk
        epilogue_title = epilogue_title_uk
        sources_title = sources_title_uk
    else:
        glossary_title = glossary_title_ru
        epilogue_title = epilogue_title_ru
        sources_title = sources_title_ru

    # Build panel descriptors
    panels: List[BookPanel] = []
    for idx, panel in enumerate(panels_raw):
        panels.append(BookPanel(
            n=idx + 1,
            image_url=_panel_image_url(scenario_id, idx, scenario),
            page_title=_page_title_for_panel(panel, idx),
            alt_text=_alt_text_for_panel(panel, scenario_id, idx),
        ))

    # Glossary (custom override → style default → empty)
    if custom_glossary is not None:
        glossary = list(custom_glossary)
    else:
        glossary = get_default_glossary(style)

    # Title / subtitle / tagline
    title = custom_title or scenario.get("title") or scenario_id
    subtitle = custom_subtitle or ""
    tagline = custom_tagline or STYLE_PALETTES[style].get("name_ru", "Knowledge comic")

    # Epigraph (custom or from context)
    epigraph = custom_epigraph or ""
    if not epigraph and isinstance(scenario.get("context"), str):
        ctx = scenario["context"].strip()
        if len(ctx) > 800:
            epigraph = ctx[:800].rsplit(" ", 1)[0] + "…"
        else:
            epigraph = ctx

    # Narrative (custom or from context paragraphs)
    if custom_narrative is not None:
        narrative_paragraphs = _split_paragraphs(custom_narrative)
    else:
        narrative_paragraphs = _split_paragraphs(scenario.get("context") or "", max_chars=2000)

    # Epilogue
    epilogue_text = custom_epilogue or ""
    epilogue_author = custom_epilogue_author or ""
    # Author of the source material (different from epilogue_author, which signs the AI-written outro)
    resolved_author = custom_author or scenario.get("author") or ""
    # Localized label for the author block in glossary
    author_label_ru = "Автор материала"
    author_label_uk = "Автор матеріалу"
    if resolved_lang == "uk":
        author_label = author_label_uk
    else:
        author_label = author_label_ru
    if not epilogue_text and isinstance(scenario.get("context"), str):
        ctx = scenario["context"].strip()
        if len(ctx) > 800:
            epilogue_text = "...(см. полный контекст в narrative выше)..."

    # Meta lines for cover
    style_name = STYLE_PALETTES[style].get("name_ru", style)
    meta_lines = [
        f"Knowledge comic · {len(panels)} актов · {len(panels)} панелей",
        f"{style_name}",
    ]
    if scenario.get("created_at"):
        created_date = scenario["created_at"][:10]
        meta_lines.append(f"Создано: {created_date}")
    if scenario.get("published_url"):
        meta_lines.append(f'<a href="{scenario["published_url"]}" style="color: var(--accent-light);">🔗 Опубликованная версия</a>')

    # Build Jinja env with autoescape enabled (CLAUDE.md rule #9)
    env = Environment(
        loader=FileSystemLoader(str(_template_dir())),
        autoescape=select_autoescape(default=True, default_for_string=True),
    )
    env.globals['roman_numeral'] = _to_roman

    css_block = _load_css_template(style)
    template = env.get_template("book.html.j2")

    rendered_html = template.render(
        css_block=css_block,
        title=title,
        subtitle=subtitle,
        tagline=tagline,
        epigraph=epigraph,
        glossary=glossary,
        glossary_title=glossary_title,
        epilogue_title=epilogue_title,
        sources_title=sources_title,
        panels=[p.__dict__ for p in panels],
        narrative_paragraphs=narrative_paragraphs,
        epilogue_text=epilogue_text,
        epilogue_author=epilogue_author,
        provider=provider,
        style_name=style_name,
        scenario_id=scenario_id,
        meta_lines=meta_lines,
        lang=resolved_lang,
        source_url=resolved_source_url,
        author=resolved_author,
        author_label=author_label,
    )

    # Atomic write
    out_dir = output_dir or comics_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{scenario_id}-book.html"
    tmp_path = out_path.with_suffix(".html.tmp")
    tmp_path.write_text(rendered_html, encoding="utf-8")
    os.replace(tmp_path, out_path)

    logger.info(
        f"Rendered book style={style} scenario={scenario_id} → {out_path} ({len(rendered_html)} chars)"
    )
    return out_path
