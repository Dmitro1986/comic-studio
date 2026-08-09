# Задачи: Верификация и контроль доступа пользователей (Web + Telegram Bot)

## Статус: ✅ Done

| ID | Задача | Статус |
|---|---|---|
| 1 | Создание реестра верифицированных пользователей Telegram `UserStore` | ✅ Done |
| 2 | Реализация администраторских команд `/add_user`, `/remove_user`, `/users` в боте | ✅ Done |
| 3 | Блокировка команд бота для неверифицированных пользователей с выводом их ID | ✅ Done |
| 4 | Валидация HMAC-SHA256 подписи Telegram WebApp `initData` в `web/lib/telegram_auth.js` | ✅ Done |
| 5 | Интеграция проверки `X-Telegram-Init-Data` в `accessControlMiddleware` | ✅ Done |
| 6 | Автопередача `X-Telegram-Init-Data` во все `apiFetch` запросы в `ui/approve.js` | ✅ Done |
| 7 | Добавление юнит-тестов HMAC подписи в `web/tests/telegram_auth.test.js` | ✅ Done |
| 8 | Прогон всех 118 тестов Node.js (118/118 passed) | ✅ Done |
| 9 | Создание и архивация OpenSpec change `verified-user-access-control` | ✅ Done |
