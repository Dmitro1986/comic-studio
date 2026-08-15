# Task 031_7: Управление опубликованными — вернуть в Готовые

## Статус: Pending

## Описание

Сейчас после публикации комикс полностью immutable — его нельзя удалить, отредактировать или снять с публикации. Это демо-блокер: опубликованный комикс нельзя убрать из галереи.

## Текущее поведение (CLAUDE.md)

- `published` immutable — не изменять, не удалять
- Редактирование только через `POST /api/scenarios/:id/remix` (новый draft)

## Нужное поведение

Кнопка **«Вернуть в Готовые»** на карточках опубликованных комиксов:

1. Снять с публикации — переместить из `data/scenarios/published/` обратно в `data/scenarios/rendered/`
2. Удалить HTML из `web/comics/` (если есть)
3. Убрать из галереи `/gallery`
4. Создать запись в логе

**Важно:** Это нарушает "published immutable" правило из CLAUDE.md. Решение принято для демо-удобства.

## API эндпоинты

```
POST /api/scenarios/:id/unpublish
  → 200: { ok: true, id, new_status: "rendered" }
  → 404: scenario not found
  → 400: not published
```

## UI

В админке/галерее на карточках published — кнопка **«Вернуть в Готовые»**.

## Файлы

- `web/routes/scenarios.js` — добавить `router.post('/:id/unpublish')`
- `web/lib/lifecycle.js` — добавить `lifecycle.unpublish(id)`
- `ui/app.js` — добавить кнопку и обработчик (или inline в gallery.html)

## Тестирование

1. Опубликовать комикс → появится в галерее
2. Нажать "Вернуть в Готовые" → исчезает из галереи
3. Появляется в разделе "Готовые" (rendered)
4. Можно снова опубликовать

## Демо-ссылка

https://comic.openaiua.fr/gallery
