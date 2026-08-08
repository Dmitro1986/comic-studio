"""Tests for py/lib/export_helper.py."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from py.lib import export_helper


class TestExportHelper(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.scenario_id = "test-export-001"

        # Mock comics dir structure
        self.comics_dir = self.root / "data" / "comics"
        self.comic_folder = self.comics_dir / self.scenario_id
        self.comic_folder.mkdir(parents=True, exist_ok=True)

        # Create dummy panel images
        for i in range(1, 3):
            img = Image.new("RGB", (100, 100), color="blue" if i == 1 else "red")
            img.save(self.comic_folder / f"panel_{i}.png")

        # Create dummy index.html
        (self.comics_dir / f"{self.scenario_id}.html").write_text("<h1>Comic</h1>")

        # Monkey-patch comics_dir
        self._orig_comics_dir = export_helper.comics_dir
        export_helper.comics_dir = lambda: self.comics_dir

    def tearDown(self):
        export_helper.comics_dir = self._orig_comics_dir
        self.temp_dir.cleanup()

    def test_export_to_pdf(self):
        pdf_path = self.root / "out.pdf"
        res_path = export_helper.export_to_pdf(self.scenario_id, pdf_path)
        self.assertTrue(res_path.exists())
        self.assertGreater(res_path.stat().st_size, 0)

    def test_export_to_zip(self):
        zip_path = self.root / "out.zip"
        res_path = export_helper.export_to_zip(self.scenario_id, zip_path)
        self.assertTrue(res_path.exists())

        with zipfile.ZipFile(res_path, "r") as zf:
            names = zf.namelist()
            self.assertIn(f"{self.scenario_id}/index.html", names)
            self.assertIn(f"{self.scenario_id}/panel_1.png", names)


if __name__ == "__main__":
    unittest.main()
