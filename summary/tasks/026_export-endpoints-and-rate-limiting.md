# Задачи: Фаза 3 — Экспорт в PDF/ZIP и защита API rate-limiting

## Статус: ✅ Done

| ID | Задача | Статус |
|---|---|---|
| 1 | Реализовать `py/lib/export_helper.py` для генерации многостраничного PDF и ZIP | ✅ Done |
| 2 | Создать CLI скрипт `scripts/export_comic.py` | ✅ Done |
| 3 | Написать юнит-тесты `tests/test_export_helper.py` | ✅ Done |
| 4 | Реализовать эндпоинты `GET /api/scenarios/:id/export/pdf` и `/zip` в `web/routes/scenarios.js` | ✅ Done |
| 5 | Внедрить rate-limiting middleware в `web/app.js` | ✅ Done |
| 6 | Добавить инструменты `export_comic_pdf` и `export_comic_zip` в `mcp-server/index.js` | ✅ Done |
| 7 | Добавить кнопки "📥 PDF" и "📦 ZIP" в карточки комиксов `ui/app.js` | ✅ Done |
| 8 | Написать интеграционные тесты `web/tests/export_and_ratelimit.test.js` | ✅ Done |
| 9 | Создать, выполнить и заархивировать OpenSpec change `export-endpoints-and-rate-limiting` | ✅ Done |
