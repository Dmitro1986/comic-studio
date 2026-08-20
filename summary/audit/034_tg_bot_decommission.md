# Аудит: Диагностика и декомиссия Telegram-бота Comic Studio

## 1. Контекст

Пользователь сообщил, что Telegram-бот `@oraclecomic_bot` не отвечает на команды `/start`, `/create`, `/published`. После диагностики выяснилось, что бот давал ответ "⛔ Доступ ограничен" с указанием Telegram ID пользователя.

Сервер работает на Oracle Cloud Free Tier с 1 GB RAM. Содержание отдельного Telegram-бота (~70 MB RSS) поверх web-сервера (~73 MB) — избыточная нагрузка. Управление комиксами уже доступно через Hermes MCP (stdio), что делает отдельного Telegram-бота избыточным.

## 2. Симптомы

- Telegram-бот запущен под PM2, статус `online` (4 дня uptime)
- Логи PM2 (`comic-tg-bot-out-1.log`, `comic-tg-bot-error-1.log`) — **полностью пустые** (0 байт с 14 авг)
- Процесс бота (PID 417271) **не открывал long-poll соединения** к `api.telegram.org` (только локальные сокеты)
- `getUpdates` через API показывал апдейты (значит, Telegram их отдавал, но Telegraf не забирал)
- При ручном запуске `node bot.js` в foreground бот работал корректно и видел ID пользователя

## 3. Корневые причины

### 3.1. Отсутствовал `data/allowed_users.json`
- `user_store.js` использует `TELEGRAM_CHAT_ID` из env как admin fallback, но в `.env` прописано `TELEGRAM_CHAT_ID`, а в `user_store.js` ожидается `process.env.CHAT_ID` (несоответствие имён)
- Файл `data/allowed_users.json` отсутствовал → admin whitelist пустой
- Пользователь `1045621572` формально был в `.env` как `TELEGRAM_CHAT_ID`, но не в `userStore.adminChatId`

### 3.2. PM2 cluster mode не перенаправлял stdout/stderr
- При рестарте через `pm2 restart` лог-файлы оставались пустыми
- PM2 показывал "online", но Telegraf не мог открыть long-poll
- В `ss -tnp` не было ни одного ESTABLISHED соединения от бота к `149.154.166.110:443`
- Процесс висел в `state: S (sleeping)` — не polling

### 3.3. Telegraf зацикливался на открытии-закрытии long-poll
- На короткое время соединение открывалось (`FIN-WAIT-2` в `ss`), но тут же рвалось
- Это указывает на возможный баг в Telegraf polling-цикле под PM2 cluster

## 4. Что сделано

1. Создан `data/allowed_users.json` с `["1045621572"]` — Telegram ID пользователя
2. Добавлен debug-лог в `assertAuthorized()` (временный, для диагностики)
3. Сменён режим запуска с `output`/`error` в `ecosystem.config.cjs` — не помогло
4. Снесён PM2-управляемый процесс: `pm2 delete comic-tg-bot`
5. Бот запущен напрямую (без PM2) как background-процесс Hermes — long-poll заработал стабильно, апдейты принимались
6. Подтверждена работоспособность бота в прямом режиме
7. Процесс бота остановлен (Hermes MCP полностью покрывает функциональность)

## 5. Решение

**Telegram-бот Comic Studio выведен из эксплуатации** на demo-production.

Обоснование:
- Hermes MCP уже предоставляет все инструменты (`list_scenarios`, `create_comic`, `render_comic`, `publish_comic` и т.д.) через stdio
- Telegram-бот дублирует функциональность, потребляя ~70 MB RAM впустую
- На сервере с 1 GB RAM это ощутимая нагрузка
- PM2 + Telegraf polling нестабильны (см. симптомы выше), требуют ручного обслуживания

## 6. Файлы

- `data/allowed_users.json` — оставлен (на случай возобновления работы бота в будущем)
- `tg-bot/bot.js` — debug-лог в `assertAuthorized()` (можно откатить)
- `tg-bot/user_store.js` — без изменений (известен баг с `CHAT_ID` vs `TELEGRAM_CHAT_ID`)
- `ecosystem.config.cjs` — секция `comic-tg-bot` оставлена, но не запускается
- `summary/CHANGELOG.md` — обновлён

## 7. Статус

✅ Done. Бот декомиссован. Управление через Hermes MCP.
