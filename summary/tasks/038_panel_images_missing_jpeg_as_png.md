# Задачи: Пропавшие панели комикса — MiniMax JPEG под маской PNG

**Дата:** 2026-11-09
**Номер:** 038
**Аудит:** `summary/audit/038_panel_images_missing_jpeg_as_png.md`

## Статус: ✅ Done

| ID | Задача | Статус |
|---|---|---|
| 1 | Диагностировать пропуск панелей 2 и 4 в `7dcd29fc.html` | ✅ Done |
| 2 | Установить корневую причину (сигнатура байтов vs MIME-заголовок) | ✅ Done |
| 3 | Исправить `py/render/minimax_client.py`: нормализация байтов провайдера в PNG | ✅ Done |
| 4 | Проверить и исправить CSS: `figure.panel > a` → `display: block` | ✅ Done |
| 5 | Сконвертировать 293 JPEG-файла под маской `.png` в 31 комиксе | ✅ Done |
| 6 | Перегенерировать `7dcd29fc.html` с новым CSS, проверить 6/6 якорей | ✅ Done |
| 7 | Пропатчить `adf83fa9.html` (единственный иной комикс с anchor-обёртками) | ✅ Done |
| 8 | Проверка всей библиотеки: 84 комикса, 882 файла, 0 ошибок | ✅ Done |
| 9 | Проверить production-хост: HTTP 200, PNG-сигнатура, декодируемость | ✅ Done |
| 10 | Попутно: исправить `str.capitalize()` → «Акт i» в `py/render/book/renderer.py` | ✅ Done |

## Детали

### T1 — Диагностика
Проверены: наличие файлов на диску, HTTP-коды и заголовки, структура HTML, состояние `<img>` в браузере (`naturalWidth=0`, `complete=false`), performance resource entries (0 запросов), сигнатуры байтов.

### T2 — Корневая причина
`ffd8ffe0...` (JFIF/JPEG) вместо `89504e47...` (PNG) при заголовке `Content-Type: image/png`. Chrome отказывается декодировать — silent fail без ошибок в консоли.

### T3 — Фикс источника
```python
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

def _ensure_png_bytes(img_bytes: bytes) -> bytes:
    if img_bytes.startswith(_PNG_SIGNATURE):
        return img_bytes
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(img_bytes)) as img:
            img.load()
            buffer = io.BytesIO()
            img.convert("RGB").save(buffer, format="PNG")
            return buffer.getvalue()
    except Exception as err:
        logger.warning("Could not convert provider payload to PNG: %s", err)
        return img_bytes
```
Вызывается перед `out_path.write_bytes(img_bytes)`.

### T4 — Фикс CSS
```css
main.comic--comic > figure.panel > a {
  display: block;
  width: 100%;
  height: 100%;
  line-height: 0;
  text-decoration: none;
}
```

### T8 — Итоговая проверка
```
comics checked: 84
bad PNG:  0
bad WebP: 0
broken HTML refs: 0
✅ LIBRARY CLEAN
```

## Следующие шаги (вне текущей задачи)

- Подобрать актуальную модель MiniMax для `py/scenario/writer.py` — `MiniMax-Text-01` більше не доступна (ошибка 2069).
- Добавить `--lang` / `--source-url` в `scripts/render_book_clean.py` для паритета с `render_book_html()`.
- Додати в render-пайплайн автопроверку сигнатур PNG (ловить баг на этапе рендера, а не на этапе публикации).
