"""按参考设计板手机端底部导航图标生成微信 tabBar PNG。

24×24 网格、1.7 线宽、圆角线帽，4 倍超采样后缩到 81×81。
重新生成：python tools/generate-tab-icons.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 81
SCALE = 4
W = SIZE * SCALE
STROKE = round(1.7 * SCALE * (SIZE / 24))
GRAY = (139, 139, 147, 255)
GOLD = (212, 175, 55, 255)
OUT = Path(__file__).resolve().parent.parent / 'tools' / 'assets' / 'tabbar'


def p(x, y):
    return x * SCALE * (SIZE / 24), y * SCALE * (SIZE / 24)


def box(x1, y1, x2, y2):
    return (*p(x1, y1), *p(x2, y2))


def canvas():
    return Image.new('RGBA', (W, W), (0, 0, 0, 0))


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.resize((SIZE, SIZE), Image.LANCZOS).save(OUT / f'{name}.png')


def draw_compass(color):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.ellipse(box(3.5, 3.5, 20.5, 20.5), outline=color, width=STROKE)
    needle = [p(15.6, 8.4), p(13.5, 13.5), p(8.4, 15.6), p(10.5, 10.5)]
    d.line(needle + [needle[0]], fill=color, width=STROKE, joint='curve')
    return img


def draw_folder(color):
    img = canvas()
    d = ImageDraw.Draw(img)
    radius = 2.4 * SCALE * (SIZE / 24)
    d.rounded_rectangle(box(3.5, 7.0, 20.5, 19.0), radius=radius, outline=color, width=STROKE)
    tab = [p(5.6, 7.2), p(6.0, 5.1), p(9.6, 5.1), p(11.7, 7.2)]
    d.line(tab, fill=color, width=STROKE, joint='curve')
    return img


def draw_clipboard(color):
    img = canvas()
    d = ImageDraw.Draw(img)
    radius = 2.2 * SCALE * (SIZE / 24)
    d.rounded_rectangle(box(5.2, 4.8, 18.8, 20.8), radius=radius, outline=color, width=STROKE)
    d.rounded_rectangle(box(9.2, 4.0, 14.8, 7.4), radius=radius * 0.6, outline=color, width=STROKE)
    d.line([p(8.6, 13.4), p(10.9, 15.7), p(15.2, 11.1)], fill=color, width=STROKE, joint='curve')
    return img


def draw_profile(color):
    img = canvas()
    d = ImageDraw.Draw(img)
    d.ellipse(box(3.4, 3.4, 20.6, 20.6), outline=color, width=STROKE)
    d.ellipse(box(9.3, 7.1, 14.7, 12.5), outline=color, width=STROKE)
    d.arc(box(7.4, 13.4, 16.6, 21.2), start=200, end=340, fill=color, width=STROKE)
    return img


ICONS = {
    'discover': draw_compass,
    'project': draw_folder,
    'agent': draw_clipboard,
    'profile': draw_profile,
}

for name, drawer in ICONS.items():
    save(drawer(GRAY), name)
    save(drawer(GOLD), f'{name}-selected')

print(f'Generated {len(ICONS) * 2} tab icons at {OUT}')
