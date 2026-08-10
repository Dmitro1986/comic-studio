# Proposal: Draft Card Actions (Revision & Restyle for Drafts)

## Context
В настоящее время на карточке сценария со статусом `draft` в Web UI отображаются только кнопки `✅ Утвердить`, `❌ Отклонить` и `🗑 Удалить`. 
Однако пользователь должен иметь возможность скорректировать сценарий еще до первого рендера:
- Отредактировать текст подписей (`captions`) или стиль баблов (`style`) без рендера (**⚡️ Быстрая правка / Restyle**).
- Отправить сценарий в LLM на перегенерацию с фидбеком (**🔄 Revision**).

Кроме того, бэкенд `POST /api/scenarios/:id/restyle` выдает `409 INVALID_STATE`, если вызывать restyle для статусов `draft` или `approved`.

## Proposed Changes
1. **Backend (`web/routes/scenarios.js`)**:
   - Расширить эндпоинт `POST /api/scenarios/:id/restyle`, разрешив его вызов для статусов `draft`, `approved`, `rendered`, `published`.
   - Для статусов `draft` и `approved` обновлять `style` и `panels[].caption` в `JSON`-файле сценария, но **пропускать** вызов Python-скрипта `restyle.py` (так как сгенерированных картинок еще нет).

2. **Frontend (`ui/app.js`)**:
   - Вывести кнопки `🔄 Revision` и `⚡️ Быстрая правка` на карточках сценариев в статусах `draft` и `approved`.
   - В модальном окне `Fast Edit (Restyle)` корректно сохранять изменения подписей и стиля баблов для любого статуса сценария.

3. **Backend Tests (`web/tests/scenarios.test.js`)**:
   - Добавить тесты на вызов `restyle` для `draft` сценариев.

## Impact
Пользователи смогут полноценно готовить и корректировать текстовый сценарий перед отправкой на рендер картинок.
