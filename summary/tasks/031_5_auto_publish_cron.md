# Задачи: Автопубликация по расписанию (Cron)

## Статус: Pending

## Описание
Настроить cron для auto-publish готовых комиксов в Telegram-канал к определённому времени.

## Задачи

| ID | Задача | Приоритет |
|---|---|---|
| 1 | Добавить поле scheduled_time в scenario schema | medium |
| 2 | Реализовать cron job для проверки scheduled_time | medium |
| 3 | Интегрировать Telegram-бот publish в cron | medium |
| 4 | Добавить UI для выбора времени публикации | medium |
| 5 | Тестировать на dev/staging | low |

## Примечание
cron/nightly.sh уже существует — расширить его.
