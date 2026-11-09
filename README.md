# Comic Studio

Конвейер производства коротких комиксов:

```text
контекст → draft → ручное approval → render job → rendered → publication
```

Сценарии хранятся как JSON на диске. Утверждение доступно через авторизованный Telegram-бот или локальный/авторизованный Web UI. `published` records считаются неизменяемыми.

## Основные компоненты

| Компонент | Назначение |
|---|---|
| `py/ingest/` | URL, YouTube и freeform ingest |
| `py/scenario/` | MiniMax LLM-сценарий и image style prompts |
| `py/render/` | MiniMax image-01 и Pillow assembly |
| `py/lib/` | Config, lifecycle, logging и частичный Notion mirror |
| `web/` | Hardened Express API, jobs, lifecycle и static UI |
| `ui/` | Vanilla dashboard |
| `tg-bot/` | Telegram approval и управление |
| `publisher/` | Site adapter; social adapters пока placeholders |
| `cron/` | Nightly orchestration |

## Быстрый старт

```bash
cd ~/Projects/comic-studio

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r py/requirements.txt

# Node
cd web && npm install && cd ..
cd tg-bot && npm install && cd ..

# Конфигурация
cp .env.example .env
# Минимум для генерации: MINIMAX_API_KEY
```

### Создать draft

```bash
python scripts/ingest_and_draft.py --freeform "Идея комикса"
python scripts/ingest_and_draft.py --url "https://example.com/article"
python scripts/ingest_and_draft.py --youtube "https://youtu.be/..."
```

Полезные параметры:

```text
--image-style cartoon|anime|comic|realistic|watercolor
--style bubble|star|gothic|boom|memo|bar
--panels 3|4
--seed N
```

### Запустить Web UI

```bash
node web/server.js
# http://127.0.0.1:3000/ui/
```

По умолчанию server слушает только `127.0.0.1` и принимает same-origin API requests. Для remote mode одновременно обязательны `WEB_API_TOKEN` и `WEB_ALLOWED_ORIGINS`; подробности — в [`docs/api.md`](docs/api.md).

### Утвердить

Draft можно утвердить вручную:

- в Telegram из разрешённого `TELEGRAM_CHAT_ID`;
- в локальном или bearer-authenticated Web UI.

Наличие persisted approval обязательно перед initial render.

### Render

```bash
python scripts/render_approved.py --scenario-id abc12345
python scripts/render_approved.py --all
```

Web API запускает render как durable job. Для `rendered` поддерживается только явный staging rerender. `published` через Web API не изменяется и не рендерится повторно.

После успешной сборки генерируются **два артефакта** (variant B):
- `data/comics/<id>.png` — PNG-preview (Pillow overlay с баблами, для backward-compat с Telegram/Notion/archive/social).
- `data/comics/<id>.html` — HTML-страница с inline-CSS и woff2 шрифтами (primary artifact, для браузера и расшаривания).
- `data/comics/<id>/layout.json` — манифест для HTML-рендера.
- `data/comics/<id>/fonts/*.woff2` — локальные шрифты для автономности HTML.

Открыть HTML в браузере:

```bash
open data/comics/abc12345.html    # macOS
xdg-open data/comics/abc12345.html # Linux
```

Или через Web API: `GET http://127.0.0.1:3000/comics/abc12345.html`.

Telegram caption для rendered/published сценариев получает ссылку на HTML и inline-кнопку, если задан env `WEB_PUBLIC_URL=https://studio.example.com`.

### Безопасный cron test

```bash
bash cron/nightly.sh --dry-run
```

Команда без `--dry-run` выполняет реальные side effects.

## Revision и remix

- Кнопка **🔄 Revision** на карточке `approved`/`rendered` сценария вызывает
  `POST /api/scenarios/:id/revise`. Server атомарно отзывает approval,
  при необходимости перемещает rendered artifacts в
  `data/.staging/legacy/<id>-<ts>/` и запускает LLM-регенерацию. После
  успешной регенерации scenario остаётся в `draft` со статусом
  `revision_succeeded` и требует повторного approval.
- Кнопка **🎨 Remix** на карточке `published` сценария вызывает
  `POST /api/scenarios/:id/remix` и создаёт новый draft с
  `remix_of: <source_id>`. Source `published` record остаётся неизменным.
- Legacy `POST /api/scenarios/:id/feedback` возвращает `409 REVISION_REQUIRED`
  для не-published и `409 PUBLISHED_IMMUTABLE` для published; feedback не
  сохраняется. Используйте `/revise` или `/remix` для реальной правки.

## Публикация

```bash
node scripts/publish_rendered.js
```

Текущее состояние интеграций:

- custom site adapter требует `SITE_API_URL`;
- Twitter/X и Mastodon являются placeholders;
- Notion scenario mirror частичный;
- Notion comic mirror не реализован.

Не следует считать эти optional integrations завершёнными без deployment-specific проверки.

## Данные

```text
data/
├── scenarios/
│   ├── draft/
│   ├── approved/
│   ├── rejected/
│   ├── rendered/
│   └── published/
├── comics/
│   ├── <id>.png
│   ├── <id>/panel_*.png
│   └── raw/<id>.png
├── jobs/                 # Web render jobs
├── .staging/             # candidate rerenders
├── .trash/               # recoverable deletes
├── freeform/
├── logs/YYYY-MM-DD.log
└── archive/YYYY-MM-DD/   # existing content immutable
```

## Проверки

```bash
cd web && npm test && cd ..
python -m unittest tests.test_render_approved -v
python -m compileall -q py scripts tests
bash -n cron/nightly.sh
bash cron/nightly.sh --dry-run
```

Web tests используют temporary data roots и mocked subprocesses — live API credentials не нужны.

## Hermes Agent Integration

Comic Studio може бути підключений як MCP-сервер до [Hermes Agent](https://hermes-agent.nousresearch.com) — тоді `mcp__comic_server__*` інструменти доступні прямо з чату.

### 1. Запустити Comic Studio

```bash
cd ~/Projects/comic-studio  # або /home/ubuntu/projects/comics
node web/server.js
# Слухає на http://localhost:3000
```

### 2. Додати MCP у `~/.hermes/config.yaml`

```yaml
mcp_servers:
  comic-server:
    command: node
    args:
      - /home/ubuntu/projects/comics/mcp-server/index.js
    env:
      API_BASE_URL: http://127.0.0.1:3000

  draw-things:
    command: node
    args:
      - /home/ubuntu/projects/comics/mcp-server/draw-things/index.js
    env:
      DRAW_THINGS_URL: http://192.168.50.250:7860
      DRAW_THINGS_TIMEOUT: '300'
```

### 3. Встановити скіли

Скіли лежать в окремих директоріях. Скопіюйте їх у `~/.hermes/skills/`:

```bash
# Якщо у вас є hermes-agent source tree
cp -r hermes-agent/skills/comic-book-pipeline ~/.hermes/skills/
cp -r hermes-agent/skills/comic-book-styles ~/.hermes/skills/

# Або створіть вручну — структура:
#   ~/.hermes/skills/comic-book-pipeline/SKILL.md
#   ~/.hermes/skills/comic-book-styles/SKILL.md
```

Або через вбудовані hermes-agent скіли:

```bash
hermes skills install official/creative/comic-book-pipeline
hermes skills install official/creative/comic-book-styles
```

### 4. Перезапустити Hermes

Після перезапуску будуть доступні:
- MCP інструменти: `mcp__comic_server__create_comic`, `mcp__comic_server__approve_scenario`, `mcp__comic_server__render_comic`, `mcp__comic_server__create_book_html`, `mcp__comic_server__publish_comic`, `mcp__comic_server__wait_for_render`, `mcp__comic_server__list_scenarios`, `mcp__comic_server__get_scenario`, `mcp__comic_server__update_comic_text`, `mcp__comic_server__restyle_comic`, `mcp__comic_server__export_comic_zip`, `mcp__comic_server__export_comic_pdf`, `mcp__comic_server__revise_scenario`, `mcp__comic_server__expand_panels`, `mcp__comic_server__read_comic_image`, `mcp__comic_server__resolve_intent`
- Draw Things MCP: `mcp__draw_things__generate_image`, `mcp__draw_things__get_options`
- Скіли: `comic-book-pipeline` (end-to-end workflow), `comic-book-styles` (палітри + стилі)

### Канонічний CLI для knowledge book

Замість написання `/tmp/render_<topic>.py` щоразу:

```bash
python scripts/render_book_clean.py \
  --scenario-id <id> \
  --style kremlin-satire \
  --title "..." \
  --subtitle "..." \
  --tagline "..." \
  --epigraph "..." \
  --narrative "..." \
  --epilogue "..." \
  --epilogue-author "..." \
  --glossary "Термін 1::Визначення 1" \
  --glossary "Термін 2::Визначення 2" \
  --lang uk \
  --source-url "https://..." \
  --provider minimax
```

Див. `comic-book-pipeline` скіл для повного опису.

## Документація

- [`ALGORITM.md`](ALGORITM.md) — фактичний pipeline і lifecycle
- [`docs/architecture.md`](docs/architecture.md) — архітектура
- [`docs/workflow.md`](docs/workflow.md) — робочі сценарії
- [`docs/api.md`](docs/api.md) — Web API і security modes
- [`docs/roadmap.md`](docs/roadmap.md) — обов'язкові follow-ups
- [`CHANGELOG.md`](CHANGELOG.md) — хронологія змін
- [`CLAUDE.md`](CLAUDE.md) — правила для AI-агентів
