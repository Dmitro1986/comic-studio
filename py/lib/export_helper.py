"""Export helper module for Comic Studio.

Provides PDF and Social ZIP export functions for rendered comics.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Optional

from PIL import Image

from py.lib.config import comics_dir
from py.lib.logging_setup import setup

logger = setup("lib.export_helper")


def export_to_pdf(scenario_id: str, output_path: Path | str) -> Path:
    """Compiles comic panel images into a single multi-page PDF document.

    Args:
        scenario_id: scenario hex ID.
        output_path: file path to save PDF.

    Returns:
        Path to generated PDF file.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    comic_folder = comics_dir() / scenario_id
    panel_files: list[Path] = []

    if comic_folder.exists() and comic_folder.is_dir():
        # Find panel_1.png, panel_2.png...
        for f in sorted(comic_folder.glob("panel_*.*")):
            if f.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg"):
                panel_files.append(f)

    # Fallback to single preview image if subfolder panels absent
    if not panel_files:
        main_png = comics_dir() / f"{scenario_id}.png"
        if main_png.exists():
            panel_files.append(main_png)

    if not panel_files:
        raise FileNotFoundError(f"No rendered panel images found for scenario {scenario_id}")

    images: list[Image.Image] = []
    try:
        for pf in panel_files:
            img = Image.open(pf)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        if not images:
            raise FileNotFoundError(f"Could not open panel images for scenario {scenario_id}")

        first_img = images[0]
        first_img.save(
            output_file,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=images[1:],
        )
        logger.info("export.pdf_created scenario_id=%s path=%s panels=%d", scenario_id, output_file, len(images))
        return output_file
    finally:
        for img in images:
            try:
                img.close()
            except Exception:
                pass


def export_to_zip(scenario_id: str, output_path: Path | str) -> Path:
    """Packages panels, fonts, layout JSON, and comic.html into a ZIP archive.

    Args:
        scenario_id: scenario hex ID.
        output_path: file path to save ZIP.

    Returns:
        Path to generated ZIP file.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    comic_folder = comics_dir() / scenario_id
    html_file = comics_dir() / f"{scenario_id}.html"
    png_file = comics_dir() / f"{scenario_id}.png"
    webp_file = comics_dir() / f"{scenario_id}.webp"

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
        if html_file.exists():
            zf.write(html_file, arcname=f"{scenario_id}/index.html")
        if png_file.exists():
            zf.write(png_file, arcname=f"{scenario_id}/preview.png")
        if webp_file.exists():
            zf.write(webp_file, arcname=f"{scenario_id}/preview.webp")

        if comic_folder.exists() and comic_folder.is_dir():
            for root, _, files in os.walk(comic_folder):
                for file in files:
                    fp = Path(root) / file
                    arc = Path(scenario_id) / fp.relative_to(comic_folder)
                    zf.write(fp, arcname=str(arc))

    logger.info("export.zip_created scenario_id=%s path=%s", scenario_id, output_file)
    return output_file
