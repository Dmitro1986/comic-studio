# Задачи: Персонажи с памятью — character consistency

## Статус: ✅ Done

## Дата фиксации: 2026-08-15

## Описание
Решить главную проблему: персонаж "плавает" между панелями (меняется лицо, одежда, телосложение). Добавить persistent character descriptions как anchor.

## Задачи

| ID | Задача | Приоритет |
|---|---|---|
| 1 | Спроектировать формат character profile (внешность, манеры, голос) | high |
| 2 | Добавить поле characters[] в scenario schema | high |
| 3 | Интегрировать character anchor в image prompt | high |
| 4 | Добавить UI для редактирования персонажей | medium |
| 5 | Тестировать консистентность на 3+ панелях | medium |

## Проблема
MiniMax image-01 генерирует каждого персонажа независимо. Без явного anchor между панелями — персонаж плавает.

## Решение
К каждому prompt добавлять stable character description: "Older man in dark suit, gray slicked hair, blue eyes, confident smirk"

## Что сделано

- `writer.py`: добавлен `characters[]` в SYSTEM_PROMPT — LLM генерирует character profiles автоматически
- Формат: `{name, appearance, mannerisms}`
- Инъекция в промты: `CHARACTERS: Name: description; Name: description. ` в начало каждого panel prompt
- Поддержка revise: characters сохраняются и передаются при регенерации
- Протестировано: комикс `2866280d` с Trump и Musk — персонажи описаны и подставляются в промты

## Примечание
Требует переработку writer.py для генерации character profiles.
