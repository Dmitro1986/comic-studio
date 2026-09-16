"""Render a knowledge book HTML from a published Comic Studio scenario.

Usage:
    python scripts/render_book.py --scenario-id 19fbc803 --style sentry
    python scripts/render_book.py --scenario-id 19fbc803 --style sentry --json-result
    python scripts/render_book.py --scenario-id 19fbc803 --style sentry \\
        --title "Sentry" --subtitle "NATO over Black Sea" \\
        --glossary '("E-3F","Sentry AWACS")' '("Link 16","tactical network")'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py.render.book import render_book_html, RenderBookError
from py.render.book.glossaries import Glossary
from py.render.book.palettes import STYLE_PALETTES


def _parse_glossary_arg(raw: str) -> tuple[str, str]:
    """Parse a single glossary arg in form 'term::definition'."""
    if "::" not in raw:
        raise ValueError(f"Glossary entry must be 'term::definition', got {raw!r}")
    term, definition = raw.split("::", 1)
    return (term.strip(), definition.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Render knowledge book HTML for a scenario")
    parser.add_argument("--scenario-id", required=True, help="8-char hex scenario ID")
    parser.add_argument(
        "--style",
        required=True,
        choices=sorted(STYLE_PALETTES.keys()),
        help="Book style (palette + default glossary)",
    )
    parser.add_argument("--output-dir", help="Override output directory")
    parser.add_argument("--title", help="Override title (default: scenario title)")
    parser.add_argument("--subtitle", help="Override subtitle")
    parser.add_argument("--tagline", help="Override cover tagline")
    parser.add_argument("--epigraph", help="Override cover epigraph")
    parser.add_argument("--narrative", help="Override narrative (default: scenario context)")
    parser.add_argument("--epilogue", help="Override epilogue text")
    parser.add_argument("--epilogue-author", help="Epilogue author signature")
    parser.add_argument(
        "--glossary",
        action="append",
        default=[],
        metavar="TERM::DEFINITION",
        help="Override glossary entry (repeatable; format 'term::definition')",
    )
    parser.add_argument("--provider", default="minimax", help="Render provider name (shown in footer)")
    parser.add_argument("--json-result", action="store_true", help="Print machine-readable JSON result")
    args = parser.parse_args()

    custom_glossary: Glossary | None = None
    if args.glossary:
        custom_glossary = [_parse_glossary_arg(item) for item in args.glossary]

    try:
        out_path = render_book_html(
            args.scenario_id,
            args.style,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            custom_glossary=custom_glossary,
            custom_title=args.title,
            custom_subtitle=args.subtitle,
            custom_tagline=args.tagline,
            custom_epigraph=args.epigraph,
            custom_narrative=args.narrative,
            custom_epilogue=args.epilogue,
            custom_epilogue_author=args.epilogue_author,
            provider=args.provider,
        )
    except RenderBookError as err:
        result = {"ok": False, "error": str(err), "code": "RENDER_BOOK_FAILED"}
        if args.json_result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"❌ {err}", file=sys.stderr)
        return 1
    except Exception as err:
        result = {"ok": False, "error": str(err), "code": "INTERNAL_ERROR"}
        if args.json_result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"❌ {err}", file=sys.stderr)
        return 1

    size_bytes = out_path.stat().st_size
    result = {
        "ok": True,
        "scenario_id": args.scenario_id,
        "style": args.style,
        "path": str(out_path),
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 1),
    }
    if args.json_result:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"✅ Book rendered → {out_path} ({result['size_kb']} KB, style={args.style})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
