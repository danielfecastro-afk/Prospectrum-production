"""WorthWired #002 — "Same Car, $14,000 More" — timeline, graphics, audio, subtitles, render."""
import math, os, subprocess, sys, json, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from lib import *

OUT = os.path.join(W, 'out')
os.makedirs(OUT, exist_ok=True)
PREVIEW = '--preview' in sys.argv          # render only selected time ranges at low cost
ONLY = None
for a in sys.argv:
    if a.startswith('--range='):
        ONLY = tuple(float(x) for x in a.split('=')[1].split(':'))

# ====================================================================== timeline
BLOCKS = ['N01', 'N02a', 'N02b', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08', 'N09', 'N10']
GAP = 0.40
OFF = {}
DRAM_DIR = os.path.join(W, 'dram')
AD = json.load(open(os.path.join(DRAM_DIR, 'align_d.json')))
# dramatization shots: (voice duration, subtitle EN, subtitle ES)
DRAM = {
    'D1': (4.127, 'Hey, my friend! No credit? No problem! Come see me today!',
           '¡Hola, amigo! ¿Sin crédito? ¡No hay problema! ¡Ven a verme hoy!'),
    'D2': (4.911, "No down payment? Doesn't matter! Just bring your license... or your passport.",
           '¿Sin pago inicial? ¡No importa! Solo trae tu licencia... o tu pasaporte.'),
    'D3': (3.318, 'Brand-new cars, from just four ninety-nine a month!',
           '¡Carros nuevos, desde solo cuatro noventa y nueve al mes!'),
    'D4': (4.441, 'And your first payment? Not for ninety days! Drive it home today!',
           '¿Y tu primer pago? ¡No hasta dentro de noventa días! ¡Llévatelo hoy!'),
}
INSERT_D3 = (1.28, 3.30)                    # "from just four ninety-nine a month!"
INS = INSERT_D3[1] - INSERT_D3[0]           # contrast insert inside N03
N03_SPLIT = None

# reel fragments (blur-verified windows): (name, src_start, src_end, crop_x, src_H, subtitle_en, original_es)
REELS = {
    'C1': (9.35, 14.45, 384, 1102, '', ''),
    'C2': (4.28, 6.45, 401, 1128, '', ''),
    'C3': (0.00, 4.10, 384, 1082, '', ''),
    'C4': (5.50, 8.31, 413, 1040, '', ''),
}
ADS_SRC = {'C1': 9.6, 'C2': 4.7, 'C3': 0.9, 'C4': 5.6}   # 1.5 s of source each, played x1.5 -> 1.0 s

t = 0.25
OFF['N01'] = t
t = OFF['N01'] + last_word_end('N01') + GAP
OFF['N02a'] = t
ADS0 = OFF['N02a'] + word_time('N02a', "If you're")
ADS1 = ADS0 + 4.0
dram_times = {}
t = ADS1
for n in ['D1', 'D2', 'D3', 'D4']:
    d = DRAM[n][0] + 0.4
    dram_times[n] = (t, t + d)
    t += d
DRAM0, DRAM1 = ADS1, t
# N02b starts at "And here's the thing" (the quote was already said by the salesman)
_and = word_time('N02b', "And here's")
_q_end = max(x['e'] for x in AL['N02b'] if x['e'] <= _and + 1e-6)
N02B_TRIM = (_q_end + _and) / 2
OFF['N02b'] = DRAM1 + 0.30 - _and
t = OFF['N02b'] + last_word_end('N02b') + GAP
OFF['N03'] = t
# split N03 in the pause before "With no credit history"
_ws = word_time('N03', 'With no credit history')
_prev_end = max(x['e'] for x in AL['N03'] if x['e'] <= _ws + 1e-6)
N03_SPLIT = (_prev_end + _ws) / 2
t = OFF['N03'] + last_word_end('N03') + INS + GAP
for b in ['N04', 'N05', 'N06', 'N07', 'N08', 'N09', 'N10']:
    OFF[b] = t
    t = OFF[b] + last_word_end(b) + GAP
END = OFF['N10'] + last_word_end('N10') + 2.2
INS_T0 = OFF['N03'] + N03_SPLIT
INS_T1 = INS_T0 + INS


def g(block, phrase, after=None, end=False):
    a = 0.0 if after is None else word_time(block, after)
    lt = word_time(block, phrase, a, end)
    extra = INS if (block == 'N03' and lt >= N03_SPLIT) else 0.0
    return OFF[block] + lt + extra


def block_end(b):
    extra = INS if b == 'N03' else 0.0
    return OFF[b] + last_word_end(b) + extra


def boundary(b_prev, b_next):
    return (block_end(b_prev) + OFF[b_next]) / 2


# section boundaries (0.2 s dip through black)
SECTION_B = [boundary('N01', 'N02a'), DRAM0, DRAM0, boundary('N02b', 'N03'), boundary('N03', 'N04'),
             boundary('N04', 'N05'), boundary('N05', 'N06'), boundary('N06', 'N07'), boundary('N07', 'N08'),
             boundary('N08', 'N09'), boundary('N09', 'N10')]


# ====================================================================== shots
class Shot:
    def __init__(self, t0, t1):
        self.t0, self.t1 = t0, t1
        self.items = []      # (el, cx, cy, ta, tb)
        self.fns = []        # (ta, tb, fn(img, lt))

    def item(self, el, cx, cy, ta, tb=None):
        self.items.append((el, cx, cy, ta, self.t1 if tb is None else tb))
        return self

    def fn(self, f, ta=None, tb=None):
        self.fns.append((self.t0 if ta is None else ta, self.t1 if tb is None else tb, f))
        return self

    def base(self, lt):
        raise NotImplementedError

    def render(self, gt):
        img = self.base(gt - self.t0)
        for ta, tb, f in self.fns:
            if ta <= gt < tb:
                f(img, gt - ta)
        for el, cx, cy, ta, tb in self.items:
            if ta <= gt < tb:
                lt = gt - ta
                paste_el(img, el, cx, cy, pop_scale(lt), pop_alpha(lt))
        return img

    def close(self):
        pass


class Navy(Shot):
    def base(self, lt):
        return navy_bg()


CARS = Image.open(os.path.join(W, 'narr', 'cars.png')).convert('RGB').resize((2112, 1188), Image.LANCZOS)


class Cars(Shot):
    """Two-car image with a slow zoom that runs on a shared clock (kb0..kb1)."""

    def __init__(self, t0, t1, kb0, kb1, z0=1.0, z1=1.08):
        super().__init__(t0, t1)
        self.kb0, self.kb1, self.z0, self.z1 = kb0, kb1, z0, z1

    def base(self, lt):
        gt = self.t0 + lt
        return ken_burns(CARS, gt - self.kb0, self.kb1 - self.kb0, self.z0, self.z1, 0.5, 0.55)


# crops for screen recordings (x, y, w, h) in source pixels, 16:9
CROPS = {
    'G01': (150, 200, 1300, 731), 'G02': (120, 170, 1580, 889), 'G03': (250, 120, 1400, 788),
    'G04': (470, 60, 1300, 731), 'G05': (120, 0, 1500, 844), 'G06': (50, 100, 1400, 788),
    'G07': (200, 110, 1760, 990), 'G08': (170, 95, 1300, 731), 'G09': (100, 0, 1450, 816),
}
SRC_DUR = {}


def src_dur(n):
    if n not in SRC_DUR:
        SRC_DUR[n] = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                           'csv=p=0', os.path.join(SRC, n + '.mp4')], capture_output=True,
                                          text=True).stdout)
    return SRC_DUR[n]


class Screen(Shot):
    """Screen recording: plays source segments back to back, then Ken Burns 5% on the last frame."""

    def __init__(self, t0, t1, name, segs, fx=0.5, fy=0.5):
        super().__init__(t0, t1)
        self.name = name
        x, y, w, h = CROPS[name]
        self.vf = f'crop={w}:{h}:{x}:{y},scale={WD}:{HT}:flags=lanczos'
        sd = src_dur(name) - 0.05
        self.segs = []
        lt = 0.0
        for s, e in segs:
            e = min(e, sd)
            if e - s < 0.1 or lt >= self.t1 - self.t0:
                continue
            d = min(e - s, (self.t1 - self.t0) - lt)
            self.segs.append((lt, s, d))
            lt += d
        self.play_end = lt
        self.cur = None
        self.cur_i = -1
        self.last = None
        self.fx, self.fy = fx, fy

    def base(self, lt):
        if lt < self.play_end:
            for i, (l0, s, d) in enumerate(self.segs):
                if l0 <= lt < l0 + d:
                    break
            if i != self.cur_i:
                if self.cur:
                    self.cur.close()
                self.cur = FrameReader(os.path.join(SRC, self.name + '.mp4'), s, d + 0.1, self.vf, WD, HT)
                self.cur_i = i
            fr = self.cur.get(int(round((lt - l0) * FPS)))
            if fr is not None:
                self.last = fr
            return self.last.copy()
        if self.cur:
            self.cur.close()
            self.cur = None
        if self.last is None:   # no playable segment: grab last frame
            r = FrameReader(os.path.join(SRC, self.name + '.mp4'), src_dur(self.name) - 0.2, 0.2, self.vf, WD, HT)
            self.last = r.get(0)
            r.close()
        rem = (self.t1 - self.t0) - self.play_end
        return ken_burns(self.last, lt - self.play_end, rem, 1.0, 1.05, self.fx, self.fy)

    def close(self):
        if self.cur:
            self.cur.close()


# ---------------------------------------------------------------- reels (privacy blur)
def lerp_keys(keys, lt):
    if lt <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= lt <= b[0]:
            p = (lt - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * p for i in range(1, len(a)))
    return keys[-1][1:]


C3_FACE = [(0.0, 333, 572), (0.588, 315, 565), (1.176, 330, 554), (1.765, 317, 576), (2.353, 282, 543),
           (2.941, 246, 532), (3.529, 224, 521), (4.2, 212, 525)]


def blur_boxes(name, lt):
    """Boxes (x0, y0, x1, y1) in native reel-crop pixels to blur at local fragment time lt."""
    if name == 'C1':   # sales rep face + shirt logo, ID card graphic, front plate frame
        return [(190, 350, 470, 660), (465, 385, 615, 525), (225, 715, 445, 845)]
    if name == 'C2':   # plate frames (front/rear) and dealer building at left
        return [(120, 690, 440, 890), (0, 470, 160, 620)]
    if name == 'C3':   # walking presenter face (tracked), street number, floor-mat logo
        cx, cy = lerp_keys(C3_FACE, lt)
        b = [(cx - 78, cy - 92, cx + 78, cy + 80), (0, 0, 230, 125)]
        if lt >= 2.2:
            b.append((0, 890, 634, 1082))
        return b
    if name == 'C4':   # rear plate frame, distant dealership buildings
        return [(15, 545, 265, 695), (0, 405, 634, 500)]
    return []


def strong_blur(im, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(im.width, x1), min(im.height, y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return
    reg = im.crop((x0, y0, x1, y1))
    small = reg.resize((max(1, (x1 - x0) // 14), max(1, (y1 - y0) // 14)), Image.BILINEAR)
    reg = small.resize(reg.size, Image.BILINEAR).filter(ImageFilter.BoxBlur(10))
    im.paste(reg, (x0, y0))


SUB_FONT = font(FONT_XB, 44)
REEL_H = 950          # reel area height; the band below carries the burned-in English subtitles


def subtitle_el(text):
    lines = wrap(text, SUB_FONT, 1780)
    els = [text_img(l, 44, WHITE, FONT_XB, stroke=4, stroke_color=(0, 0, 0), shadow=False) for l in lines]
    return vstack(els, gap=-50)


def compose_reel(native, gray=False, full=False):
    H = native.height
    reel = native.crop((0, 0, native.width, H - 40))     # drop the app's mute/profile icons
    fh = HT if full else REEL_H
    fw = int(reel.width * fh / reel.height)
    fg = reel.resize((fw, fh), Image.LANCZOS)
    bh = int(reel.height * WD / reel.width)
    bg = reel.resize((96, int(96 * bh / WD) or 1), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    bg = bg.resize((WD, bh), Image.BILINEAR).crop((0, (bh - HT) // 2, WD, (bh - HT) // 2 + HT))
    bg = Image.eval(bg, lambda v: int(v * 0.42))
    bg.paste(fg, ((WD - fw) // 2, 0))
    d = ImageDraw.Draw(bg)
    x0 = (WD - fw) // 2
    d.rectangle([x0 - 3, 0, x0 - 1, fh], fill=(0, 0, 0))
    d.rectangle([x0 + fw, 0, x0 + fw + 2, fh], fill=(0, 0, 0))
    if not full:
        d.rectangle([0, fh, WD, HT], fill=(6, 10, 20))
        d.rectangle([0, fh, WD, fh + 3], fill=YEL)
    if gray:
        bg = ImageOps.grayscale(bg).convert('RGB')
    return bg


class Reel(Shot):
    def __init__(self, t0, t1, name, s, e, subtitle, speed=1.0, full=False):
        super().__init__(t0, t1)
        self.name, self.s, self.e = name, s, e
        self.speed, self.full = speed, full
        _, _, x, H, _, _ = REELS[name]
        self.x, self.H = x, H
        self.reader = None
        self.sub = subtitle_el(subtitle) if subtitle else None
        self.last_native = None

    def native(self, lt):
        if self.reader is None:
            sp = f'setpts=PTS/{self.speed},' if self.speed != 1.0 else ''
            self.reader = FrameReader(os.path.join(SRC, self.name + '.mp4'), self.s, self.e - self.s + 0.1,
                                      sp + f'crop=634:{self.H}:{self.x}:0', 634, self.H)
        fr = self.reader.get(int(round(lt * FPS)))
        im = fr.copy()
        for b in blur_boxes(self.name, lt * self.speed + (self.s - REELS[self.name][0])):
            strong_blur(im, b)
        self.last_native = im
        return im

    def base(self, lt):
        img = compose_reel(self.native(lt), full=self.full)
        if self.sub is not None:
            img.paste(self.sub, ((WD - self.sub.width) // 2, REEL_H + (HT - REEL_H - self.sub.height) // 2 + 2),
                      self.sub)
        return img

    def close(self):
        if self.reader:
            self.reader.close()


class Freeze(Shot):
    """Last frame of the C4 fragment, greyed, with a slow push-in."""

    def __init__(self, t0, t1, still):
        super().__init__(t0, t1)
        self.still = Image.eval(compose_reel(still, gray=True), lambda v: int(v * 0.8))

    def base(self, lt):
        return ken_burns(self.still, lt, self.t1 - self.t0, 1.0, 1.05)


def last_reel_frame(name):
    s, e, x, H, _, _ = REELS[name]
    r = FrameReader(os.path.join(SRC, name + '.mp4'), e - 0.12, 0.12, f'crop=634:{H}:{x}:0', 634, H)
    im = r.get(0).copy()
    for i in range(1, 4):
        f = r.get(i)
        if f is not None:
            im = f.copy()
    r.close()
    for b in blur_boxes(name, e - s):
        strong_blur(im, b)
    return im


WARM = ('scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,'
        'colorbalance=rs=0.06:gs=0.02:bs=-0.06:rm=0.05:gm=0.01:bm=-0.05,eq=contrast=1.05:saturation=1.08,'
        'vignette=angle=PI/5')
COOL = ('scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,'
        'eq=saturation=0.62:brightness=-0.03:contrast=1.03,colorbalance=rs=-0.05:bs=0.06:rm=-0.03:bm=0.05,'
        'vignette=angle=PI/4.5')


def dram_label():
    if not hasattr(dram_label, 'el'):
        dram_label.el = panel(T('DRAMATIZATION', 34, WHITE, FONT_XB, shadow=False, tracking=3), pad=(22, 10),
                              fill=(0, 0, 0, 153), radius=10)
    return dram_label.el


def ads_label():
    if not hasattr(ads_label, 'el'):
        ads_label.el = panel(T('REAL DEALER ADS · Social media, 2026', 34, WHITE, FONT_XB, shadow=False),
                             pad=(22, 10), fill=(0, 0, 0, 153), radius=10)
    return ads_label.el


def add_dram_label(shot):
    el = dram_label()
    shot.items.append((el, WD - 40 - el.width / 2, 40 + el.height / 2, shot.t0 - 1.0, shot.t1))


DSUB_FONT = font(FONT_XB, 50)


def dram_sub_el(text):
    lines = wrap(text, DSUB_FONT, 1700)
    els = [text_img(l, 50, WHITE, FONT_XB, stroke=5, stroke_color=(0, 0, 0), shadow=False) for l in lines]
    return vstack(els, gap=-54)


class Dram(Shot):
    """Dramatized salesman shot: warm 'dealer ad' grade, own audio (mixed separately), burned subtitle."""

    def __init__(self, t0, t1, name, src_start=0.0, grade=WARM, speed=1.0, subtitle=None, still_at=None):
        super().__init__(t0, t1)
        self.name, self.src_start, self.grade, self.speed, self.still_at = name, src_start, grade, speed, still_at
        self.reader = None
        self.sub = dram_sub_el(subtitle) if subtitle else None
        self.still = None
        add_dram_label(self)

    def base(self, lt):
        path = os.path.join(DRAM_DIR, self.name + '.mp4')
        if self.still_at is not None:
            if self.still is None:
                r = FrameReader(path, self.still_at, 0.2, self.grade, WD, HT)
                self.still = r.get(0).copy()
                r.close()
            img = ken_burns(self.still, lt, self.t1 - self.t0, 1.0, 1.04)
        else:
            if self.reader is None:
                sp = f'setpts={self.speed}*PTS,' if self.speed != 1.0 else ''
                self.reader = FrameReader(path, self.src_start, (self.t1 - self.t0) / self.speed + 0.2,
                                          sp + self.grade, WD, HT)
            img = self.reader.get(int(round(lt * FPS))).copy()
        if self.sub is not None:
            img.paste(self.sub, ((WD - self.sub.width) // 2, HT - 50 - self.sub.height), self.sub)
        return img

    def close(self):
        if self.reader:
            self.reader.close()


SELLER = Image.open(os.path.join(DRAM_DIR, 'seller.png')).convert('RGB').resize((2112, 1188), Image.LANCZOS)


def _grade_cool_img(im):
    a = np.asarray(im).astype(np.float32)
    g_ = a.mean(axis=2, keepdims=True)
    a = g_ + (a - g_) * 0.62
    a[..., 0] *= 0.95
    a[..., 2] *= 1.06
    a *= 0.97
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


SELLER = _grade_cool_img(SELLER)


class SellerStill(Shot):
    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        add_dram_label(self)

    def base(self, lt):
        return ken_burns(SELLER, lt, self.t1 - self.t0, 1.0, 1.06, 0.4, 0.4)


class DramFreezeGray(Shot):
    """Last frame of D4 in grey with a slow push-in (under N02b)."""

    def __init__(self, t0, t1, at):
        super().__init__(t0, t1)
        r = FrameReader(os.path.join(DRAM_DIR, 'D4.mp4'), at, 0.15, WARM, WD, HT)
        im = r.get(0).copy()
        r.close()
        self.still = Image.eval(ImageOps.grayscale(im).convert('RGB'), lambda v: int(v * 0.8))

    def base(self, lt):
        return ken_burns(self.still, lt, self.t1 - self.t0, 1.0, 1.05)


# ====================================================================== graphic elements
def T(text, size=120, color=WHITE, f=FONT_BLACK, **kw):
    return text_img(text, size, color, f, **kw)


def source_label(text):
    el = panel(T(text, 30, (225, 230, 240), FONT_B, shadow=False), pad=(22, 10), fill=(11, 20, 38, 215),
               radius=14)
    return el


def add_label(shot, text):
    el = source_label(text)
    shot.items.append((el, 40 + el.width / 2, HT - 46 - el.height / 2, shot.t0 + 0.0001, shot.t1))
    # labels should not pop: mark via negative-time trick (appear fully from start)
    shot.items[-1] = (el, 40 + el.width / 2, HT - 46 - el.height / 2, shot.t0 - 1.0, shot.t1)


def logo_el(size=190):
    word = T('WORTHWIRED', size, YEL, tracking=6)
    bar = Image.new('RGBA', (int(word.width * 0.62), 14), YEL + (255,))
    tag = T('FOLLOW THE MONEY', 40, WHITE, FONT_XB, tracking=10, shadow=False)
    return vstack([word, bar, tag], gap=6)


def title_card(shot, top, bottom, ta, top_color=YEL, top_size=150, bottom_size=96, gap=0):
    els = []
    if top:
        els.append(T(top, top_size, top_color))
    if bottom:
        for line in bottom.split('\n'):
            els.append(T(line, bottom_size, WHITE))
    el = vstack(els, gap=gap)
    shot.item(el, WD / 2, HT / 2, ta)


def money(v):
    return '${:,.0f}'.format(v)


def calc_fn(rate, payment, interest, label, label_color, count_from=None, t_count=0.6):
    """WorthWired loan-calculator card (same inputs as the Bankrate screen: $27,852 over 72 months)."""
    head = T('AUTO LOAN  ·  $27,852  ·  72 MONTHS', 46, GREY, FONT_XB, shadow=False)
    tag = T(label, 54, label_color, FONT_BLACK, shadow=False)

    def f(img, lt):
        s = pop_scale(lt)
        p = ease_out(lt / t_count) if count_from else 1.0
        pay = payment if not count_from else count_from[0] + (payment - count_from[0]) * p
        intr = interest if not count_from else count_from[1] + (interest - count_from[1]) * p
        pw, ph = 1240, 640
        pan = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(pan)
        d.rounded_rectangle([0, 0, pw - 1, ph - 1], 36, fill=(20, 33, 60, 255), outline=(60, 80, 120, 255), width=3)
        pan.alpha_composite(head, ((pw - head.width) // 2, 20))
        pan.alpha_composite(tag, ((pw - tag.width) // 2, 92))
        rows = [('INTEREST RATE', f'{rate:.2f}%', YEL), ('MONTHLY PAYMENT', money(pay), WHITE),
                ('TOTAL INTEREST', money(intr), YEL)]
        y = 200
        for k, v, c in rows:
            d.text((70, y + 40), k, font=font(FONT_XB, 44), fill=(200, 208, 225))
            fv = font(FONT_BLACK, 104)
            d.text((pw - 70 - fv.getlength(v), y + 6), v, font=fv, fill=c)
            y += 138
            if k != 'TOTAL INTEREST':
                d.line([70, y - 6, pw - 70, y - 6], fill=(60, 80, 120), width=2)
        paste_el(img, pan, WD / 2, HT / 2 - 10, s, pop_alpha(lt))
    return f


def arrow(d, x0, y, x1, p, color=YEL, w=12):
    if p <= 0:
        return
    xe = x0 + (x1 - x0) * p
    d.line([x0, y, xe, y], fill=color, width=w)
    if p > 0.25:
        d.polygon([(xe + 8, y), (xe - 28, y - 24), (xe - 28, y + 24)], fill=color)


# ====================================================================== build the shot list
shots = []


def add(shot):
    shots.append(shot)
    return shot


# ---------------- 1. N01 hook
B = 'N01'
kb0, kb1 = 0.0, g(B, 'This is WorthWired.')
t_real1, t_real2, t_rule = g(B, 'real numbers'), g(B, 'real government'), g(B, 'the one rule')
t_logo = g(B, 'This is WorthWired.')
cars_shared = []


def cars_shot(a, b):
    s = add(Cars(a, b, kb0, kb1))
    cars_shared.append(s)
    return s


cars_shot(0.0, t_real1)
add(Screen(t_real1, t_real2, 'G02', [(9.3, 11.0)]))
add(Screen(t_real2, t_rule, 'G05', [(2.0, 4.5)]))
add(Screen(t_rule, t_rule + 1.0, 'G07', [(6.0, 7.0)]))
cars_shot(t_rule + 1.0, t_logo)
s_same = [T('SAME CAR', 84, WHITE, stroke=3), T('SAME PRICE', 84, WHITE, stroke=3), T('SAME DAY', 84, WHITE, stroke=3)]
same_t = [g(B, 'Same car.'), g(B, 'Same price.'), g(B, 'Same day.')]
plus14 = T('+$14,000', 210, RED, stroke=8, stroke_color=WHITE)
t14 = g(B, 'fourteen')
for s in cars_shared:
    for i, (el, ta) in enumerate(zip(s_same, same_t)):
        s.item(el, 370 + i * 590, 150, ta)
    s.item(plus14, 1395, 470, t14)
lg = add(Navy(t_logo, SECTION_B[0]))
lg.item(logo_el(), WD / 2, HT / 2, t_logo)

# ---------------- 2. N02a "The promise" + real ads burst
s = add(Navy(SECTION_B[0], ADS0))
title_card(s, 'THE PROMISE', None, SECTION_B[0] + 0.05, top_size=170)
for i, n in enumerate(['C1', 'C2', 'C3', 'C4']):
    s0 = ADS_SRC[n]
    r = add(Reel(ADS0 + i, ADS0 + i + 1.0, n, s0, s0 + 1.55, None, speed=1.5, full=True))
    el = ads_label()
    r.items.append((el, 40 + el.width / 2, 40 + el.height / 2, r.t0 - 1.0, r.t1))

# ---------------- 3. dramatization D1-D4 (own audio)
for n in ['D1', 'D2', 'D3', 'D4']:
    a_, b_ = dram_times[n]
    add(Dram(a_, b_, n, subtitle=DRAM[n][1]))

# ---------------- 4. N02b over a grey freeze of D4
B = 'N02b'
fz = add(DramFreezeGray(DRAM1, SECTION_B[3], DRAM['D4'][0] + 0.4 - 0.05))
fz.item(T('AT WHAT PRICE?', 170, YEL, stroke=4), WD / 2, HT / 2, g(B, 'at what price?'))

# ---------------- 5. N03 the gap
B = 'N03'
a = SECTION_B[3]
b = g(B, 'Now look')
s = add(Screen(a, g(B, 'According'), 'G01', [(1.0, 8.6), (17.2, 20.6)], fy=0.4))
add_label(s, 'Source: CFPB (2015)')
t_acc, t_nohist = g(B, 'According'), g(B, 'With no history')
L = t_nohist - t_acc
s = add(Screen(t_acc, t_nohist, 'G02', [(max(0.3, 17.0 - L), 17.0)]))
add_label(s, 'Source: Experian, Q2 2026')
t_same2 = g(B, 'Same car. Same price.', after='costs you.')
s = add(Screen(t_nohist, t_same2, 'G02', [(17.2, 20.0)], fy=0.85))
add_label(s, 'Source: Experian, Q2 2026')
L = INS_T0 - t_same2
s = add(Screen(t_same2, INS_T0, 'G03', [(max(0.2, 16.3 - L), 16.3)], fx=0.6, fy=0.4))
add_label(s, 'Source: Bankrate auto loan calculator')
add(Dram(INS_T0, INS_T1, 'D3', src_start=INSERT_D3[0], subtitle='From just four ninety-nine a month!'))
t_14 = g(B, "That's fourteen")
s = add(Navy(INS_T1, t_14))
s.fn(calc_fn(21.62, 693.54, 22083, 'NO CREDIT HISTORY', RED, count_from=(499.42, 8107), t_count=0.9), INS_T1 + 0.05)
add_label(s, 'WorthWired calculation · same inputs, 21.62% APR')
t_because = g(B, 'Because inside')
s = add(Navy(t_14, t_because))
left = vstack([T('$8,107', 150, WHITE), T('GOOD CREDIT · 8.81%', 40, GREY, FONT_XB, shadow=False)], gap=-10)
right = vstack([T('$22,083', 150, YEL), T('NO CREDIT · 21.62%', 40, GREY, FONT_XB, shadow=False)], gap=-10)
s.item(left, 520, 380, t_14)
s.item(T('vs', 80, GREY, FONT_XB), WD / 2, 370, t_14 + 0.25)
s.item(right, 1400, 380, t_14 + 0.45)
s.item(T('→ +$14,000', 190, RED, stroke=6, stroke_color=WHITE), WD / 2, 760, g(B, 'fourteen', after="That's"))
s.item(T('TOTAL INTEREST · SAME CAR · SAME LOAN', 38, GREY, FONT_XB, shadow=False), WD / 2, 560, t_14 + 0.6)
t_four = g(B, 'four traps')
s = add(Navy(t_because, t_four))
title_card(s, 'THE FINANCE', 'OFFICE', t_because + 0.05, top_color=WHITE, top_size=150, bottom_size=150)
s = add(Navy(t_four, SECTION_B[4]))
s.item(hstack([T('4', 360, YEL), T('TRAPS', 200, WHITE)], gap=40), WD / 2, HT / 2, t_four)

# ---------------- 6. N04 trap 1
B = 'N04'
a = SECTION_B[4]
t_when = g(B, 'When the dealer')
s = add(Navy(a, t_when))
title_card(s, 'TRAP #1', 'THE HIDDEN MARKUP', a + 0.05)
t_ex = g(B, 'On our example')
s = add(Navy(t_when, t_ex))
bank = panel(vstack([T('BANK', 70, WHITE), T('8.81%', 110, YEL)], gap=-14), pad=(60, 30), fill=(20, 33, 60, 255),
             outline=(90, 110, 150, 255))
dealer = panel(vstack([T('DEALER', 70, WHITE), T('11.31%', 110, RED)], gap=-14), pad=(60, 30),
               fill=(20, 33, 60, 255), outline=(90, 110, 150, 255))
keeps = vstack([T('Dealer keeps', 64, YEL), T('the difference', 64, YEL)], gap=-20)
t_bank, t_dealer, t_keep = g(B, 'the bank approves'), g(B, 'The dealer can'), g(B, 'and keep part')
s.item(T('THE BUY RATE  →  YOUR RATE', 52, GREY, FONT_XB, shadow=False), WD / 2, 250, t_when + 0.05)
s.item(bank, 330, 560, t_bank)
s.item(dealer, 960, 560, t_dealer + 0.35)
s.item(keeps, 1590, 560, t_keep + 0.3)


def arrows_fn(img, lt):
    d = ImageDraw.Draw(img)
    gt_ = t_when + lt
    arrow(d, 520, 560, 760, ease_out((gt_ - t_dealer) / 0.35))
    arrow(d, 1155, 560, 1355, ease_out((gt_ - t_keep) / 0.3))


s.fn(arrows_fn, t_when, t_ex)
t_adds = g(B, 'And it adds up')
s = add(Navy(t_ex, t_adds))
s.fn(calc_fn(11.31, 534.57, 10637, 'DEALER MARKUP: +2.5 POINTS', YEL, count_from=(499.42, 8107), t_count=0.9), t_ex)
s.item(T('+$2,500', 130, RED, stroke=5, stroke_color=WHITE), 1610, 118, g(B, 'twenty-five hundred'))
add_label(s, 'WorthWired calculation · $10,637 vs $8,107 interest')
t_not = g(B, 'Not on the car.')
t_almost = g(B, 'almost two thousand')
s = add(Screen(t_adds, t_not, 'G04', [(max(0.2, 6.0 - (t_almost - t_adds)), 6.0), (19.2, 21.0)], fy=0.6))
add_label(s, 'Source: StoneEagle, Dec 2025')
s = add(Navy(t_not, SECTION_B[5]))
s.item(T('Not on the car.', 120, WHITE), WD / 2, 430, t_not)
s.item(T('On the paperwork.', 140, YEL), WD / 2, 610, g(B, 'On the paperwork.'))

# ---------------- 7. N05 trap 2
B = 'N05'
a = SECTION_B[5]
t_23 = g(B, 'In twenty twenty-three')
s = add(Navy(a, t_23))
s.item(T('TRAP #2', 130, YEL), WD / 2, 230, a + 0.05)
s.item(T('THE EXTRAS', 86, WHITE), WD / 2, 360, a + 0.05)
for i, (txt, ph) in enumerate([('GAP', 'GAP coverage.'), ('EXTENDED WARRANTY', 'Extended warranties.'),
                               ('CREDIT INSURANCE', 'Credit insurance.')]):
    s.item(panel(T(txt, 76, WHITE), pad=(44, 14), fill=(20, 33, 60, 255), outline=YEL + (255,), radius=20),
           WD / 2, 540 + i * 150, g(B, ph))
t_saw = g(B, 'If you saw')
t_60 = g(B, 'sixty million')
s = add(Screen(t_23, t_saw, 'G05', [(max(0.3, 6.0 - (t_60 - t_23)), 6.0), (6.3, 15.8)], fy=0.3))
add_label(s, 'Source: CFPB via KBB, 2023')
t_easy = g(B, 'easy to buy')
s = add(Screen(t_saw, t_easy, 'G05', [(0.4, 0.4 + (t_easy - t_saw))], fy=0.1))
add_label(s, 'Source: KBB, Nov 2023')
s = add(Navy(t_easy, SECTION_B[6]))
s.item(T('EASY TO BUY.', 140, WHITE), WD / 2, 440, t_easy)
s.item(T('HARD TO CANCEL.', 140, YEL), WD / 2, 620, g(B, 'hard to cancel.', after='easy'))

# ---------------- 8. N06 trap 3
B = 'N06'
a = SECTION_B[6]
t_then = g(B, 'Then, days later')
s = add(Navy(a, t_then))
s.item(T('TRAP #3', 130, YEL), WD / 2, 340, a + 0.05)
s.item(T('"TAKE IT HOME TODAY"', 100, WHITE), WD / 2, 480, a + 0.05)
s.item(panel(T('= SPOT DELIVERY', 64, NAVY, shadow=False), pad=(36, 12), fill=YEL + (255,), radius=16),
       WD / 2, 680, g(B, 'spot delivery.'))
t_five = g(B, 'about five')
t_your = g(B, 'Your financing')
t_yoyo = g(B, 'yo-yo financing.')
s = add(Navy(t_then, t_five))


def phone_fn(img, lt):
    gt_ = t_then + lt
    d = ImageDraw.Draw(img)
    px, py, pw, ph = 600, 90, 470, 900
    d.rounded_rectangle([px, py, px + pw, py + ph], 60, fill=(5, 8, 15), outline=(90, 100, 120), width=6)
    d.rounded_rectangle([px + 22, py + 22, px + pw - 22, py + ph - 22], 44, fill=(30, 45, 80))
    d.rounded_rectangle([px + pw / 2 - 70, py + 38, px + pw / 2 + 70, py + 70], 16, fill=(5, 8, 15))
    ft = font(FONT_XB, 120)
    tt = '9:41'
    d.text((px + pw / 2 - ft.getlength(tt) / 2, py + 120), tt, font=ft, fill=WHITE)
    fd = font(FONT_B, 34)
    dd = 'Tuesday, 3 days later'
    d.text((px + pw / 2 - fd.getlength(dd) / 2, py + 270), dd, font=fd, fill=(200, 210, 230))
    if gt_ >= t_then + 0.5:  # ringing call
        ring = 'Incoming call · Dealer'
        fr = font(FONT_XB, 36)
        k = (math.sin((gt_ - t_then) * 14) + 1) / 2
        d.rounded_rectangle([px + 50, py + 700, px + pw - 50, py + 790], 45,
                            fill=(int(40 + 40 * k), int(170 + 30 * k), 90))
        d.text((px + pw / 2 - fr.getlength(ring) / 2, py + 726), ring, font=fr, fill=WHITE)
    if gt_ >= t_your:  # notification slides in
        p = ease_out((gt_ - t_your) / 0.25)
        ny = py + 340 - (1 - p) * 120
        nb = Image.new('RGBA', (pw - 60, 190), (0, 0, 0, 0))
        nd = ImageDraw.Draw(nb)
        nd.rounded_rectangle([0, 0, nb.width - 1, nb.height - 1], 30, fill=(245, 246, 250, int(255 * p)))
        nd.rounded_rectangle([22, 24, 72, 74], 12, fill=RED + (int(255 * p),))
        nd.text((90, 26), 'DEALER FINANCE · now', font=font(FONT_B, 28), fill=(90, 95, 110, int(255 * p)))
        nd.text((24, 88), 'Your financing fell through.', font=font(FONT_XB, 34), fill=(15, 20, 30, int(255 * p)))
        nd.text((24, 132), 'Come back and sign a new contract.', font=font(FONT_B, 28), fill=(60, 65, 80, int(255 * p)))
        img.paste(nb, (px + 30, int(ny)), nb)


s.fn(phone_fn, t_then, t_five)
s.item(T('AT A HIGHER RATE', 70, RED, stroke=2), 1490, 420, g(B, 'At a higher rate.'))
s.item(panel(T('YO-YO FINANCING', 70, NAVY, shadow=False), pad=(36, 12), fill=YEL + (255,), radius=16),
       1490, 600, t_yoyo)
t_warn = g(B, 'Warning signs')
s = add(Navy(t_five, t_warn))
s.item(T('+5 POINTS', 230, YEL, stroke=4), WD / 2, 470, t_five)
s.item(T('AVERAGE EXTRA RATE AFTER RE-SIGNING', 46, GREY, FONT_XB, shadow=False), WD / 2, 650, t_five + 0.3)
s = add(Navy(t_warn, SECTION_B[7]))
s.item(T('WARNING SIGNS', 110, YEL), WD / 2, 220, t_warn)
for i, (txt, ph) in enumerate([('BLANK SPACES', 'blank spaces'), ('"CONDITIONAL" SALE', 'a form that'),
                               ('NO FINAL CONTRACT', 'or leaving')]):
    row = hstack([T('⚠' if False else '!', 90, NAVY, shadow=False)], gap=0)
    badge = panel(T('!', 70, NAVY, shadow=False), pad=(30, 4), fill=YEL + (255,), radius=40)
    s.item(hstack([badge, T(txt, 84, WHITE)], gap=36), WD / 2, 440 + i * 170, g(B, ph))

# ---------------- 9. N07 trap 4
B = 'N07'
a = SECTION_B[7]
t_owe = g(B, 'If you owe')
s = add(Navy(a, t_owe))
title_card(s, 'TRAP #4', '"WE\'LL PAY OFF\nYOUR OLD CAR"', a + 0.05, bottom_size=96)
t_ed = g(B, 'Edmunds says')
t_roll = g(B, 'They roll it')
s = add(Navy(t_owe, t_ed))


def debt_fn(img, lt):
    gt_ = t_owe + lt
    d = ImageDraw.Draw(img)
    p = ease_io((gt_ - t_roll) / 0.9)
    grow = 1 + 0.18 * p
    nw, nh = 560 * grow, 380 * grow
    ncx, ncy = 1280, 540
    d.rounded_rectangle([ncx - nw / 2, ncy - nh / 2, ncx + nw / 2, ncy + nh / 2], 34, fill=(20, 33, 60),
                        outline=YEL, width=6)
    fl = font(FONT_BLACK, 84)
    lab = 'NEW LOAN'
    d.text((ncx - fl.getlength(lab) / 2, ncy - nh / 2 + 34), lab, font=fl, fill=WHITE)
    if p >= 0.98:
        f2 = font(FONT_XB, 52)
        l2 = '+ OLD DEBT inside'
        d.text((ncx - f2.getlength(l2) / 2, ncy + nh / 2 - 100), l2, font=f2, fill=RED)
    sc = 1 - 0.45 * p
    ow, oh = 420 * sc, 260 * sc
    ocx = 520 + (ncx - 520) * p
    ocy = 540 + 40 * p
    a_in = ease_out((gt_ - t_owe) / 0.2)
    if p < 1:
        box = Image.new('RGBA', (int(ow) + 8, int(oh) + 8), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle([2, 2, ow + 2, oh + 2], 28, fill=RED + (int(255 * a_in),))
        fo = font(FONT_BLACK, max(10, int(72 * sc)))
        bd.text(((ow - fo.getlength('OLD DEBT')) / 2 + 2, oh / 2 - 44 * sc), 'OLD DEBT', font=fo,
                fill=(255, 255, 255, int(255 * a_in)))
        img.paste(box, (int(ocx - ow / 2), int(ocy - oh / 2)), box)


s.fn(debt_fn, t_owe, t_ed)
t_those = g(B, 'Those buyers')
L = t_those - t_ed
s = add(Screen(t_ed, t_those, 'G06', [(max(3.6, 15.0 - L), 15.0), (18.4, 23.7)]))
add_label(s, 'Source: Edmunds, Q2 2026')
s = add(Navy(t_those, SECTION_B[8]))
s.item(T('$944/mo', 200, YEL), WD / 2, 400, g(B, 'nine hundred forty-four'))
s.item(T('$16,270 interest', 130, YEL), WD / 2, 640, g(B, 'sixteen thousand'))
s.item(T('NEGATIVE-EQUITY BUYERS · Q2 2026 AVERAGE', 40, GREY, FONT_XB, shadow=False), WD / 2, 800,
       g(B, 'sixteen thousand') + 0.3)

# ---------------- 10. N08 law & consequences
B = 'N08'
a = SECTION_B[8]
t_today = g(B, 'Today, the only')
t_jan = g(B, 'In January')
s = add(Screen(a, t_today, 'G07', [(max(0.8, 11.0 - (t_jan - a)), 11.0), (14.8, 22.6)], fy=0.3))
add_label(s, 'Source: 5th Circuit, Jan 27 2025')
st = T('VACATED', 190, RED, stroke=0, shadow=False)
stamp = Image.new('RGBA', (st.width + 60, st.height + 40), (0, 0, 0, 0))
sd = ImageDraw.Draw(stamp)
sd.rounded_rectangle([6, 6, stamp.width - 6, stamp.height - 6], 24, outline=RED, width=14)
stamp.alpha_composite(st, (30, 20))
stamp = stamp.rotate(14, expand=True, resample=Image.BICUBIC)
s.item(stamp, WD / 2 + 180, HT / 2 + 40, g(B, 'threw it out.'))
t_res = g(B, 'And the results')
s = add(Navy(t_today, t_res))
s.item(T('THE ONLY PERSON', 110, WHITE), WD / 2, 360, t_today)
s.item(T('PROTECTING YOU…', 110, WHITE), WD / 2, 500, t_today)
s.item(T('IS YOU.', 200, YEL), WD / 2, 720, g(B, 'is you.'))
t_24 = g(B, 'And in twenty twenty-four')
t_share = g(B, 'the share of')
s = add(Screen(t_res, t_24, 'G08', [(max(0.3, 6.2 - (t_share - t_res)), 6.2), (12.3, 22.0)], fy=0.4))
add_label(s, 'Source: Fitch via Bloomberg, Oct 2025')
s = add(Screen(t_24, SECTION_B[9], 'G09', [(0.3, 6.2), (6.3, 9.6)], fy=0.2))
add_label(s, 'Source: Cox Automotive (est.)')
card = panel(vstack([T('1.73M', 170, YEL), T('REPOSSESSED (2024)', 64, WHITE)], gap=-16), pad=(70, 30),
             fill=(11, 20, 38, 240), outline=YEL + (255,), radius=30)
s.item(card, WD / 2, HT / 2 + 60, g(B, 'one point seven'))

# ---------------- 11. N09 playbook
B = 'N09'
a = SECTION_B[9]
s = add(Navy(a, SECTION_B[10]))
s.item(T('YOUR PLAYBOOK', 120, YEL), WD / 2, 150, a + 0.05)
moves = [('One:', 'GET PRE-APPROVED FIRST'), ('Two:', 'ASK: "WHAT\'S THE BUY RATE?"'),
         ('Three:', 'NEGOTIATE OUT-THE-DOOR PRICE'), ('Four:', 'ITEMIZE EVERY EXTRA'),
         ('Five:', 'NO BLANKS. NO "CONDITIONAL".')]
for i, (w_, txt) in enumerate(moves):
    num = T(f'#{i + 1}', 84, YEL)
    row = hstack([num, T(txt, 70, WHITE)], gap=30)
    row_canvas = Image.new('RGBA', (1500, row.height), (0, 0, 0, 0))
    row_canvas.alpha_composite(row, (0, 0))
    s.item(row_canvas, WD / 2, 320 + i * 150, g(B, w_, after='desk.'))

# ---------------- 12. N10 close
B = 'N10'
a = SECTION_B[10]
t_logo2 = g(B, 'This is WorthWired.')
s = add(Cars(a, t_logo2, a, t_logo2, 1.08, 1.0))
s.item(plus14, 1395, 470, a - 1.0)
t_strike = g(B, 'Now you know it.')


def strike_fn(img, lt):
    p = ease_out(lt / 0.45)
    d = ImageDraw.Draw(img)
    x0, x1 = 1395 - plus14.width / 2 + 30, 1395 + plus14.width / 2 - 30
    d.line([x0, 490, x0 + (x1 - x0) * p, 455], fill=YEL, width=22)


s.fn(strike_fn, t_strike, t_logo2)
q = T('What did a dealer promise you?', 70, WHITE, FONT_BLACK, shadow=False)
cq = panel(hstack([q, emoji_img('👇', 76)], gap=20), pad=(50, 26), fill=(11, 20, 38, 235), outline=YEL + (255,))
s.item(cq, WD / 2, 880, g(B, 'comments:'))
lg = add(Navy(t_logo2, END))
lg.item(logo_el(), WD / 2, HT / 2, t_logo2)

# ====================================================================== B-roll inserts (drawn over the shot list)
INSERTS = []
t_bec = g('N03', 'Because inside')
INSERTS.append(SellerStill(t_bec, t_bec + 3.0))
t_ = g('N04', 'When the dealer')
INSERTS.append(Dram(t_, t_ + 2.5, 'D2', 0.0, COOL, 1.5))
t_ = g('N05', 'Sometimes useful')
INSERTS.append(Dram(t_, t_ + 2.5, 'D3', 0.0, COOL, 1.5))
t_ = g('N06', 'You sign,')
INSERTS.append(Dram(t_, t_ + 3.0, 'D4', 0.0, COOL, 1.5))
t_ = g('N07', "We'll pay off")
INSERTS.append(Dram(t_, t_ + 2.5, 'D1', 0.0, COOL, 1.5))
t_ = g('N10', 'Not knowing')
keys = Dram(t_, max(t_ + 2.0, g('N10', 'Now you know it.')), 'D4', grade=COOL, still_at=1.6)


def keys_strike(img, lt):
    p = ease_out((lt - 0.35) / 0.45)
    if p <= 0:
        return
    d = ImageDraw.Draw(img)
    d.line([430, 700, 430 + 1060 * p, 700 - 330 * p], fill=YEL, width=22)


keys.fn(keys_strike)
INSERTS.append(keys)
INSERTS.sort(key=lambda x: x.t0)
# items hidden under an insert pop when the insert ends
for sh in shots:
    fixed = []
    for el, cx, cy, ta, tb in sh.items:
        for ins in INSERTS:
            if ins.t0 <= ta < ins.t1:
                ta = ins.t1
        fixed.append((el, cx, cy, ta, tb))
    sh.items = fixed
for ins in INSERTS:
    assert not any(ins.t0 < b_ < ins.t1 for b_ in SECTION_B), ('insert crosses a section', ins.t0)

shots.sort(key=lambda x: x.t0)
for a_, b_ in zip(shots, shots[1:]):
    assert abs(a_.t1 - b_.t0) < 1e-6, (a_.t0, a_.t1, b_.t0, type(a_).__name__, type(b_).__name__)
assert shots[0].t0 == 0 and abs(shots[-1].t1 - END) < 1e-6

# ====================================================================== audio
SR = 48000


def decode(path, start=None, dur=None):
    cmd = ['ffmpeg', '-v', 'error']
    if start is not None:
        cmd += ['-ss', f'{start:.3f}']
    cmd += ['-i', path]
    if dur is not None:
        cmd += ['-t', f'{dur:.3f}']
    cmd += ['-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).copy()


def rms(x):
    x = x[np.abs(x) > 1e-4]
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else 1e-6


def swoosh(dur=0.32):
    n = int(SR * dur)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n).astype(np.float64)
    out = np.zeros(n)
    y1 = y2 = 0.0
    for i in range(n):  # resonant band-pass sweeping 400 Hz -> 5 kHz
        p = i / n
        fc = 400 * (5000 / 400) ** p
        w0 = 2 * math.pi * fc / SR
        q = 2.5
        alpha = math.sin(w0) / (2 * q)
        a0 = 1 + alpha
        b0 = alpha / a0
        a1 = -2 * math.cos(w0) / a0
        a2 = (1 - alpha) / a0
        x = noise[i]
        y = b0 * x - b0 * (noise[i - 2] if i >= 2 else 0) - a1 * y1 - a2 * y2
        y2, y1 = y1, y
        out[i] = y
    env = np.minimum(np.linspace(0, 1, n) / 0.35, 1) * np.exp(-np.linspace(0, 1, n) * 3.0)
    out = out * env
    return (out / np.max(np.abs(out)) * 0.5).astype(np.float32)


def fade_edges(x, ms=12):
    k = min(len(x) // 2, int(SR * ms / 1000))
    if k > 0:
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
    return x


def write_wav(path, st):
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())


def read_wav(path):
    with wave.open(path) as wf:
        x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32767
        return x.reshape(-1, wf.getnchannels())


def loudnorm(src, dst, I=-14, TP=-1.5):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', src, '-af',
                        f'loudnorm=I={I}:TP={TP}:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    js = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f'loudnorm=I={I}:TP={TP}:LRA=11:linear=true:measured_I={{input_i}}:measured_TP={{input_tp}}:'
          'measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}').format(**js)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', af + ',aresample=48000', '-ar', '48000',
                    '-c:a', 'pcm_s16le', dst], check=True)


MUSIC_LUFS = -12.0          # measured integrated loudness of MUSICA.mp3
BAR = 4 * 60 / 95.0         # 95 BPM, 4/4


def music_bed(n):
    m = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(DRAM_DIR, 'music.mp3'), '-ac', '2',
                                      '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout,
                      np.float32).reshape(-1, 2).copy()
    LE, X, xf = 66 * BAR, 4 * BAR, 2.0       # loop out on bar 66 into bar 4, 2 s equal-power crossfade
    out = m[:int((LE + xf / 2) * SR)].copy()
    pos_end = LE
    k = int(xf * SR)
    th = np.linspace(0, np.pi / 2, k)[:, None]
    while len(out) < n:
        seg = m[int((X - xf / 2) * SR):int((LE + xf / 2) * SR)]
        st = int((pos_end - xf / 2) * SR)
        out = np.concatenate([out[:st], out[st:st + k] * np.cos(th) + seg[:k] * np.sin(th), seg[k:]])
        pos_end += LE - X
    return out[:n]


def voice_intervals():
    iv = []
    for b in BLOCKS:
        for w in AL[b]:
            if b == 'N02b' and w['s'] < N02B_TRIM:
                continue
            sh = INS if (b == 'N03' and w['s'] >= N03_SPLIT) else 0.0
            iv.append([OFF[b] + w['s'] + sh, OFF[b] + w['e'] + sh])
    iv.sort()
    merged = [iv[0]]
    for a_, b_ in iv[1:]:
        if a_ - merged[-1][1] < 0.8:
            merged[-1][1] = max(merged[-1][1], b_)
        else:
            merged.append([a_, b_])
    return merged


def music_env(n):
    """Music gain (linear) per sample following the brief's levels."""
    cr = 100
    m = int(n / SR * cr) + 2
    tt = np.arange(m) / cr
    lev = np.full(m, -18.0)                              # cards / moments without voice
    first = None
    for a_, b_ in voice_intervals():
        first = a_ if first is None else first
        lev[(tt >= a_ - 0.15) & (tt < b_ + 0.25)] = -28.0
    lev[tt < first] = -22.0
    t_ok = OFF['N09'] + word_time('N09', 'Okay.')
    n09 = (tt >= t_ok + 0.5) & (tt < block_end('N09') + 0.3)
    lev[n09 & (lev < -18)] = -24.0                       # lift after the drop
    for a_, b_ in [(DRAM0, DRAM1), (INS_T0, INS_T1)]:
        lev[(tt >= a_ - 0.1) & (tt < b_ + 0.05)] = -32.0
    lin = 10 ** ((lev - MUSIC_LUFS) / 20)
    w = int(0.3 * cr)
    lin = np.convolve(np.pad(lin, (w, w), mode='edge'), np.ones(2 * w + 1) / (2 * w + 1), 'same')[w:-w]
    drop = np.ones(m)
    drop[(tt >= t_ok) & (tt < t_ok + 0.5)] = 0.0
    drop = np.convolve(np.pad(drop, (4, 4), mode='edge'), np.ones(9) / 9, 'same')[4:-4]
    lin *= drop
    fo = tt > END - 3.0
    lin[fo] *= np.clip((END - tt[fo]) / 3.0, 0, 1)
    return np.interp(np.arange(n) / SR, tt, lin).astype(np.float32)


def build_audio():
    total = int(SR * END)
    voice = np.zeros(total, np.float32)
    narr = {b: decode(os.path.join(W, 'narr', b + '.mp3')) for b in BLOCKS}
    voice_rms = rms(np.concatenate(list(narr.values())))

    def place(x, t0):
        i = int(round(t0 * SR))
        voice[i:i + len(x)] += x[:max(0, total - i)]

    for b in BLOCKS:
        x = narr[b]
        if b == 'N03':
            k = int(N03_SPLIT * SR)
            place(x[:k], OFF[b])
            place(x[k:], OFF[b] + N03_SPLIT + INS)
        elif b == 'N02b':
            k = int(N02B_TRIM * SR)
            place(fade_edges(x[k:].copy(), 15), OFF[b] + N02B_TRIM)
        else:
            place(x, OFF[b])
    for n in ['D1', 'D2', 'D3', 'D4']:
        a_, b_ = dram_times[n]
        x = decode(os.path.join(DRAM_DIR, n + '.mp4'), 0.0, b_ - a_)
        place(fade_edges(x * (voice_rms / rms(x)), 25), a_)
    x = decode(os.path.join(DRAM_DIR, 'D3.mp4'), INSERT_D3[0], INS)
    place(fade_edges(x * (voice_rms / rms(x)), 25), INS_T0)
    vraw = os.path.join(OUT, 'v2_voice_raw.wav')
    write_wav(vraw, np.stack([voice, voice], 1))
    vn = os.path.join(OUT, 'v2_voice_norm.wav')
    loudnorm(vraw, vn)
    v = read_wav(vn)[:total]
    if len(v) < total:
        v = np.pad(v, ((0, total - len(v)), (0, 0)))
    mus = music_bed(total) * music_env(total)[:, None]
    mix = v + mus
    k = int(SR * 1.0)
    mix[-k:] *= np.linspace(1, 0, k)[:, None]
    raw = os.path.join(OUT, 'v2_mix_raw.wav')
    write_wav(raw, mix)
    final = os.path.join(OUT, 'v2_mix.wav')
    loudnorm(raw, final)
    return final


# ====================================================================== subtitles
def srt_time(x):
    x = max(0, x)
    h = int(x // 3600)
    m = int(x % 3600 // 60)
    s = x % 60
    return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}'


def build_srt():
    cues = {'en': [], 'es': []}
    idx = {b: 0 for b in BLOCKS}
    for line in open(os.path.join(W, 'cues.txt')):
        b, en, es = line.rstrip('\n').split('|')
        n = len(en.split())
        ws = AL[b][idx[b]:idx[b] + n]
        idx[b] += n
        if b == 'N02b' and ws[0]['s'] < N02B_TRIM:
            continue                                  # quote removed from N02b
        a = OFF[b] + ws[0]['s'] + (INS if b == 'N03' and ws[0]['s'] >= N03_SPLIT else 0)
        e = OFF[b] + ws[-1]['e'] + (INS if b == 'N03' and ws[-1]['e'] > N03_SPLIT else 0)
        cues['en'].append((a, e, en))
        cues['es'].append((a, e, es))
    for n in ['D1', 'D2', 'D3', 'D4']:
        a0 = dram_times[n][0]
        wd = AD['V' + n[1]]
        cues['en'].append((a0 + wd[0][1], a0 + wd[-1][2], DRAM[n][1]))
        cues['es'].append((a0 + wd[0][1], a0 + wd[-1][2], DRAM[n][2]))
    wd = [w for w in AD['V3'] if w[1] >= INSERT_D3[0] - 0.01]
    cues['en'].append((INS_T0 + wd[0][1] - INSERT_D3[0], INS_T0 + wd[-1][2] - INSERT_D3[0],
                       'From just four ninety-nine a month!'))
    cues['es'].append((INS_T0 + wd[0][1] - INSERT_D3[0], INS_T0 + wd[-1][2] - INSERT_D3[0],
                       '¡Desde solo cuatro noventa y nueve al mes!'))
    for lang in cues:
        cs = sorted(cues[lang])
        out = []
        for i, (a, e, txt) in enumerate(cs):
            nxt = cs[i + 1][0] if i + 1 < len(cs) else e + 2
            e2 = min(max(e + 0.25, a + 1.0), nxt - 0.04)
            lines = [txt]
            if len(txt) > 42:   # balanced two-line split at the space nearest the middle
                sp = [i for i, c in enumerate(txt) if c == ' ']
                k = min(sp, key=lambda i: abs(i - len(txt) / 2))
                lines = [txt[:k], txt[k + 1:]]
            out.append(f'{i + 1}\n{srt_time(a)} --> {srt_time(e2)}\n' + '\n'.join(lines) + '\n')
        open(os.path.join(OUT, f'WW002_{lang}.srt'), 'w', encoding='utf-8').write('\n'.join(out))


# ====================================================================== render
def fade_factor(gt):
    f = 1.0
    for b in SECTION_B:
        d = abs(gt - b)
        if d < 0.1:
            f = min(f, d / 0.1)
    if gt > END - 1.0:
        f = min(f, max(0.0, (END - gt) / 1.0))
    return f


def render(video_path, t_from=0.0, t_to=None, scale=1.0):
    t_to = END if t_to is None else t_to
    ow, oh = int(WD * scale) // 2 * 2, int(HT * scale) // 2 * 2
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{ow}x{oh}', '-r', '30',
           '-i', '-', '-c:v', 'libx264', '-preset', 'medium' if scale == 1 else 'veryfast', '-crf',
           '17' if scale == 1 else '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', video_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    si = 0
    import time
    tt = time.time()
    for i in range(n0, n1):
        gt = i / FPS
        while shots[si].t1 <= gt and si < len(shots) - 1:
            shots[si].close()
            si += 1
        while shots[si].t0 > gt and si > 0:
            si -= 1
        ins = next((x for x in INSERTS if x.t0 <= gt < x.t1), None)
        if ins is not None:
            shots[si].base_skip = True
            img = ins.render(gt)
        else:
            img = shots[si].render(gt)
        f = fade_factor(gt)
        if f < 1.0:
            img = Image.eval(img, lambda v, f=f: int(v * f))
        if scale != 1.0:
            img = img.resize((ow, oh), Image.BILINEAR)
        p.stdin.write(img.tobytes())
        if (i - n0) % 300 == 0:
            el = time.time() - tt
            print(f'frame {i}/{n1}  t={gt:.1f}s  {el:.0f}s elapsed', flush=True)
    p.stdin.close()
    p.wait()
    for s_ in shots + INSERTS:
        s_.close()


def chapters():
    marks = [('Same car, $14,000 more', 0.0), ('The promise', SECTION_B[0]), ('The $14,000 gap', SECTION_B[3]),
             ('Trap 1: The hidden markup', SECTION_B[4]), ('Trap 2: The extras', SECTION_B[5]),
             ('Trap 3: "Take it home today"', SECTION_B[6]), ('Trap 4: "We\'ll pay off your old car"', SECTION_B[7]),
             ('The rule that got thrown out', SECTION_B[8]), ('Your 5-step playbook', SECTION_B[9])]
    lines = []
    for name, t_ in marks:
        sec = int(math.ceil(t_))   # first whole second inside the section
        lines.append(f'{sec // 60}:{sec % 60:02d} {name}')
    lines[0] = '0:00 Same car, $14,000 more'
    return '\n'.join(lines)


if __name__ == '__main__':
    print(f'END={END:.2f}s  ads {ADS0:.2f}  dram {DRAM0:.2f}-{DRAM1:.2f}  insert {INS_T0:.2f}')
    print(chapters())
    open(os.path.join(OUT, 'WW002_chapters.txt'), 'w').write(chapters() + '\n')
    json.dump({'END': END, 'OFF': OFF, 'dram': dram_times, 'inserts': [(x.t0, x.t1, type(x).__name__) for x in INSERTS], 'insert': [INS_T0, INS_T1], 'sections': SECTION_B,
               'shots': [(round(s_.t0, 2), round(s_.t1, 2), type(s_).__name__, getattr(s_, 'name', ''))
                         for s_ in shots]},
              open(os.path.join(OUT, 'timeline_v2.json'), 'w'), indent=1)
    if '--srt' in sys.argv or '--all' in sys.argv:
        build_srt()
        print('srt done')
    if '--audio' in sys.argv or '--all' in sys.argv:
        print('audio:', build_audio())
    for a in sys.argv:
        if a.startswith('--part='):
            p0, p1 = (float(x) for x in a.split('=')[1].split(':'))
            render(os.path.join(OUT, f'v2part_{int(p0):04d}.mp4'), p0, min(p1, END))
    if ONLY:
        render(os.path.join(OUT, f'v2preview_{ONLY[0]:.0f}_{ONLY[1]:.0f}.mp4'), ONLY[0], ONLY[1], 0.5)
    if '--video' in sys.argv or '--all' in sys.argv:
        render(os.path.join(OUT, 'video.mp4'))
        print('video done')
