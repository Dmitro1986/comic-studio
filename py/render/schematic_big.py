"""Hand-drawn schematic SVG panel for comic studio — BIG version for mobile.

Mobile-optimized: larger icons (140px), larger fonts (20-32px), more spacing.
"""
from pathlib import Path
from xml.sax.saxutils import escape


# Memo color palette
COLORS = {
    'paper': '#F5F0E1',
    'ink': '#2C3E50',
    'corporate_blue': '#2D4A7A',
    'muted_gold': '#B8975C',
    'soft_red': '#B54A4A',
    'bg': '#FAF6E8',
}


def _sketch_line(x1, y1, x2, y2, stroke='#2C3E50', stroke_width=2, roughness=1.5):
    """Generate slightly wavy SVG path between two points (hand-drawn effect)."""
    import random
    random.seed(int(abs((x1 * 7 + y1 * 13 + x2 * 17 + y2 * 19)) % 100))

    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5

    n = max(2, int(length / 30))

    points = [(x1, y1)]
    for i in range(1, n):
        t = i / n
        mx = x1 + dx * t + random.uniform(-roughness, roughness)
        my = y1 + dy * t + random.uniform(-roughness, roughness)
        points.append((mx, my))
    points.append((x2, y2))

    path_d = f'M {points[0][0]:.1f} {points[0][1]:.1f}'
    for px, py in points[1:]:
        path_d += f' L {px:.1f} {py:.1f}'

    return f'<path d="{path_d}" stroke="{stroke}" stroke-width="{stroke_width}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'


def _sketch_rect(x, y, w, h, fill='#FAF6E8', stroke='#2C3E50', stroke_width=2, radius=4):
    parts = [
        _sketch_line(x + radius, y, x + w - radius, y, stroke, stroke_width),
        _sketch_line(x + w - radius, y, x + w, y + radius, stroke, stroke_width),
        _sketch_line(x + w, y + radius, x + w, y + h - radius, stroke, stroke_width),
        _sketch_line(x + w, y + h - radius, x + w - radius, y + h, stroke, stroke_width),
        _sketch_line(x + w - radius, y + h, x + radius, y + h, stroke, stroke_width),
        _sketch_line(x + radius, y + h, x, y + h - radius, stroke, stroke_width),
        _sketch_line(x, y + h - radius, x, y + radius, stroke, stroke_width),
        _sketch_line(x, y + radius, x + radius, y, stroke, stroke_width),
    ]
    fill_rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"/>'
    return fill_rect + ''.join(parts)


def _sketch_arrow(x1, y1, x2, y2, stroke='#2C3E50', stroke_width=2.5, head_size=10):
    import math
    main = _sketch_line(x1, y1, x2, y2, stroke, stroke_width)

    angle = math.atan2(y2 - y1, x2 - x1)
    ah1_x = x2 - head_size * math.cos(angle - 0.5)
    ah1_y = y2 - head_size * math.sin(angle - 0.5)
    ah2_x = x2 - head_size * math.cos(angle + 0.5)
    ah2_y = y2 - head_size * math.sin(angle + 0.5)

    head = (
        _sketch_line(x2, y2, ah1_x, ah1_y, stroke, stroke_width) +
        _sketch_line(x2, y2, ah2_x, ah2_y, stroke, stroke_width)
    )
    return main + head


def _text(x, y, text, size=14, color='#2C3E50', anchor='middle', weight='normal', style=''):
    safe = escape(str(text))
    style_attr = f' style="{style}"' if style else ''
    return f'<text x="{x}" y="{y}" font-family="Caveat, Comic Sans MS, cursive" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}"{style_attr}>{safe}</text>'


def _icon_notion_page(x, y, size=140, color='#2D4A7A'):
    """Notion document icon — BIG."""
    w = size * 0.85
    h = size
    parts = [
        _sketch_rect(x, y, w, h, fill='#FFFFFF', stroke=color, stroke_width=3),
        _sketch_line(x + w - 20, y, x + w - 20, y + 20, color, 3),
        _sketch_line(x + w - 20, y + 20, x + w, y + 20, color, 3),
    ]
    for i in range(6):
        ly = y + 35 + i * 16
        lw = w - 25 - (i * 6 if i == 5 else 0)
        parts.append(_sketch_line(x + 15, ly, x + 15 + lw, ly, color, 2.5, roughness=1.2))
    return ''.join(parts)


def _icon_folder(x, y, size=140, color='#B8975C'):
    """Folder icon — BIG."""
    parts = [
        _sketch_rect(x, y + 20, size, size - 20, fill='#F4E5C2', stroke=color, stroke_width=3),
        _sketch_line(x + 15, y + 20, x + size * 0.4, y + 20, color, 3),
        _sketch_line(x + size * 0.4, y + 20, x + size * 0.4, y + 10, color, 3),
        _sketch_line(x + size * 0.4, y + 10, x + size * 0.55, y + 10, color, 3),
        _sketch_line(x + size * 0.55, y + 10, x + size * 0.6, y + 20, color, 3),
    ]
    # Folder content lines
    for i in range(3):
        ly = y + 50 + i * 18
        lw = size - 30 - (i * 10 if i == 2 else 0)
        parts.append(_sketch_line(x + 18, ly, x + 18 + lw, ly, color, 2, roughness=1.0))
    return ''.join(parts)


def _icon_robot(x, y, size=140, color='#2D4A7A'):
    """Robot/agent avatar icon — BIG."""
    cx = x + size / 2
    head_y = y + 15
    parts = []
    # Antenna
    parts.append(_sketch_line(cx, y, cx, head_y - 6, color, 3))
    parts.append(f'<circle cx="{cx}" cy="{y - 4}" r="5" fill="{color}"/>')
    # Head
    head_r = size * 0.28
    head_cy = head_y + head_r
    parts.append(f'<circle cx="{cx}" cy="{head_cy}" r="{head_r}" fill="#FFFFFF" stroke="{color}" stroke-width="3"/>')
    # Eyes
    parts.append(f'<circle cx="{cx - 10}" cy="{head_cy - 4}" r="5" fill="{color}"/>')
    parts.append(f'<circle cx="{cx + 10}" cy="{head_cy - 4}" r="5" fill="{color}"/>')
    # Smile
    parts.append(f'<path d="M {cx - 10} {head_cy + 12} Q {cx} {head_cy + 20} {cx + 10} {head_cy + 12}" stroke="{color}" stroke-width="3" fill="none"/>')
    # Body
    body_y = head_cy + head_r + 10
    body_w = size * 0.55
    body_h = size * 0.32
    parts.append(_sketch_rect(cx - body_w / 2, body_y, body_w, body_h, fill='#FFFFFF', stroke=color, stroke_width=3))
    # Body control panel (3 dots)
    for i, dx in enumerate([-15, 0, 15]):
        parts.append(f'<circle cx="{cx + dx}" cy="{body_y + body_h * 0.5}" r="3.5" fill="{color}"/>')
    return ''.join(parts)


def render_panel_1_schematic_big(output_path):
    """Render Panel 1 of dd6d0bbf: Notion page → folder → robot. BIG for mobile."""
    W, H = 1280, 720

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%">',
        f'<rect width="{W}" height="{H}" fill="{COLORS["paper"]}"/>',
    ]

    # Title — BIG (Ukrainian)
    svg_parts.append(_text(W / 2, 70, 'АРХІТЕКТУРА', size=36, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(W / 2, 105, 'Notion Skills API', size=22, color=COLORS['ink']))
    svg_parts.append(_text(W / 2, 135, 'Знання редагуються в Notion → доставляються агенту', size=18, color=COLORS['muted_gold']))

    # Element 1: Notion page icon (left, BIG)
    page_size = 140
    page_x = 80
    page_y = 280
    svg_parts.append(_icon_notion_page(page_x, page_y, size=page_size, color=COLORS['corporate_blue']))
    svg_parts.append(_text(page_x + page_size * 0.42, page_y + page_size + 35, 'NOTION', size=20, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(page_x + page_size * 0.42, page_y + page_size + 60, 'wiki-сторінка', size=15, color=COLORS['ink']))

    # Arrow 1: page → folder (THICKER, with label above)
    arrow_y = page_y + page_size / 2
    svg_parts.append(_sketch_arrow(page_x + page_size + 30, arrow_y, page_x + page_size + 230, arrow_y,
                                    stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))
    svg_parts.append(_text(page_x + page_size + 130, arrow_y - 25, 'API extract', size=18, color=COLORS['muted_gold'], weight='bold'))

    # Element 2: Folder icon (center, BIG)
    folder_size = 140
    folder_x = page_x + page_size + 260
    folder_y = 280
    svg_parts.append(_icon_folder(folder_x, folder_y, size=folder_size, color=COLORS['muted_gold']))
    svg_parts.append(_text(folder_x + folder_size / 2, folder_y + folder_size + 35, 'SKILL.ZIP', size=20, color=COLORS['muted_gold'], weight='bold'))
    svg_parts.append(_text(folder_x + folder_size / 2, folder_y + folder_size + 60, 'код + таблиці', size=15, color=COLORS['ink']))

    # Arrow 2: folder → robot
    svg_parts.append(_sketch_arrow(folder_x + folder_size + 30, arrow_y, folder_x + folder_size + 230, arrow_y,
                                    stroke=COLORS['muted_gold'], stroke_width=4, head_size=18))
    svg_parts.append(_text(folder_x + folder_size + 130, arrow_y - 25, 'load skill', size=18, color=COLORS['muted_gold'], weight='bold'))

    # Element 3: Robot avatar (right, BIG)
    robot_size = 140
    robot_x = folder_x + folder_size + 260
    robot_y = 250
    svg_parts.append(_icon_robot(robot_x, robot_y, size=robot_size, color=COLORS['corporate_blue']))
    svg_parts.append(_text(robot_x + robot_size / 2, robot_y + robot_size + 50, 'AI AGENT', size=20, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(robot_x + robot_size / 2, robot_y + robot_size + 75, 'Claude · ChatGPT · Grok', size=14, color=COLORS['ink']))

    # Bottom info bar — BIGGER
    bar_y = H - 90
    svg_parts.append(_sketch_rect(60, bar_y, W - 120, 60, fill='#FAF6E8', stroke=COLORS['corporate_blue'], stroke_width=2.5))
    svg_parts.append(_text(W / 2, bar_y + 28, '17 вересня 2026 · Notion Skills API', size=18, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(W / 2, bar_y + 50, 'Стандартизований формат · Agent Skills spec', size=14, color=COLORS['ink']))

    # Footer caption
    svg_parts.append(_text(W / 2, H - 18, 'I · АРХІТЕКТУРА', size=14, color=COLORS['muted_gold'], weight='bold'))

    svg_parts.append('</svg>')

    Path(output_path).write_text('\n'.join(svg_parts), encoding='utf-8')
    return Path(output_path)


if __name__ == '__main__':
    out = '/home/ubuntu/projects/comics/data/comics/dd6d0bbf/schematic_panel_1_big.svg'
    p = render_panel_1_schematic_big(out)
    print(f'Written: {p}')
    print(f'Size: {p.stat().st_size:,} bytes')
