"""Per-style colour palettes for knowledge book HTML.

Each palette maps to a CSS `:root` block via `to_css_vars()`. The names of
the CSS variables follow the canonical book.css schema:

  --primary, --primary-light, --primary-dark
  --accent, --accent-light, --accent-dark
  --paper, --paper-dark, --paper-light
  --ink, --ink-light, --shadow
  --ui (background UI panels, optional)

Adding a new style = add an entry here + add a glossary in `glossaries.py`.
"""
from __future__ import annotations

from typing import TypedDict


class Palette(TypedDict, total=False):
    primary: str
    primary_light: str
    primary_dark: str
    accent: str
    accent_light: str
    accent_dark: str
    paper: str
    paper_dark: str
    paper_light: str
    ink: str
    ink_light: str
    shadow: str
    ui: str
    # Display label shown on the cover meta line.
    name_ru: str


STYLE_PALETTES: dict[str, Palette] = {
    "sentry": {
        "primary": "#003366",
        "primary_light": "#1F5F8B",
        "primary_dark": "#001f3f",
        "accent": "#D4AF37",
        "accent_light": "#F4D58D",
        "accent_dark": "#9c7d1c",
        "paper": "#F5EFE6",
        "paper_dark": "#8A8275",
        "paper_light": "#FBF6EB",
        "ink": "#0A1525",
        "ink_light": "#2A3855",
        "shadow": "#050A14",
        "name_ru": "E-3F Sentry · NATO",
    },
    "ramstein": {
        "primary": "#0057B7",
        "primary_light": "#3D7DC4",
        "primary_dark": "#003F86",
        "accent": "#FFD700",
        "accent_light": "#FFEC8B",
        "accent_dark": "#C9A700",
        "paper": "#F5EFE6",
        "paper_dark": "#8A8275",
        "paper_light": "#FBF6EB",
        "ink": "#0A1525",
        "ink_light": "#2C3E50",
        "shadow": "#050A14",
        "name_ru": "Ramstein AB · NATO blue-gold",
    },
    "hornsdale": {
        "primary": "#E31937",
        "primary_light": "#FF5577",
        "primary_dark": "#B0142A",
        "accent": "#00A4A6",
        "accent_light": "#4DD0CE",
        "accent_dark": "#007678",
        "paper": "#F5EFE6",
        "paper_dark": "#8A8275",
        "paper_light": "#FBF6EB",
        "ink": "#1A2332",
        "ink_light": "#2D3849",
        "shadow": "#050A14",
        "name_ru": "Hornsdale · Tesla red-teal",
    },
    "partition": {
        "primary": "#8B0000",
        "primary_light": "#B22222",
        "primary_dark": "#5C0000",
        "accent": "#B8860B",
        "accent_light": "#DAA520",
        "accent_dark": "#7A5A00",
        "paper": "#F4E4BC",
        "paper_dark": "#8A7B5A",
        "paper_light": "#FBF1D5",
        "ink": "#2A2418",
        "ink_light": "#5C4A2E",
        "shadow": "#1A1612",
        "name_ru": "Partition · Parchment",
    },
    "puppet": {
        "primary": "#6B1F2E",
        "primary_light": "#9F3F4F",
        "primary_dark": "#3F0E1A",
        "accent": "#C9A14B",
        "accent_light": "#E8C77E",
        "accent_dark": "#8C6A26",
        "paper": "#E8D9B8",
        "paper_dark": "#A89878",
        "paper_light": "#F4EBD0",
        "ink": "#0A0810",
        "ink_light": "#2D1E2A",
        "shadow": "#050309",
        "ui": "#2D1E2A",
        "name_ru": "Puppet · Burgundy-gold",
    },
    "ai-paradox": {
        "primary": "#6B2D8C",
        "primary_light": "#9D5BB8",
        "primary_dark": "#3F1A56",
        "accent": "#00E5FF",
        "accent_light": "#66F0FF",
        "accent_dark": "#00A0B5",
        "paper": "#F0EBFA",
        "paper_dark": "#5C5677",
        "paper_light": "#FAF6FF",
        "ink": "#0A0814",
        "ink_light": "#1F1B33",
        "shadow": "#050309",
        "ui": "#150F22",
        "name_ru": "AI Paradox · Violet-cyber",
    },
    "stalker": {
        "primary": "#3D2817",
        "primary_light": "#5C3D26",
        "primary_dark": "#1F140B",
        "accent": "#C9A14B",
        "accent_light": "#E8C77E",
        "accent_dark": "#8C6A26",
        "paper": "#D9C896",
        "paper_dark": "#8A7B5A",
        "paper_light": "#F4E4BC",
        "ink": "#0A0805",
        "ink_light": "#2A1F14",
        "shadow": "#050302",
        "name_ru": "S.T.A.L.K.E.R. · Zone",
    },
}


def to_css_vars(palette: Palette) -> str:
    """Render a palette as a CSS `:root` block string.

    Uses the canonical CSS variable names expected by `py/render/book/static/book.css`:
        --primary, --primary-light, --primary-dark
        --accent, --accent-light, --accent-dark
        --paper, --paper-dark, --paper-light
        --ink, --ink-light, --shadow
        --ui (optional)
    """
    lines = [":root {"]
    pairs = [
        ("--primary", palette.get("primary")),
        ("--primary-light", palette.get("primary_light")),
        ("--primary-dark", palette.get("primary_dark")),
        ("--accent", palette.get("accent")),
        ("--accent-light", palette.get("accent_light")),
        ("--accent-dark", palette.get("accent_dark")),
        ("--paper", palette.get("paper")),
        ("--paper-dark", palette.get("paper_dark")),
        ("--paper-light", palette.get("paper_light")),
        ("--ink", palette.get("ink")),
        ("--ink-light", palette.get("ink_light")),
        ("--shadow", palette.get("shadow")),
        ("--ui", palette.get("ui")),
    ]
    for var_name, value in pairs:
        if value:
            lines.append(f"  {var_name}: {value};")
    lines.append("}")
    return "\n    ".join(lines)


def get_palette(style: str) -> Palette:
    if style not in STYLE_PALETTES:
        raise KeyError(
            f"Unknown book style {style!r}. Available: {sorted(STYLE_PALETTES.keys())}"
        )
    return STYLE_PALETTES[style]
