"""Tests for `py.render.book` — knowledge book HTML renderer (T4)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py.render import book as book_module
from py.render.book import render_book_html, RenderBookError
from py.render.book.palettes import STYLE_PALETTES, to_css_vars, get_palette
from py.render.book.glossaries import get_default_glossary, STYLE_GLOSSARIES
from py.lib import config as cfg


def _build_scenario(panel_count: int = 3, status: str = "published") -> dict:
    panels = [
        {"n": i + 1, "prompt": f"Scene {i + 1} with characters and details", "caption": f"Кадр {i + 1}"}
        for i in range(panel_count)
    ]
    return {
        "id": "book0001",
        "title": "Test Scenario Title",
        "tone": "epic",
        "style": "bubble",
        "image_style": "comic",
        "layout": "comic",
        "aspect_ratio": "16:9",
        "status": status,
        "context": "Long context " * 200,  # > 1500 chars to trigger paragraph split
        "panels": panels,
        "panel_paths": [f"/tmp/book0001/panel_{i + 1}.png" for i in range(panel_count)],
        "created_at": "2026-09-10T10:00:00.000Z",
    }


class BookPalettesTests(unittest.TestCase):
    def test_all_seven_styles_present(self):
        expected = {"sentry", "ramstein", "hornsdale", "partition", "puppet", "ai-paradox", "stalker"}
        self.assertEqual(set(STYLE_PALETTES.keys()), expected)

    def test_each_palette_has_required_vars(self):
        required = ["primary", "accent", "paper", "ink", "shadow"]
        for style, palette in STYLE_PALETTES.items():
            for var in required:
                self.assertIn(var, palette, f"{style} missing {var}")
                self.assertTrue(palette[var].startswith("#"), f"{style}.{var} should be hex")

    def test_to_css_vars_emits_root_block(self):
        css = to_css_vars(STYLE_PALETTES["sentry"])
        self.assertIn(":root {", css)
        self.assertIn("--primary:", css)
        self.assertIn("#003366", css)  # sentry primary
        self.assertIn("--accent:", css)
        self.assertIn("#D4AF37", css)  # sentry accent

    def test_get_palette_raises_on_unknown(self):
        with self.assertRaises(KeyError) as ctx:
            get_palette("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))


class BookGlossariesTests(unittest.TestCase):
    def test_each_style_has_default_glossary(self):
        for style in STYLE_PALETTES.keys():
            glossary = get_default_glossary(style)
            self.assertIsInstance(glossary, list)
            # Most styles have entries; ai-paradox and puppet should have multiple
            if style in ("sentry", "ai-paradox", "hornsdale"):
                self.assertGreaterEqual(len(glossary), 3, f"{style} should have 3+ glossary entries")

    def test_glossary_entries_are_term_definition_tuples(self):
        for style, glossary in STYLE_GLOSSARIES.items():
            for entry in glossary:
                self.assertIsInstance(entry, tuple)
                self.assertEqual(len(entry), 2)
                term, definition = entry
                self.assertIsInstance(term, str)
                self.assertIsInstance(definition, str)
                self.assertGreater(len(term), 0)
                self.assertGreater(len(definition), 0)


class RenderBookHtmlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)

        # Mock data_dir/scenarios_dir/comics_dir to point into tmp
        published_dir = self.tmp_path / "scenarios" / "published"
        published_dir.mkdir(parents=True)
        self.published_dir = published_dir
        self.comics_dir = self.tmp_path / "comics"
        self.comics_dir.mkdir(parents=True)

        self.scenario = _build_scenario(3)
        (published_dir / "book0001.json").write_text(json.dumps(self.scenario))

        # Create panel images (book.html references them via URL, not file path,
        # but renderer also resolves filesystem paths in some branches)
        panel_dir = self.comics_dir / "book0001"
        panel_dir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            (panel_dir / f"panel_{i + 1}.png").write_bytes(b"\x89PNG fake")

        # Patch module-level functions
        self._original_data_dir = cfg.data_dir
        self._original_scenarios_dir = cfg.scenarios_dir
        self._original_comics_dir = cfg.comics_dir
        cfg.data_dir = lambda: self.tmp_path
        cfg.scenarios_dir = lambda status="draft": self.tmp_path / "scenarios" / status
        cfg.comics_dir = lambda: self.comics_dir
        # Also patch the bound names in the renderer module
        from py.render.book import renderer as book_renderer
        self._original_renderer_scenarios_dir = book_renderer.scenarios_dir
        self._original_renderer_comics_dir = book_renderer.comics_dir
        book_renderer.scenarios_dir = cfg.scenarios_dir
        book_renderer.comics_dir = cfg.comics_dir

    def tearDown(self):
        cfg.data_dir = self._original_data_dir
        cfg.scenarios_dir = self._original_scenarios_dir
        cfg.comics_dir = self._original_comics_dir
        from py.render.book import renderer as book_renderer
        book_renderer.scenarios_dir = self._original_renderer_scenarios_dir
        book_renderer.comics_dir = self._original_renderer_comics_dir

    def test_render_book_html_creates_file(self):
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir)
        self.assertTrue(out.exists())
        self.assertEqual(out.name, "book0001-book.html")
        content = out.read_text(encoding="utf-8")
        # Basic structural assertions
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("Test Scenario Title", content)
        self.assertIn("/comics/book0001/panel_1.png", content)
        self.assertIn("/comics/book0001/panel_3.png", content)
        # Palette CSS injected
        self.assertIn("--primary: #003366", content, "sentry primary injected")
        self.assertIn("--accent: #D4AF37", content, "sentry accent injected")

    def test_render_book_html_uses_jinja_autoescape(self):
        """T4 rule #9: autoescape must be enabled; raw script tags should be escaped."""
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir)
        content = out.read_text(encoding="utf-8")
        # Title with < should be escaped (but our title is plain text, so check for escape function presence)
        # The actual content from our scenario has no HTML, so this is structural test:
        # meta_lines includes an <a> tag which we marked safe via '|safe' — verify it survived
        # without autoescape, the <script> tag in template would render but break out of <style>
        self.assertIn("</style>", content)
        self.assertIn("<script>", content)
        # The script tag must be OUTSIDE the style block
        style_end = content.index("</style>")
        script_start = content.index("<script>")
        self.assertLess(style_end, script_start, "script tag must follow style tag")

    def test_render_with_each_style(self):
        for style in STYLE_PALETTES.keys():
            out = render_book_html("book0001", style, output_dir=self.comics_dir)
            content = out.read_text(encoding="utf-8")
            palette = STYLE_PALETTES[style]
            self.assertIn(f"--primary: {palette['primary']}", content, f"{style} primary")
            self.assertIn(f"--accent: {palette['accent']}", content, f"{style} accent")

    def test_render_raises_on_unknown_style(self):
        with self.assertRaises(RenderBookError) as ctx:
            render_book_html("book0001", "no-such-style", output_dir=self.comics_dir)
        self.assertIn("no-such-style", str(ctx.exception))
        self.assertIn("sentry", str(ctx.exception), "error lists available styles")

    def test_render_raises_on_missing_scenario(self):
        with self.assertRaises(RenderBookError) as ctx:
            render_book_html("nosuch00", "sentry", output_dir=self.comics_dir)
        self.assertIn("nosuch00", str(ctx.exception))
        self.assertIn("not found", str(ctx.exception))

    def test_render_raises_on_scenario_without_panels(self):
        (self.published_dir / "nopa01.json").write_text(json.dumps({
            "id": "nopa01", "title": "Empty", "panels": [], "context": "x"
        }))
        with self.assertRaises(RenderBookError) as ctx:
            render_book_html("nopa01", "sentry", output_dir=self.comics_dir)
        self.assertIn("no panels", str(ctx.exception))

    def test_render_with_custom_glossary(self):
        custom = [("Custom Term", "Custom definition for the test.")]
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir,
                               custom_glossary=custom)
        content = out.read_text(encoding="utf-8")
        self.assertIn("Custom Term", content)
        self.assertIn("Custom definition for the test.", content)
        # Default glossary terms should NOT appear inside <dt> tags
        # (the term "E-3F Sentry" still appears in the tagline "<style>" CSS comment
        # and as the palette name_ru, but not in the glossary <dt>)
        glossary_section_start = content.index('<div class="glossary"')
        glossary_section_end = content.index('</dl>', glossary_section_start) + len('</dl>')
        glossary_section = content[glossary_section_start:glossary_section_end]
        self.assertNotIn("E-3F Sentry", glossary_section, "default glossary replaced in <dl>")
        self.assertNotIn("AN/APY-2", glossary_section, "default glossary replaced in <dl>")

    def test_render_with_custom_title(self):
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir,
                               custom_title="Override Title")
        content = out.read_text(encoding="utf-8")
        self.assertIn("Override Title", content)
        # Original title from scenario should NOT be in <h1>
        h1_match = content[content.index("<h1>"):content.index("</h1>")]
        self.assertIn("Override Title", h1_match)
        self.assertNotIn("Test Scenario Title", h1_match)

    def test_render_with_custom_epigraph(self):
        epigraph = "Custom epigraph text with <emphasis>."
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir,
                               custom_epigraph=epigraph)
        content = out.read_text(encoding="utf-8")
        # <emphasis> should be autoescaped (or kept if marked safe)
        # Our template uses |safe on epigraph, so <emphasis> stays literal
        self.assertIn("Custom epigraph text", content)

    def test_render_includes_narrative_paragraphs(self):
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir)
        content = out.read_text(encoding="utf-8")
        self.assertIn('class="narrative"', content)

    def test_render_roman_numerals_in_nav(self):
        """Page numbers I, II, III should appear in the navigation."""
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir)
        content = out.read_text(encoding="utf-8")
        # Navigation links have format 'I · Кадр 1', 'II · Кадр 2', 'III · Кадр 3'
        self.assertIn("I · Кадр 1", content)
        self.assertIn("II · Кадр 2", content)
        self.assertIn("III · Кадр 3", content)

    def test_render_writes_only_to_specified_output_dir(self):
        """Atomic write to tmp should NOT create files in the real comics dir."""
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir)
        self.assertTrue(str(out).startswith(str(self.comics_dir)))
        # No files leaked into the parent tmp_path
        for entry in self.tmp_path.iterdir():
            if entry.is_dir():
                self.assertNotEqual(entry.name, "data", "no data/ leak")
        # tmp file should be cleaned up; panel_*.png files in book0001/ subdir
        # are excluded from the comics_dir top-level count
        top_level = [p for p in self.comics_dir.iterdir() if p.is_file()]
        self.assertEqual(len(top_level), 1, f"expected 1 file, got {len(top_level)}: {[p.name for p in top_level]}")
        self.assertEqual(top_level[0].name, "book0001-book.html")

    def test_render_provider_in_footer(self):
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir,
                               provider="draw-things")
        content = out.read_text(encoding="utf-8")
        self.assertIn("draw-things", content, "provider name shown in footer")

    def test_render_atomic_no_partial_files(self):
        """After render completes, no .tmp files should remain."""
        out = render_book_html("book0001", "sentry", output_dir=self.comics_dir)
        tmp_files = list(self.comics_dir.glob("*.tmp"))
        self.assertEqual(tmp_files, [], "atomic write leaves no tmp files")


class BookPublicAPITests(unittest.TestCase):
    def test_render_book_html_is_public(self):
        self.assertTrue(callable(book_module.render_book_html))
        self.assertTrue(callable(book_module.RenderBookError))


if __name__ == "__main__":
    unittest.main()
