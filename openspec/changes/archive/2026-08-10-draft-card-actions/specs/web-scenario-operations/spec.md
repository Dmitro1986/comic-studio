# web-scenario-operations Delta

## Requirements

### Requirement: Restyle operations across lifecycle statuses
Restyle API (`POST /api/scenarios/:id/restyle`) SHALL разрешать редактирование текстов подписей (`captions`) и визуального стиля баблов (`style`) для сценариев во всех активных статусах (`draft`, `approved`, `rendered`, `published`).

#### Scenario: Restyle on draft or approved scenario
- **WHEN** клиент вызывает `POST /api/scenarios/:id/restyle` для сценария в статусе `draft` или `approved`
- **THEN** сервер обновляет `style` и `panels[].caption` в canonical JSON record на диске без запуска Python restyle process и возвращает 200 OK.

#### Scenario: Restyle on rendered or published scenario
- **WHEN** клиент вызывает `POST /api/scenarios/:id/restyle` для сценария в статусе `rendered` или `published`
- **THEN** сервер обновляет canonical JSON record и выполняет локальный Python restyle process для обновления PNG/HTML артефактов.

### Requirement: Editable status UI action controls
Web UI SHALL выводить контролы `Revision` и `⚡️ Быстрая правка` на карточках сценариев для всех редактируемых статусов (`draft`, `approved`, `rendered`).
