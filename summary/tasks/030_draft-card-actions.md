# Задачи: Вывод и поддержка редактирования (Revision & Restyle) на карточках черновиков (Draft)

## Статус: ✅ Done

| ID | Задача | Статус |
|---|---|---|
| 1 | Обновить эндпоинт `POST /api/scenarios/:id/restyle` в `web/routes/scenarios.js` — добавить поддержку статусов `draft` и `approved` без вызова Python restyle process | ✅ Done |
| 2 | Добавить unit-тест `restyle` для `draft` сценариев в `web/tests/operations.test.js` | ✅ Done |
| 3 | Обновить `ui/app.js` — добавить кнопки `🔄 Revision` и `⚡️ Быстрая правка` на карточки в статусах `draft` и `approved` | ✅ Done |
| 4 | Запустить и прогнать полный свит Web API тестов (`npm test` в `web/`) | ✅ Done (119/119 tests passed) |
