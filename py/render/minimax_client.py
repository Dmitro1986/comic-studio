"""HTTP клиент к MiniMax image-01 API."""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

import requests

from py.lib.config import MINIMAX_API_KEY, MINIMAX_BASE_URL
from py.lib.image_cache import compute_prompt_hash, get_cached_image, save_cached_image
from py.lib.logging_setup import setup

logger = setup("render.minimax_client")


def _convert_to_webp(png_path: Path, quality: int = 82) -> Optional[Path]:
    """Generates a WebP copy of a PNG image."""
    try:
        from PIL import Image
        webp_path = Path(png_path).with_suffix(".webp")
        with Image.open(png_path) as img:
            img.save(webp_path, "WEBP", quality=quality)
        logger.info(f"Generated WebP → {webp_path}")
        return webp_path
    except Exception as err:
        logger.warning(f"WebP conversion skipped for {png_path}: {err}")
        return None


def generate_image(
    prompt: str,
    output_path: str | Path,
    aspect_ratio: str = "16:9",
    seed: Optional[int] = None,
    subject_reference_b64: Optional[str] = None,
) -> Path:
    """Генерирует одну картинку через MiniMax image-01. Сохраняет в output_path.

    Возвращает Path к сохранённому файлу. Ищет в image_cache перед вызовом API.
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Prompt-Image Cache lookup
    prompt_hash = compute_prompt_hash(
        character_prompt=subject_reference_b64 or "",
        scene_prompt=prompt,
        style=aspect_ratio,
        seed=seed or 0,
    )
    cached_bytes = get_cached_image(prompt_hash)
    if cached_bytes:
        out_path.write_bytes(cached_bytes)
        _convert_to_webp(out_path)
        logger.info(f"Used cached image ({len(cached_bytes)} bytes) → {out_path}")
        return out_path

    if not MINIMAX_API_KEY:
        raise RuntimeError("MINIMAX_API_KEY not set in .env")

    base = MINIMAX_BASE_URL or "https://api.minimax.io"
    url = f"{base}/v1/image_generation"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "model": "image-01",
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "n": 1,
        "response_format": "base64",
        "prompt_optimizer": True,
    }
    if seed is not None:
        payload["seed"] = seed
    if subject_reference_b64:
        payload["subject_reference"] = [{
            "type": "character",
            "image_file": f"data:image/jpeg;base64,{subject_reference_b64}",
        }]

    logger.info(f"Generating image via MiniMax API → {output_path}")
    resp = requests.post(url, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()

    # Проверяем base_resp.status_code (MiniMax возвращает 200 даже при ошибках)
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(
            f"MiniMax API error {base_resp.get('status_code')}: "
            f"{base_resp.get('status_msg')}"
        )

    images = data.get("data", {}).get("image_base64") or data.get("data", {}).get("image_urls")
    if not images:
        raise RuntimeError(f"No images in response: {data}")

    img_b64 = images[0]
    if img_b64.startswith("http"):
        # Если вернулся URL, скачиваем
        img_resp = requests.get(img_b64, timeout=60)
        img_resp.raise_for_status()
        img_bytes = img_resp.content
    else:
        img_bytes = base64.b64decode(img_b64)

    out_path.write_bytes(img_bytes)
    save_cached_image(prompt_hash, img_bytes)
    _convert_to_webp(out_path)
    logger.info(f"Saved {len(img_bytes)} bytes → {out_path}")
    return out_path



def encode_image_b64(path: str | Path) -> str:
    """Кодирует локальный файл в base64 (для subject_reference)."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m py.render.minimax_client <prompt> <output>")
        sys.exit(1)
    print(generate_image(sys.argv[1], sys.argv[2]))