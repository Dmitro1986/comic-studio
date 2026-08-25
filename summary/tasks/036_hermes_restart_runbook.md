# Task 036: Runbook — перезапуск Hermes

## Статус: Active (runbook)

## Назначение

Пошаговая процедура безопасного рестарта Hermes на demo-production.
Покрывает два независимых процесса:

- `hermes-gateway` — long-running gateway под `systemd --user` (MCP, платформы).
- `hermes dashboard` — web-UI для владельца, запущен напрямую (orphan PID 1).

Использовать, когда:

- Подхватить новый MCP после правки `~/.hermes/config.yaml` (требование F14 из `PRD/DrawThings.md`).
- Gateway ушёл в `parked` / `failed` / `disconnected` (см. `~/.hermes/gateway_state.json`).
- Зависли платформы (Telegram, и т.д.) и `hermes gateway status` показывает ошибки.
- После обновления `~/.hermes/hermes-agent/` (uv sync, новая версия).

## Предусловия

- SSH-доступ к серверу под пользователем `ubuntu`.
- `~/.hermes/` на месте, `config.yaml` валиден.
- Текущая сессия **не** живёт критическими in-flight задачами через gateway (рестарт оборвёт активные MCP-вызовы, включая текущий чат с AI-агентом, если он сам — Hermes).
- Понятно, **что именно** рестартуем — gateway / dashboard / оба.

## Текущее состояние (на момент написания)

```
PID 615342  hermes-gateway   systemd --user (hermes-gateway.service)
PID 17986   hermes dashboard orphan (PPID=1), команда: hermes dashboard --host 10.6.0.5 ...
```

Hermes **не** в Docker — это user-mode systemd на хосте `openclaw-vcn` (Ubuntu, systemd PID 1).

## Процедура

### 1. Dry-run / диагностика (без side effects)

```bash
# Кто жив?
ps -o pid,ppid,user,etime,cmd -C python 2>/dev/null | grep -E "hermes|gateway" | grep -v grep

# Статус gateway через CLI
/usr/local/bin/hermes gateway status    # или: ~/.local/bin/hermes gateway status

# Статус systemd-unit
systemctl --user status hermes-gateway.service --no-pager

# Последние рестарты и текущее состояние
tail -20 ~/.hermes/gateway-starts.log
cat   ~/.hermes/gateway_state.json
cat   ~/.hermes/gateway.pid
```

Ожидаемый результат dry-run:

- Видны живые PID-ы gateway и dashboard.
- `gateway status` → `running` (или `stopped`, если уже упал — тогда шаг 2 пропускаем).
- В `gateway_state.json` поле `gateway_state: "running"`, `restart_requested: false`.

**Если уже `stopped` / `failed`** — переходим сразу к шагу 3 (старт без стопа).

### 2. Мягкий стоп gateway

```bash
systemctl --user stop hermes-gateway.service

# Подтверждение
systemctl --user is-active hermes-gateway.service   # должно вернуть "inactive"
pgrep -f "hermes_cli.main gateway run" || echo "OK: gateway process gone"
```

Альтернатива через CLI (если systemd-юнит не подхвачен):

```bash
hermes gateway stop
```

**Важно:** стоп НЕ трогает dashboard (это отдельный orphan-процесс) — владелец
продолжает видеть web-UI.

### 3. (Опционально) Стоп dashboard

Только если рестартуем и web-UI:

```bash
# Dashboard НЕ под systemd — kill по PID, найденному на шаге 1
DASH_PID=$(pgrep -f "hermes dashboard --host")
[ -n "$DASH_PID" ] && kill "$DASH_PID" && sleep 1
pgrep -f "hermes dashboard --host" || echo "OK: dashboard stopped"
```

Не делаем `kill -9` без необходимости — даём процессу корректно отвязаться от порта.

### 4. (Опционально) Подхват новой конфигурации

Если цель рестарта — подхватить изменения `~/.hermes/config.yaml` (новый MCP, токен,
лимит памяти) — проверить файл **до** старта:

```bash
# Снапшот для отката
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak.$(date -u +%FT%T)

# Валидация YAML + наличие нужной секции (например, для comic-studio MCP)
python3 -c "import yaml,sys; cfg=yaml.safe_load(open('/home/ubuntu/.hermes/config.yaml')); \
  print('mcp_servers keys:', list((cfg.get('mcp_servers') or {}).keys()))"
```

Ожидаемый результат: YAML парсится, нужный ключ (`comic-studio` / `draw-things` / …)
присутствует в `mcp_servers`.

### 5. Старт gateway

```bash
systemctl --user start hermes-gateway.service

# Подтверждение
systemctl --user status hermes-gateway.service --no-pager
sleep 2
cat ~/.hermes/gateway_state.json | python3 -m json.tool | head -20
```

Альтернатива: `hermes gateway start` (CLI сам дёргает systemd).

### 6. Старт dashboard (если стопили)

Запускаем **в фоне** тем же способом, каким был запущен изначально.
Текущая команда по `ps`:

```bash
nohup /home/ubuntu/.hermes/hermes-agent/venv/bin/hermes dashboard \
  --host 10.6.0.5 --insecure --no-open --skip-build \
  >> ~/.hermes/logs/dashboard.log 2>&1 &
disown
sleep 2
pgrep -f "hermes dashboard --host"    # должен вернуть новый PID
```

Если на сервере есть wrapper-скрипт (`~/bin/hermes-dashboard.sh` и т.п.) —
использовать его и зафиксировать команду здесь.

### 7. Верификация

```bash
# 7.1 Оба процесса живы
pgrep -af "hermes_cli.main gateway run"
pgrep -af "hermes dashboard --host"

# 7.2 Gateway отвечает
hermes gateway status

# 7.3 Свежий лог без критичных ошибок
tail -50 ~/.hermes/logs/agent.log | grep -iE "ERROR|FATAL" | tail -20
# Допустимы WARNING по parked MCP (норма при первом старте до reconnect).

# 7.4 Рестарт зафиксирован в логе рестартов
tail -3 ~/.hermes/gateway-starts.log    # последняя метка времени — свежая

# 7.5 Проверка подхвата MCP (если причина рестарта — новый MCP)
hermes mcp list    # если подкоманда существует; иначе:
grep -E "comic-studio|draw-things" ~/.hermes/logs/agent.log | tail -10
```

Ожидаемый результат: оба процесса в `running`, в `agent.log` видна успешная
инициализация MCP-серверов, в `gateway-starts.log` появилась свежая метка.

## Rollback

Если после рестарта gateway не поднимается или потерял MCP:

```bash
# Вернуть конфиг
cp ~/.hermes/config.yaml.bak.<timestamp> ~/.hermes/config.yaml

# Перезапустить
systemctl --user restart hermes-gateway.service

# Если юнит сам не стартует — запустить в foreground для диагностики
/home/ubuntu/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run
# (Ctrl-C для выхода после диагностики)
```

## Типичные отказы и реакции

| Симптом                                                       | Причина                                  | Реакция                                                                 |
|---------------------------------------------------------------|------------------------------------------|-------------------------------------------------------------------------|
| `gateway status` → `stopped`, юнит `inactive`                | Предыдущий крэш                          | Перейти к шагу 5 (старт без стопа).                                     |
| `agent.log`: `MCP server 'X' failed initial connection`       | MCP-скрипт не найден / не executable     | Проверить `command` / `args` в `~/.hermes/config.yaml` → рестарт.       |
| `gateway-starts.log` не пополняется после шага 5              | Юнит не подхвачен (нет `hermes-gateway.service`) | `hermes gateway install && systemctl --user start hermes-gateway.service`. |
| Dashboard не поднимается, порт занят | Прошлый процесс ещё держит порт | `lsof -iTCP:8501 -sTCP:LISTEN` → kill старого PID → повторить шаг 6. |
| После рестарта пропали сессии/kanban.db                       | Нормально (in-memory state)              | Не критично для прод, документировать в `summary/audit/`.              |

## Чего НЕ делать

- ❌ `kill -9` gateway без причины — теряем корректное состояние в `gateway_state.json`.
- ❌ Редактировать `~/.hermes/config.yaml` без бэкапа (шаг 4.1 обязателен).
- ❌ Запускать второй gateway параллельно (CLI: `hermes gateway run` в foreground) — будет конфликт портов / dual state.
- ❌ Трогать `gateway.pid` руками — это сгенерированный артефакт, Hermes его перезапишет.
- ❌ Рестартить во время активного рендера/публикации (cм. `data/logs/`) — оборвёт LLM/MiniMax вызовы.

## Связанные документы

- `PRD/DrawThings.md` §15 Phase 1 — требование F14 «перезапуск Hermes для подхвата MCP».
- `MCP_GUIDE.md` — где живут `mcp_servers` и как их регистрировать.
- `summary/audit/034_tg_bot_decommission.md` — почему Telegram-бот декомиссован в пользу Hermes MCP.
- `summary/audit/031_project-audit-and-ideas-2026-08-14.md` — Hermes-центричная архитектура.

## История изменений

- `2026-08-25` — создан по факту проверки окружения (`openclaw-vcn`, user-mode systemd, gateway PID 615342, dashboard PID 17986).