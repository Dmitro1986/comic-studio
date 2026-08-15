# Аудит: Полный обзор проекта Comic Studio + Идеи расширения

## 1. Контекст

Дата: 2026-08-14
Проект: Comic Studio — конвейер производства серийных комиксов (контекст → сценарий → утверждение → рендер → публикация).

Основание: инвентаризация текущего состояния по итогам 30 аудитов и задач, а также идей, обсуждённых в сессии.

---

## 2. Что сделано (30 аудитов)

### Инфраструктура и интеграции

| # | Аудит | Статус |
|---|---|---|
| 023 | Разделение веток main / demo-production | ✅ |
| 020 | Системный setup (Node.js, Python, Oracle Cloud) | ✅ |
| 021 | gitignore, Mini App в боте | ✅ |
| 026 | Rate-limiting (express-rate-limit, 60/15min) | ✅ |
| 018 | MCP server integration | ✅ (фикс stderr-line сегодня) |

### AI и генерация сценариев

| # | Аудит | Статус |
|---|---|---|
| 003 | Style prompt system (image_style × caption_style) | ✅ |
| 015 | AiPULT phase 1 — resolution backend | ✅ |
| 016 | AiPULT phase 2 — UI chat panel | ✅ |
| 017 | AiPULT phase 2.5 — scenario focus | ✅ |
| 027 | AiPULT image style и execute fixes | ✅ |
| 028 | AiPULT execution, self-healing ScenarioStore | ✅ |
| 008 | Scenario revision and remix | ✅ |

### Рендеринг

| # | Аудит | Статус |
|---|---|---|
| 011 | Caption font и bubble sizes | ✅ |
| 012 | Comic HTML rendering (design) | ✅ |
| 013 | Comic HTML rendering (implementation) | ✅ |
| 014 | Restyle — quick bubble style change | ✅ |
| 024 | Image optimization (WebP) + prompt cache | ✅ |
| 022 | MCP port fix + CSS autoescape | ✅ |

### UI/UX

| # | Аудит | Статус |
|---|---|---|
| 004 | Image style UI selector | ✅ |
| 005 | Edit scenario UI | ✅ |
| 006 | Documentation, OpenSpec, CHANGELOG | ✅ |
| 019 | Fast restyle UX | ✅ |
| 025 | SSE real-time updates + pure-Python fuzzy search | ✅ |
| 030 | Draft card actions (Revision + Restyle на карточках) | ✅ |

### Экспорт и публикация

| # | Аудит | Статус |
|---|---|---|
| 026 | PDF/ZIP export endpoints + MCP tools | ✅ |
| 009 | Bot publish/render fixes | ✅ |
| 010 | Tg-bot revision tests | ✅ |
| 029 | Verified user access control (Web + Telegram) | ✅ |

---

## 3. Текущее состояние компонентов

```
✅ MCP server (comic-server)      — исправлен stderr, перезапущен
✅ Web API (port 3000)             — работает
✅ Telegram Bot                     — работает, авторизация по Chat ID
✅ Python pipeline (ingest/render) — работает, MiniMax API
✅ HTML rendering (Jinja2)         — primary artifact
✅ PNG rendering (Pillow fallback)  — для Telegram preview
✅ AiPULT resolution              — fuzzy search, intent parsing
✅ SSE real-time                  — live status updates
✅ Image cache                    — sha256 prompt hash, 0.05s reuse
✅ Prompt cache                   — LLM-generated prompts cached
✅ WebP optimization              — сжатие тяжёлых PNG
✅ Rate limiting                  — 60 req / 15 min
✅ User access control            — HMAC-SHA256 Telegram WebApp
✅ PDF export                     — multi-page
✅ ZIP export                     — panels + HTML
```

---

## 4. Что НЕ сделано (пробелы и идеи)

### 4.1 Контент и пайплайн

| Идея | Описание | Приоритет |
|---|---|---|
| **Автопубликация по расписанию** | Cron для auto-publish в Telegram-канал к определённому времени | medium |
| **Больше источников ингеста** | RSS-фиды, Reddit, Twitter/X parsing | low |
| **Серии/сезоны** | `series_id` + `episode` для персонажей с памятью | medium |
| **Персонажи с памятью** | Persistent character descriptions — anchor для консистентности между панелями | high |
| **Несколько image_style в одном комиксе** | Разные панели — разный стиль арта | low |

### 4.2 AI и сценарии

| Идея | Описание | Приоритет |
|---|---|---|
| **Caption style families** | ~1000 vocabulary entries в 18 families (аналог music-caption-rewriter). Tone: `humor`, `epic`, `breaking_news`, `satire`. LLM использует готовую vocabulary вместо генерации с нуля | **high** |
| **GPT-продюссер** | LLM сам предлагает идеи комиксов на основе новостей и трендов | medium |
| **Автогенерация альтернативных captions** | 3 варианта text per panel → выбор лучшего перед рендером | low |
| **Baoyu workflow → skill** | Hermes skill: контент → analysis framework → structured storyboard → Comic Studio API | medium |

### 4.3 UX и интерфейс

| Идея | Описание | Приоритет |
|---|---|---|
| **Публичная галерея** | Фильтры по стилю, дате, статусу — отдельная страница | medium |
| **Рендер-превью до утверждения** | Low-res fast preview перед approve | high |
| **WebSocket вместо SSE** | Более надёжное real-time соединение | low |
| **HTML preview перед MiniMax** | Fast HTML-рендер без API-стоимости | medium |

### 4.4 Публикация и соцсети

| Идея | Описание | Приоритет |
|---|---|---|
| **Twitter/X интеграция** | Реальная отправка в Twitter (publisher/social.js — placeholder) | medium |
| **Telegram-канал для публикации** | Публикация готовых комиксов в канал, не только бот-управление | medium |
| **Embed-код** | iframe или script для встраивания комикса на внешний сайт | low |
| **WEB_PUBLIC_URL** | Не настроен — ссылки на HTML не добавляются в Telegram-caption | medium |

### 4.5 Инфраструктура

| Идея | Описание | Приоритет |
|---|---|---|
| **CDN** | Все картинки с localhost:3000 — для внешнего доступа нужен CDN | medium |
| **Priority render queue** | urgent > normal > batch, возможность отмены | low |
| **Stats dashboard** | Количество по статусам, время рендера, cost tracking | low |
| **Comic-as-a-service API** | Публичное API для внешних клиентов | low |
| **Interactive HTML** | click-to-advance, sound effects, анимация | low |
| **Рейтинговая система** | Best/worst после публикации | low |

---

## 5. Самые ценные улучшения (топ-5) → Tasks: 031_1–031_6

1. **WEB_PUBLIC_URL** (031_1) — 5 минут настройки, сразу ссылки в Telegram
2. **Caption style families** (031_2) — консистентность и качество captions без допcost
3. **Рендер-превью** (031_3) — экономия MiniMax tokens перед approve
4. **Персонажи с памятью** (031_4) — убирает главный косяк: персонаж "плавает" между панелями
5. **Автопубликация cron** (031_5) — регулярный контент без ручного запуска
6. **Публичная галерея** (031_6) —豆瓣-подобная страница всех опубликованных комиксов

---

## 6. Нетронутые / неактуальные файлы аудитов

- `002_supadata-integration.md` — специфика supadata (не в main-ветке)
- `007_harden-web-server-api.md` — возможно частично перекрыт 029
- `024_image-opt...`, `025_sse...`, `026_export...` — done, не архивированы в openspec
