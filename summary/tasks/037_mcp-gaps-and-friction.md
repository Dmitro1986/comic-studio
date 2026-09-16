# Задачі: MCP gaps and operator friction

## Статус: 🟡 In Progress (audit done, T1-T4 done, T5-T6 scoped)

Деривація: `summary/audit/037_mcp-gaps-and-friction.md`. 10 проблем, згруповані у 6 task-блоків (бо частина фіксів перетинаються — описано в аудиті).

| ID | Задача | Пріоритет | Статус | Прувер |
|---|---|---|---|---|
| **T1** | **Виправити `revise_scenario` — logging + graceful fallback** (issue #1) | 🔴 P0 | ✅ Done | Operator: `revise_scenario` з валідним фідбеком не губить сценарій |
| **T2** | **`create_comic` + `expand_panels` — підтримка panel_count 3..6** (issue #2) | 🔴 P0 | ✅ Done | Operator: `create_comic(content, panel_count=6)` дає 6 panels без ручного edit |
| **T3** | **`render_comic` приймає `provider` + `publish`** (issues #3, #4) | 🔴 P0 | ✅ Done | Operator: один MCP-виклик рендерить через Draw Things + публікує на comic.openaiua.fr |
| **T4** | **`create_book_html` MCP tool + `book.html.j2` + `book.css`** (issues #5, #7) | 🔴 P0 | ✅ Done | Operator: `create_book_html(id, "sentry")` дає готовий `*-book.html` з правильною палітрою |
| **T5** | **Draw Things MCP registration + render callback** (issues #6, #9) | 🟡 P1 | ⏳ Todo | `hermes mcp list` показує `draw-things ✓ enabled`; `wait_for_render(id, 240)` повертає done/error |
| **T6** | **Operations: SSH key + palitra skill + audit→tasks→CHANGELOG→commit** (issues #8, #10) | 🟢 P2 | ⏳ Todo | `git push` працює без ручного вводу пароля; `~/.hermes/skills/comic-book-styles/SKILL.md` існує |

---

### T1 — `revise_scenario`: logging + graceful fallback ✅ DONE

**Реалізовано:**

1. `py/scenario/writer.py`:
   - Новий exception `RevisionFallback(reason, warnings, original_error)`
   - Wrapper `_call_minimax_chat_for_revision()` з structured logging `revision.llm_failed` (error_class, http_status, response_excerpt, traceback)
   - `revise_scenario()` тепер ловить всі LLM/JSON/validation помилки і кидає `RevisionFallback` з reason codes:
     - `llm_timeout`, `llm_rate_limited`, `llm_server_error`, `llm_invalid_json`, `llm_no_panels`, `panel_count_out_of_range`, `llm_validation_failed`
   - Log events: `revision.llm_failed`, `revision.json_invalid`, `revision.validation_failed`

2. `scripts/revise_scenario.py`:
   - Окремий `except RevisionFallback` повертає `{ok: True, fallback: True, id, status, panels_unchanged: True, reason, warnings, feedback_count}` з exit 0
   - Файли сценарію НЕ модифікуються на fallback

3. `web/lib/scenario_store.js`:
   - `revokeApproval`: більше НЕ видаляє `approved_at`/`rendered_at`/`render_revision`/`panel_paths`/`comic_path` — зберігає для можливого fallback
   - Новий метод `restoreApproval(id, {requestId, reason})` — атомарно повертає сценарій з draft у approved/rendered, очищає `revision_status`/`revision_source`, додає `revision_restored` entry в history

4. `web/lib/runtime.js`:
   - `defaultOnRevisionComplete`: при `parsed.fallback === true` викликає `restoreApproval` замість `applyRevision`
   - При error: намагається `restoreApproval`, fallback на legacy `markRevisionFailed` якщо restore неможливий
   - Нові log events: `revision.fallback`, `revision.fallback.restore_failed`, `revision.failed_restored`

5. `web/lib/job_manager.js`:
   - `_runRevision` зберігає `stderr_excerpt` у job error та logger при process failure
   - Job success з `parsed.fallback === true`: result містить `fallback: true, fallback_reason`
   - Log event: `job.revision.fallback` (замість `job.revision.succeeded` для fallback)

**Тести:**
- `tests/test_revise_scenario.py`: 21/21 pass (5 нових: `fallback_on_wrong_panel_count`, `fallback_on_rate_limit`, `fallback_on_server_error`, `fallback_on_validation_error`, `revision_fallback_exception_attributes`)
- `tests/web_scenario_store_restore.test.js`: 5/5 pass (новий файл, Node `--test` runner)
- Pre-existing: `test_lifecycle_revision.py` (8/8), `test_lifecycle_fixtures.py` — без регресій

**Acceptance досягнуто:**
- ✅ `revision_failed` більше не з'являється при валідному фідбеку — fallback повертає panels без зміни status
- ✅ Logs містять `revision.llm_failed` з повним traceback при реальних збоях
- ✅ Operator може продовжити працювати з поточним сценарієм після невдалої revision

---

### T2 — `create_comic` + `expand_panels` panel_count 3..6 ✅ DONE

**Реалізовано:**

1. `py/scenario/writer.py`:
   - `ACCEPTED_PANEL_COUNTS = (3, 4, 5, 6)` + `MIN_PANEL_COUNT` / `MAX_PANEL_COUNT` / `DEFAULT_PANEL_COUNT`
   - `SYSTEM_PROMPT` оновлено: «3-6 панелей включительно (не меньше 3, не больше 6)»
   - `generate_scenario()` валідує `num_panels in ACCEPTED_PANEL_COUNTS` зрозумілим ValueError
   - Нова функція `expand_panels(current_scenario, target_count, scene_hints=None)`:
     - Інкрементально додає по 1 панелі через LLM (з `EXPANSION_SYSTEM_PROMPT` + per-panel user msg)
     - Зберігає оригінальні panels недоторканими
     - Позначає нові panels через `added_via_expansion: True`
     - Валідує кожну відповідь LLM (prompt не порожній, ≤ MAX_PROMPT_CHARS; caption ≤ MAX_CAPTION_WORDS)
     - Truncate long captions (як у revise)
     - Записує `expansion_history` з `from_count`/`to_count`/`added_panels`/`hints_provided`
     - На LLM/JSON помилки кидає `RevisionFallback(reason="expand_*", ...)` з повним traceback
     - Reason codes: `llm_timeout`, `llm_rate_limited`, `llm_server_error`, `expand_invalid_json`, `expand_invalid_structure`, `expand_empty_prompt`, `expand_empty_caption`, `expand_prompt_too_long`

2. `scripts/expand_panels.py` (новий CLI):
   - `--scenario-id`, `--target-count`, `--scene-hint` (repeatable), `--json-result`
   - Окремий `except RevisionFallback` → exit 0 з `{ok: True, fallback: True, panels_unchanged: True, reason, warnings}`
   - Перевіряє що сценарій у `draft` state (інакше повертає `EXPANSION_REQUIRES_DRAFT` error)
   - Записує розширений сценарій атомарно у `data/scenarios/draft/<id>.json`

3. `scripts/ingest_and_draft.py`:
   - `--panels` help text: «3-6» (default 3)
   - Валідація через `writer.generate_scenario(num_panels=...)`

4. `web/lib/validation.js`:
   - `PANEL_COUNTS = Object.freeze([3, 4, 5, 6])` + `MIN_PANEL_COUNT` / `MAX_PANEL_COUNT` / `DEFAULT_PANEL_COUNT`
   - Нова функція `panelCount(value)`: integer 3..6, default 3, кидає `INVALID_PANEL_COUNT` (HTTP 400)

5. `web/routes/scenarios.js`:
   - `POST /api/scenarios` приймає `panel_count` (валідується через `validate.panelCount`), прокидає у `--panels` Python аргумент
   - Response тепер включає `panel_count`
   - Новий `POST /api/scenarios/:id/expand`:
     - Валідує `target_count` (3..6)
     - Pre-check: сценарій існує, state='draft', `target_count > current_count`
     - Spawns `scripts/expand_panels.py --target-count N --scene-hint ...`
     - Returns 201 на success, 200 на `fallback: true`

6. `mcp-server/index.js`:
   - `create_comic.inputSchema`: додано `panel_count: integer 3..6, default 3`
   - Pass-through у body `panel_count`
   - Новий tool `expand_panels(id, target_count, scene_hints)` з input schema

**Тести:**
- `tests/test_panel_expansion.py`: 16/16 pass (новий файл)
  - 4 для `generate_scenario` panel_count валідації (5, 6, 2 reject, 7 reject)
  - 12 для `expand_panels` (rejection paths, hints, history append, fallback paths, truncation)
- `tests/web_panel_count_validation.test.js`: 9/9 pass (новий файл)
- `tests/web_expand_route.test.js`: 9/9 pass (новий файл, mock-based через `errorMiddleware`)
- Pre-existing: `test_revise_scenario.py` (21/21) — оновлено `test_revise_scenario_fallback_on_wrong_panel_count` щоб використовувати 7 panels (бо 5 тепер valid)

**Acceptance досягнуто:**
- ✅ `create_comic(content, panel_count=5)` повертає 5 panels у draft
- ✅ `create_comic(content, panel_count=6)` повертає 6 panels у draft
- ✅ `create_comic(content, panel_count=2)` повертає HTTP 400 `INVALID_PANEL_COUNT`
- ✅ `expand_panels(id, target_count=5)` додає 2 panels до існуючого 3-panel draft (incremental, не переписує)
- ✅ `expand_panels(id, target_count=4)` повертає fallback на LLM error, status залишається `draft`, panels недоторкані

---

### T3 — `render_comic` provider + publish ✅ DONE

**Реалізовано:**

1. `web/lib/validation.js`:
   - `RENDER_PROVIDERS = Object.freeze(['minimax', 'draw-things'])` + `DEFAULT_RENDER_PROVIDER = 'minimax'`
   - Нова функція `renderProvider(value)` — case-insensitive, кидає `INVALID_RENDER_PROVIDER`

2. `web/lib/config.js`:
   - `nodeBin` (для spawn `node scripts/publish_rendered.js`)
   - `publishTimeoutMs` (default 180s, env: `WEB_PUBLISH_TIMEOUT_MS`)
   - `defaultRenderProvider` (env: `WEB_DEFAULT_RENDER_PROVIDER`)

3. `web/lib/job_manager.js`:
   - `enqueueRender({ scenarioId, mode, seed, provider, publish, requestId })` — зберігає provider/publish в job
   - `_runRender`: додає `--provider X` тільки якщо provider !== 'minimax' (default)
   - Auto-publish chain: при `publish=true` після успішного render еnqueueє `enqueuePublish()` (sibling job, не блокує render job)
   - `enqueuePublish({ scenarioId, requestId })` — spawn `node scripts/publish_rendered.js --scenario-id X`
   - `_runPublish`: читає `data/scenarios/published/<id>.json` після publish для `published_url`, поміщає в `job.result.published_url`
   - Новий log event `render.publish.queued` / `render.publish.queue_failed` / `job.publish.succeeded` / `job.publish.failed`
   - Захист: якщо publish enqueue падає — render job все одно вважається успішним (publish — optional enhancement)

4. `web/routes/scenarios.js`:
   - `POST /:id/render` приймає `provider`, `publish` (boolean), defaults: `minimax`, `false`
   - Response включає `provider`, `publish` для клієнта
   - Новий `POST /api/scenarios/:id/publish`:
     - Pre-check: scenario exists, state ∈ {`rendered`, `published`}
     - Enqueues publish job, returns 202
     - Кидає `PUBLISH_REQUIRES_RENDERED` (409) якщо state ∈ {`draft`, `approved`}

5. `mcp-server/index.js`:
   - `render_comic.inputSchema`:
     - `provider: enum ['minimax', 'draw-things'], default 'minimax'`
     - `publish: boolean, default false`
   - Pass-through `provider` та `publish` у body
   - Новий tool `publish_comic(id)` → POST `/api/scenarios/:id/publish`

**Тести:**
- `tests/web_render_provider_validation.test.js`: 6/6 pass (validation function)
- `tests/web_render_publish_job_manager.test.js`: 6/6 pass (enqueueRender provider + publish chain + enqueuePublish)
- `tests/web_render_publish_route.test.js`: 10/10 pass (HTTP routes — provider validation, publish enqueue, state guards)
- Pre-existing: всі T1/T2 тести як і раніше (без регресій)

**Acceptance досягнуто:**
- ✅ `render_comic(id, provider='draw-things')` через MCP рендерить через Draw Things
- ✅ `render_comic(id, provider='draw-things', publish=true)` через MCP виконує render + publish одним викликом
- ✅ `publish_comic(id)` через MCP повертає 202 + job_id (після poll `get_scenario(id)` показує `published_url`)
- ✅ `POST /:id/render` HTTP body `{provider: 'minimax', publish: true}` повертає 202 з `provider` + `publish` в response
- ✅ `POST /:id/publish` повертає 409 якщо scenario в draft/approved state

---

### T4 — `create_book_html` + `book.html.j2` + `book.css` consolidation ✅ DONE

**Реалізовано:**

1. `py/render/book/__init__.py` — public API: `render_book_html()`, `RenderBookError`

2. `py/render/book/palettes.py` — `STYLE_PALETTES` dict з 7 палітрами:
   - sentry, ramstein, hornsdale, partition, puppet, ai-paradox, stalker
   - Canonical CSS variable schema: `--primary`, `--primary-light/-dark`, `--accent`, `--accent-light/-dark`, `--paper`, `--paper-dark/-light`, `--ink`, `--ink-light`, `--shadow`, `--ui`
   - `to_css_vars(palette)` рендерить palette як `:root { ... }` блок
   - `get_palette(style)` валідує та повертає palette

3. `py/render/book/glossaries.py` — `STYLE_GLOSSARIES` dict з дефолтними глосаріями для кожного стилю (4 entries для sentry/ai-paradox/hornsdale, по 3 для інших). `get_default_glossary(style)` повертає список `(term, definition)` tuples.

4. `py/render/book/static/book.css` — Єдиний generic CSS (~400 рядків) з `{{palette_vars}}` placeholder. Використовує `color-mix(in srgb, var(--primary) 30%, transparent)` для backwards-compat з широкою підтримкою браузерів (CSS Color Module Level 5).

5. `py/render/book/templates/book.html.j2` — Єдиний Jinja-шаблон з блоками:
   - cover (tagline, title, subtitle, meta_lines, epigraph)
   - glossary (якщо `glossary` непорожній)
   - nav (з roman numerals)
   - narrative (розбитий на параграфи)
   - pages (panel renders з image URL)
   - epilogue
   - footer (scenario ID, provider, palette name)
   - modal/lightbox JS (vanilla, keyboard nav)

6. `py/render/book/renderer.py` — `render_book_html()`:
   - Валідує style (7 enum), завантажує scenario з `published/` або `rendered/`
   - Будує panel descriptors (image URL → `/comics/<id>/panel_N.png`, page_title з caption, alt_text з prompt)
   - Glossary: custom override → style default → empty
   - Epigraph: custom → context[:800]+"…"
   - Narrative paragraphs: split by `\n\n` або sentence boundaries
   - Atomic write через `tmp + os.replace` (no `.tmp` left over)
   - Autoescape увімкнено (`select_autoescape(default=True, default_for_string=True)`) — CLAUDE.md rule #9

7. `scripts/render_book.py` — CLI wrapper:
   - `--scenario-id`, `--style`, `--output-dir`
   - `--title`, `--subtitle`, `--tagline`, `--epigraph`, `--narrative`, `--epilogue`, `--epilogue-author`
   - `--glossary "TERM::DEFINITION"` (repeatable)
   - `--provider`, `--json-result`
   - Returns 0 на success, 1 на помилку з `{ok, error, code}`

8. `web/routes/scenarios.js` — новий `POST /api/scenarios/:id/book`:
   - Валідує style enum (7 значень)
   - Pre-check: scenario ∈ {rendered, published} (409 `BOOK_REQUIRES_RENDERED` інакше)
   - Spawns `scripts/render_book.py --scenario-id X --style Y --json-result`
   - Returns 201 з `{path, size_bytes, size_kb, style}`

9. `mcp-server/index.js` — новий tool `create_book_html(scenario_id, style, title?, subtitle?, provider?)` з input schema. Pass-through у body.

**Тести:**
- `tests/test_book_renderer.py`: 21/21 pass (новий файл):
  - 4 для `palettes.py` (7 стилів, required vars, to_css_vars, get_palette)
  - 2 для `glossaries.py` (defaults, tuple schema)
  - 13 для `render_book_html()` (file creation, autoescape, кожна палітра, помилки, custom glossary/title/epigraph, narrative, roman numerals, atomic write, provider, public API)
  - 1 для public API re-export
- `tests/web_book_route.test.js`: 8/8 pass (новий файл, з `errorMiddleware`)
- Pre-existing: всі T1/T2/T3 тести як раніше (без регресій)

**Acceptance досягнуто:**
- ✅ `python scripts/render_book.py --scenario-id 19fbc803 --style sentry` генерує `data/comics/19fbc803-book.html` (26.5 KB, 694 рядки)
- ✅ `python scripts/render_book.py --scenario-id 19fbc803 --style {sentry,ramstein,hornsdale,partition,puppet,ai-paradox,stalker}` — всі 7 палітр працюють
- ✅ `create_book_html(scenario_id, "sentry")` через MCP повертає `{path, size_kb: 26.5}`
- ✅ `POST /api/scenarios/:id/book` HTTP повертає 201 з `{path, size_bytes, size_kb, style}`
- ✅ `POST /api/scenarios/:id/book` з `style: "no-such-style"` → 400 `INVALID_BOOK_STYLE`
- ✅ `POST /api/scenarios/:id/book` для draft state → 409 `BOOK_REQUIRES_RENDERED`
- ✅ Autoescape увімкнено — raw HTML escape у script/style границях
- ✅ Atomic write — no `.tmp` files залишаються після рендеру

---

## T1 — `revise_scenario`: logging + graceful fallback

**Issue:** #1 (audit)

**Файли:**
- `py/scenario/writer.py` — `revise_scenario()` (рядки ~280–360)
- `web/lib/lifecycle.js` — `revise()` handler
- `web/routes/scenarios.js:172` — `POST /:id/revise`
- `web/lib/logger.js` — додати `revision.error` event з structured полями

**Кроки:**
1. Обгорнути `_call_minimax_chat(REVISION_SYSTEM_PROMPT, user_msg)` у `try/except` з логуванням:
   - logger.error з полями `{ event: "revision.llm_failed", scenario_id, request_id, stderr, traceback, feedback_preview }`
2. У `revise_scenario()` після `json.loads()`: якщо `len(payload["panels"]) not in ACCEPTED_PANEL_COUNTS`:
   - замість `raise ValueError(...)` → повернути `{ panels: current_scenario["panels"], fallback: true, reason: "panel_count_out_of_range", expected: ACCEPTED_PANEL_COUNTS }`
   - lifecycle.mark fallback у `revision_history`
3. У `web/lib/lifecycle.js` `revise()`: якщо worker повернув `fallback: true`:
   - status залишається `approved`/`rendered` (НЕ переводити у `draft`)
   - response: `{ ok: true, fallback: true, panels_unchanged: true, warnings: [...] }`
4. Додати unit-test: `tests/test_revise_fallback.py` — мокаємо LLM, що повертає JSON з 2 панелями, очікуємо 200 + `fallback: true`

**Acceptance:**
- `revision_failed` більше не з'являється у `data/logs/` при валідному фідбеку
- Operator може продовжити працювати з поточним сценарієм після невдалої revision
- Logs містять `revision_error` з повним traceback

---

## T2 — `create_comic`: panel_count 3..6 + `expand_panels`

**Issue:** #2 (audit)

**Файли:**
- `py/scenario/writer.py:111` — розширити `ACCEPTED_PANEL_COUNTS = (3, 4, 5, 6)`
- `py/scenario/writer.py:147` — `num_panels` вже існує, нічого не міняємо
- `web/routes/scenarios.js` — POST `/api/scenarios` приймає `panel_count`
- `mcp-server/index.js:59` — `create_comic.inputSchema` додати `panel_count: integer 3..6`
- `mcp-server/index.js` — новий tool `expand_panels`
- `py/scenario/writer.py` — `expand_panels(scenario, target_count, scenes)` (iterative, по 1 панелі через LLM, з контекстом попередніх)

**Кроки:**
1. `ACCEPTED_PANEL_COUNTS = (3, 4, 5, 6)` — одна строка
2. `POST /api/scenarios` — `panel_count` валідація (3..6), default 3
3. MCP `create_comic` — input додати `panel_count`, прокинути у body
4. MCP `expand_panels(id, target_count, scenes)`:
   - читає `data/scenarios/draft/<id>.json`
   - для кожної нової панелі викликає LLM з `{ existing_panels, new_panel_n, scenes }`
   - зберігає атомарно через `lifecycle.store.update()`
5. Unit-test: `panel_count=5` повертає 5 panels; `expand_panels(id, 6)` додає 1 панель

**Acceptance:**
- `create_comic(content, panel_count=5, ...)` → 5 panels у draft
- `expand_panels(id, 6)` → 6 panels у тому ж draft, status залишається `draft`
- Тести з `panel_count=4, 5, 6` проходять

---

## T3 — `render_comic`: provider + publish

**Issues:** #3, #4 (audit)

**Файли:**
- `mcp-server/index.js:110` — `render_comic.inputSchema` додати `provider` + `publish`
- `web/routes/scenarios.js:88` — `POST /:id/render` приймає `req.body.provider` і `req.body.publish`
- `web/lib/job_manager.js` — `enqueueRender({ provider })` прокидає у command
- `scripts/render_approved.py:61` — вже має `--provider`, тільки binding
- `web/routes/scenarios.js` — новий `POST /api/scenarios/:id/publish`
- `mcp-server/index.js` — новий tool `publish_comic(id)` (опційно; `publish: true` у render — основний шлях)

**Кроки:**
1. `render_comic.inputSchema`:
   ```json
   provider: { type: "string", enum: ["minimax", "draw-things"], default: "minimax" }
   publish: { type: "boolean", default: false }
   ```
2. `POST /:id/render` body: `{ mode, provider, publish, seed }`
3. `job_manager.enqueueRender`: spawn `scripts/render_approved.py --provider X`, чекати completion
4. Якщо `publish: true` і status `rendered` → після job enqueue `POST /:id/publish` job (spawn `node scripts/publish_rendered.js`)
5. `POST /:id/publish` новий route → `runner.run(config.nodeBin, ['scripts/publish_rendered.js', '--scenario-id', id], { timeoutMs: 120000 })`
6. Response: `{ published_url: "https://comic.openaiua.fr/comics/<id>.html" }` (або `localhost:3000/comics/<id>.html` якщо `WEB_PUBLIC_URL` не встановлено)

**Acceptance:**
- `render_comic(id, provider="draw-things", publish=true)` повертає `published_url`
- `render_comic(id, provider="minimax")` працює як раніше (backward compat)
- `publish_comic(id)` окремий tool теж працює

---

## T4 — `create_book_html` + book.css + book.html.j2

**Issues:** #5, #7 (audit)

**Файли (створити):**
- `py/render/book/__init__.py`
- `py/render/book/templates/book.html.j2` — єдиний Jinja-шаблон
- `py/render/book/static/book.css` — єдиний CSS (~500 рядків)
- `py/render/book/palettes.py` — dict `STYLE_PALETTES = { "sentry": {...}, "ramstein": {...}, ... }`
- `py/render/book/glossaries.py` — dict `STYLE_GLOSSARIES = { "sentry": [...], ... }`
- `py/render/book/renderer.py` — `render_book_html(scenario_id, style) -> Path`

**Файли (редагувати):**
- `mcp-server/index.js` — новий tool `create_book_html(scenario_id, style)`
- `web/routes/comics.js` або новий `web/routes/books.js` — `POST /api/scenarios/:id/book`
- `py/render/html_renderer/` — НЕ чіпаємо (legacy pipeline)

**Палітри (з аудиту 036 + вже існуючих book.html):**

```python
STYLE_PALETTES = {
  "sentry":     {"primary": "#003366", "accent": "#D4AF37", "name_ru": "E-3F Sentry / NATO"},
  "ramstein":   {"primary": "#0057B7", "accent": "#FFD700", "name_ru": "Ramstein AB"},
  "hornsdale":  {"primary": "#E31937", "accent": "#00A4A6", "name_ru": "Hornsdale / Tesla"},
  "partition":  {"primary": "#8B0000", "accent": "#B8860B", "name_ru": "Partition / Parchment"},
  "puppet":     {"primary": "#6B1F2E", "accent": "#C9A14B", "name_ru": "Puppet / Strings"},
  "ai-paradox": {"primary": "#6B2D8C", "accent": "#00E5FF", "name_ru": "AI Paradox / Cyber"},
  "stalker":    {"primary": "#3D2817", "accent": "#C9A14B", "name_ru": "S.T.A.L.K.E.R. / Zone"},
}
```

**Кроки:**
1. Витягти CSS з `data/comics/sentry-book.html` як baseline (~500 рядків)
2. Замінити всі hex-літерали на `var(--primary)`, `var(--accent)` тощо
3. Jinja-шаблон приймає: `scenario`, `panels`, `palette`, `glossary`, `sources`, `epilogue`
4. `render_book_html(id, style)`:
   - читає `data/scenarios/published/<id>.json`
   - читає `data/comics/<id>/*.png` (або `data/comics/<id>/panel_*.png`)
   - генерує HTML → `data/comics/<id>-book.html`
5. MCP `create_book_html(scenario_id, style)`:
   - input: `scenario_id: string, style: enum[sentry,ramstein,hornsdale,partition,puppet,ai-paradox,stalker]`
   - викликає Python через `runner.run(config.pythonBin, ['-m', 'py.render.book.renderer', '--scenario-id', id, '--style', style])`
   - повертає `{ path: "data/comics/<id>-book.html", size_kb: ... }`

**Acceptance:**
- `create_book_html("19fbc803", "sentry")` повертає валідний HTML ~30 KB (замість ~30 KB raw)
- Візуально ідентичний до існуючого `19fbc803-book.html`
- Всі 7 палітр доступні
- Autoescape увімкнено (CLAUDE.md rule #9)

---

## T5 — Draw Things MCP registration + render callback

**Issues:** #6, #9 (audit)

**Файли:**
- `~/.hermes/config.yaml` — додати секцію `mcp_servers.draw-things`
- `mcp-server/draw-things/index.js` — вже існує (audit 036)
- `mcp-server/index.js` — новий tool `wait_for_render(id, timeout_seconds)`
- `web/routes/jobs.js` — GET endpoint для polling (або reuse `jobManager.jobStore.findByScenario`)

**Кроки:**
1. **Draw Things registration** (10 хв):
   ```yaml
   mcp_servers:
     draw-things:
       command: node
       args: [/home/ubuntu/projects/comics/mcp-server/draw-things/index.js]
       env:
         DRAW_THINGS_URL: http://192.168.50.250:7860
         DRAW_THINGS_TIMEOUT: 180
   ```
   `hermes gateway restart && hermes mcp list` → перевірити `draw-things ✓ enabled`
2. **`wait_for_render(id, timeout_seconds)` MCP tool**:
   - поллить `GET /api/jobs?scenario_id=<id>` кожні 3 секунди
   - exit коли `status: done` або `failed`, або timeout
   - повертає `{ status, duration_seconds, panel_paths }` або `{ timeout: true, last_status: "running" }`

**Acceptance:**
- `wait_for_render("drawtest3acd", 300)` повертає done через ~5 хв (або timeout 300s)
- Draw Things доступний через `mcp-server/draw-things/index.js` без `urllib.request`

---

## T6 — Operations: SSH key + palitra skill + фінальна фіксація

**Issues:** #8, #10 (audit)

**Файли:**
- `~/.ssh/config` — додати `Host github.com` блок
- `~/.ssh/comic-studio-ed25519` — згенерувати або скопіювати з backup
- `gh auth login` — fallback якщо SSH неможливий
- `~/.hermes/skills/comic-book-styles/SKILL.md` — створити palitra cheat-sheet
- `CHANGELOG.md` — додати підсумковий запис з timestamp
- `openspec/changes/` — синхронізувати delta specs (якщо створювались) + archive active change
- `git add . && git commit -m "..." && git push` — без ручного вводу

**Палітра skill структура:**
```markdown
# Comic Book Styles — Knowledge

## sentry (E-3F Sentry / NATO)
- palette: nato #003366 + gold #D4AF37
- mood: розвідка, blue-water, sky #6FA8DC
- cover motif: AWACS silhouette, radar circle
- glossary: NATO, AWACS, E-3 Sentry, AWACS crew

## ramstein (Ramstein AB)
- palette: blue #0057B7 + yellow #FFD700
- mood: авіабаза, steel #2C3E50
- ...
```

**Кроки:**
1. SSH: `ssh-keygen -t ed25519 -f ~/.ssh/comic-studio-ed25519 -N ""` + додати публічний ключ у github.com → Settings → SSH keys
2. `~/.ssh/config`:
   ```
   Host github.com
     IdentityFile ~/.ssh/comic-studio-ed25519
     IdentitiesOnly yes
   ```
3. `ssh -T git@github.com` → перевірити `Hi <user>! You've successfully authenticated`
4. Створити `~/.hermes/skills/comic-book-styles/SKILL.md` з 7 палітр
5. `CHANGELOG.md` — додати запис:
   ```
   ## 2026-XX-XX
   - `<ISO timestamp>` — MCP gap audit + 6 task blocks. Виправлено: revise_scenario fallback (T1), panel_count 3..6 + expand_panels (T2), render_comic provider + publish (T3), create_book_html + book.css consolidation (T4), Draw Things MCP registration + wait_for_render (T5), SSH key + palitra skill (T6). Аудит: `summary/audit/037_mcp-gaps-and-friction.md`.
   ```
6. OpenSpec: якщо є active change — archive через `openspec-archive-change` skill
7. `git add . && git commit -m "fix: MCP gaps — revise fallback, panel_count, render provider+publish, book_html, draw-things MCP, ops" && git push`

**Acceptance:**
- `git push origin <branch>` проходить без password prompt
- `~/.hermes/skills/comic-book-styles/SKILL.md` доступний з будь-якої сесії
- CHANGELOG.md містить запис про audit 037
- OpenSpec archived (якщо був active)

---

## Артефакти (після виконання)

- `py/scenario/writer.py` — розширений `ACCEPTED_PANEL_COUNTS` + graceful fallback у `revise_scenario`
- `py/render/book/` — новий модуль з Jinja + CSS + palettes + glossaries
- `web/routes/scenarios.js` — `panel_count`, `provider`, `publish` параметри + новий `/publish` route
- `mcp-server/index.js` — розширені `create_comic`, `render_comic`, нові `expand_panels`, `publish_comic`, `create_book_html`, `wait_for_render`
- `~/.hermes/config.yaml` — `draw-things` секція
- `~/.ssh/config` — github IdentityFile
- `~/.hermes/skills/comic-book-styles/SKILL.md` — palitra cheat-sheet
- `data/logs/YYYY-MM-DD.log` — `revision.error` події з traceback (тільки при реальних збоях)
- Тести: `tests/test_revise_fallback.py`, `tests/test_panel_count.py`, `tests/test_book_renderer.py`

## Ризики

- **T3 publish flow**: `publisher/site.js` може вимагати SSH/SCP доступ до production. Якщо нема — fallback на локальний `data/comics/` + warning "manual deploy needed"
- **T4 book.css**: існуючі 24 `*-book.html` можуть мати незначні CSS-відмінності (custom shadows, gradients). Міграція не в scope — лишаємо як legacy, новий pipeline генерує тільки новий формат
- **T5 wait_for_render**: polling кожні 3 сек може створити noise у logs; використовувати `INFO` рівень з throttle
- **T6 SSH**: якщо сервер не має доступу до github.com (firewall), fallback на `gh auth login` + HTTPS
