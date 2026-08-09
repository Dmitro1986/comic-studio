# Design: Verified User Access Control

## Architectural Overview

```
                        ┌──────────────────────────────────────────────┐
                        │              Пользователь                    │
                        └──────────────────────┬───────────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
              [ Telegram MiniApp / Bot ]                      [ Обычный Веб-браузер ]
                       │                                               │
                       ▼                                               ▼
        telegram.WebApp.initData                             Session Cookie / Bearer
        (HMAC-SHA256 verification)                                  Passcode
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               ▼
                                   ┌──────────────────────┐
                                   │  Access Middleware   │
                                   └──────────┬───────────┘
                                              │
                                   ┌──────────┴───────────┐
                                   ▼                      ▼
                           [ Telegram Bot ]        [ Web Studio API ]
                         (data/allowed_users)        (/api/* & /ui/)
```

## Detailed Specifications

### 1. Telegram Bot User Verification (`tg-bot/bot.js` & `tg-bot/user_store.js`)
- Файл хранения: `data/allowed_users.json`
- При запуске список инициализируется из `data/allowed_users.json` и `process.env.ALLOWED_TELEGRAM_USERS`.
- Модуль `assertAuthorized(ctx)` проверяет `ctx.from.id` по списку разрешённых ID.
- Если ID не найден:
  - Выводится интерактивное сообщение:
    `⛔ Доступ ограничен. Ваш Telegram ID: <code>123456789</code>.\nОбратитесь к администратору или введите инвайт-код: /verify <code>`
- Администраторские команды:
  - `/add_user <id>`: добавляет ID в `data/allowed_users.json`.
  - `/remove_user <id>`: удаляет ID.
  - `/users`: выводит список авторизованных Telegram пользователей.

### 2. Web Application Authentication (`web/lib/telegram_auth.js` & `web/lib/access_control.js`)
- Создаётся вспомогательный модуль `web/lib/telegram_auth.js`:
  - Функция `verifyTelegramInitData(initDataRaw, botToken)` производит разбор параметров `initData`, сортирует ключи по алфавиту, вычисляет `secret_key = HMAC-SHA256("WebAppData", botToken)` и сравнивает `hash` через `crypto.timingSafeEqual`.
  - Извлекает `user.id` и проверяет его наличие в `allowed_users`.
- Создаётся модуль проверки веб-сессии:
  - Если передан заголовок `x-telegram-init-data` или `Authorization: Bearer initData:...`, валидируется `initData`.
  - Если передан токен сессии / PIN-код `Authorization: Bearer <token>` или Cookie `comic_session`, валидируется соответствие `WEB_AUTH_PASSWORD` / `API_TOKEN`.
- При неудаче:
  - Запросы к `/api/*` возвращают `401 Unauthorized` (`{ error: { code: 'UNAUTHORIZED', message: 'Authentication required' } }`).

### 3. Frontend Integration (`ui/app.js` & `ui/login.html`)
- В `ui/app.js`:
  - Если доступен объект `window.Telegram?.WebApp?.initData`, он автоматически передаётся во всех запросах `apiFetch` через заголовок `X-Telegram-Init-Data`.
  - Если API возвращает `401 Unauthorized`, клиент перенаправляется на `/ui/login.html` или показывает модальное окно авторизации.

## Migration & Backward Compatibility
- Если `ALLOWED_TELEGRAM_USERS` не задан в `.env`, по умолчанию используется текущий `CHAT_ID` администратора (backward compatibility).
- Если `WEB_AUTH_REQUIRED=false`, сервер работает в режиме разработчика без обязательной авторизации.
