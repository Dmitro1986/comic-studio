# Аудит: Верификация и контроль доступа пользователей (Web + Telegram Bot)

## 1. Контекст
Внедрен механизм контроля доступа только для верифицированных пользователей на Веб-сайте (`/ui/`, `/comics/`, `/api/*`) и в Telegram-боте.

## 2. Что сделано
- **Telegram Bot (`tg-bot/user_store.js`, `tg-bot/bot.js`)**:
  - Создан динамический реестр `UserStore` (`data/allowed_users.json` + `ALLOWED_TELEGRAM_USERS` + `CHAT_ID`).
  - Функция `assertAuthorized` проверяет `ctx.from.id`. Неверифицированные юзеры получают системный блокирующий ответ с показом их Telegram ID.
  - Добавлены администраторские команды управления доступом: `/add_user <id>`, `/remove_user <id>`, `/users`.

- **Web API & Telegram WebApp HMAC Validation (`web/lib/telegram_auth.js`, `web/lib/access_control.js`)**:
  - Реализована валидация HMAC-SHA256 подписи Telegram WebApp `initData` по официальной спецификации Telegram.
  - В `accessControlMiddleware` добавлена проверка заголовка `X-Telegram-Init-Data` с извлечением информации об авторизованном верифицированном юзере.
  - В `ui/approve.js` на фронтенде добавлена автоматическая подстановка `X-Telegram-Init-Data` во все вызовы `apiFetch` при открытии в Telegram MiniApp.

## 3. Статус
- Юнит-тесты валидации HMAC подписи написаны в `web/tests/telegram_auth.test.js`.
- Все 118 тестов Node.js успешно проходят (118/118 passed).
- OpenSpec change `verified-user-access-control` заархивирован в `openspec/changes/archive/2026-08-09-verified-user-access-control/`.
