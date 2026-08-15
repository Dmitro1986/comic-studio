# Таска: Публичная галерея опубликованных комиксов

## Статус: ✅ Done

## Дата фиксации: 2026-08-15

## Описание

Создать публичную страницу-галерею всех опубликованных комиксов на comic.openaiua.fr. Сейчас комиксы публикуются, но нет интерфейса для просмотра — ссылки работают, но ими никто не пользуется.

## Задачи

| # | Задача | Приоритет |
|---|---|---|
| 1 | Проектировать layout: сетка карточек с превью, заголовок, дата | high |
| 2 | Endpoint `GET /api/comics` — список published комиксов (без sensitive данных) | high |
| 3 | Публичная HTML-страница `/comics/` или `/gallery/` | high |
| 4 | Карточка комикса: thumbnail, title, date, link | high |
| 5 | Responsive дизайн (мобильные) | medium |
| 6 | SEO meta tags, open graph | low |

## Что сделано

- Создан `/ui/gallery.html` — публичная страница-галерея
- Добавлен route `/gallery` в `web/app.js`
- Расширен endpoint `GET /api/comics`: добавлены title, style, panels_count, url_html, created
- Исправлен баг: `store.find()` возвращает `{ state, path, record }`, не сам record
- URL: https://comic.openaiua.fr/gallery
