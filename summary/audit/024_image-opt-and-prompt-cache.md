# Аудит: Фаза 1 — Оптимизация WebP изображений и кэширование промтов MiniMax

## 1. Контекст
В рамках реализации **Фазы 1** документа [PRD_NEW1.md](file:///home/ubuntu/projects/comic-studio/PRD/PRD_NEW1.md) требовалось сократить объём передаваемых графических данных и убрать дублирование вызовов платного API MiniMax при повторном рендеринге панелей.

## 2. Что сделано
1. **Prompt-Image Cache (`py/lib/image_cache.py`)**:
   - Реализовано хэширование промтов по `sha256(character_prompt + scene_prompt + style + seed)`.
   - Внедрена проверка перед вызовом MiniMax API: если хэш существует в `data/.cache/images/<hash>.png`, изображение подгружается из кэша за **0.05 сек** без вызова платного API.
   - Директория `data/.cache/` добавлена в `.gitignore`.
2. **WebP Конвертация и Рендер Pipeline**:
   - Модуль `py/render/minimax_client.py` и `py/render/comic_assembler.py` генерируют файлы `.webp` (качество 82) параллельно с `.png` для отрендеренных панелей и итоговых превью комиксов.
3. **Web API & UI интеграция**:
   - В `web/app.js` и `web/lib/html_static.js` добавлены эндпоинты `/comics/<id>.webp` и `/comics/<id>/panel_<N>.webp` с заголовками долговременного кэширования (`Cache-Control: public, max-age=31536000, immutable`).
   - В `ui/app.js` дашборда внедрены адаптивные теги `<picture>` с поддержкой WebP и фоллбэком на PNG.
4. **OpenSpec Change**:
   - Создан, выполнен и заархивирован change `2026-08-08-image-opt-and-prompt-cache`.

## 3. Статус
✅ **Завершено**. Все 112/112 тестов Node.js и 3/3 юнит-тестов `test_image_cache.py` прошли успешно.
