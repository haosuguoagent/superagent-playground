#!/usr/bin/env python3
"""Animated concept-graphic scenes rendered with Pillow + ffmpeg."""

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 30
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def font(path, size):
    return ImageFont.truetype(path, size)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def draw_background(draw, accent):
    draw.rectangle([0, 0, W, H], fill='#05070f')
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 8), width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 8), width=1)
    draw.ellipse([W * 0.15, -260, W * 0.85, 380], fill=(34, 211, 238, 14))
    draw.ellipse([-200, H - 520, 360, H + 80], fill=(99, 102, 241, 12))


def wrap_text(text, size, max_width):
    f = font(FONT_REG, size)
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


def render(out, title, bullets, seconds, accent='#22d3ee', label='概念解说', kind='list'):
    frames_dir = Path(out).with_suffix('')
    frames_dir.mkdir(parents=True, exist_ok=True)
    total = int(seconds * FPS)
    title_font = font(FONT_BOLD, 58)
    bullet_font = font(FONT_REG, 34)
    small_font = font(FONT_REG, 26)
    accent_rgb = tuple(int(accent[i:i + 2], 16) for i in (1, 3, 5))
    for index in range(total):
        t = index / FPS
        image = Image.new('RGB', (W, H), '#05070f')
        draw = ImageDraw.Draw(image, 'RGBA')
        draw_background(draw, accent)
        # top label
        draw.rounded_rectangle([48, 90, 48 + 8 * len(label) + 46, 148], radius=14,
                               fill=(34, 211, 238, 30), outline=(34, 211, 238, 90))
        draw.text((72, 104), label, font=small_font, fill=(34, 211, 238, 220))
        # title reveal
        title_alpha = ease((t - 0.15) / 0.6)
        title_y = 250 + (1 - title_alpha) * 26
        title_lines = wrap_text(title, 58, W - 120)
        for line_index, line in enumerate(title_lines):
            draw.text((60, title_y + line_index * 74), line, font=title_font,
                      fill=(255, 255, 255, int(235 * title_alpha)))
        # underline grows
        grow = ease((t - 0.5) / 0.7)
        draw.rounded_rectangle([60, title_y + len(title_lines) * 74 + 16,
                                60 + int(170 * grow), title_y + len(title_lines) * 74 + 24],
                               radius=4, fill=accent_rgb + (230,))
        # bullets appear one by one
        base_y = title_y + len(title_lines) * 74 + 90
        for bullet_index, bullet in enumerate(bullets[:4]):
            start = 0.9 + bullet_index * 0.75
            alpha = ease((t - start) / 0.55)
            if alpha <= 0:
                continue
            lines = wrap_text(bullet, 34, W - 190)
            y = base_y + bullet_index * 150 + (1 - alpha) * 22
            draw.ellipse([64, y + 14, 76, y + 26], fill=accent_rgb + (int(220 * alpha),))
            for line_index, line in enumerate(lines[:2]):
                draw.text((96, y + line_index * 46), line, font=bullet_font,
                          fill=(226, 232, 240, int(225 * alpha)))
        # flow diagram for the last part of the scene
        if kind == 'flow' and t > 1.6:
            flow_alpha = ease((t - 1.6) / 0.8)
            boxes = ['输入', '计算', '输出']
            box_w, box_h, gap = 150, 76, 46
            start_x = (W - (box_w * 3 + gap * 2)) / 2
            y = H - 330
            for box_index, text in enumerate(boxes):
                x = start_x + box_index * (box_w + gap)
                draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=16,
                                       fill=(15, 23, 42, int(230 * flow_alpha)),
                                       outline=accent_rgb + (int(200 * flow_alpha),), width=2)
                f = font(FONT_BOLD, 30)
                draw.text((x + (box_w - f.getlength(text)) / 2, y + 22), text,
                          font=f, fill=(255, 255, 255, int(230 * flow_alpha)))
                if box_index < 2:
                    ax = x + box_w + 8
                    for arrow_index in range(3):
                        offset = (t * 60 + arrow_index * 12) % 24
                        draw.line([(ax + offset, y + box_h / 2), (ax + offset + 10, y + box_h / 2)],
                                  fill=accent_rgb + (int(180 * flow_alpha),), width=3)
        # bottom progress
        progress = min(1.0, t / seconds)
        draw.rectangle([0, H - 8, int(W * progress), H], fill=accent_rgb + (200,))
        image.save(frames_dir / f'{index:04d}.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', str(frames_dir / '%04d.png'), '-c:v', 'libx264', '-preset',
                    'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', str(out)], check=True)
    for path in frames_dir.glob('*.png'):
        path.unlink()
    frames_dir.rmdir()
    return out
