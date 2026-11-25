#!/usr/bin/env python3
"""Animated concept-graphic scenes rendered with Pillow + ffmpeg.

Layout follows an 8px baseline grid with fixed margins and box sizes so the
frames read as engineering diagrams rather than free-form slides.
"""

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 30
MARGIN = 64
GRID = 8
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
ACCENT = (167, 139, 250)   # violet
ACCENT2 = (34, 211, 238)  # cyan


def font(path, size):
    return ImageFont.truetype(path, size)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def snap(value):
    return int(round(value / GRID) * GRID)


def corner_brackets(draw, box, color, alpha=200, size=26, width=2):
    x0, y0, x1, y1 = box
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([(cx, cy), (cx + dx * size, cy)], fill=color + (alpha,), width=width)
        draw.line([(cx, cy), (cx, cy + dy * size)], fill=color + (alpha,), width=width)


def hud_ticks(draw, color, alpha=90):
    for y in range(160, H - 120, 48):
        draw.line([(28, y), (40, y)], fill=color + (alpha,), width=2)
        draw.line([(W - 40, y), (W - 28, y)], fill=color + (alpha,), width=2)
    for x in range(120, W - 100, 64):
        draw.line([(x, 46), (x, 56)], fill=color + (alpha,), width=2)


def scanlines(draw, top, bottom, alpha=14):
    for y in range(top, bottom, 6):
        draw.line([(MARGIN - 24, y), (W - MARGIN + 24, y)], fill=(255, 255, 255, alpha), width=1)


def background(draw):
    draw.rectangle([0, 0, W, H], fill='#080414')
    for x in range(0, W + GRID, GRID * 8):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 7), width=1)
    for y in range(0, H + GRID, GRID * 8):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 7), width=1)
    draw.ellipse([W * 0.10, -300, W * 0.90, 420], fill=ACCENT + (16,))
    draw.ellipse([-240, H - 560, 400, H + 120], fill=(34, 211, 238, 8))
    for radius in (150, 240, 330):
        draw.ellipse([W / 2 - radius, 320 - radius, W / 2 + radius, 320 + radius],
                     outline=ACCENT + (10,), width=1)


def glass_panel(draw, box, alpha=22, brackets=True):
    x0, y0, x1, y1 = [snap(v) for v in box]
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=(255, 255, 255, alpha))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18, outline=ACCENT + (70,), width=1)
    if brackets:
        corner_brackets(draw, (x0, y0, x1, y1), ACCENT2, alpha=170, size=22, width=2)


def wrap_text(text, size, max_width, bold=False):
    f = font(FONT_BOLD if bold else FONT_REG, size)
    lines, current = [], ''
    for char in text:
        candidate = current + char
        if f.getlength(candidate) > max_width and current:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_brain(draw, cx, cy, scale, alpha):
    a = int(210 * alpha)
    r = scale * 0.42
    for angle in range(0, 360, 60):
        rad = math.radians(angle + 30)
        x = cx + math.cos(rad) * r * 0.55
        y = cy + math.sin(rad) * r * 0.55
        draw.ellipse([x - r * 0.42, y - r * 0.42, x + r * 0.42, y + r * 0.42],
                     outline=ACCENT2 + (a,), width=3)
    draw.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3],
                 fill=ACCENT + (int(40 * alpha),), outline=ACCENT2 + (a,), width=3)
    for angle in range(0, 360, 60):
        rad = math.radians(angle + 30)
        draw.line([(cx + math.cos(rad) * r * 0.3, cy + math.sin(rad) * r * 0.3),
                   (cx + math.cos(rad) * r * 0.55, cy + math.sin(rad) * r * 0.55)],
                  fill=ACCENT2 + (int(150 * alpha),), width=2)


def draw_triangle(draw, cx, cy, scale, alpha, t):
    a = int(220 * alpha)
    size = scale * 0.45
    rotation = math.sin(t * 0.8) * 6
    points = []
    for angle in (0, 120, 240):
        rad = math.radians(angle + rotation - 90)
        points.append((cx + math.cos(rad) * size, cy + math.sin(rad) * size))
    draw.polygon(points, outline=ACCENT + (a,), width=3)
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=ACCENT + (a,))


def draw_chip(draw, cx, cy, scale, alpha):
    a = int(220 * alpha)
    half = scale * 0.32
    draw.rounded_rectangle([cx - half, cy - half, cx + half, cy + half], radius=12,
                           outline=ACCENT + (a,), width=3)
    draw.rounded_rectangle([cx - half * 0.5, cy - half * 0.5, cx + half * 0.5, cy + half * 0.5],
                           radius=6, fill=ACCENT + (int(28 * alpha),))
    for i in range(4):
        offset = -half + half * 0.55 * i
        draw.line([(cx - half - 14, cy + offset), (cx - half, cy + offset)],
                  fill=ACCENT + (int(160 * alpha),), width=2)
        draw.line([(cx + half, cy + offset), (cx + half + 14, cy + offset)],
                  fill=ACCENT + (int(160 * alpha),), width=2)


def draw_bars(draw, cx, cy, scale, alpha, t):
    a = int(220 * alpha)
    bar_w = 26
    gap = 16
    heights = [0.45, 0.7, 0.9, 0.6]
    total = len(heights) * bar_w + (len(heights) - 1) * gap
    start = cx - total / 2
    for index, ratio in enumerate(heights):
        h = scale * 0.5 * ratio * (0.75 + 0.25 * math.sin(t * 2 + index))
        x = start + index * (bar_w + gap)
        draw.rounded_rectangle([x, cy + scale * 0.25 - h, x + bar_w, cy + scale * 0.25],
                               radius=6, fill=ACCENT + (int(120 * alpha),),
                               outline=ACCENT + (a,), width=2)




def draw_split(draw, cx, cy, scale, alpha, t):
    """A sentence block being cut apart: slicing line sweeps, pieces separate."""
    a = int(230 * alpha)
    block_w, block_h = 420, 96
    gap = ease((t - 1.0) / 0.9) * 26
    cut = ease((t - 0.6) / 0.8)
    pieces = 3
    piece_w = block_w / pieces
    for index in range(pieces):
        x0 = cx - block_w / 2 + index * piece_w + index * gap - gap * (pieces - 1) / 2
        draw.rounded_rectangle([x0, cy - block_h / 2, x0 + piece_w - 6, cy + block_h / 2],
                               radius=10, fill=(167, 139, 250, int(28 * alpha)),
                               outline=ACCENT2 + (a,), width=2)
        for line in range(2):
            y = cy - 16 + line * 26
            draw.line([(x0 + 14, y), (x0 + piece_w - 26, y)],
                      fill=(226, 232, 240, int(120 * alpha)), width=3)
    # slicing beam
    if 0 < cut < 1:
        x = cx - block_w / 2 + block_w * cut
        draw.line([(x, cy - block_h / 2 - 30), (x, cy + block_h / 2 + 30)],
                  fill=ACCENT + (int(230 * alpha),), width=3)
        draw.ellipse([x - 6, cy - block_h / 2 - 36, x + 6, cy - block_h / 2 - 24],
                     fill=ACCENT2 + (int(230 * alpha),))


def draw_tokens(draw, cx, cy, scale, alpha, t):
    """A sentence bar resolving into token chips, one chip at a time."""
    a = int(230 * alpha)
    bar_w, bar_h = 440, 64
    draw.rounded_rectangle([cx - bar_w / 2, cy - 120, cx + bar_w / 2, cy - 120 + bar_h],
                           radius=12, fill=(255, 255, 255, int(16 * alpha)),
                           outline=ACCENT2 + (int(150 * alpha),), width=2)
    for line in range(2):
        y = cy - 104 + line * 22
        draw.line([(cx - bar_w / 2 + 18, y), (cx + bar_w / 2 - 18, y)],
                  fill=(226, 232, 240, int(90 * alpha)), width=3)
    chips = 4
    chip_w, chip_h, gap = 96, 64, 14
    total = chips * chip_w + (chips - 1) * gap
    start_x = cx - total / 2
    for index in range(chips):
        appear = ease((t - (1.0 + index * 0.45)) / 0.45)
        if appear <= 0:
            continue
        x = start_x + index * (chip_w + gap)
        y = cy + 10 + (1 - appear) * 18
        draw.rounded_rectangle([x, y, x + chip_w, y + chip_h], radius=10,
                               fill=ACCENT + (int(40 * appear),),
                               outline=ACCENT2 + (int(210 * appear),), width=2)
        f = font(FONT_BOLD, 26)
        label = str(index + 1)
        draw.text((x + (chip_w - f.getlength(label)) / 2, y + 16), label,
                  font=f, fill=(255, 255, 255, int(220 * appear)))
        if index < chips - 1:
            ax = x + chip_w + 2
            draw.line([(ax, y + chip_h / 2), (ax + gap - 4, y + chip_h / 2)],
                      fill=ACCENT2 + (int(150 * appear),), width=2)


def draw_gear(draw, cx, cy, scale, alpha, t):
    a = int(220 * alpha)
    r = scale * 0.26
    teeth = 10
    rotation = t * 0.8
    for index in range(teeth):
        angle = rotation + index * (2 * math.pi / teeth)
        x = cx + math.cos(angle) * (r + 12)
        y = cy + math.sin(angle) * (r + 12)
        draw.rectangle([x - 7, y - 7, x + 7, y + 7], fill=ACCENT2 + (a,))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT2 + (a,), width=4)
    draw.ellipse([cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35],
                 fill=ACCENT + (int(50 * alpha),), outline=ACCENT + (a,), width=3)


def draw_database(draw, cx, cy, scale, alpha, t):
    a = int(220 * alpha)
    rw, rh = scale * 0.34, scale * 0.12
    for index in range(3):
        y = cy - rh * 1.4 + index * rh * 1.3
        draw.ellipse([cx - rw, y - rh, cx + rw, y + rh], outline=ACCENT2 + (a,), width=3)
        if index < 2:
            draw.line([(cx - rw, y), (cx - rw, y + rh * 1.3)], fill=ACCENT2 + (a,), width=3)
            draw.line([(cx + rw, y), (cx + rw, y + rh * 1.3)], fill=ACCENT2 + (a,), width=3)


FIGURES = {'brain': draw_brain, 'triangle': draw_triangle, 'chip': draw_chip,
           'bars': draw_bars, 'split': draw_split, 'tokens': draw_tokens,
           'gear': draw_gear, 'database': draw_database}


def draw_flow(draw, top, alpha, t):
    boxes = ['输入', '计算', '输出']
    box_w, box_h, gap = 152, 88, 48
    total = box_w * 3 + gap * 2
    start_x = snap((W - total) / 2)
    for index, text in enumerate(boxes):
        x = start_x + index * (box_w + gap)
        draw.rounded_rectangle([x, top, x + box_w, top + box_h], radius=14,
                               fill=(13, 20, 38, int(240 * alpha)),
                               outline=ACCENT2 + (int(230 * alpha),), width=3)
        f = font(FONT_BOLD, 30)
        draw.text((x + (box_w - f.getlength(text)) / 2, top + 26), text,
                  font=f, fill=(255, 255, 255, int(225 * alpha)))
        if index < 2:
            ax = x + box_w + 8
            for dash in range(3):
                offset = (t * 70 + dash * 12) % 32
                draw.line([(ax + offset, top + box_h / 2),
                           (ax + offset + 12, top + box_h / 2)],
                          fill=ACCENT + (int(170 * alpha),), width=3)
            dot_x = ax + 4 + (t * 70) % 32
            draw.ellipse([dot_x - 3, top + box_h / 2 - 3, dot_x + 3, top + box_h / 2 + 3],
                         fill=ACCENT + (int(220 * alpha),))


def render(out, title, bullets, seconds, accent='#22d3ee', label='概念解说', kind='list',
           figure='chip'):
    frames_dir = Path(out).with_suffix('')
    frames_dir.mkdir(parents=True, exist_ok=True)
    total = int(seconds * FPS)
    title_font = font(FONT_BOLD, 56)
    bullet_font = font(FONT_REG, 32)
    small_font = font(FONT_REG, 24)
    for index in range(total):
        t = index / FPS
        image = Image.new('RGB', (W, H), '#05070f')
        draw = ImageDraw.Draw(image, 'RGBA')
        background(draw)
        hud_ticks(draw, ACCENT2)
        # header label, grid-aligned
        label_w = small_font.getlength(label) + 40
        glass_panel(draw, (MARGIN, 80, MARGIN + label_w, 128), alpha=26)
        draw.text((MARGIN + 20, 90), label, font=small_font, fill=ACCENT + (220,))
        scanlines(draw, 210, 430)
        # figure area
        figure_alpha = ease((t - 0.1) / 0.7)
        fig_cy = 300
        if figure == 'flow':
            draw_flow(draw, 250, figure_alpha, t)
        else:
            drawer = FIGURES.get(figure, draw_chip)
            if figure in ('triangle', 'bars', 'split', 'tokens', 'gear', 'database'):
                drawer(draw, W / 2, fig_cy, 300, figure_alpha, t)
            else:
                drawer(draw, W / 2, fig_cy, 300, figure_alpha)
        # title panel
        panel_top = 470
        title_lines = wrap_text(title, 56, W - MARGIN * 2 - 48, bold=True)
        panel_h = 64 + len(title_lines) * 70 + 40
        glass_panel(draw, (MARGIN - 24, panel_top, W - MARGIN + 24, panel_top + panel_h))
        title_alpha = ease((t - 0.2) / 0.6)
        for line_index, line in enumerate(title_lines):
            draw.text((MARGIN, panel_top + 30 + line_index * 70 + (1 - title_alpha) * 18),
                      line, font=title_font, fill=(255, 255, 255, int(238 * title_alpha)))
        grow = ease((t - 0.5) / 0.7)
        underline_y = panel_top + 30 + len(title_lines) * 70 + 12
        draw.rounded_rectangle([MARGIN, underline_y, MARGIN + int(160 * grow), underline_y + 6],
                               radius=3, fill=ACCENT + (230,))
        # bullets panel sized to the wrapped text
        layout = [(wrap_text(bullet, 32, W - MARGIN * 2 - 40)[:3], bullet)
                  for bullet in bullets[:3]]
        bullets_top = panel_top + panel_h + 32
        bullets_h = 28 + sum(len(lines) * 42 + 22 for lines, _ in layout)
        glass_panel(draw, (MARGIN - 24, bullets_top, W - MARGIN + 24, bullets_top + bullets_h),
                    alpha=16)
        y = bullets_top + 20
        for bullet_index, (lines, _) in enumerate(layout):
            start = 0.9 + bullet_index * 0.6
            alpha = ease((t - start) / 0.5)
            block_h = len(lines) * 42 + 22
            if alpha > 0:
                off = (1 - alpha) * 16
                draw.ellipse([MARGIN, y + 10 + off, MARGIN + 10, y + 20 + off],
                             fill=ACCENT + (int(220 * alpha),))
                for line_index, line in enumerate(lines):
                    draw.text((MARGIN + 28, y + off + line_index * 42), line,
                              font=bullet_font, fill=(226, 232, 240, int(225 * alpha)))
            y += block_h
        # progress
        progress = min(1.0, t / seconds)
        draw.rectangle([0, H - 6, int(W * progress), H], fill=ACCENT + (200,))
        image.save(frames_dir / f'{index:04d}.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', str(frames_dir / '%04d.png'), '-c:v', 'libx264', '-preset',
                    'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', str(out)], check=True)
    for path in frames_dir.glob('*.png'):
        path.unlink()
    frames_dir.rmdir()
    return out
