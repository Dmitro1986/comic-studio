"""Tests for `py.scenario.writer.expand_panels` and panel count handling.

T2 — `create_comic` panel_count 3..6 + `expand_panels` incremental tool.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py.scenario import writer
from py.scenario.writer import RevisionFallback


def _build_scenario(panel_count: int = 3) -> dict:
    panels = [
        {"n": i + 1, "prompt": f"Scene {i + 1}", "caption": f"Кадр {i + 1}"}
        for i in range(panel_count)
    ]
    return {
        "id": "exp-0001",
        "title": "Expand Test",
        "tone": "epic",
        "style": "star",
        "image_style": "comic",
        "layout": "comic",
        "aspect_ratio": "16:9",
        "panels": panels,
        "context": "Test context for expansion",
        "feedback": [],
    }


class GenerateScenarioPanelCountTests(unittest.TestCase):
    def test_generate_scenario_accepts_panel_count_5(self):
        scenario = _build_scenario(5)
        def fake_chat(system, user):
            return json.dumps({
                "title": "Test",
                "tone": "epic",
                "style": "star",
                "image_style": "comic",
                "panels": [{"n": i + 1, "prompt": "p", "caption": "ok"} for i in range(5)],
            })
        original = writer._call_minimax_chat
        writer._call_minimax_chat = fake_chat
        try:
            result = writer.generate_scenario("ctx", num_panels=5)
        finally:
            writer._call_minimax_chat = original
        self.assertEqual(len(result["panels"]), 5)

    def test_generate_scenario_accepts_panel_count_6(self):
        def fake_chat(system, user):
            return json.dumps({
                "title": "Test",
                "tone": "epic",
                "style": "star",
                "image_style": "comic",
                "panels": [{"n": i + 1, "prompt": "p", "caption": "ok"} for i in range(6)],
            })
        original = writer._call_minimax_chat
        writer._call_minimax_chat = fake_chat
        try:
            result = writer.generate_scenario("ctx", num_panels=6)
        finally:
            writer._call_minimax_chat = original
        self.assertEqual(len(result["panels"]), 6)

    def test_generate_scenario_rejects_panel_count_2(self):
        with self.assertRaises(ValueError) as ctx:
            writer.generate_scenario("ctx", num_panels=2)
        self.assertIn("num_panels=2", str(ctx.exception))
        self.assertIn("[3, 4, 5, 6]", str(ctx.exception))

    def test_generate_scenario_rejects_panel_count_7(self):
        with self.assertRaises(ValueError) as ctx:
            writer.generate_scenario("ctx", num_panels=7)
        self.assertIn("num_panels=7", str(ctx.exception))


class ExpandPanelsTests(unittest.TestCase):
    def test_expand_panels_rejects_target_count_outside_range(self):
        scenario = _build_scenario(3)
        with self.assertRaises(ValueError) as ctx:
            writer.expand_panels(scenario, target_count=7)
        self.assertIn("target_count=7", str(ctx.exception))

    def test_expand_panels_rejects_target_not_greater_than_current(self):
        scenario = _build_scenario(5)
        with self.assertRaises(ValueError) as ctx:
            writer.expand_panels(scenario, target_count=5)
        self.assertIn("already has 5 panels", str(ctx.exception))

    def test_expand_panels_rejects_scenario_below_minimum(self):
        scenario = _build_scenario(2)
        with self.assertRaises(ValueError) as ctx:
            writer.expand_panels(scenario, target_count=4)
        self.assertIn("minimum is 3", str(ctx.exception))

    def test_expand_panels_rejects_non_dict_scenario(self):
        with self.assertRaises(ValueError):
            writer.expand_panels([], target_count=4)

    def test_expand_panels_adds_one_panel_per_iteration(self):
        scenario = _build_scenario(3)

        chat_calls = []

        def fake_chat(system, user):
            chat_calls.append(user)
            # Each LLM call asks for ONE panel (numbered N+offset)
            # Parse the new_panel_n from the user_msg by searching for "Придумай ОДНУ новую панель №"
            import re
            match = re.search(r"Придумай ОДНУ новую панель №(\d+)", user)
            n = int(match.group(1)) if match else len(chat_calls)
            return json.dumps({
                "panel": {
                    "n": n,
                    "prompt": f"Generated panel {n}",
                    "caption": f"Кадр {n}",
                }
            })

        original = writer._call_minimax_chat
        writer._call_minimax_chat = fake_chat
        try:
            # Mock the revision wrapper too
            original_revision_chat = writer._call_minimax_chat_for_revision
            writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
            try:
                result = writer.expand_panels(scenario, target_count=6)
            finally:
                writer._call_minimax_chat_for_revision = original_revision_chat
        finally:
            writer._call_minimax_chat = original

        # 3 → 6 requires 3 new panels → 3 LLM calls
        self.assertEqual(len(chat_calls), 3, "three LLM calls for 3→6 expansion")
        self.assertEqual(len(result["panels"]), 6, "scenario has 6 panels after expansion")
        # New panels marked as added via expansion
        for n in (4, 5, 6):
            self.assertTrue(result["panels"][n - 1]["added_via_expansion"], f"panel #{n} marked")
            self.assertEqual(result["panels"][n - 1]["n"], n, f"panel #{n} has correct number")
        # Original panels unchanged
        self.assertEqual(result["panels"][0]["caption"], "Кадр 1")
        self.assertEqual(result["panels"][2]["caption"], "Кадр 3")
        # History populated
        self.assertEqual(len(result["expansion_history"]), 1)
        self.assertEqual(result["expansion_history"][0]["from_count"], 3)
        self.assertEqual(result["expansion_history"][0]["to_count"], 6)
        self.assertEqual(result["expansion_history"][0]["added_panels"], [4, 5, 6])
        self.assertIn("expanded_at", result)

    def test_expand_panels_3_to_5_with_hints(self):
        scenario = _build_scenario(3)

        hints_received = []

        def fake_chat(system, user):
            import re
            match = re.search(r"Придумай ОДНУ новую панель №(\d+)", user)
            n = int(match.group(1)) if match else 0
            # Capture hint presence
            hints_received.append("Подсказка от автора" in user)
            return json.dumps({
                "panel": {"n": n, "prompt": "p", "caption": "fine"},
            })

        original_revision_chat = writer._call_minimax_chat_for_revision
        writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
        try:
            result = writer.expand_panels(
                scenario,
                target_count=5,
                scene_hints=["Rooftop chase scene", "Face-off in the rain"],
            )
        finally:
            writer._call_minimax_chat_for_revision = original_revision_chat

        self.assertEqual(len(result["panels"]), 5)
        self.assertEqual(hints_received, [True, True], "both hints included in user_msg")

    def test_expand_panels_fallback_when_llm_fails(self):
        """T2: graceful fallback on LLM failure — scenario unchanged."""
        scenario = _build_scenario(3)
        original_panels = list(scenario["panels"])

        class _Fake429Response:
            status_code = 429
            text = 'rate limit'

        class _RateLimitError(Exception):
            def __init__(self):
                super().__init__('Too Many Requests')
                self.response = _Fake429Response()

        def fake_chat(system, user):
            raise _RateLimitError()

        # Patch the inner function so the wrapper still wraps the exception
        original = writer._call_minimax_chat
        writer._call_minimax_chat = fake_chat
        try:
            with self.assertRaises(RevisionFallback) as ctx:
                writer.expand_panels(scenario, target_count=5)
        finally:
            writer._call_minimax_chat = original

        self.assertEqual(ctx.exception.reason, "llm_rate_limited")
        # Original scenario panels unchanged
        self.assertEqual(scenario["panels"], original_panels, "original panels preserved")

    def test_expand_panels_fallback_on_invalid_json(self):
        scenario = _build_scenario(3)
        original_panels = list(scenario["panels"])

        def fake_chat(system, user):
            return "not a json response"

        original_revision_chat = writer._call_minimax_chat_for_revision
        writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
        try:
            with self.assertRaises(RevisionFallback) as ctx:
                writer.expand_panels(scenario, target_count=5)
        finally:
            writer._call_minimax_chat_for_revision = original_revision_chat

        self.assertEqual(ctx.exception.reason, "expand_invalid_json")
        self.assertEqual(scenario["panels"], original_panels)

    def test_expand_panels_fallback_on_missing_panel_object(self):
        scenario = _build_scenario(3)

        def fake_chat(system, user):
            return json.dumps({"unexpected_key": "no panel here"})

        original_revision_chat = writer._call_minimax_chat_for_revision
        writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
        try:
            with self.assertRaises(RevisionFallback) as ctx:
                writer.expand_panels(scenario, target_count=4)
        finally:
            writer._call_minimax_chat_for_revision = original_revision_chat
        self.assertEqual(ctx.exception.reason, "expand_invalid_structure")

    def test_expand_panels_fallback_on_empty_caption(self):
        scenario = _build_scenario(3)

        def fake_chat(system, user):
            return json.dumps({"panel": {"n": 4, "prompt": "ok", "caption": ""}})

        original_revision_chat = writer._call_minimax_chat_for_revision
        writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
        try:
            with self.assertRaises(RevisionFallback) as ctx:
                writer.expand_panels(scenario, target_count=4)
        finally:
            writer._call_minimax_chat_for_revision = original_revision_chat
        self.assertEqual(ctx.exception.reason, "expand_empty_caption")

    def test_expand_panels_truncates_long_captions(self):
        scenario = _build_scenario(3)

        def fake_chat(system, user):
            return json.dumps({
                "panel": {
                    "n": 4,
                    "prompt": "ok",
                    "caption": "one two three four five six seven eight",  # 8 words
                }
            })

        original_revision_chat = writer._call_minimax_chat_for_revision
        writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
        try:
            result = writer.expand_panels(scenario, target_count=4)
        finally:
            writer._call_minimax_chat_for_revision = original_revision_chat
        self.assertEqual(result["panels"][3]["caption"], "one two three four five six")

    def test_expand_panels_appends_to_existing_history(self):
        scenario = _build_scenario(3)
        # Pre-existing history entry (scenario was previously expanded 3→4)
        scenario["expansion_history"] = [
            {"ts": "2026-09-01T00:00:00", "from_count": 3, "to_count": 4, "added_panels": [4]}
        ]

        def fake_chat(system, user):
            return json.dumps({"panel": {"n": 5, "prompt": "ok", "caption": "fine"}})

        original_revision_chat = writer._call_minimax_chat_for_revision
        writer._call_minimax_chat_for_revision = lambda sys, user, scenario_id=None: fake_chat(sys, user)
        try:
            result = writer.expand_panels(scenario, target_count=5)
        finally:
            writer._call_minimax_chat_for_revision = original_revision_chat

        self.assertEqual(len(result["expansion_history"]), 2, "history extended")
        self.assertEqual(result["expansion_history"][0]["to_count"], 4)
        self.assertEqual(result["expansion_history"][1]["to_count"], 5)
        # Current scenario has 3 panels (history entry describes a previous run,
        # not the current panel count); expansion goes 3→5 = added panels [4, 5]
        self.assertEqual(result["expansion_history"][1]["added_panels"], [4, 5])


if __name__ == "__main__":
    unittest.main()
