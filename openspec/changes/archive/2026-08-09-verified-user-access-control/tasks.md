# Tasks: Verified User Access Control

## 1. Telegram Bot Verification Module
- [x] 1.1 Создать модуль хранения разрешённых пользователей Telegram (`tg-bot/user_store.js` / `data/allowed_users.json`).
- [x] 1.2 Обновить `assertAuthorized` в `tg-bot/bot.js` для проверки по списку ID.
- [x] 1.3 Реализовать команды администратора `/add_user`, `/remove_user`, `/users`.

## 2. Web API Authentication & HMAC Validation
- [x] 2.1 Создать модуль валидации Telegram initData (`web/lib/telegram_auth.js`).
- [x] 2.2 Добавить поддержку сессий и авторизации в `web/lib/access_control.js`.

## 3. Web UI Integration
- [x] 3.1 Обновить `ui/approve.js` для автоматической передачи Telegram initData в `apiFetch`.

## 4. Testing & Verification
- [x] 4.1 Написать юнит-тесты валидации Telegram HMAC подписи в `web/tests/telegram_auth.test.js`.
- [x] 4.2 Убедиться, что все 118+ Node тестов проходят (118/118 passed).
