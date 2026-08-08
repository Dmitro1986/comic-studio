# Задачи: Фаза 1 — Оптимизация WebP изображений и кэширование промтов MiniMax

## Статус: ✅ Done

| ID | Задача | Статус |
|---|---|---|
| 1 | Реализовать модуль кэширования `py/lib/image_cache.py` с алгоритмом SHA256 | ✅ Done |
| 2 | Добавить `data/.cache/*` в `.gitignore` | ✅ Done |
| 3 | Интегрировать проверку кэша и генерацию `.webp` в `py/render/minimax_client.py` | ✅ Done |
| 4 | Добавить конвертацию `.webp` при сборке превью комикса в `py/render/comic_assembler.py` | ✅ Done |
| 5 | Реализовать отдачу `.webp` с заголовками immutable кэша в `web/app.js` и `web/lib/html_static.js` | ✅ Done |
| 6 | Обновить отображение картинок в дашборде `ui/app.js` на `<picture>` с источником WebP | ✅ Done |
| 7 | Написать юнит-тесты `tests/test_image_cache.py` и HTTP тесты в `web/tests/html_rendering.test.js` | ✅ Done |
| 8 | Создать, выполнить и заархивировать OpenSpec change `image-opt-and-prompt-cache` | ✅ Done |
