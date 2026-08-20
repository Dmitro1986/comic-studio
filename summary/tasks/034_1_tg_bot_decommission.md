# Task 034_1: Декомиссия Telegram-бота Comic Studio

## Статус: Done

## Описание

Telegram-бот Comic Studio (`@oraclecomic_bot`, PID ком. в `tg-bot/bot.js`) выведен из эксплуатации на demo-production. Управление сценариями/комиксами полностью покрывается через Hermes MCP.

## Причины

1. **Дублирование функциональности.** Hermes MCP (stdio) уже предоставляет все инструменты:
   - `list_scenarios`, `get_scenario`, `create_comic`, `approve_scenario`
   - `render_comic`, `revise_scenario`, `restyle_comic`
   - `resolve_intent`, `read_comic_image`, `update_comic_text`
   - `export_comic_pdf`, `export_comic_zip`
2. **Нагрузка на сервер с 1 GB RAM.** RSS Telegram-бота — ~70 MB, что критично для Oracle Cloud Free Tier.
3. **Нестабильность PM2 + Telegraf polling** (см. аудит 034).

## Что сделано

1. ✅ Создан `data/allowed_users.json` с `["1045621572"]` — ID владельца
2. ✅ Добавлен debug-лог в `tg-bot/bot.js::assertAuthorized()` для диагностики
3. ✅ Снесён PM2-управляемый процесс: `pm2 delete comic-tg-bot`
4. ✅ Подтверждена работоспособность бота в foreground-режиме (но не используется)
5. ✅ Процесс бота остановлен окончательно

## Что НЕ сделано (осознанно)

- **Не удалён** `tg-bot/bot.js` — оставлен на случай возобновления
- **Не удалён** `data/allowed_users.json` — whitelist оставлен как артефакт
- **Не откачен** debug-лог в `assertAuthorized()` — не вредит, видно состояние авторизации
- **Секция `comic-tg-bot`** в `ecosystem.config.cjs` оставлена, но не запускается

## Если потребуется возобновить

```bash
# 1. Поправить user_store.js — брать adminChatId из TELEGRAM_CHAT_ID
# 2. Запустить через systemd (НЕ PM2) — проверено, foreground работает стабильно
cd /home/ubuntu/projects/comics/tg-bot && node bot.js
# 3. Настроить автозапуск через systemd unit с Restart=always
```

## Файлы

- `summary/audit/034_tg_bot_decommission.md` — подробный аудит
- `data/allowed_users.json` — whitelist (1 запись)
- `tg-bot/bot.js` — debug-лог в `assertAuthorized()`
- `ecosystem.config.cjs` — секция бота оставлена

## Экономия ресурсов

| Метрика | До | После |
|---|---|---|
| Процессов Node | 2 (web + tg-bot) | 1 (web) |
| RSS суммарно | ~143 MB | ~73 MB |
| RAM свободно | ~280 MB | ~350 MB |
