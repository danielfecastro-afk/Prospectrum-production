"""Shared helpers for the WorthWired #002 build: fonts, text elements, pops, video readers."""
import json, math, os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(W, 'src')
FPS = 30
WD, HT = 1920, 1080
NAVY = (11, 20, 38)
YEL = (255, 212, 0)
RED = (230, 57, 70)
WHITE = (255, 255, 255)
GREY = (150, 160, 180)
FONT_BLACK = '/usr/share/fonts/opentype/inter/Inter-Black.otf'
FONT_XB = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
FONT_EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'

_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


# ---------------------------------------------------------------- alignment
AL = json.load(open(os.path.join(W, 'align.json')))


def norm(w):
    return re.sub(r"[^a-z0-9'-]", '', w.lower())


def word_time(block, phrase, after=0.0, end=False):
    ws = [norm(x) for x in phrase.split()]
    seq = AL[block]
    for i in range(len(seq) - len(ws) + 1):
        if seq[i]['s'] >= after - 1e-6 and all(norm(seq[i + k]['w']) == ws[k] for k in range(len(ws))):
            return seq[i + len(ws) - 1]['e'] if end else seq[i]['s']
    raise KeyError((block, phrase, after))


def last_word_end(block):
    return AL[block][-1]['e']


# ---------------------------------------------------------------- easing
def ease_out_back(x):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


POP = 0.2


def pop_scale(lt):
    """Fast scale pop: 0.6 -> overshoot -> 1.0 in 0.2 s."""
    if lt >= POP:
        return 1.0
    return 0.6 + 0.4 * ease_out_back(max(lt, 0) / POP)


def pop_alpha(lt):
    return min(1.0, max(lt, 0) / 0.07)


# ---------------------------------------------------------------- text elements
def text_img(text, size, color=WHITE, fpath=FONT_BLACK, stroke=0, stroke_color=(0, 0, 0), shadow=True,
             tracking=0):
    f = font(fpath, size)
    pad = stroke + 24
    bbox = f.getbbox(text, stroke_width=stroke)
    w = bbox[2] - bbox[0] + 2 * pad + max(0, tracking * len(text))
    h = bbox[3] - bbox[1] + 2 * pad
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = pad - bbox[0], pad - bbox[1]
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((ox + 4, oy + 6), text, font=f, fill=(0, 0, 0, 150), stroke_width=stroke,
                                stroke_fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        im.alpha_composite(sh)
    if tracking:
        x = ox
        for ch in text:
            d.text((x, oy), ch, font=f, fill=color, stroke_width=stroke, stroke_fill=stroke_color)
            x += f.getlength(ch) + tracking
    else:
        d.text((ox, oy), text, font=f, fill=color, stroke_width=stroke, stroke_fill=stroke_color)
    return im


def emoji_img(ch, size):
    f = font(FONT_EMOJI, 109)
    im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    s = size / im.height
    return im.resize((max(1, int(im.width * s)), size), Image.LANCZOS)


def hstack(parts, gap=0, valign='center'):
    w = sum(p.width for p in parts) + gap * (len(parts) - 1)
    h = max(p.height for p in parts)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    x = 0
    for p in parts:
        y = (h - p.height) // 2 if valign == 'center' else h - p.height
        im.alpha_composite(p, (x, y))
        x += p.width + gap
    return im


def vstack(parts, gap=0, align='center'):
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts) + gap * (len(parts) - 1)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    y = 0
    for p in parts:
        x = (w - p.width) // 2 if align == 'center' else 0
        im.alpha_composite(p, (x, y))
        y += p.height + gap
    return im


def panel(el, pad=(50, 30), fill=(11, 20, 38, 235), radius=28, outline=None, width=4):
    w, h = el.width + 2 * pad[0], el.height + 2 * pad[1]
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=fill, outline=outline, width=width if outline else 0)
    im.alpha_composite(el, (pad[0], pad[1]))
    return im


def paste_el(img, el, cx, cy, scale=1.0, alpha=1.0):
    """Paste RGBA element centred at (cx, cy) on an RGB PIL image."""
    if scale != 1.0:
        w = max(1, int(el.width * scale))
        h = max(1, int(el.height * scale))
        el = el.resize((w, h), Image.BILINEAR)
    if alpha < 1.0:
        a = el.getchannel('A').point(lambda v: int(v * alpha))
        el = el.copy()
        el.putalpha(a)
    img.paste(el, (int(cx - el.width / 2), int(cy - el.height / 2)), el)


def wrap(text, f, maxw):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- backgrounds
def navy_bg():
    if not hasattr(navy_bg, 'img'):
        y, x = np.mgrid[0:HT, 0:WD]
        r = np.sqrt(((x - WD * 0.5) / WD) ** 2 + ((y - HT * 0.45) / HT) ** 2)
        k = np.clip(1.25 - r * 0.9, 0.7, 1.25)[..., None]
        base = np.array(NAVY, np.float32)[None, None, :] * k
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        d.rectangle([0, HT - 10, WD, HT], fill=YEL)
        navy_bg.img = img
    return navy_bg.img.copy()


def ken_burns(src_img, lt, dur, z0=1.0, z1=1.05, fx=0.5, fy=0.5):
    """Slow zoom on a PIL image; returns 1920x1080."""
    p = 0 if dur <= 0 else min(max(lt / dur, 0), 1)
    z = z0 + (z1 - z0) * ease_io(p)
    sw, sh = src_img.size
    cw, ch = sw / z, sh / z
    x0 = (sw - cw) * fx
    y0 = (sh - ch) * fy
    return src_img.resize((WD, HT), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


class FrameReader:
    """Sequential raw-frame reader for a section of a source video."""

    def __init__(self, path, start, dur, vf, w, h):
        self.w, self.h = w, h
        cmd = ['ffmpeg', '-v', 'error', '-ss', f'{start:.3f}', '-i', path, '-t', f'{dur:.3f}', '-vf',
               vf + ',fps=30', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w * h * 3 * 4)
        self.idx = -1
        self.last = None

    def get(self, i):
        while self.idx < i:
            buf = self.p.stdout.read(self.w * self.h * 3)
            if len(buf) < self.w * self.h * 3:
                break
            self.last = Image.frombytes('RGB', (self.w, self.h), buf)
            self.idx += 1
        return self.last

    def close(self):
        try:
            self.p.stdout.close()
            self.p.kill()
            self.p.wait()
        except Exception:
            pass
