# Задачи: Поддержка смены стиля рисунка в AiPULT и отладка кнопки выполнения

## Статус: ⚠️ In Progress / Documented

| ID | Задача | Статус |
|---|---|---|
| 1 | Добавить распознавание арт-стилей рисунка (`anime`, `realistic`, `cyberpunk` и др.) в эвристику AiPULT (`web/lib/aipult/heuristic.js`) | ✅ Done |
| 2 | Разрешить показ кнопки `▶️ Run` для интентов `revise` и `render` в `ui/aipult.js` | ✅ Done |
| 3 | Сделать `--scenario-path` опциональным с автодетектом в `scripts/revise_scenario.py` | ✅ Done |
| 4 | Исправить обработку строковых отзывов в `py/scenario/writer.py` | ✅ Done |
| 5 | Смягчить серверную проверку `card_id` и `scenario_id` в `web/routes/aipult.js` (устранить HTTP 400) | ✅ Done |
| 6 | Дополнительная отладка браузерного исполнения карточек `revise` | ⏳ Pending / Tomorrow |
