# Задачи: Персонажи с памятью — character consistency

## Статус: Pending

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

## Примечание
Требует переработку writer.py для генерации character profiles.
