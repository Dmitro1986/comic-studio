"""Генерация сценария комикса из контекста через LLM.

Использует MiniMax chat API (та же компания, что и image-01). По умолчанию
провайдер можно переопределить через переменную SCENARIO_LLM_PROVIDER.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from py.lib.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, scenarios_dir
from py.lib.logging_setup import setup

logger = setup("scenario.writer")

# Стили изображений для MiniMax image-01
STYLE_TEMPLATES = {
    "cartoon": "cartoon style, vibrant colors, animated, fun, expressive characters, bold outlines",
    "anime": "anime style, Japanese animation, cel shaded, detailed background, dramatic lighting",
    "comic": "comic book style, bold outlines, halftone dots, pop art colors, dramatic shadows",
    "realistic": "photorealistic, 8K, detailed, cinematic lighting, high contrast, sharp focus",
    "watercolor": "watercolor painting style, soft edges, artistic, paper texture, gentle colors",
}

SYSTEM_PROMPT = """Ты креативный сценарист коротких кинематографичных комиксов (3-6 панелей).
Тебе дают контекст (статья, транскрипт видео, свободный текст).
Твоя задача — придумать визуальную мини-историю.

ПРАВИЛА:
- От 3 до 6 панелей включительно (не меньше 3, не больше 6). Точное количество указывается в требованиях.
- Каждая панель — конкретная визуальная сцена, описанная как кинематографист.
- **ПОДПИСИ (captions) — ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.** Краткие, дерзкие, ≤6 слов.
- Стиль подписей: по умолчанию 'bubble', также 'star', 'gothic', 'boom', 'memo', 'bar'.
- Если контекст серьёзный — tone='epic'. Если юмор — tone='funny'. Если обучение — tone='educational'.
- Персонажи должны быть описаны детально (внешность, одежда, отличительные черты) — это КЛЮЧ к консистентности между панелями.
- Верни СТРОГО JSON без markdown-обёртки.

Формат ответа:
{
  "title": "Название комикса",
  "tone": "epic|funny|educational|dark|whimsical",
  "style": "bubble|star|gothic|boom|memo|bar",
  "layout": "comic|grid",
  "aspect_ratio": "16:9",
  "characters": [
    {"name": "Имя персонажа", "appearance": "детальное описание внешности", "mannerisms": "отличительные жесты, мимика, голос"}
  ],
  "panels": [
    {"n": 1, "prompt": "детальное визуальное описание сцены на английском, ≤1500 chars. В начале: CHARACTERS: <имя>: <описание внешности>. Персонажей указывать по именам.", "caption": "подпись на РУССКОМ, ≤6 слов"},
    {"n": 2, "prompt": "...", "caption": "..."},
    {"n": 3, "prompt": "...", "caption": "..."}
  ]
}
"""


def _call_minimax_chat(system: str, user: str) -> str:
    """Минимальный вызов MiniMax chat API (compatible mode).

    Raises RuntimeError on auth/network/JSON errors. Callers (e.g. revise_scenario)
    are responsible for wrapping this in RevisionFallback to enable graceful
    degradation when the LLM is unavailable.
    """
    import requests

    if not MINIMAX_API_KEY:
        raise RuntimeError("MINIMAX_API_KEY not set")

    base = MINIMAX_BASE_URL or "https://api.minimax.io"
    url = f"{base}/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.8,
        "max_tokens": 2048,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    # Поддержка обоих форматов
    if "choices" in data and data["choices"]:
        return data["choices"][0]["message"]["content"]
    if "base_resp" in data and data["base_resp"].get("status_code") != 0:
        raise RuntimeError(f"API error: {data['base_resp']}")
    raise RuntimeError(f"Unexpected response: {data}")


def _call_minimax_chat_for_revision(system: str, user: str, scenario_id: Optional[str] = None) -> str:
    """Wrapper around _call_minimax_chat that logs full diagnostics on failure.

    Emits a `revision.llm_failed` log event with stderr-style fields (HTTP status,
    response excerpt, exception class). Returns raw LLM text on success.
    Raises RevisionFallback on any error so the caller can return current panels.
    """
    import traceback

    try:
        return _call_minimax_chat(system, user)
    except Exception as error:
        tb = traceback.format_exc()
        error_class = error.__class__.__name__
        http_status = getattr(getattr(error, "response", None), "status_code", None)
        response_excerpt = None
        response_obj = getattr(error, "response", None)
        if response_obj is not None:
            try:
                response_excerpt = (response_obj.text or "")[:500]
            except Exception:
                response_excerpt = None

        logger.error(
            "revision.llm_failed",
            extra={
                "scenario_id": scenario_id,
                "error_class": error_class,
                "error_message": str(error),
                "http_status": http_status,
                "response_excerpt": response_excerpt,
                "traceback": tb,
            },
        )

        reason = "llm_error"
        message = str(error) or error_class
        if "timeout" in message.lower() or "timed out" in message.lower():
            reason = "llm_timeout"
        elif http_status == 429:
            reason = "llm_rate_limited"
        elif http_status is not None and http_status >= 500:
            reason = "llm_server_error"

        raise RevisionFallback(
            reason=reason,
            warnings=[
                f"LLM call failed: {error_class}: {message}",
                "Returning current panels unchanged; scenario status preserved.",
            ],
            original_error=error,
        )


def _extract_json(text: str) -> dict:
    """Извлекает JSON из ответа LLM, даже если обёрнут в ```json ... ```."""
    text = text.strip()
    # Удаляем markdown fence
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


MAX_CONTEXT_CHARS = 8_000
MAX_REVISION_HISTORY = 10
MAX_FEEDBACK_FOR_REVISION = 20
MAX_PROMPT_CHARS = 1_500
MAX_CAPTION_WORDS = 6
ACCEPTED_PANEL_COUNTS = (3, 4, 5, 6)
DEFAULT_PANEL_COUNT = 3
MIN_PANEL_COUNT = 3
MAX_PANEL_COUNT = 6


class RevisionFallback(Exception):
    """Raised when revision cannot be safely regenerated via LLM.

    Carries enough context for the caller to gracefully return current panels
    WITHOUT changing the scenario status. Used when:
      - LLM call timed out, rate-limited, or 5xx
      - LLM returned malformed JSON
      - LLM returned a panel count outside ACCEPTED_PANEL_COUNTS

    Attributes:
        reason: short machine-readable code (e.g. "llm_timeout", "panel_count_out_of_range")
        warnings: list of human-readable strings for the operator
        original_error: underlying exception (if any) for diagnostics
    """

    def __init__(self, reason: str, warnings: list, original_error: Optional[BaseException] = None):
        self.reason = reason
        self.warnings = list(warnings)
        self.original_error = original_error
        super().__init__(f"Revision fallback: {reason}")

REVISION_SYSTEM_PROMPT = """Ты редактор комикс-сценария, который обновляет существующий JSON-сценарий, применяя отзыв автора.

ПРАВИЛА:
- Сохрани все ранее зафиксированные метаданные: title, tone, style, image_style, layout, aspect_ratio, seed, characters.
- Допускается 3 или 4 панели; используй количество панелей, ближайшее к прежнему, если в feedback не указано иное.
- Каждая панель: prompt ≤1500 символов, caption ≤6 слов, только на русском.
- Персонажи (если есть) должны сохраняться и их описания могут обновляться для лучшей консистентности.
- Не добавляй markdown-обёртку; верни только валидный JSON.
- Учитывай source context, исходные panels и всю feedback history; не игнорируй явные замечания автора.
- Не повторяй panels без необходимости; изменяй только то, что вытекает из feedback.

Формат ответа:
{
  "title": "Название комикса",
  "tone": "epic|funny|educational|dark|whimsical",
  "style": "bubble|star|gothic|boom|memo|bar",
  "layout": "comic|grid",
  "aspect_ratio": "16:9",
  "characters": [
    {"name": "Имя", "appearance": "описание", "mannerisms": "жесты"}
  ],
  "panels": [
    {"n": 1, "prompt": "≤1500 chars. CHARACTERS: <имя>: <описание>.", "caption": "≤6 слов на русском"},
    ...
  ]
}
"""


def generate_scenario(
    context: str,
    tone: Optional[str] = None,
    style: Optional[str] = None,
    image_style: Optional[str] = None,
    num_panels: int = 3,
) -> dict:
    """Генерирует сценарий комикса из текстового контекста.

    Args:
        context: Текстовый контекст для сценария
        tone: Тон комикса (epic, funny, educational, dark, whimsical)
        style: Стиль подписей (star, bubble, gothic, boom, memo, bar)
        image_style: Стиль изображений (cartoon, anime, comic, realistic, watercolor)
        num_panels: Количество панелей

    Returns:
        dict со всеми полями сценария + id, created_at, status, source
    """
    if num_panels not in ACCEPTED_PANEL_COUNTS:
        raise ValueError(
            f"generate_scenario: num_panels={num_panels} must be in {list(ACCEPTED_PANEL_COUNTS)}"
        )
    # Enforce spec drafting context bound
    bounded = context[:MAX_CONTEXT_CHARS]
    if len(context) > MAX_CONTEXT_CHARS:
        logger.info(f"Context {len(context)} chars exceeds {MAX_CONTEXT_CHARS}, truncating to {MAX_CONTEXT_CHARS}")
    
    user_msg = (
        f"Контекст:\n\n{bounded}\n\n"
        f"Требования: {num_panels} панели."
        + (f" Тон: {tone}." if tone else "")
        + (f" Стиль подписей: {style}." if style else "")
        + (f" Стиль картинок: {image_style}." if image_style else "")
    )

    logger.info(f"Generating scenario ({num_panels} panels, {len(context)} chars context)")
    raw = _call_minimax_chat(SYSTEM_PROMPT, user_msg)
    scenario = _extract_json(raw)

    # Обогащаем метаданными
    scenario["id"] = str(uuid.uuid4())[:8]
    scenario["created_at"] = datetime.now().isoformat()
    scenario["status"] = "draft"
    scenario["source"] = "context"
    scenario["context"] = context[:2000]  # хранить первые 2k как превью

    # Дефолты
    scenario.setdefault("tone", tone or "epic")
    scenario.setdefault("style", style or "bubble")
    scenario.setdefault("image_style", image_style or "comic")
    scenario.setdefault("layout", "comic")
    scenario.setdefault("aspect_ratio", "16:9")
    scenario.setdefault("characters", [])

    # Собираем CHARACTERS строку для промптов
    characters_list = scenario.get("characters", [])
    if characters_list:
        char_parts = []
        for c in characters_list:
            name = c.get("name", "Character")
            appearance = c.get("appearance", "")
            mannerisms = c.get("mannerisms", "")
            char_str = f"{name}: {appearance}"
            if mannerisms:
                char_str += f", {mannerisms}"
            char_parts.append(char_str)
        characters_str = "CHARACTERS: " + "; ".join(char_parts) + ". "
    else:
        characters_str = ""

    # Добавляем стиль и персонажей к промптам панелей
    style_suffix = STYLE_TEMPLATES.get(scenario["image_style"], STYLE_TEMPLATES["comic"])
    for panel in scenario.get("panels", []):
        if "prompt" in panel:
            panel["prompt"] = f"{characters_str}{panel['prompt']}, {style_suffix}"

    # Проверка структуры
    if not isinstance(scenario.get("panels"), list) or not scenario["panels"]:
        raise ValueError(f"Invalid scenario structure: {scenario}")

    logger.info(f"Generated scenario id={scenario['id']} title={scenario['title']!r}, image_style={scenario['image_style']}")
    return scenario


def save_scenario(scenario: dict, status: str = "draft") -> str:
    """Сохраняет сценарий в data/scenarios/<status>/<id>.json."""
    out_dir = scenarios_dir(status)
    out_path = out_dir / f"{scenario['id']}.json"
    out_path.write_text(
        json.dumps(scenario, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"Saved scenario → {out_path}")
    return str(out_path)


def _build_expand_panel_user_msg(
    current_scenario: dict,
    new_panel_n: int,
    target_count: int,
    scene_hint: Optional[str] = None,
) -> str:
    """Build the LLM user-message that asks for ONE additional panel."""
    bounded_context = (current_scenario.get("context") or "")[:MAX_CONTEXT_CHARS]
    panels_summary = json.dumps(current_scenario.get("panels", []), ensure_ascii=False)[:2000]
    characters_summary = json.dumps(current_scenario.get("characters", []), ensure_ascii=False)
    style_suffix = STYLE_TEMPLATES.get(current_scenario.get("image_style", "comic"), STYLE_TEMPLATES["comic"])
    msg = (
        f"Исходный контекст:\n\n{bounded_context}\n\n"
        f"Текущий сценарий (id={current_scenario.get('id')}, panel {new_panel_n - 1} из {target_count}):\n"
        f"title={current_scenario.get('title', '')}\n"
        f"tone={current_scenario.get('tone', 'epic')}\n"
        f"style={current_scenario.get('style', 'bubble')}\n"
        f"image_style={current_scenario.get('image_style', 'comic')}\n"
        f"characters={characters_summary}\n"
        f"existing_panels={panels_summary}\n\n"
        f"Придумай ОДНУ новую панель №{new_panel_n}, которая продолжает историю."
        f" Сохраняй стиль подписей: 'bubble', 'star', 'gothic', 'boom', 'memo', 'bar'."
        f" Финальный итог сценария: {target_count} панелей.\n"
    )
    if scene_hint:
        msg += f"\nПодсказка от автора: {scene_hint}\n"
    msg += (
        "\nФормат ответа (СТРОГО JSON без markdown):\n"
        "{\n"
        '  "panel": {\n'
        '    "n": ' + str(new_panel_n) + ",\n"
        '    "prompt": "детальное визуальное описание сцены на английском, ≤1500 chars. В начале: CHARACTERS: <имя>: <описание>. Персонажей указывать по именам. Затем: , ' + style_suffix + '",\n'
        '    "caption": "подпись на РУССКОМ, ≤6 слов"\n'
        "  }\n"
        "}\n"
    )
    return msg


EXPANSION_SYSTEM_PROMPT = """Ты сценарист комикса, который добавляет ОДНУ новую панель к существующему сценарию.

ПРАВИЛА:
- Сохрани тон, стиль подписей и описания персонажей из существующего сценария.
- Новая панель должна логически продолжать историю, не повторять уже существующие панели.
- Caption ≤6 слов, только на русском.
- Prompt ≤1500 символов, на английском. Если есть персонажи — начни с `CHARACTERS: <имя>: <описание>.`
- Верни СТРОГО JSON без markdown-обёртки.
"""


def expand_panels(
    current_scenario: dict,
    target_count: int,
    scene_hints: Optional[list] = None,
) -> dict:
    """Incrementally expand a draft scenario up to ``target_count`` panels.

    Adds one panel at a time via LLM, preserving all existing panels. If the
    LLM fails for any single panel, raises RevisionFallback so the caller can
    leave the scenario unchanged.

    Args:
        current_scenario: current draft record (must have id, panels, status).
        target_count: desired final panel count, must be in ACCEPTED_PANEL_COUNTS
                      and strictly greater than the current panel count.
        scene_hints: optional list of natural-language hints, one per new panel.
                     If shorter than the number of new panels, missing hints are
                     filled with empty strings.

    Returns:
        dict clone of ``current_scenario`` with extended ``panels`` list, an
        ``expansion_history`` field tracking each added panel, and updated
        ``expanded_at`` timestamp.
    """
    if not isinstance(current_scenario, dict) or not current_scenario.get("id"):
        raise ValueError("expand_panels: current_scenario must include id")
    if target_count not in ACCEPTED_PANEL_COUNTS:
        raise ValueError(
            f"expand_panels: target_count={target_count} must be in {list(ACCEPTED_PANEL_COUNTS)}"
        )
    existing_panels = current_scenario.get("panels") or []
    if not isinstance(existing_panels, list):
        raise ValueError("expand_panels: existing panels must be a list")
    current_count = len(existing_panels)
    if current_count >= target_count:
        raise ValueError(
            f"expand_panels: scenario already has {current_count} panels, target={target_count} is not greater"
        )
    if current_count < MIN_PANEL_COUNT:
        raise ValueError(
            f"expand_panels: scenario has only {current_count} panels; minimum is {MIN_PANEL_COUNT}"
        )

    scene_hints = scene_hints or []
    added_panels = []
    panels_working = list(existing_panels)  # shallow copy

    for offset, new_n in enumerate(range(current_count + 1, target_count + 1)):
        hint = scene_hints[offset] if offset < len(scene_hints) else None
        user_msg = _build_expand_panel_user_msg(
            current_scenario={**current_scenario, "panels": panels_working},
            new_panel_n=new_n,
            target_count=target_count,
            scene_hint=hint,
        )
        try:
            raw = _call_minimax_chat_for_revision(
                EXPANSION_SYSTEM_PROMPT,
                user_msg,
                scenario_id=current_scenario.get("id"),
            )
        except RevisionFallback:
            # Surface so caller can leave scenario unchanged.
            raise

        try:
            parsed = _extract_json(raw)
        except (ValueError, json.JSONDecodeError) as error:
            raise RevisionFallback(
                reason="expand_invalid_json",
                warnings=[
                    f"LLM returned malformed JSON for panel #{new_n}: {error}",
                    "Expansion aborted; scenario panels unchanged.",
                ],
                original_error=error,
            )

        if not isinstance(parsed, dict) or not isinstance(parsed.get("panel"), dict):
            raise RevisionFallback(
                reason="expand_invalid_structure",
                warnings=[
                    f"LLM response for panel #{new_n} has no 'panel' object.",
                    "Expansion aborted; scenario panels unchanged.",
                ],
            )
        new_panel = parsed["panel"]
        if not isinstance(new_panel.get("prompt"), str) or not new_panel["prompt"].strip():
            raise RevisionFallback(
                reason="expand_empty_prompt",
                warnings=[
                    f"LLM returned empty prompt for panel #{new_n}.",
                    "Expansion aborted; scenario panels unchanged.",
                ],
            )
        if not isinstance(new_panel.get("caption"), str) or not new_panel["caption"].strip():
            raise RevisionFallback(
                reason="expand_empty_caption",
                warnings=[
                    f"LLM returned empty caption for panel #{new_n}.",
                    "Expansion aborted; scenario panels unchanged.",
                ],
            )
        if len(new_panel["prompt"]) > MAX_PROMPT_CHARS:
            raise RevisionFallback(
                reason="expand_prompt_too_long",
                warnings=[
                    f"LLM prompt for panel #{new_n} exceeds {MAX_PROMPT_CHARS} chars.",
                    "Expansion aborted; scenario panels unchanged.",
                ],
            )
        # Truncate caption to MAX_CAPTION_WORDS (same as revise)
        caption_words = new_panel["caption"].split()
        if len(caption_words) > MAX_CAPTION_WORDS:
            new_panel["caption"] = " ".join(caption_words[:MAX_CAPTION_WORDS])

        # Re-stamp panel number and append
        new_panel["n"] = new_n
        new_panel["added_via_expansion"] = True
        panels_working.append(new_panel)
        added_panels.append(new_n)

        logger.info(
            f"Expansion added panel {new_n}/{target_count} for scenario id={current_scenario.get('id')}"
        )

    # Build updated scenario record
    expansion_history = list(current_scenario.get("expansion_history") or [])
    expansion_history.append(
        {
            "ts": datetime.now().isoformat(),
            "from_count": current_count,
            "to_count": target_count,
            "added_panels": added_panels,
            "hints_provided": len(scene_hints),
        }
    )
    updated = {
        **current_scenario,
        "panels": panels_working,
        "expansion_history": expansion_history,
        "expanded_at": datetime.now().isoformat(),
    }
    return updated


def _format_feedback_history(feedback_history: list) -> str:
    lines = []
    for index, item in enumerate(feedback_history, start=1):
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
        else:
            text = str(item).strip()
        if not text:
            continue
        lines.append(f"{index}. {text}")
    return "\n".join(lines)


def _validate_revision_response(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("revise_scenario: LLM response is not a JSON object")
    if not isinstance(payload.get("panels"), list) or not payload["panels"]:
        raise ValueError("revise_scenario: response has no panels")
    if len(payload["panels"]) not in ACCEPTED_PANEL_COUNTS:
        raise ValueError(f"revise_scenario: panel count must be {ACCEPTED_PANEL_COUNTS}")
    for index, panel in enumerate(payload["panels"], start=1):
        if not isinstance(panel, dict):
            raise ValueError(f"revise_scenario: panel #{index} is not an object")
        prompt = str(panel.get("prompt", "")).strip()
        caption = str(panel.get("caption", "")).strip()
        if not prompt:
            raise ValueError(f"revise_scenario: panel #{index} has empty prompt")
        if len(prompt) > MAX_PROMPT_CHARS:
            raise ValueError(f"revise_scenario: panel #{index} prompt exceeds {MAX_PROMPT_CHARS} chars")
        if not caption:
            raise ValueError(f"revise_scenario: panel #{index} has empty caption")
        words = caption.split()
        if len(words) > MAX_CAPTION_WORDS:
            raise ValueError(f"revise_scenario: panel #{index} caption exceeds {MAX_CAPTION_WORDS} words")


def revise_scenario(
    current_scenario: dict,
    feedback_history: list[dict],
    source_context: str = "",
    image_style: Optional[str] = None,
) -> dict:
    """Регенерирует сценарий, применяя bounded feedback history.

    Args:
        current_scenario: текущий canonical record (draft/approved/rendered).
        feedback_history: ограниченная история правок автора.
        source_context: bounded исходный контекст (статья, YouTube, freeform).
        image_style: стиль изображений для style suffix.

    Returns:
        dict со revised panels, prompts, captions и сохранёнными метаданными.
    """
    if not isinstance(current_scenario, dict) or not current_scenario.get("id"):
        raise ValueError("revise_scenario: current_scenario must include id")
    if not isinstance(feedback_history, list) or not feedback_history:
        raise ValueError("revise_scenario: feedback_history must be a non-empty list")
    if len(feedback_history) > MAX_FEEDBACK_FOR_REVISION:
        raise ValueError(f"revise_scenario: feedback history exceeds {MAX_FEEDBACK_FOR_REVISION}")

    bounded_context = (source_context or "")[:MAX_CONTEXT_CHARS]
    formatted_feedback = _format_feedback_history(feedback_history)
    panels_summary = json.dumps(current_scenario.get("panels", []), ensure_ascii=False)[:2000]
    image_style = image_style or current_scenario.get("image_style", "comic")

    user_msg = (
        f"Исходный контекст:\n\n{bounded_context}\n\n"
        f"Текущий сценарий (id={current_scenario.get('id')}):\n"
        f"title={current_scenario.get('title', '')}\n"
        f"tone={current_scenario.get('tone', 'epic')}\n"
        f"style={current_scenario.get('style', 'star')}\n"
        f"image_style={image_style}\n"
        f"layout={current_scenario.get('layout', 'comic')}\n"
        f"aspect_ratio={current_scenario.get('aspect_ratio', '16:9')}\n"
        f"characters={json.dumps(current_scenario.get('characters', []), ensure_ascii=False)}\n"
        f"panels={panels_summary}\n\n"
        f"История правок автора:\n{formatted_feedback}\n\n"
        f"Примени ВСЕ отзывы и верни revised JSON."
    )

    logger.info(
        f"Revising scenario id={current_scenario.get('id')} with {len(feedback_history)} feedback items"
    )

    # Step 1: call LLM with structured fallback on any error (timeout, rate-limit, 5xx, JSON)
    try:
        raw = _call_minimax_chat_for_revision(REVISION_SYSTEM_PROMPT, user_msg, scenario_id=current_scenario.get("id"))
    except RevisionFallback:
        # Re-raise so caller (CLI / runtime) can restore scenario state and return panels unchanged.
        raise

    # Step 2: parse JSON (catch malformed output as fallback)
    try:
        revised = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as error:
        logger.error(
            "revision.json_invalid",
            extra={
                "scenario_id": current_scenario.get("id"),
                "error_class": error.__class__.__name__,
                "error_message": str(error),
                "raw_excerpt": (raw or "")[:500],
            },
        )
        raise RevisionFallback(
            reason="llm_invalid_json",
            warnings=[
                f"LLM returned malformed JSON: {error}",
                "Returning current panels unchanged; scenario status preserved.",
            ],
            original_error=error,
        )

    if isinstance(revised, dict) and isinstance(revised.get("panels"), list):
        for panel in revised["panels"]:
            if isinstance(panel, dict) and isinstance(panel.get("caption"), str):
                words = panel["caption"].split()
                if len(words) > MAX_CAPTION_WORDS:
                    panel["caption"] = " ".join(words[:MAX_CAPTION_WORDS])

    # Step 3: validate panel count — if LLM gave us wrong shape, fall back instead of failing
    if not isinstance(revised, dict):
        raise RevisionFallback(
            reason="llm_invalid_json",
            warnings=["LLM response is not a JSON object.", "Returning current panels unchanged."],
        )
    if not isinstance(revised.get("panels"), list) or not revised["panels"]:
        raise RevisionFallback(
            reason="llm_no_panels",
            warnings=["LLM response has no panels array.", "Returning current panels unchanged."],
        )
    if len(revised["panels"]) not in ACCEPTED_PANEL_COUNTS:
        actual = len(revised["panels"])
        raise RevisionFallback(
            reason="panel_count_out_of_range",
            warnings=[
                f"LLM returned {actual} panels, expected one of {list(ACCEPTED_PANEL_COUNTS)}.",
                "Returning current panels unchanged; scenario status preserved.",
            ],
        )

    # Step 4: full validation only when shape passed; surface remaining issues as fallback
    try:
        _validate_revision_response(revised)
    except ValueError as error:
        logger.error(
            "revision.validation_failed",
            extra={
                "scenario_id": current_scenario.get("id"),
                "error_message": str(error),
            },
        )
        raise RevisionFallback(
            reason="llm_validation_failed",
            warnings=[
                f"LLM response failed validation: {error}",
                "Returning current panels unchanged; scenario status preserved.",
            ],
            original_error=error,
        )

    revised.setdefault("title", current_scenario.get("title"))
    revised.setdefault("tone", current_scenario.get("tone", "epic"))
    revised.setdefault("style", current_scenario.get("style", "bubble"))
    revised.setdefault("image_style", image_style)
    revised.setdefault("layout", current_scenario.get("layout", "comic"))
    revised.setdefault("aspect_ratio", current_scenario.get("aspect_ratio", "16:9"))
    revised.setdefault("characters", current_scenario.get("characters", []))

    # Инъекция персонажей в промты
    characters_list = revised.get("characters", [])
    if characters_list:
        char_parts = []
        for c in characters_list:
            name = c.get("name", "Character")
            appearance = c.get("appearance", "")
            mannerisms = c.get("mannerisms", "")
            char_str = f"{name}: {appearance}"
            if mannerisms:
                char_str += f", {mannerisms}"
            char_parts.append(char_str)
        characters_str = "CHARACTERS: " + "; ".join(char_parts) + ". "
    else:
        characters_str = ""

    style_suffix = STYLE_TEMPLATES.get(revised["image_style"], STYLE_TEMPLATES["comic"])
    for panel in revised["panels"]:
        if "prompt" in panel:
            prompt = panel["prompt"]
            # Избегаем дублирования CHARACTERS
            if "CHARACTERS:" not in prompt:
                panel["prompt"] = f"{characters_str}{prompt}, {style_suffix}"

    revised["id"] = current_scenario["id"]
    revised["status"] = "draft"
    revised["revision_of"] = current_scenario["id"]
    revised["revision_at"] = datetime.now().isoformat()
    return revised


def _read_feedback_file(path: str) -> list[dict]:
    raw = Path(path).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("--feedback-file must be a JSON array")
    return parsed


def _read_source_context_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Revise an existing scenario via LLM")
    parser.add_argument("--scenario-id", required=True, help="ID of the scenario to revise")
    parser.add_argument("--scenario-path", required=True, help="Path to the canonical scenario JSON")
    parser.add_argument("--feedback-file", help="Path to JSON array of feedback items")
    parser.add_argument("--feedback", help="Inline JSON array of feedback items")
    parser.add_argument("--source-context-file", help="Optional file with source context")
    parser.add_argument("--source-context", help="Optional inline source context")
    parser.add_argument("--image-style", choices=list(STYLE_TEMPLATES.keys()), help="Override image style")
    parser.add_argument("--json-result", action="store_true", help="Print machine-readable result")
    parser.add_argument("--out", help="Path to write revised scenario JSON")
    args = parser.parse_args()

    if bool(args.feedback_file) == bool(args.feedback):
        parser.error("Provide exactly one of --feedback-file or --feedback")

    scenario_path = Path(args.scenario_path)
    current = json.loads(scenario_path.read_text(encoding="utf-8"))
    if current.get("id") != args.scenario_id:
        raise SystemExit(f"--scenario-id {args.scenario_id!r} does not match record id {current.get('id')!r}")

    if args.feedback_file:
        feedback = _read_feedback_file(args.feedback_file)
    else:
        feedback = json.loads(args.feedback)
    if not isinstance(feedback, list) or not feedback:
        raise SystemExit("feedback list must be non-empty")

    source_context = args.source_context or ""
    if args.source_context_file:
        source_context = _read_source_context_file(args.source_context_file)

    try:
        revised = revise_scenario(current, feedback, source_context=source_context, image_style=args.image_style)
    except Exception as error:
        result = {"ok": False, "error": str(error)}
        if args.json_result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"❌ {error}", file=sys.stderr)
        return 1

    out_path = Path(args.out) if args.out else scenario_path
    out_path.write_text(json.dumps(revised, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "ok": True,
        "id": revised["id"],
        "status": revised["status"],
        "path": str(out_path),
        "revision_at": revised["revision_at"],
        "feedback_count": len(feedback),
    }
    if args.json_result:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"✅ Revised → {out_path}")
    return 0


if __name__ == "__main__":
    import sys
    text = sys.stdin.read() if not sys.argv[1:] else " ".join(sys.argv[1:])
    s = generate_scenario(text)
    save_scenario(s)
    print(json.dumps(s, ensure_ascii=False, indent=2))