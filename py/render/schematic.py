"""Hand-drawn schematic SVG panel for comic studio.

Generates whiteboard-style technical diagrams with:
- Sketchy borders (slightly irregular lines)
- Hand-drawn boxes (rectangles, rounded)
- Arrows (curved, with arrowhead)
- Inline icons (page, folder, robot)
- Sans-serif labels
- Memo color palette (cream paper, corporate blue, muted gold)
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

    # Number of segments
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
    """Sketchy rectangle with hand-drawn border."""
    # Top
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
    """Sketchy arrow with arrowhead."""
    main = _sketch_line(x1, y1, x2, y2, stroke, stroke_width)

    # Arrowhead (simple V-shape)
    import math
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


def _icon_notion_page(x, y, size=50, color='#2D4A7A'):
    """Simple Notion-like document icon."""
    w = size * 0.85
    h = size
    parts = [
        _sketch_rect(x, y, w, h, fill='#FFFFFF', stroke=color, stroke_width=2),
    ]
    # Page corner fold
    parts.append(_sketch_line(x + w - 12, y, x + w - 12, y + 12, color, 2))
    parts.append(_sketch_line(x + w - 12, y + 12, x + w, y + 12, color, 2))
    # Lines inside (text representation)
    for i in range(4):
        ly = y + 25 + i * 12
        lw = w - 20 - (i * 4 if i == 3 else 0)
        parts.append(_sketch_line(x + 10, ly, x + 10 + lw, ly, color, 1.5, roughness=0.8))
    return ''.join(parts)


def _icon_folder(x, y, size=50, color='#B8975C'):
    """Folder icon."""
    parts = [
        _sketch_rect(x, y + 12, size, size - 12, fill='#F4E5C2', stroke=color, stroke_width=2),
        _sketch_line(x + 8, y + 12, x + size * 0.4, y + 12, color, 2),
        _sketch_line(x + size * 0.4, y + 12, x + size * 0.4, y + 6, color, 2),
        _sketch_line(x + size * 0.4, y + 6, x + size * 0.55, y + 6, color, 2),
        _sketch_line(x + size * 0.55, y + 6, x + size * 0.6, y + 12, color, 2),
    ]
    return ''.join(parts)


def _icon_robot(x, y, size=50, color='#2D4A7A'):
    """Robot/agent avatar icon."""
    cx = x + size / 2
    head_y = y + 8
    parts = []
    # Antenna
    parts.append(_sketch_line(cx, y, cx, head_y - 4, color, 2))
    parts.append(f'<circle cx="{cx}" cy="{y - 2}" r="3" fill="{color}"/>')
    # Head (round)
    parts.append(f'<circle cx="{cx}" cy="{head_y + size * 0.25}" r="{size * 0.25}" fill="#FFFFFF" stroke="{color}" stroke-width="2.5"/>')
    # Eyes
    parts.append(f'<circle cx="{cx - 6}" cy="{head_y + size * 0.22}" r="2.5" fill="{color}"/>')
    parts.append(f'<circle cx="{cx + 6}" cy="{head_y + size * 0.22}" r="2.5" fill="{color}"/>')
    # Smile
    parts.append(f'<path d="M {cx - 6} {head_y + size * 0.32} Q {cx} {head_y + size * 0.38} {cx + 6} {head_y + size * 0.32}" stroke="{color}" stroke-width="2" fill="none"/>')
    # Body (rectangular)
    body_y = head_y + size * 0.55
    parts.append(_sketch_rect(cx - size * 0.25, body_y, size * 0.5, size * 0.35, fill='#FFFFFF', stroke=color, stroke_width=2))
    # Body control dot
    parts.append(f'<circle cx="{cx}" cy="{body_y + size * 0.17}" r="3" fill="{color}"/>')
    return ''.join(parts)


def render_panel_1_schematic(output_path):
    """Render Panel 1 of dd6d0bbf: Notion page → folder → robot."""
    W, H = 1280, 720

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%">',
        f'<rect width="{W}" height="{H}" fill="{COLORS["paper"]}"/>',
    ]

    # Title at top
    svg_parts.append(_text(W / 2, 50, 'Архитектура · Notion Skills API', size=24, color=COLORS['ink'], weight='bold'))
    svg_parts.append(_text(W / 2, 80, 'Знания редактируются в Notion · Доставляются агенту', size=16, color=COLORS['ink']))

    # Element 1: Notion page icon (left)
    page_x, page_y = 120, 280
    svg_parts.append(_icon_notion_page(page_x, page_y, size=80))
    svg_parts.append(_text(page_x + 34, page_y + 110, 'NOTION', size=12, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(page_x + 34, page_y + 130, 'wiki page', size=10, color=COLORS['ink']))

    # Arrow 1: page → folder
    svg_parts.append(_sketch_arrow(page_x + 100, page_y + 40, page_x + 280, page_y + 40,
                                    stroke=COLORS['muted_gold'], stroke_width=3))
    svg_parts.append(_text(page_x + 190, page_y + 25, 'API extract', size=12, color=COLORS['muted_gold']))

    # Element 2: Folder icon (center)
    folder_x, folder_y = 520, 270
    svg_parts.append(_icon_folder(folder_x, folder_y, size=80))
    svg_parts.append(_text(folder_x + 40, folder_y + 110, 'SKILL.ZIP', size=12, color=COLORS['muted_gold'], weight='bold'))
    svg_parts.append(_text(folder_x + 40, folder_y + 130, 'code + docs + tables', size=10, color=COLORS['ink']))

    # Arrow 2: folder → robot
    svg_parts.append(_sketch_arrow(folder_x + 100, folder_y + 40, folder_x + 280, folder_y + 40,
                                    stroke=COLORS['muted_gold'], stroke_width=3))
    svg_parts.append(_text(folder_x + 190, folder_y + 25, 'load skill', size=12, color=COLORS['muted_gold']))

    # Element 3: Robot avatar (right)
    robot_x, robot_y = 940, 250
    svg_parts.append(_icon_robot(robot_x, robot_y, size=100))
    svg_parts.append(_text(robot_x + 50, robot_y + 130, 'AI AGENT', size=12, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(robot_x + 50, robot_y + 150, 'Claude · ChatGPT · Grok', size=10, color=COLORS['ink']))

    # Bottom info bar
    bar_y = H - 110
    svg_parts.append(_sketch_rect(80, bar_y, W - 160, 70, fill='#FAF6E8', stroke=COLORS['corporate_blue'], stroke_width=1.5))
    svg_parts.append(_text(W / 2, bar_y + 28, '17 сентября 2026 · Notion Skills API',
                          size=14, color=COLORS['corporate_blue'], weight='bold'))
    svg_parts.append(_text(W / 2, bar_y + 50, 'Стандартизированный формат · Agent Skills spec',
                          size=12, color=COLORS['ink']))

    # Footer caption
    svg_parts.append(_text(W / 2, H - 20, 'I · АРХИТЕКТУРА', size=11, color=COLORS['muted_gold'], weight='bold'))

    svg_parts.append('</svg>')

    Path(output_path).write_text('\n'.join(svg_parts), encoding='utf-8')
    return Path(output_path)


if __name__ == '__main__':
    out = '/home/ubuntu/projects/comics/data/comics/dd6d0bbf/schematic_panel_1.svg'
    p = render_panel_1_schematic(out)
    print(f'Written: {p}')
    print(f'Size: {p.stat().st_size:,} bytes')
