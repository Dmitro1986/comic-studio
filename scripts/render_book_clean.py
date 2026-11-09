#!/usr/bin/env python3
"""Render a Comic Studio knowledge book from scratch — no copy-paste, no sed.

Usage:
    python scripts/render_book_clean.py \\
        --scenario-id 32dc5e3c \\
        --style kremlin-satire \\
        --title "Шойгу · Шаманы · Рублёвка · Сентябрь" \\
        --subtitle "Кремлёвский водевиль · осенний выпуск" \\
        --tagline "Satirical editorial · начало осени · 2026" \\
        --epigraph "🪘 На Рублёво-Успенском шоссе о четыре утра стало шумно." \\
        --narrative "Источник ВЧК-ОГПУ рассказал..." \\
        --epilogue "В этой истории нет ни одной политической новости..." \\
        --epilogue-author "— Шойгу · Шаманы · Рублёвка · сентябрь · 4 утра" \\
        --glossary "Секретарь Совбеза::Бывший министр обороны, нервный сосед" \\
        --glossary "Лысый сосед в круглых очках::Анонимный бюрократ" \\
        --provider minimax

ALL text fields are required because the source scenario rarely has them in the
right voice. The script calls the canonical `py.render.book.render_book_html()`
— there is intentionally no `cp + sed` shortcut.

Required vs optional:
    Required: --scenario-id, --style, --title, --tagline,
              --epigraph, --narrative, --epilogue, --epilogue-author
              AND at least one --glossary.
    Optional: --subtitle, --provider (default "minimax").
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from py.render.book import render_book_html, RenderBookError
from py.render.book.palettes import STYLE_PALETTES


def parse_glossary_arg(raw: str) -> tuple[str, str]:
    if "::" not in raw:
        raise SystemExit(
            f"Glossary arg must be 'term::definition', got {raw!r}"
        )
    term, definition = raw.split("::", 1)
    return (term.strip(), definition.strip())


def main() -> int:
    p = argparse.ArgumentParser(
        description="Render a Comic Studio knowledge book from a scenario."
    )
    p.add_argument("--scenario-id", required=True)
    p.add_argument(
        "--style",
        required=True,
        choices=sorted(STYLE_PALETTES),
        help="Book style (see py/render/book/palettes.py)",
    )
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--tagline", required=True)
    p.add_argument("--epigraph", required=True)
    p.add_argument("--narrative", required=True)
    p.add_argument("--epilogue", required=True)
    p.add_argument("--epilogue-author", required=True)
    p.add_argument(
        "--glossary",
        action="append",
        default=[],
        metavar="term::definition",
        help="Repeatable. At least one is required — a book without a topic-specific glossary inherits the previous book's noise (same anti-pattern as `cp + sed`).",
    )
    p.add_argument("--provider", default="minimax", choices=["minimax", "draw-things"])
    args = p.parse_args()

    if not args.glossary:
        raise SystemExit(
            "At least one --glossary term::definition is required. "
            "A book without a topic-specific glossary is the same anti-pattern "
            "as `cp + sed` — it inherits the previous book's noise."
        )

    glossary = [parse_glossary_arg(g) for g in args.glossary]

    try:
        out = render_book_html(
            scenario_id=args.scenario_id,
            style=args.style,
            custom_glossary=glossary,
            custom_title=args.title,
            custom_subtitle=args.subtitle,
            custom_tagline=args.tagline,
            custom_epigraph=args.epigraph,
            custom_narrative=args.narrative,
            custom_epilogue=args.epilogue,
            custom_epilogue_author=args.epilogue_author,
            provider=args.provider,
        )
    except RenderBookError as e:
        raise SystemExit(f"render_book_html failed: {e}")

    size = out.stat().st_size
    print(f"Rendered: {out}  ({size} bytes)")

    # Sanity lint — flag obvious cross-book leakage. Block the user from
    # shipping a book about Russian politics that links to a Dutch defense
    # article, or a Tesla hornsdale book that has ВЧК-ОГПУ framing.
    text = out.read_text()
    leakage_signals = [
        ("defensie.nl", "Netherlands book leakage"),
        ("Hornsdale",   "Tesla book leakage"),
        ("Ramstein",    "NATO book leakage"),
    ]
    flagged = []
    for token, label in leakage_signals:
        if token in text:
            # Only flag if the title clearly does NOT belong to that book
            lower_title = args.title.lower()
            if any(k in lower_title for k in token.lower().split()):
                continue
            flagged.append(f"  ⚠  {label}: '{token}' present but title='{args.title}'")

    if flagged:
        print("\nSibling-book leakage detected:")
        for line in flagged:
            print(line)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
