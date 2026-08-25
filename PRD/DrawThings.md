# PRD: Draw Things Plugin для Comic Studio

**Версия:** 0.1
**Дата:** 2026-08-25
**Владелец:** Vlad
**Статус:** Draft → review

---

## Содержание

1. [Problem Statement](#1-problem-statement)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [User Personas](#3-user-personas)
4. [User Stories](#4-user-stories)
5. [Solution Overview](#5-solution-overview)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Architecture](#8-architecture)
9. [Data Model](#9-data-model)
10. [Workflows](#10-workflows)
11. [Integration Points](#11-integration-points)
12. [UI/UX](#12-uiux)
13. [Observability](#13-observability)
14. [Security & Privacy](#14-security-privacy)
15. [Rollout Plan](#15-rollout-plan)
16. [Risks & Mitigations](#16-risks--mitigations)
17. [Acceptance Criteria](#17-acceptance-criteria)
18. [Open Questions](#18-open-questions)

---

## 1. Problem Statement

Comic Studio сейчас использует **только MiniMax image-01** для генерации панелей. Это работает, но имеет ограничения:

1. **Стиль**: нельзя использовать кастомные LoRA (например, `STALKER_SDXL` для документального S.T.A.L.K.E.R. стиля)
2. **Контроль композиции**: нет ControlNet — модель решает композицию сама
3. **Стоимость**: каждый рендер тратит MiniMax кредиты
4. **Лица**: MiniMax часто рисует «усреднённые» лица, тогда как SDXL + LoRA даёт более характерные
5. **Зависимость от облака**: требует интернет и активный API ключ

У пользователя уже есть **локальный Draw Things** на `http://192.168.50.250:7860` в домашней сети (SDXL + ControlNet + STALKER_SDXL LoRA).

### 1.1. Текущая боль

Для тестового проекта «П'ять днів» (S.T.A.L.K.E.R. стиль) LLM MiniMax:
- Плохо держит точный возраст персонажа через серию панелей
- Игнорирует инструкции про подписи (генерирует свои)
- Не понимает «S.T.A.L.K.E.R.» как стиль — приходится описывать палитру текстом

Draw Things + STALKER_SDXL LoRA решил бы всё это через fine-tuned модель.

---

## 2. Goals & Non-Goals

### 2.1. Goals

1. **Двусторонний render**: каждый комикс может рендериться через MiniMax ИЛИ Draw Things
2. **Плагин для Hermes**: tool `generate_image` доступен мне в любой сессии (не только в Comic Studio контексте)
3. **Минимальные изменения**: ни Comic Studio архитектура, ни workflow не должны ломаться
4. **Без сетевых проблем**: если Draw Things выключен, fallback на MiniMax автоматически
5. **Прозрачный выбор провайдера**: пользователь явно указывает `provider="draw-things"` или `"minimax"` (или через `.env`)

### 2.2. Non-Goals

1. ❌ **Не строим** полноценный GUI для Draw Things — только HTTP/MCP интеграция
2. ❌ **Не делаем** img2img в первой версии — только txt2img
3. ❌ **Не интегрируем** ControlNet API — это будущее расширение
4. ❌ **Не уходим** от MiniMax — он остаётся default провайдером
5. ❌ **Не решаем** проблему монопольного доступа к Draw Things (одновременно работает только один пользователь)

---

## 3. User Personas

### 3.1. Vlad (текущий)

- Работает над Comic Studio на Oracle Cloud Free Tier (1 GB RAM)
- Дома имеет Mac с локальным Draw Things (SDXL, ControlNet, LoRA)
- Использует Comic Studio MCP для генерации комиксов
- Хочет качественнее лица и стиль (S.T.A.L.K.E.R.) в определённых проектах

### 3.2. Hermes (я)

- AI агент с доступом к терминалу и MCP
- Могу делать HTTP запросы через `curl` или MCP tools
- Должен уметь вызывать Draw Things так же, как вызываю MiniMax через Comic Studio

---

## 4. User Stories

### Story 1: Vlad пробует новый стиль

> **Как** Vlad,  
> **Хочу** сгенерировать одну панель через Draw Things, чтобы увидеть результат STALKER_SDXL LoRA,  
> **Чтобы** оценить, стоит ли переключать весь проект на локальный render.

**Команда через Comic Studio:**
```bash
python3 scripts/render_approved.py --scenario-id <id> --provider draw-things
```

### Story 2: Hermes генерирует ad-hoc

> **Как** Hermes,  
> **Хочу** вызвать `generate_image` tool с промптом про Славянск 2014 и LoRA STALKER_SDXL,  
> **Чтобы** показать Vlad альтернативный рендер без изменения Comic Studio сценария.

**Действие:** вызов MCP tool `draw-things.generate_image` с `lora="STALKER_SDXL.safetensors"`.

### Story 3: Автоматический fallback

> **Как** Vlad,  
> **Хочу** если Draw Things выключен, рендер не падает, а идёт через MiniMax,  
> **Чтобы** pipeline работал 24/7 без ручного переключения.

**Реализация:** try-except в `py/render/draw_things_client.py` с fallback на `minimax_client.generate_image()`.

---

## 5. Solution Overview

### 5.1. Архитектура (3 уровня)

```
┌─────────────────────────────────────────────────┐
│  Уровень 1: Hermes (AI Agent)                   │
│  ─────────────────────────────                  │
│  Tool: mcp__draw-things__generate_image         │
│  Tool: mcp__draw-things__get_options            │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────�
│  Уровень 2: MCP Server (stdio JSON-RPC)         │
│  ──────────────────────────────────────         │
│  Файл: mcp-server/draw-things/index.js (9.3 KB) │
│  Уже создан, НЕ зарегистрирован в config.yaml   │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  Уровень 3: Draw Things (HTTP)                  │
│  ───────────────────────────────                │
│  URL: http://192.168.50.250:7860                │
│  API: GET /sdapi/v1/options, POST /txt2img      │
│  Модель: sd_xl_base_1.0_f16.ckpt                │
│  LoRA: STALKER_SDXL, pixar_sdxl_lora            │
└─────────────────────────────────────────────────┘
```

### 5.2. Опционально: провайдер в Comic Studio

```
scripts/render_approved.py
       │
       ▼
py/render/comic_assembler.py
       │
       ├── provider=minimax → py/render/minimax_client.py (по умолчанию)
       │
       └── provider=draw-things → py/render/draw_things_client.py (новый)
```

---

## 6. Functional Requirements

### 6.1. MCP Server (Hermes → Draw Things)

| ID | Требование | Приоритет |
|---|---|---|
| F1 | Tool `generate_image` принимает prompt, width, height, steps, sampler, cfg_scale, seed, lora, lora_weight | must |
| F2 | Tool возвращает JSON с path к PNG + bytes + seed + модель | must |
| F3 | Tool `get_options` возвращает текущие настройки Draw Things (модель, LoRA, last prompt) | should |
| F4 | Если Draw Things недоступен — вернуть понятную ошибку (не молча упасть) | must |
| F5 | Поддержка timeout через env `DRAW_THINGS_TIMEOUT` (default 300 сек) | must |
| F6 | LoRA инжектится в prompt как `<lora:NAME:WEIGHT>` | must |
| F7 | PNG сохраняется в `os.tmpdir()` с уникальным именем `draw-things-TIMESTAMP.png` | must |

### 6.2. Comic Studio провайдер (опционально)

| ID | Требование | Приоритет |
|---|---|---|
| F8 | `py/render/draw_things_client.py` с функцией `generate_image(prompt, output_path, aspect_ratio, seed) -> Path` | should |
| F9 | `scripts/render_approved.py` принимает `--provider draw-things` | should |
| F10 | Если Draw Things выключен — fallback на MiniMax через try-except | must |
| F11 | Env `DRAW_THINGS_URL` в `.env` (default `http://127.0.0.1:7860`) | should |

### 6.3. Конфигурация

| ID | Требование | Приоритет |
|---|---|---|
| F12 | Регистрация в `~/.hermes/config.yaml` секция `mcp_servers.draw-things` | must |
| F13 | `.env` опционально `DRAW_THINGS_URL=http://192.168.50.250:7860` | should |
| F14 | После регистрации — перезапуск Hermes для подхвата MCP | must |

---

## 7. Non-Functional Requirements

| ID | Требование |
|---|---|
| NF1 | Латентность одного `generate_image` вызова: 5-60 сек (SDXL на Mac обычно 10-30 сек на панель) |
| NF2 | Плагин не должен ломать существующие comic-server MCP (отдельный процесс) |
| NF3 | stdio MCP — никакого `console.log`, только `console.error` в stderr (иначе JSON-RPC ломается) |
| NF4 | Плагин переиспользует `node_modules` от `comic-server` через симлинк — нет дублирования SDK |
| NF5 | Код плагина < 200 строк (минимализм) |
| NF6 | Без секретов в коде — URL через env |

---

## 8. Architecture

### 8.1. Текущее состояние (что уже сделано)

```
✅ mcp-server/draw-things/index.js  — 9.3 KB, stdio MCP server
✅ mcp-server/draw-things/node_modules → симлинк на ../node_modules
❌ ~/.hermes/config.yaml — НЕ зарегистрирован
❌ .env — DRAW_THINGS_URL не задан
```

### 8.2. Проверка соответствия конфигурации

После сброса (reset) Hermes плагинов **мой файл `index.js` остался** — это потому что он лежит в `mcp-server/draw-things/`, а не в `~/.hermes/plugins/`. Сброс плагинов в `~/.hermes/plugins/` **не затрагивает** мой код в проекте.

**Что соответствует конфигурации:**
- ✅ Структура совпадает с эталоном (`mcp-server/index.js` для comic-studio)
- ✅ Использует тот же `@modelcontextprotocol/sdk` через симлинк
- ✅ Env-based конфигурация (`DRAW_THINGS_URL`, `DRAW_THINGS_TIMEOUT`)
- ✅ stdio JSON-RPC, без console.log
- ✅ Два tools: `generate_image` + `get_options`

**Что нужно добавить для активации:**
1. Регистрация в `~/.hermes/config.yaml`:
   ```yaml
   mcp_servers:
     draw-things:
       command: node
       args: [mcp-server/draw-things/index.js]
       env:
         DRAW_THINGS_URL: http://192.168.50.250:7860
   ```
2. (Опционально) `.env` в проекте с тем же URL

### 8.3. Структура файлов после активации

```
comics/
├── mcp-server/
│   ├── index.js              ← comic-server (уже работает)
│   ├── draw-things/
│   │   ├── index.js          ← draw-things (готов, не зарегистрирован)
│   │   └── node_modules → ../node_modules
│   └── package.json
├── .env                       ← + DRAW_THINGS_URL=http://192.168.50.250:7860
└── PRD/DrawThings.md          ← этот файл

~/.hermes/
└── config.yaml                ← + mcp_servers.draw-things секция
```

---

## 9. Data Model

Не применимо — это stateless MCP plugin. Состояние хранится в Draw Things (server-side).

---

## 10. Workflows

### 10.1. Hermes вызывает Draw Things

```
[User] "Сгенерируй панель про Славянск 2014 в стиле S.T.A.L.K.E.R."
       │
       ▼
[Hermes] вызывает mcp__draw-things__generate_image
       │
       ▼
[MCP server] POST /sdapi/v1/options + POST /sdapi/v1/txt2img
       │
       ▼
[Draw Things] генерация 20 steps × cfg 7
       │
       ▼
[MCP server] save base64 PNG → /tmp/draw-things-XXX.png
       │
       ▼
[Hermes] возвращает user: путь + vision_analyze превью
```

### 10.2. Comic Studio через Draw Things (опционально)

```
[User] python3 scripts/render_approved.py --scenario-id <id> --provider draw-things
       │
       ▼
[script] provider=draw-things → import draw_things_client
       │
       ▼
[draw_things_client] POST к /sdapi/v1/txt2img
       │
       ▼ (if error)
[fallback] minimax_client.generate_image()
```

---

## 11. Integration Points

### 11.1. Внутренние

| Откуда | Куда | Что |
|---|---|---|
| Hermes | `mcp__draw-things__generate_image` | tool call |
| `mcp-server/draw-things/index.js` | `http://192.168.50.250:7860` | HTTP POST |
| `os.tmpdir()` | User filesystem | PNG файл |
| `~/.hermes/config.yaml` | Hermes runtime | регистрация MCP |

### 11.2. Внешние

| Куда | Порт | Авторизация |
|---|---|---|
| Draw Things HTTP API | 7860 | нет (LAN-only) |

---

## 12. UI/UX

Нет UI — это backend-интеграция. Пользователь видит результат через:
- vision_analyze превью PNG (через меня)
- Comic Studio gallery если провайдер интегрирован
- Telegram/Notion если PNG публикуется стандартным способом

---

## 13. Observability

### 13.1. Логирование

- `console.error` в stderr для debug (через `DRAW_THINGS_DEBUG=1`)
- Структурированный JSON в MCP response (`success`, `path`, `bytes`, `seed`, `model`, `prompt`)
- Draw Things собственные логи — на сервере пользователя

### 13.2. Метрики (опционально, future)

- Количество вызовов в день
- Среднее время генерации
- Success/fallback rate

---

## 14. Security & Privacy

| Риск | Митигация |
|---|---|
| Draw Things в публичной сети | Только LAN (`192.168.*`), no external exposure |
| API key leak | Нет — Draw Things без auth |
| PNG leak в tmpdir | TTL очистка, только для текущей сессии |
| Command injection через prompt | JSON-escape в fetch body, нет shell |
| stdio JSON-RPC corruption | Только `console.error`, никакого `console.log` |

---

## 15. Rollout Plan

### Phase 1: MVP (только Hermes plugin)

**Scope:** регистрация MCP, тестовый вызов `generate_image`  
**Steps:**
1. Регистрация в `~/.hermes/config.yaml`
2. Перезапуск Hermes
3. Тест: сгенерировать одну панель через `generate_image`
4. Vision-проверка результата

**Критерии готовности:**
- ✅ Tool `mcp__draw-things__generate_image` доступен в моих tools
- ✅ Один успешный рендер с сохранением PNG
- ✅ Error handling при недоступности Draw Things

**Ожидаемое время:** 5-10 минут

### Phase 2: Comic Studio провайдер (если Phase 1 успешен)

**Scope:** `py/render/draw_things_client.py`, `--provider` flag  
**Steps:**
1. Создать `draw_things_client.py` (аналог `minimax_client.py`)
2. Добавить в `comic_assembler.py` case
3. Тест: рендер существующего approved сценария через Draw Things

**Критерии:**
- ✅ Один комикс отрендерен через Draw Things
- ✅ Fallback на MiniMax при недоступности

### Phase 3: img2img + ControlNet (future, через 1-2 месяца)

**Scope:** переработка существующих панелей через STALKER_SDXL + ControlNet depth  
**Steps:**
1. Tool `img2img` через тот же MCP
2. ControlNet API integration

---

## 16. Risks & Mitigations

| Риск | Вероятность | Импакт | Митигация |
|---|---|---|---|
| Draw Things offline во время генерации | высокая | средний | timeout + fallback на MiniMax |
| Очередь в Draw Things (Vlad генерирует своё) | средняя | низкий | retry с exponential backoff, до 3 раз |
| Модель не подходит (LoRA конфликт) | низкая | средний | явное `lora_weight` параметр, default 0.7 |
| Латентность 30+ сек убивает timeout | средняя | средний | env `DRAW_THINGS_TIMEOUT=300` |
| MCP регистрация конфликтует с comic-server | низкая | высокий | отдельный `command: node` процесс, разные имена |

---

## 17. Acceptance Criteria

### Phase 1

- [ ] `mcp__draw-things__generate_image` виден в моём tool list после перезапуска Hermes
- [ ] Вызов с prompt="test cat" возвращает JSON с `path`, `bytes > 0`
- [ ] PNG на диске существует и не пустой (`test -s`)
- [ ] vision_analyze на PNG работает и видит изображение
- [ ] При недоступном Draw Things возвращается JSON с `success: false, error: ...`

### Phase 2

- [ ] `--provider draw-things` в `render_approved.py` работает
- [ ] Один сценарий отрендерен через Draw Things + STALKER_SDXL LoRA
- [ ] Fallback на MiniMax при ошибке

---

## 18. Open Questions

1. **Q1**: Нужен ли img2img в Phase 1, или только txt2img?
   - **Decision pending** — предлагаю txt2img first, img2img в Phase 3

2. **Q2**: Должны ли мы хранить seed в сценарии для идемпотентности?
   - **Decision pending** — сейчас seed в Comic Studio есть, но Draw Things клиент может его игнорировать

3. **Q3**: Как тестировать плагин offline (без Draw Things)?
   - **Решение**: mock HTTP server через Python (отдельный test fixture, не в Phase 1)

4. **Q4**: Должны ли мы лимитировать LoRA вес через Comic Studio?
   - **Decision pending** — пользователь может переопределить через `--lora-weight`

5. **Q5**: Phase 1 или Phase 2 первым?
   - **Предложение**: Phase 1 (5-10 мин, низкий риск), потом решение про Phase 2

---

## Текущий статус

- ✅ PRD создан
- ✅ MCP server код готов (`mcp-server/draw-things/index.js`)
- ❌ НЕ зарегистрирован в `~/.hermes/config.yaml`
- ❌ НЕ активирован

**Следующее действие** (по запросу пользователя): регистрация MCP в `~/.hermes/config.yaml` + перезапуск + Phase 1 тест.
