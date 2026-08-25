"""HTTP клиент к Draw Things (локальный SDXL backend)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

from py.lib.config import data_dir
from py.lib.image_cache import compute_prompt_hash, get_cached_image, save_cached_image
from py.lib.logging_setup import setup

logger = setup("render.draw_things_client")

DRAW_THINGS_URL = os.environ.get("DRAW_THINGS_URL", "http://192.168.50.250:7860")
DRAW_THINGS_TIMEOUT = int(os.environ.get("DRAW_THINGS_TIMEOUT", "300"))

# Default LoRA, который загружен у пользователя — STALKER_SDXL даёт документальный стиль.
DEFAULT_LORA = os.environ.get("DRAW_THINGS_DEFAULT_LORA", "STALKER_SDXL")
DEFAULT_LORA_WEIGHT = float(os.environ.get("DRAW_THINGS_DEFAULT_LORA_WEIGHT", "0.7"))

# Negative prompt специально для комиксов — без текста, без крови, без подписей
DEFAULT_NEGATIVE_PROMPT = (
    "speech bubble, dialogue bubble, text bubble, thought bubble, "
    "text, letters, words, writing, glyphs, characters, symbols, "
    "typography, watermark, signature, hieroglyphs, kanji, "
    "blood, wound, injury, gore, violence, dead body, corpse, "
    "low quality, blurry, cartoon, anime, deformed, nsfw"
)


def _convert_to_jpg(png_path: Path, quality: int = 90) -> Optional[Path]:
    """Опционально создаёт JPEG-копию."""
    try:
        from PIL import Image
        jpg_path = png_path.with_suffix(".jpg")
        with Image.open(png_path) as img:
            img.convert("RGB").save(jpg_path, "JPEG", quality=quality)
        logger.info(f"Generated JPG → {jpg_path}")
        return jpg_path
    except Exception as err:
        logger.warning(f"JPG conversion skipped for {png_path}: {err}")
        return None


def _inject_lora(prompt: str, lora: Optional[str], weight: float) -> str:
    """Добавляет <lora:NAME:WEIGHT> в prompt если задан LoRA."""
    if not lora:
        return prompt
    name = lora.replace(".safetensors", "")
    return f"{prompt} <lora:{name}:{weight}>"


def is_draw_things_available(url: Optional[str] = None) -> bool:
    """Health-check Draw Things."""
    target = (url or DRAW_THINGS_URL).rstrip("/")
    try:
        resp = requests.get(f"{target}/sdapi/v1/options", timeout=5)
        return resp.ok
    except Exception:
        return False


def generate_image(
    prompt: str,
    output_path: str | Path,
    aspect_ratio: str = "16:9",
    seed: Optional[int] = None,
    *,
    lora: Optional[str] = None,
    lora_weight: Optional[float] = None,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler: str = "DPM++ SDE Karras",
    width: Optional[int] = None,
    height: Optional[int] = None,
    use_cache: bool = True,
) -> Path:
    """Генерирует одну картинку через Draw Things.

    Сохраняет в output_path. Использует кэш при возможности.
    Возвращает Path к сохранённому файлу.
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # aspect_ratio → width/height если явно не заданы
    if width is None or height is None:
        ratio_map = {
            "1:1": (1024, 1024),
            "16:9": (1280, 720),
            "9:16": (720, 1280),
            "4:3": (1024, 768),
            "3:4": (768, 1024),
        }
        width, height = ratio_map.get(aspect_ratio, (1024, 1024))

    full_prompt = _inject_lora(
        prompt,
        lora or DEFAULT_LORA,
        lora_weight if lora_weight is not None else DEFAULT_LORA_WEIGHT,
    )

    # Cache lookup
    if use_cache:
        prompt_hash = compute_prompt_hash(
            character_prompt="",
            scene_prompt=full_prompt,
            style=aspect_ratio,
            seed=seed or 0,
        )
        cached = get_cached_image(prompt_hash)
        if cached:
            out_path.write_bytes(cached)
            logger.info(f"Used cached image ({len(cached)} bytes) → {out_path}")
            return out_path

    # Draw Things — SDXL ожидает dimensions кратные 64
    width = (width // 64) * 64
    height = (height // 64) * 64

    url = DRAW_THINGS_URL.rstrip("/")
    payload = {
        "prompt": full_prompt,
        "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
        "width": width,
        "height": height,
        "steps": steps,
        "sampler": sampler,
        "seed": seed if seed is not None else -1,
        "cfg_scale": cfg_scale,
        "batch_size": 1,
        "batch_count": 1,
    }

    logger.info(
        f"Generating via Draw Things → {out_path} "
        f"({width}x{height}, steps={steps}, seed={seed})"
    )

    try:
        resp = requests.post(
            f"{url}/sdapi/v1/txt2img",
            json=payload,
            timeout=DRAW_THINGS_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Draw Things HTTP error: {e}") from e

    images = data.get("images") or []
    if not images:
        raise RuntimeError(f"Draw Things returned no images: {data}")

    import base64
    img_b64 = images[0]
    if isinstance(img_b64, str) and img_b64.startswith("data:image"):
        img_b64 = img_b64.split(",", 1)[1]

    img_bytes = base64.b64decode(img_b64)
    out_path.write_bytes(img_bytes)

    if use_cache:
        save_cached_image(prompt_hash, img_bytes)

    logger.info(f"Saved {len(img_bytes)} bytes → {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m py.render.draw_things_client <prompt> <output>")
        sys.exit(1)
    print(generate_image(sys.argv[1], sys.argv[2]))
