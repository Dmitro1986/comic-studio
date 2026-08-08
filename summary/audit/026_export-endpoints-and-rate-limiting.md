# Аудит: Фаза 3 — Экспорт в PDF/ZIP и защита API rate-limiting

## 1. Контекст
В рамках реализации **Фазы 3** документа [PRD_NEW1.md](file:///home/ubuntu/projects/comic-studio/PRD/PRD_NEW1.md) требовалось:
1. Реализовать эндпоинты скачивания готовых комиксов в формате многостраничного PDF (`GET /api/scenarios/:id/export/pdf`) и Social ZIP архива (`GET /api/scenarios/:id/export/zip`).
2. Добавить интеграцию инструментов экспорта `export_comic_pdf` и `export_comic_zip` в MCP-сервер (`mcp-server/index.js`).
3. Внедрить кнопки быстрого скачивания "📥 PDF" и "📦 ZIP" в карточки комиксов Web UI (`ui/app.js`).
4. Настроить middleware защиты от спама и перерасхода токенов API (`express-rate-limit` окно 15 мин / лимит 60 операций) в `web/app.js`.

## 2. Что сделано
1. **Python Export Helper (`py/lib/export_helper.py` и `scripts/export_comic.py`)**:
   - Реализована сборка многостраничных PDF высокого качества с помощью Pillow (`Image.save(pdf_path, save_all=True)`).
   - Реализовано упаковывание панелей, шрифтов woff2 и HTML файла в портативный `.zip` архив через `zipfile`.
   - Написаны юнит-тесты `tests/test_export_helper.py` (**75/75** тестов Python проходят OK).
2. **Web API & MCP Интеграция**:
   - В `web/routes/scenarios.js` добавлены стриминговые эндпоинты с заголовком `Content-Disposition: attachment`.
   - В `mcp-server/index.js` зарегистрированы инструменты `export_comic_pdf` и `export_comic_zip`.
   - В `ui/app.js` добавлены кнопки для прямого скачивания архива и PDF.
3. **API Rate Limiting (`web/app.js`)**:
   - Добавлен middleware учета запросов с IP-адресов для `POST/PUT/DELETE` эндпоинтов с ответом `HTTP 429 Too Many Requests` при превышении лимита.
   - Написаны интеграционные тесты в `web/tests/export_and_ratelimit.test.js` (**115/115** тестов Node.js проходят OK).
4. **OpenSpec Change**:
   - Создан, выполнен и заархивирован change `2026-08-08-export-endpoints-and-rate-limiting`.

## 3. Статус
✅ **Завершено**. Все 115/115 тестов Node.js и 75/75 тестов Python прошли успешно.
