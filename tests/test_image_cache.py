"""Tests for py/lib/image_cache.py — Prompt-Image Caching."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from py.lib import image_cache


class TestImageCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compute_prompt_hash_deterministic(self):
        hash1 = image_cache.compute_prompt_hash("char1", "scene1", "comic", 42)
        hash2 = image_cache.compute_prompt_hash("char1", "scene1", "comic", 42)
        hash3 = image_cache.compute_prompt_hash("char1", "scene1", "star", 42)

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)  # SHA256 length

    def test_cache_miss_returns_none(self):
        result = image_cache.get_cached_image("nonexistent_hash_12345", cache_dir=self.cache_dir)
        self.assertIsNone(result)

    def test_save_and_get_cached_image(self):
        prompt_hash = image_cache.compute_prompt_hash("cat", "cat sitting", "bubble", 123)
        dummy_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest"

        saved_path = image_cache.save_cached_image(prompt_hash, dummy_bytes, cache_dir=self.cache_dir)
        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.name, f"{prompt_hash}.png")

        cached = image_cache.get_cached_image(prompt_hash, cache_dir=self.cache_dir)
        self.assertEqual(cached, dummy_bytes)


if __name__ == "__main__":
    unittest.main()
