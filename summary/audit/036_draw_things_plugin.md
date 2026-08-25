# Аудит: Draw Things plugin (Phase 1 + Phase 2)

## Контекст
Подключить локальный Draw Things (SDXL) как опциональный провайдер изображений для Comic Studio, чтобы получить фотореализм, кастомные LoRA (STALKER_SDXL) и независимость от MiniMax.

## Что сделано

### Phase 1 — Hermes MCP plugin
- `mcp-server/draw-things/index.js` (305 строк, stdio JSON-RPC) с tools `generate_image` + `get_options`
- Симлинк `node_modules → ../node_modules` (переиспользование SDK от comic-server)
- `~/.hermes/config.yaml` — секция `mcp_servers.draw-things` с env `DRAW_THINGS_URL` и `DRAW_THINGS_TIMEOUT`
- Gateway перезапущен 17:25, `hermes mcp list` показывает `draw-things ✓ enabled`

### Phase 2 — Comic Studio provider
- `py/render/draw_things_client.py` (170 строк) с `generate_image()`, кэш, negative prompt без крови/текста
- `scripts/render_approved.py` — добавлен `--provider {minimax,draw-things}`, sequential rendering для DT (single-job backend), параллельный для MiniMax
- Default LoRA `STALKER_SDXL` через `DRAW_THINGS_DEFAULT_LORA` env

### Тестовая генерация
- `data/scenarios/approved/drawtest3acd.json` — тестовый сценарий про Слов'янськ 2014
- Все 3 панели отрендерены через Draw Things (87 + 168 + 84 сек = 5 мин total)
- Комикс собран: `data/comics/drawtest3acd.png` (4.8 MB, 2602×1449)
- Vision-проверка подтвердила: документальный реализм, S.T.A.L.K.E.R. палитра, memo-стикеры

## Статус
✅ Phase 1 + Phase 2 PRD выполнены. Комикс рендерится через Draw Things end-to-end.
