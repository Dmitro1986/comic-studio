"""Prompt-Image Caching Module.

Caches generated panel images by sha256(character_prompt + scene_prompt + style + seed).
Skips MiniMax API calls when the prompt hash exists in data/.cache/images/<hash>.png.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from py.lib.logging_setup import setup

logger = setup("lib.image_cache")

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / ".cache" / "images"


def compute_prompt_hash(character_prompt: str, scene_prompt: str, style: str, seed: int | str = 0) -> str:
    """Computes a SHA256 hex string for the given prompt parameters."""
    raw = f"{character_prompt}|{scene_prompt}|{style}|{seed}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_cache_dir(custom_dir: Optional[Path] = None) -> Path:
    """Returns the cache directory, creating it if necessary."""
    target = custom_dir or DEFAULT_CACHE_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_cached_image(prompt_hash: str, cache_dir: Optional[Path] = None) -> Optional[bytes]:
    """Retrieves cached image bytes if prompt_hash exists in cache."""
    cdir = get_cache_dir(cache_dir)
    file_path = cdir / f"{prompt_hash}.png"
    if file_path.exists():
        logger.info(f"image_cache.hit hash={prompt_hash[:8]}")
        return file_path.read_bytes()
    logger.info(f"image_cache.miss hash={prompt_hash[:8]}")
    return None


def save_cached_image(prompt_hash: str, image_bytes: bytes, cache_dir: Optional[Path] = None) -> Path:
    """Saves image bytes to cache for prompt_hash."""
    cdir = get_cache_dir(cache_dir)
    file_path = cdir / f"{prompt_hash}.png"
    file_path.write_bytes(image_bytes)
    logger.info(f"image_cache.saved hash={prompt_hash[:8]} bytes={len(image_bytes)}")
    return file_path
