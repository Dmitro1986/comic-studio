# Аудит: MCP gaps and operator friction

## Контекст

За останні ~10 сесій експлуатації Comic Studio через MCP (`mcp-server/index.js`, 333 рядки, 11 tools) накопичились системні прогалини, які перетворюють MCP-workflow з автоматизації на ручну працю. Усі перераховані проблеми відтворюються стабільно та збільшують time-to-publish у 2–5 разів.

## Поточний стан MCP-сервера

Файл: `mcp-server/index.js`. Наявні tools (11):

- `list_scenarios` — список за status
- `get_scenario` — повний JSON сценарію
- `create_comic` — створює draft (POST `/api/scenarios`, **без `panel_count`**)
- `approve_scenario` — POST `/api/scenarios/:id/approve`
- `render_comic` — POST `/api/scenarios/:id/render`, mode=initial|rerender (**без `provider`**)
- `revise_scenario` — POST `/api/scenarios/:id/revise` (ламається, див. нижче)
- `restyle_comic` — POST `/api/scenarios/:id/restyle`
- `resolve_intent` — AiPULT fuzzy search
- `read_comic_image` — base64 повернення PNG (composite / panel_N)
- `update_comic_text` — швидкий рестейл без ре-рендеру
- `export_comic_pdf` / `export_comic_zip` — лінки на `/export/pdf|zip`

`mcp-server/draw-things/` існує, але **не зареєстрований** в жодному config (`~/.hermes/config.yaml`, `claude_desktop_config.json`). Operator працював через `urllib.request` напряму до `http://192.168.50.250:7860`.

## Знайдені проблеми (10 шт., пріоритизовані)

### 🔴 Must-add (5) — зараз ламають workflow

#### 1. `revise_scenario` падає без діагностики
**Симптом:** два послідовні виклики повернули `revision_failed: PROCESS_FAILED` та початкові 3 панелі. Англійський фідбек, простий текст. Operator обійшов шляхом ручного редагування `data/scenarios/draft/<id>.json`.

**Корінь:**
- `py/scenario/writer.py:111` — `ACCEPTED_PANEL_COUNTS = (3, 4)` (але це не причина падіння)
- `py/scenario/writer.py:253-254` — `revise_scenario` raises якщо `len(payload["panels"]) not in (3, 4)` → PROCESS_FAILED
- `web/routes/scenarios.js:172` — `lifecycle.revise()` запускає job без structured logging stderr
- Жодних log-записів типу `revision_error`, `revision.stderror`, `revision.traceback` у `data/logs/`

**Fix:**
1. Логувати у `revision_error` повний stderr + traceback LLM-виклику (`_call_minimax_chat`)
2. Graceful fallback: якщо LLM повернув невалідний JSON або panel count поза межами — зберегти поточні panels без зміни `status`, повернути `{ ok: true, fallback: true, panels: <current>, warnings: [...] }`
3. Operator не повинен втрачати сценарій через таймаут/rate limit/OOM

#### 2. `create_comic` завжди дає 3 панелі
**Симптом:** Operator мусить після кожного `create_comic` відкривати JSON і вручну дописувати panels 4–N. Це найбільше джерело тертя.

**Корінь:**
- `py/scenario/writer.py:147` — `generate_scenario(num_panels: int = 3)` але `web/routes/scenarios.js` не приймає `panel_count` і передає default
- `ACCEPTED_PANEL_COUNTS = (3, 4)` — навіть якщо передати 5, валідація відкине

**Fix:**
1. Новий параметр `--panel-count N` у `create_comic` MCP tool + прокинути у `POST /api/scenarios`
2. Розширити `ACCEPTED_PANEL_COUNTS` до `(3, 4, 5, 6)` (або прибрати constraint для revision, залишити тільки для initial)
3. Додати `expand_panels(id, count, scenes)` окремою командою для інкрементального розширення існуючого draft

#### 3. `render_comic` не приймає `provider`
**Симптом:** MCP рендерить тільки через MiniMax. Для Draw Things доводиться викликати `scripts/render_approved.py --provider draw-things` вручну (поза MCP).

**Корінь:**
- `web/routes/scenarios.js:88-103` — `POST /api/scenarios/:id/render` ігнорує `req.body.provider`
- `scripts/render_approved.py:61` має `provider: str = "minimax"` параметр, але web-шар не прокидає

**Fix:**
1. Додати `provider: "minimax" | "draw-things"` у inputSchema `render_comic`
2. Прокинути у `req.body.provider` через `jobManager.enqueueRender({ provider })`
3. `scripts/render_approved.py` вже підтримує — тільки binding

#### 4. Немає MCP-шляху для publication
**Симптом:** Operator має `export_comic_pdf`/`export_comic_zip`, але немає `publish_site`. Щоб закомітити HTML на `comic.openaiua.fr/comics/<slug>.html`, треба вручну запускати `node scripts/publish_rendered.js`.

**Корінь:**
- `publisher/site.js` і `scripts/publish_rendered.js` не мають HTTP-ендпоінту
- `web/routes/` не має `/api/scenarios/:id/publish`

**Fix:**
1. Новий параметр `publish: true` у `render_comic` (рендер → автопублікація)
2. Або окрема команда `publish_comic(id)` → POST `/api/scenarios/:id/publish` → spawns `publish_rendered.js`
3. Повертати `{ published_url: "https://comic.openaiua.fr/comics/<id>.html" }`

#### 5. Немає MCP-команди для knowledge book HTML
**Симптом:** Operator пише `data/comics/<id>-book.html` (37 рядків шаблону, ~500 рядків CSS) вручну щоразу. 7 стилів (Tesla/Sentry/Ramstein/Partition/Hornsdale/Puppet/AI-Paradox) мають ідентичну структуру (cover → glossary → nav → pages → sources → epilogue → footer → modal), але CSS дублюється.

**Корінь:**
- `py/render/html_renderer/` має тільки звичайний HTML (без book-розширення)
- Knowledge book — окремий ручний процес, не інтегрований у pipeline

**Fix:**
1. `create_book_html(scenario_id, style)` MCP tool:
   - читає `data/comics/<id>/` (panels) + `data/scenarios/published/<id>.json`
   - генерує копію відповідного шаблону
   - накладає палітру (palette key per style) + глосарій (Glossary dict per style)
   - публікує на `data/comics/<id>-book.html`

### 🟡 Worth-adding (4) — автоматизують поточну рутину

#### 6. Draw Things MCP не зареєстрований
- `mcp-server/draw-things/index.js` (305 рядків) існує з Phase 1 (audit 036)
- Але в `~/.hermes/config.yaml` немає `mcp_servers.draw-things`
- 10 хв роботи: додати секцію, env `DRAW_THINGS_URL=http://192.168.50.250:7860`, restart gateway

#### 7. Knowledge book template не стандартизований
- 24 файли `*-book.html` зараз (24 з 69 HTML)
- Кожен має власний `:root { --pallette... }` блок + повний CSS (~500 рядків)
- Потрібен `py/render/book/static/book.css` (один файл) + `book.html.j2` Jinja-шаблон з `style_palette` параметром
- Дасть: -90% розміру book.html, єдине джерело правди для палітр

#### 8. SSH-ключ для GitHub не налаштований
- `FIXATION.md` вимагає `git commit && git push` при фіксуванні
- `git push` постійно падає без ключа/PAT
- Потрібен `~/.ssh/config` з `Host github.com IdentityFile ~/.ssh/comic-studio-ed25519` (або PAT через `gh auth login`)

#### 9. Render notification через callback
- `render_comic` повертає `request_id` і `status: queued`
- Operator робить `sleep 240 && ls panel_*.png` щоб перевірити готовність
- Кумедно і марнує час
- Потрібен `wait_for_render(id, timeout)` MCP tool, який поллить `jobStore.activeForScenario(id)` до `status: done` або таймаут
- Або callback URL `notify_url: "..."` у `render_comic`

### 🟢 Less-urgent (1) — операційне знання

#### 10. Журнал палітр/стилів не збережений
- 5+ knowledge books зроблено вручну → Operator запам'ятав патерни: `partition` = пергамент, `sentry` = NATO blue, `ramstein` = синьо-жовтий, `hornsdale` = Tesla (E31937), `puppet` = бордо+золото, `ai-paradox` = violet+cyber
- Шпаргалка існує тільки в context кожної сесії, зникає при перезапуску
- Рішення: `~/.hermes/skills/comic-book-styles/SKILL.md` з key-value палітрами + прикладами cover-зображень
- Вирішується автоматично при #7 (book.css стає канонічним джерелом палітр)

## Зв'язки між проблемами

```
[5 knowledge book]    ─┐
[7 template]          ─┴─→ один і той самий фікс (book.css + book.html.j2)
[10 palitra journal]  ─┘

[2 panel_count]       ─┐
[1 revise fallback]   ─┴─→ обидва стосуються writer.py + scenarios.js

[3 provider]          ─┐
[4 publish]           ─┴─→ обидва розширюють render_comic / routes/scenarios.js

[6 draw-things MCP]   ──→ окремий, але блокує [3]
[8 ssh key]           ──→ оркестрація, не код
[9 render callback]   ──→ окремий tool
```

## Що НЕ чіпаємо в цьому аудиті

- Не змінюємо provider-нейтральність `py/scenario/writer.py` (тільки розширюємо panel counts)
- Не чіпаємо `publisher/site.js` (тільки додаємо HTTP-обгортку)
- Не мігруємо існуючі 24 `*-book.html` (залишаємо як legacy, новий pipeline генерує тільки новий)
- Не змінюємо Telegram caption / web UI (тільки MCP surface)

## Метрика успіху

- Час від `create_comic` до опублікованого `*-book.html` з 6+ панелями через Draw Things + custom palette ≤ 15 хв (зараз ~50 хв)
- 0 випадків втрати сценарію через `revision_failed`
- Operator не відкриває `data/scenarios/*.json` руками після цього аудиту
