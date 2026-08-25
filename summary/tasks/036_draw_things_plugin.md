# Задачи: Draw Things plugin (Phase 1 + Phase 2)

## Статус: ✅ Done

| ID | Задача | Статус |
|---|---|---|
| 1 | `mcp-server/draw-things/index.js` — stdio MCP server с tools `generate_image` + `get_options` | ✅ Done |
| 2 | Регистрация в `~/.hermes/config.yaml` + restart gateway | ✅ Done |
| 3 | `py/render/draw_things_client.py` — Python клиент с кэшем и negative prompt | ✅ Done |
| 4 | `scripts/render_approved.py` — флаг `--provider {minimax,draw-things}` + sequential для DT | ✅ Done |
| 5 | End-to-end тест: тестовый сценарий → 3 панели → собранный комикс через Draw Things | ✅ Done |
| 6 | Vision-проверка результата: S.T.A.L.K.E.R. палитра, документальный стиль | ✅ Done |

## Артефакты
- `mcp-server/draw-things/index.js` (305 строк)
- `py/render/draw_things_client.py` (170 строк)
- `prd/DrawThings.md` (21 KB)
- `data/comics/drawtest3acd.png` (4.8 MB, 2602×1449)
- Аудит: `summary/audit/036_draw_things_plugin.md`
