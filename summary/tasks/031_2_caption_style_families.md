# Задачи: Caption Style Families — библиотека vocabulary для LLM

## Статус: Pending

## Описание
Реализовать справочник caption vocabulary (~1000 entries, 18 style families) для генерации качественных и консистентных captions без дополнительной стоимости.

## Задачи

| ID | Задача | Приоритет |
|---|---|---|
| 1 | Изучить music-caption-rewriter подход (~1000 refs, 18 families) | medium |
| 2 | Спроектировать структуру caption families для Comic Studio | medium |
| 3 | Создать файл с vocabulary (tone: humor, epic, breaking_news, satire) | high |
| 4 | Интегрировать vocabulary в writer.py system prompt | high |
| 5 | Добавить switch tone в API /create_scenario | medium |
| 6 | Тестировать на 3-5 комиксах, сравнить качество | medium |

## Референс
Аналог: MiniMax Music skill music-caption-rewriter с 18 style families.

## Примечание
Не требует дополнительных API — использует существующий MiniMax.
