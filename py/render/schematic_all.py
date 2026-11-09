"""Hand-drawn schematic SVG panels — full dd6d0bbf comic, 8 panels, Ukrainian."""
from pathlib import Path
from xml.sax.saxutils import escape
import cairosvg

import sys
sys.path.insert(0, '/home/ubuntu/projects/comics')

from py.render.schematic_big import (
    _sketch_line, _sketch_rect, _sketch_arrow, _text,
    _icon_notion_page, _icon_folder, _icon_robot,
    COLORS
)


def _icon_plugin(x, y, size=140, color='#2D4A7A'):
    """Stacked rectangles — plugin = group of skills."""
    parts = []
    for i, dy in enumerate([0, 18, 36]):
        c = '#F4E5C2' if i % 2 == 0 else '#FFFFFF'
        parts.append(_sketch_rect(x + dy, y + dy, size - dy, size * 0.45, fill=c, stroke=color, stroke_width=2.5))
        # Inner label line
        parts.append(_sketch_line(x + dy + 15, y + dy + size * 0.22, x + dy + (size - dy) - 25, y + dy + size * 0.22, color, 1.5))
    return ''.join(parts)


def _icon_doc_with_check(x, y, size=140, color='#2D4A7A'):
    """Document with checkmark — example/правило/образец."""
    parts = [
        _sketch_rect(x, y, size * 0.85, size, fill='#FFFFFF', stroke=color, stroke_width=3),
    ]
    # Lines
    for i in range(4):
        ly = y + 35 + i * 18
        lw = size * 0.7 - (i * 8 if i == 3 else 0)
        parts.append(_sketch_line(x + 15, ly, x + 15 + lw, ly, color, 2, roughness=1.2))
    # Big green checkmark
    check_color = '#5A8C5A'
    cx = x + size * 0.55
    cy = y + size * 0.7
    parts.append(f'<path d="M {cx - 15} {cy} L {cx - 5} {cy + 10} L {cx + 18} {cy - 15}" stroke="{check_color}" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(parts)


def _icon_sync(x, y, size=140, color='#2D4A7A'):
    """Two arrows in circle — sync icon."""
    cx = x + size / 2
    cy = y + size / 2
    parts = []
    # Outer circle
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{size * 0.4}" fill="none" stroke="{color}" stroke-width="3"/>')
    # Two curved arrows (sync)
    parts.append(f'<path d="M {cx - size * 0.25} {cy - 5} A {size * 0.25} {size * 0.25} 0 0 1 {cx + size * 0.15} {cy - size * 0.2}" stroke="{color}" stroke-width="3" fill="none"/>')
    parts.append(f'<path d="M {cx + size * 0.25} {cy + 5} A {size * 0.25} {size * 0.25} 0 0 1 {cx - size * 0.15} {cy + size * 0.2}" stroke="{color}" stroke-width="3" fill="none"/>')
    # Arrowheads
    parts.append(_sketch_line(cx + size * 0.15, cy - size * 0.2, cx + size * 0.05, cy - size * 0.3, color, 3))
    parts.append(_sketch_line(cx + size * 0.15, cy - size * 0.2, cx + size * 0.25, cy - size * 0.25, color, 3))
    parts.append(_sketch_line(cx - size * 0.15, cy + size * 0.2, cx - size * 0.25, cy + size * 0.3, color, 3))
    parts.append(_sketch_line(cx - size * 0.15, cy + size * 0.2, cx - size * 0.05, cy + size * 0.25, color, 3))
    return ''.join(parts)


def _icon_warning(x, y, size=140, color='#B54A4A'):
    """Warning triangle with !."""
    cx = x + size / 2
    cy = y + size * 0.45
    r = size * 0.45
    parts = []
    # Triangle (approximation)
    parts.append(f'<path d="M {cx} {cy - r} L {cx + r * 0.95} {cy + r * 0.7} L {cx - r * 0.95} {cy + r * 0.7} Z" fill="#FFF4E0" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')
    # Exclamation
    parts.append(f'<rect x="{cx - 3}" y="{cy - r * 0.4}" width="6" height="{r * 0.7}" fill="{color}"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy + r * 0.45}" r="5" fill="{color}"/>')
    return ''.join(parts)


def _icon_database(x, y, size=140, color='#2D4A7A'):
    """Database cylinder icon."""
    cx = x + size / 2
    parts = []
    top_y = y + 10
    parts.append(f'<ellipse cx="{cx}" cy="{top_y}" rx="{size * 0.4}" ry="{size * 0.1}" fill="#FFFFFF" stroke="{color}" stroke-width="2.5"/>')
    parts.append(f'<rect x="{x + size * 0.1}" y="{top_y}" width="{size * 0.8}" height="{size * 0.55}" fill="#FFFFFF" stroke="{color}" stroke-width="2.5"/>')
    parts.append(f'<ellipse cx="{cx}" cy="{top_y + size * 0.55}" rx="{size * 0.4}" ry="{size * 0.1}" fill="#F0EBD8" stroke="{color}" stroke-width="2.5"/>')
    # Horizontal lines (data layers)
    for i in range(3):
        ly = top_y + size * 0.2 + i * size * 0.12
        parts.append(f'<path d="M {x + size * 0.1} {ly} Q {cx} {ly - 6} {x + size * 0.9} {ly}" stroke="{color}" stroke-width="1.5" fill="none"/>')
    return ''.join(parts)


def _icon_github(x, y, size=140, color='#2C3E50'):
    """GitHub octocat-style icon."""
    cx = x + size / 2
    cy = y + size / 2
    r = size * 0.35
    parts = []
    # Circle
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#FFFFFF" stroke="{color}" stroke-width="3"/>')
    # Cat ears (two triangles)
    parts.append(f'<path d="M {cx - r * 0.6} {cy - r * 0.85} L {cx - r * 0.2} {cy - r * 0.4} L {cx - r * 0.4} {cy - r * 0.7} Z" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
    parts.append(f'<path d="M {cx + r * 0.6} {cy - r * 0.85} L {cx + r * 0.2} {cy - r * 0.4} L {cx + r * 0.4} {cy - r * 0.7} Z" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
    # Eyes
    parts.append(f'<circle cx="{cx - r * 0.3}" cy="{cy - r * 0.1}" r="{r * 0.1}" fill="{color}"/>')
    parts.append(f'<circle cx="{cx + r * 0.3}" cy="{cy - r * 0.1}" r="{r * 0.1}" fill="{color}"/>')
    # Mouth (curved line)
    parts.append(f'<path d="M {cx - r * 0.25} {cy + r * 0.25} Q {cx} {cy + r * 0.4} {cx + r * 0.25} {cy + r * 0.25}" stroke="{color}" stroke-width="2" fill="none"/>')
    # Tentacle
    parts.append(f'<path d="M {cx - r * 0.4} {cy + r * 0.5} Q {cx - r * 0.6} {cy + r * 0.85} {cx - r * 0.2} {cy + r * 0.95}" stroke="{color}" stroke-width="2" fill="none"/>')
    parts.append(f'<path d="M {cx + r * 0.4} {cy + r * 0.5} Q {cx + r * 0.6} {cy + r * 0.85} {cx + r * 0.2} {cy + r * 0.95}" stroke="{color}" stroke-width="2" fill="none"/>')
    return ''.join(parts)


def render_panel(n, title, subtitle, caption_label, output_svg, output_png=None):
    """Render a panel with standard layout: title, central element, info bar, footer caption."""
    W, H = 1280, 720
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%">',
        f'<rect width="{W}" height="{H}" fill="{COLORS["paper"]}"/>',
    ]

    # Title — BIG
    parts.append(_text(W / 2, 70, title, size=36, color=COLORS['corporate_blue'], weight='bold'))
    if subtitle:
        parts.append(_text(W / 2, 110, subtitle, size=18, color=COLORS['ink']))

    # Specific composition per panel
    if n == 1:
        # Архітектура: page → folder → robot
        page_size = 140
        page_x = 80
        page_y = 270
        parts.append(_icon_notion_page(page_x, page_y, size=page_size, color=COLORS['corporate_blue']))
        parts.append(_text(page_x + page_size * 0.42, page_y + page_size + 35, 'NOTION', size=20, color=COLORS['corporate_blue'], weight='bold'))
        parts.append(_text(page_x + page_size * 0.42, page_y + page_size + 60, 'wiki-сторінка', size=15, color=COLORS['ink']))

        arrow_y = page_y + page_size / 2
        parts.append(_sketch_arrow(page_x + page_size + 30, arrow_y, page_x + page_size + 230, arrow_y,
                                    stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))
        parts.append(_text(page_x + page_size + 130, arrow_y - 25, 'API extract', size=18, color=COLORS['muted_gold'], weight='bold'))

        folder_size = 140
        folder_x = page_x + page_size + 260
        folder_y = 270
        parts.append(_icon_folder(folder_x, folder_y, size=folder_size, color=COLORS['muted_gold']))
        parts.append(_text(folder_x + folder_size / 2, folder_y + folder_size + 35, 'SKILL.ZIP', size=20, color=COLORS['muted_gold'], weight='bold'))
        parts.append(_text(folder_x + folder_size / 2, folder_y + folder_size + 60, 'код + таблиці', size=15, color=COLORS['ink']))

        parts.append(_sketch_arrow(folder_x + folder_size + 30, arrow_y, folder_x + folder_size + 230, arrow_y,
                                    stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))
        parts.append(_text(folder_x + folder_size + 130, arrow_y - 25, 'load skill', size=18, color=COLORS['muted_gold'], weight='bold'))

        robot_size = 140
        robot_x = folder_x + folder_size + 260
        robot_y = 240
        parts.append(_icon_robot(robot_x, robot_y, size=robot_size, color=COLORS['corporate_blue']))
        parts.append(_text(robot_x + robot_size / 2, robot_y + robot_size + 50, 'AI AGENT', size=20, color=COLORS['corporate_blue'], weight='bold'))
        parts.append(_text(robot_x + robot_size / 2, robot_y + robot_size + 75, 'Claude · ChatGPT · Grok', size=14, color=COLORS['ink']))

    elif n == 2:
        # Упаковка: stacked layers with labels
        layer_size = 140
        cx = W / 2 - 70
        labels = [
            ('ІНСТРУКЦІЯ', 'SKILL.md'),
            ('КОД', 'Python · JSON'),
            ('ДОВІДНИКИ', 'docs.pdf'),
            ('ТАБЛИЦІ', 'data.csv'),
        ]
        for i, (lbl, sub) in enumerate(labels):
            ly = 200 + i * 90
            color = COLORS['corporate_blue'] if i % 2 == 0 else COLORS['muted_gold']
            parts.append(_sketch_rect(cx, ly, layer_size * 1.4, 70, fill='#FAF6E8', stroke=color, stroke_width=3))
            parts.append(_text(cx + layer_size * 0.7, ly + 32, lbl, size=20, color=color, weight='bold'))
            parts.append(_text(cx + layer_size * 1.8, ly + 38, sub, size=16, color=COLORS['ink']))

        # Side note
        parts.append(_text(cx + layer_size * 1.7, 580, '1 навичка = N файлів', size=20, color=COLORS['muted_gold'], weight='bold', anchor='middle'))

    elif n == 3:
        # Специфікація: stack of cards aligned to spec
        cards = [
            ('spec', 'Agent Skills'),
            ('folder', 'структура'),
            ('API', 'ендпоінти'),
        ]
        cx = W / 2
        for i, (lbl, sub) in enumerate(cards):
            cy = 220 + i * 90
            color = COLORS['corporate_blue']
            parts.append(_sketch_rect(cx - 200, cy, 400, 70, fill='#FFFFFF', stroke=color, stroke_width=3))
            parts.append(_text(cx, cy + 30, f'{lbl.upper()} · {sub}', size=22, color=color, weight='bold'))
            # Alignment markers
            parts.append(_sketch_line(cx - 230, cy + 35, cx - 200, cy + 35, COLORS['muted_gold'], 2))
            parts.append(_sketch_line(cx + 200, cy + 35, cx + 230, cy + 35, COLORS['muted_gold'], 2))

        # Bottom: checkmark + standardized label
        parts.append(_text(cx, 580, '✓ стандартизовано', size=24, color='#5A8C5A', weight='bold'))

    elif n == 4:
        # Приклад: folder with 3 items (rules, template, data) → skill
        cx = W / 2 - 80
        folder_x = cx - 200
        folder_y = 240
        items = [
            ('ПРАВИЛА', 'rules.md'),
            ('ЗРАЗОК', 'template.docx'),
            ('ДАНІ', 'data.csv'),
        ]
        parts.append(_icon_folder(folder_x, folder_y, size=180, color=COLORS['muted_gold']))
        parts.append(_text(folder_x + 90, folder_y + 230, 'папка навички', size=16, color=COLORS['ink']))
        # Items inside
        for i, (lbl, _) in enumerate(items):
            iy = folder_y + 50 + i * 35
            parts.append(_text(folder_x + 95, iy, lbl, size=18, color=COLORS['corporate_blue'], weight='bold', anchor='start'))

        # Arrow → ready skill
        parts.append(_sketch_arrow(folder_x + 220, folder_y + 90, folder_x + 380, folder_y + 90,
                                    stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))
        parts.append(_text(folder_x + 300, folder_y + 70, 'готовий навик', size=16, color=COLORS['muted_gold'], weight='bold'))

        # Result: skill icon (folder with checkmark)
        parts.append(_sketch_rect(folder_x + 400, folder_y + 30, 160, 130, fill='#FAF6E8', stroke=COLORS['corporate_blue'], stroke_width=3))
        parts.append(_text(folder_x + 480, folder_y + 80, 'SKILL', size=22, color=COLORS['corporate_blue'], weight='bold'))
        parts.append(f'<path d="M {folder_x + 450} {folder_y + 130} L {folder_x + 470} {folder_y + 150} L {folder_x + 510} {folder_y + 110}" stroke="#5A8C5A" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')

        parts.append(_text(W / 2, 590, 'Приклад: підготовка комерційної пропозиції', size=18, color=COLORS['ink']))

    elif n == 5:
        # GitHub sync: notion → github → agent
        items = [
            (_icon_notion_page, 'Notion', 'редагування'),
            (_icon_github, 'GitHub', 'доставка'),
            (_icon_robot, 'Agent', 'виконання'),
        ]
        gap = 380
        start_x = 80
        for i, (icon_fn, lbl, sub) in enumerate(items):
            x = start_x + i * gap
            color = COLORS['corporate_blue'] if i != 1 else '#2C3E50'
            parts.append(icon_fn(x, 280, size=140, color=color))
            parts.append(_text(x + 70, 460, lbl, size=22, color=color, weight='bold'))
            parts.append(_text(x + 70, 485, sub, size=14, color=COLORS['ink']))

            # Arrow
            if i < 2:
                parts.append(_sketch_arrow(x + 160, 350, x + gap - 30, 350,
                                            stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))

    elif n == 6:
        # Чесне попередження: two folders with timestamps, broken sync arrow
        cy = 350
        # Folder 1
        parts.append(_icon_folder(180, cy, size=140, color=COLORS['muted_gold']))
        parts.append(_text(250, cy + 195, '09:00', size=20, color=COLORS['ink'], weight='bold'))
        parts.append(_text(250, cy + 220, 'версія 1', size=14, color=COLORS['ink']))

        # Folder 2 (newer)
        parts.append(_icon_folder(840, cy, size=140, color=COLORS['muted_gold']))
        parts.append(_text(910, cy + 195, '11:00', size=20, color=COLORS['ink'], weight='bold'))
        parts.append(_text(910, cy + 220, 'версія 2', size=14, color=COLORS['ink']))

        # Broken sync arrow between
        parts.append(_sketch_line(380, cy + 70, 780, cy + 70, COLORS['soft_red'], 4, roughness=3))
        parts.append(_sketch_line(780, cy + 70, 770, cy + 50, COLORS['soft_red'], 4))
        parts.append(_sketch_line(780, cy + 70, 790, cy + 85, COLORS['soft_red'], 4))
        parts.append(_sketch_line(380, cy + 70, 390, cy + 50, COLORS['soft_red'], 4))
        parts.append(_sketch_line(380, cy + 70, 370, cy + 85, COLORS['soft_red'], 4))
        # Dashed line
        parts.append('<line x1="480" y1="280" x2="680" y2="280" stroke="#B54A4A" stroke-width="3" stroke-dasharray="12,8"/>')
        parts.append(_text(580, 260, 'синхронізація?', size=18, color=COLORS['soft_red'], weight='bold'))

        parts.append(_text(W / 2, 590, 'Зміни не доходять автоматично', size=20, color=COLORS['ink'], weight='bold'))

    elif n == 7:
        # Практичний сенс: 1 person → 3 agents
        # Person silhouette
        px = 200
        cy_body_top = 380
        parts.append(f'<circle cx="{px + 70}" cy="320" r="40" fill="#FFFFFF" stroke="{COLORS["ink"]}" stroke-width="3"/>')
        parts.append(f'<path d="M {px + 30} 480 Q {px + 70} {cy_body_top} {px + 110} 480" stroke="{COLORS["ink"]}" stroke-width="3" fill="none"/>')
        parts.append(_text(px + 70, 530, 'людина', size=20, color=COLORS['ink'], weight='bold'))
        parts.append(_text(px + 70, 555, 'один комплект', size=14, color=COLORS['muted_gold']))

        # Arrow
        parts.append(_sketch_arrow(px + 130, 400, 480, 400,
                                    stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))
        parts.append(_text(340, 380, 'передати', size=18, color=COLORS['muted_gold'], weight='bold'))

        # 3 agents
        agents = [
            ('Claude', '#2D4A7A'),
            ('ChatGPT', '#10A37F'),
            ('Grok', '#1E1E1E'),
        ]
        for i, (name, col) in enumerate(agents):
            ax = 540 + i * 220
            parts.append(_icon_robot(ax, 280, size=120, color=col))
            parts.append(_text(ax + 60, 430, name, size=18, color=col, weight='bold'))

        parts.append(_text(W / 2, 580, 'Передавати комплект різним агентам — просто.', size=18, color=COLORS['ink']))
        parts.append(_text(W / 2, 605, 'Результат — перевіряти на задачі.', size=18, color=COLORS['ink']))

    elif n == 8:
        # Підсумок: 3 layers Notion → Skill package → AI agent
        # Layout: title, subtitle (top), 3 layers stacked vertically, info bar, caption
        # Vertical budget: title y=70, subtitle y=110, layers 180-560, info bar 580-630, caption 680
        layers = [
            (_icon_notion_page, 'Notion wiki', 'знання команди', 180, COLORS['corporate_blue']),
            ('box', 'Skill package', 'SKILL.md + файли', 320, COLORS['muted_gold']),
            (_icon_robot, 'AI Agent', 'застосування', 460, COLORS['corporate_blue']),
        ]
        cx = W / 2
        for i, (icon_fn, lbl, sub, ly, color) in enumerate(layers):
            if icon_fn == 'box':
                # Package box
                parts.append(_sketch_rect(cx - 100, ly, 200, 90, fill='#F4E5C2', stroke=color, stroke_width=3))
                parts.append(_text(cx, ly + 34, lbl, size=20, color=color, weight='bold'))
                parts.append(_text(cx, ly + 60, sub, size=13, color=COLORS['ink']))
            else:
                parts.append(icon_fn(cx - 60, ly, size=120, color=color))
                parts.append(_text(cx, ly + 150, lbl, size=20, color=color, weight='bold'))
                parts.append(_text(cx, ly + 172, sub, size=13, color=COLORS['ink']))

            # Vertical dotted arrow to next
            if i < 2:
                ay = ly + 100 if icon_fn == 'box' else ly + 125
                parts.append(f'<line x1="{cx}" y1="{ay}" x2="{cx}" y2="{ay + 18}" stroke="{COLORS["muted_gold"]}" stroke-width="3" stroke-dasharray="6,4"/>')
                parts.append(f'<path d="M {cx - 5} {ay + 16} L {cx} {ay + 22} L {cx + 5} {ay + 16}" stroke="{COLORS["muted_gold"]}" stroke-width="3" fill="none"/>')

        # Subtitle at y=140 (below title, above first layer at y=180)
        parts.append(_text(W / 2, 140, 'Від знання — до агента. Через файл.', size=20, color=COLORS['muted_gold'], weight='bold'))

    # Bottom info bar — positioned at y=580 (above caption at y=685)
    bar_y = H - 130
    parts.append(_sketch_rect(60, bar_y, W - 120, 50, fill='#FAF6E8', stroke=COLORS['corporate_blue'], stroke_width=2))
    parts.append(_text(W / 2, bar_y + 32, '17 вересня 2026 · Notion Skills API', size=18, color=COLORS['corporate_blue'], weight='bold'))

    # Footer caption — positioned safely at y=H-30 (below info bar with margin)
    parts.append(_text(W / 2, H - 30, caption_label, size=14, color=COLORS['muted_gold'], weight='bold'))

    parts.append('</svg>')

    Path(output_svg).write_text('\n'.join(parts), encoding='utf-8')
    if output_png:
        cairosvg.svg2png(url=str(output_svg), write_to=str(output_png), output_width=W, output_height=H)
    return Path(output_svg)


if __name__ == '__main__':
    out_dir = Path('/home/ubuntu/projects/comics/data/comics/dd6d0bbf/schematic')

    panels = [
        (1, 'АРХІТЕКТУРА', 'Notion Skills API', 'I · АРХІТЕКТУРА'),
        (2, 'УПАКОВКА', 'Навичка = інструкція + файли', 'II · УПАКОВКА'),
        (3, 'СПЕЦИФІКАЦІЯ', 'Відповідає стандарту Agent Skills', 'III · СПЕЦИФІКАЦІЯ'),
        (4, 'ПРИКЛАД', 'Правила + зразок + дані = навичка', 'IV · ПРИКЛАД'),
        (5, 'GITHUB SYNC', 'Notion → GitHub → Agent', 'V · GITHUB SYNC'),
        (6, 'ЧЕСНЕ ПОПЕРЕДЖЕННЯ', 'Зміни не доходять автоматично', 'VI · ЧЕСНЕ ПОПЕРЕДЖЕННЯ'),
        (7, 'ПРАКТИЧНИЙ СЕНС', 'Один комплект → різні агенти', 'VII · ПРАКТИЧНИЙ СЕНС'),
        (8, 'ПІДСУМОК', '', 'VIII · ПІДСУМОК'),  # subtitle всередині panel 8
    ]

    for n, title, subtitle, caption in panels:
        svg = out_dir / f'panel_{n}.svg'
        png = out_dir / f'panel_{n}.png'
        render_panel(n, title, subtitle, caption, svg, png)
        print(f'Panel {n}: {png.stat().st_size:,} bytes')

    print()
    print('All 8 panels rendered.')
