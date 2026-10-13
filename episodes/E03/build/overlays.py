import json, os, sys, math, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1920, 1080, 24
FONT = f'{S}/fonts/Fredoka-Bold.ttf'
AVATAR = f'{S}/../images/1.webp'
OV = f'{S}/work/ov'
J = json.load(open(f'{S}/work/timeline.json'))
segs, TL = J['segs'], J['tl']
MANGO, CORAL, BROWN = (255, 201, 60), (242, 122, 107), (92, 40, 20)
ENC = ['-c:v', 'libx264', '-crf', '12', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-r', '24']
GRADE = 'eq=saturation=1.05,colorbalance=rs=0.015:bs=-0.015:rm=0.02:bm=-0.02:rh=0.01:bh=-0.01'


def font(sz):
    return ImageFont.truetype(FONT, sz)


def ease_out_back(x, s=1.9):
    x = min(max(x, 0), 1) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_out(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


def text_sprite(txt, sz, fill=MANGO, stroke=CORAL, sw=None, shadow=True):
    f = font(sz)
    sw = sw or max(4, sz // 11)
    l, t, r, b = f.getbbox(txt, stroke_width=sw)
    pad = sw * 3
    im = Image.new('RGBA', (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + sz * 0.04, pad - t + sz * 0.07), txt, font=f, fill=BROWN + (150,),
                                stroke_width=sw, stroke_fill=BROWN + (150,))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(sz * 0.05)))
    d = ImageDraw.Draw(im)
    d.text((pad - l, pad - t), txt, font=f, fill=BROWN, stroke_width=sw + max(3, sz // 30), stroke_fill=BROWN)
    d.text((pad - l, pad - t), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    # glossy highlight on upper half of the letters
    return im


def paste_scaled(canvas, spr, cx, cy, sc, alpha=1.0, rot=0.0):
    if sc <= 0.01 or alpha <= 0.01:
        return
    w, h = spr.size
    s = spr.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
    if rot:
        s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = s.getchannel('A').point(lambda v: int(v * alpha))
        s.putalpha(a)
    canvas.alpha_composite(s, (int(cx - s.size[0] / 2), int(cy - s.size[1] / 2)))


def avatar_circle(d):
    im = Image.open(AVATAR).convert('RGBA')
    cx, cy, r = 626, 620, 609
    im = im.crop((cx - r, cy - r, cx + r, cy + r))
    m = Image.new('L', (r * 8, r * 8), 0)
    ImageDraw.Draw(m).ellipse((0, 0, r * 8 - 1, r * 8 - 1), fill=255)
    im.putalpha(m.resize(im.size, Image.LANCZOS))
    return im.resize((d, d), Image.LANCZOS)


def save_seq(name, frames_fn, n):
    d = f'{OV}/{name}'
    os.makedirs(d, exist_ok=True)
    for k in range(n):
        frames_fn(k).save(f'{d}/{k:04d}.png', compress_level=1)


def read_frames(path, n, ss=0.0, vf=None):
    vf = vf or f'scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,{GRADE}'
    raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(ss), '-i', path, '-vf',
                          f'fps=24,{vf},tpad=stop_mode=clone:stop_duration=10', '-frames:v', str(n),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return [Image.fromarray(x).convert('RGBA') for x in a]


def encode_frames(frames, out):
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                          '-s', f'{W}x{H}', '-r', '24', '-i', '-', *ENC, out], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.convert('RGB').tobytes())
    p.stdin.close()
    p.wait()


def glow(size, color, alpha):
    g = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((size * .2, size * .2, size * .8, size * .8), fill=color + (int(255 * alpha),))
    return g.filter(ImageFilter.GaussianBlur(size * 0.12))


# ---------------------------------------------------------------- A1 intro
def make_A1():
    sg = segs[0]
    n = sg['n']
    bg = read_frames(f'{S}/dl/V01.mp4', n)
    av = avatar_circle(780)
    shadow = Image.new('RGBA', (900, 900), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((60, 80, 840, 860), fill=(40, 20, 10, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    frames = []
    for k in range(n):
        t = k / FPS
        b = bg[k].filter(ImageFilter.GaussianBlur(22))
        b = Image.blend(b, Image.new('RGBA', b.size, (255, 220, 170, 255)), 0.12)
        sc = 0.92 + 0.08 * ease_out(t / 2.6)
        paste_scaled(b, shadow, W / 2, H / 2, sc)
        paste_scaled(b, av, W / 2, H / 2, sc)
        # flash at ~0.55 s
        fl = max(0.0, 1 - abs(t - 0.55) / 0.12) if t < 0.55 else math.exp(-(t - 0.55) / 0.18)
        if fl > 0.01:
            paste_scaled(b, glow(1400, (255, 250, 230), 1.0), W / 2, H / 2, 1.6, alpha=0.85 * fl)
        # sparkle twinkles on the ring after the flash
        if 0.55 < t < 2.4:
            for j in range(6):
                ph = (t - 0.55) * 2.2 - j * 0.28
                if 0 < ph < 1:
                    ang = j * 1.05 + 0.4
                    x = W / 2 + math.cos(ang) * 400 * sc
                    y = H / 2 + math.sin(ang) * 400 * sc
                    paste_scaled(b, star_sprite(), x, y, math.sin(ph * math.pi) * 0.9, rot=ph * 90)
        # from black
        a = ease_out(t / 0.6)
        if a < 1:
            b = Image.blend(Image.new('RGBA', b.size, (0, 0, 0, 255)), b, a)
        frames.append(b)
    encode_frames(frames, f'{S}/work/segs/s000.mp4')


_star = None


def star_sprite():
    global _star
    if _star is None:
        s = Image.new('RGBA', (120, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(s)
        pts = []
        for i in range(8):
            r = 58 if i % 2 == 0 else 14
            a = i * math.pi / 4
            pts.append((60 + r * math.cos(a), 60 + r * math.sin(a)))
        d.polygon(pts, fill=(255, 250, 220, 255))
        _star = Image.alpha_composite(glow(120, (255, 230, 150), 0.8), s)
    return _star


# ---------------------------------------------------------------- A2 title
def make_title():
    n = segs[1]['n']
    lines = [['Thank', 'You,', 'God,'], ['for', 'My', 'Family!']]
    sz = 150
    sprites = [[text_sprite(w, sz, sw=14) for w in ln] for ln in lines]
    f = font(sz)
    space = f.getlength(' ') * 1.6
    layout = []
    order = 0
    for li, ln in enumerate(lines):
        widths = [f.getlength(w) for w in ln]
        tot = sum(widths) + space * (len(ln) - 1)
        x = W / 2 - tot / 2
        y = 330 + li * 185
        for wi, w in enumerate(ln):
            layout.append((sprites[li][wi], x + widths[wi] / 2, y, order))
            x += widths[wi] + space
            order += 1

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        out_a = 1 - ease_out((t - 3.7) / 0.3) if t > 3.7 else 1.0
        for spr, cx, cy, o in layout:
            t0 = 0.25 + o * 0.2
            p = (t - t0) / 0.45
            if p <= 0:
                continue
            sc = ease_out_back(p, 2.6)
            dy = -90 * (1 - ease_out(p)) + (math.sin((t - t0) * 5.65 + o) * 5 if p > 1 else 0)
            paste_scaled(c, spr, cx, cy + dy, sc, alpha=min(1, p * 3) * out_a)
        return c
    save_seq('title', fr, n)


# ---------------------------------------------------------------- B card
def make_card():
    n = int(2.5 * FPS)
    spr = text_sprite('Every good gift comes from God!', 96, sw=10)

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        sc = ease_out_back(t / 0.35, 2.4)
        a = 1 - ease_out((t - 2.2) / 0.3) if t > 2.2 else 1
        paste_scaled(c, spr, W / 2, 935, sc, alpha=a)
        return c
    save_seq('card', fr, n)


# ---------------------------------------------------------------- transition objects
def flower_sprite():
    s = 600
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(6):
        a = i * math.pi / 3
        cx, cy = s / 2 + math.cos(a) * 140, s / 2 + math.sin(a) * 140
        d.ellipse((cx - 120, cy - 120, cx + 120, cy + 120), fill=(255, 120, 170, 255), outline=(230, 80, 140, 255), width=8)
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 6
        cx, cy = s / 2 + math.cos(a) * 90, s / 2 + math.sin(a) * 90
        d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), fill=(255, 170, 200, 255))
    d.ellipse((s / 2 - 85, s / 2 - 85, s / 2 + 85, s / 2 + 85), fill=MANGO + (255,), outline=(240, 150, 40, 255), width=10)
    return im


def make_flower():
    n = int(0.8 * FPS)
    spr = flower_sprite()

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        fl = math.exp(-((t - 0.22) / 0.13) ** 2)
        c.alpha_composite(Image.new('RGBA', (W, H), (255, 150, 195, int(140 * fl))))
        sc = 0.15 + 2.4 * ease_out(t / 0.6)
        a = 1 if t < 0.25 else max(0, 1 - (t - 0.25) / 0.3)
        paste_scaled(c, spr, W / 2, H / 2, sc, alpha=a, rot=-t * 220)
        return c
    save_seq('flower', fr, n)


def spoon_sprite():
    im = Image.new('RGBA', (1100, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((330, 128, 1080, 172), radius=22, fill=(196, 130, 70, 255), outline=(140, 80, 35, 255), width=6)
    d.ellipse((20, 40, 380, 260), fill=(210, 145, 80, 255), outline=(140, 80, 35, 255), width=8)
    d.ellipse((60, 75, 330, 225), fill=(185, 118, 60, 255))
    d.ellipse((90, 90, 190, 140), fill=(240, 200, 150, 200))
    return im


def make_spoon():
    n = int(0.6 * FPS)
    spr = spoon_sprite()

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        p = ease_out(t / 0.5)
        x = W + 700 - p * (W + 1400)
        paste_scaled(c, spr, x, H / 2 + math.sin(p * math.pi) * -80, 1.1, rot=-12 + 24 * p)
        return c
    save_seq('spoon', fr, n)


def ball_sprite():
    s = 600
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cols = [(255, 90, 90), (255, 201, 60), (80, 190, 255), (120, 210, 110), (255, 255, 255), (255, 140, 200)]
    for i in range(6):
        d.pieslice((10, 10, s - 10, s - 10), i * 60, (i + 1) * 60, fill=cols[i] + (255,))
    d.ellipse((10, 10, s - 10, s - 10), outline=(120, 60, 30, 255), width=10)
    d.ellipse((s / 2 - 45, s / 2 - 45, s / 2 + 45, s / 2 + 45), fill=(255, 255, 255, 255))
    d.ellipse((120, 90, 260, 180), fill=(255, 255, 255, 110))
    return im


def make_ball():
    n = int(0.6 * FPS)
    spr = ball_sprite()

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        p = t / 0.5
        sc = 0.12 + 4.0 * p ** 2
        a = 1 if p < 0.6 else max(0, 1 - (p - 0.6) / 0.4)
        paste_scaled(c, spr, W / 2, H / 2 - 120 * math.sin(p * math.pi), sc, alpha=a, rot=t * 400)
        return c
    save_seq('ball', fr, n)


# ---------------------------------------------------------------- heart (V33)
def heart_sprite(s=360):
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    pts = []
    for i in range(200):
        a = i / 200 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((s / 2 + x * s / 38, s / 2 - y * s / 38 - s * 0.03))
    big = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.polygon(pts, fill=CORAL + (255,), outline=(200, 70, 70, 255), width=10)
    hl = [(s / 2 + (x - s / 2) * 0.5 - s * 0.1, s / 2 + (y - s / 2) * 0.5 - s * 0.1) for x, y in pts]
    d2 = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(d2).polygon(hl, fill=(255, 190, 180, 120))
    big.alpha_composite(d2.filter(ImageFilter.GaussianBlur(10)))
    return Image.alpha_composite(glow(s, (255, 150, 160), 0.6), big)


def make_heart(n):
    spr = heart_sprite()

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        pop = ease_out_back(t / 0.35, 2.2)
        beat = 1 + 0.12 * max(0, math.sin(t * 2 * math.pi * 1.6)) ** 3
        a = 1 if t < n / FPS - 0.25 else max(0, (n / FPS - t) / 0.25)
        paste_scaled(c, spr, W / 2, 190, pop * beat * 0.8, alpha=a)
        return c
    save_seq('heart', fr, n)


# ---------------------------------------------------------------- confetti
def make_confetti(n):
    rnd = random.Random(7)
    cols = [(255, 201, 60), (242, 122, 107), (255, 120, 170), (80, 190, 255), (120, 210, 110), (255, 255, 255)]
    parts = [dict(x=rnd.uniform(0, W), y=rnd.uniform(-H * 1.2, -20), vy=rnd.uniform(140, 260),
                  sw=rnd.uniform(0.5, 2.0), ph=rnd.uniform(0, 6.28), amp=rnd.uniform(20, 60),
                  w=rnd.uniform(14, 24), h=rnd.uniform(8, 14), c=rnd.choice(cols), spin=rnd.uniform(2, 6))
             for _ in range(110)]

    def fr(k):
        t = k / FPS
        c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        fade = min(1, t / 0.4, max(0, (n / FPS - t) / 0.6))
        for p in parts:
            y = (p['y'] + p['vy'] * t) % (H + 200) - 100
            x = p['x'] + math.sin(t * p['sw'] + p['ph']) * p['amp']
            fl = abs(math.cos(t * p['spin'] + p['ph']))
            hw, hh = p['w'] / 2, max(1.5, p['h'] / 2 * fl)
            a = t * p['spin'] * 0.5 + p['ph']
            ca, sa = math.cos(a), math.sin(a)
            pts = [(x + ca * dx - sa * dy, y + sa * dx + ca * dy) for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            d.polygon(pts, fill=p['c'] + (int(235 * fade),))
        return c
    save_seq('confetti', fr, n)


# ---------------------------------------------------------------- H closing
def make_H():
    sg = segs[-1]
    n = sg['n']
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-sseof', '-0.3', '-i',
                    f'{S}/work/segs/s{len(segs) - 2:03d}.mp4', '-update', '1', f'{S}/work/lastV39.png'])
    last = Image.open(f'{S}/work/lastV39.png').convert('RGBA')
    blurs = [last.filter(ImageFilter.GaussianBlur(r)) for r in range(0, 26, 2)]
    av = avatar_circle(560)
    txt = text_sprite('Thank you, God, for my family!', 96, sw=10)
    frames = []
    for k in range(n):
        t = k / FPS
        bi = min(len(blurs) - 1, int(t / 0.5 * (len(blurs) - 1)))
        b = Image.blend(blurs[bi], Image.new('RGBA', (W, H), (255, 225, 180, 255)), 0.12 * min(1, t / 0.5))
        sc = ease_out_back((t - 0.2) / 0.5, 2.0)
        paste_scaled(b, av, W / 2, 420, sc)
        p = (t - 0.7) / 0.45
        if p > 0:
            paste_scaled(b, txt, W / 2, 880, ease_out_back(p, 2.2), alpha=min(1, p * 2))
        a = 1 - ease_out((t - 3.0) / 1.0) if t > 3.0 else 1
        if a < 1:
            b = Image.blend(Image.new('RGBA', b.size, (0, 0, 0, 255)), b, max(a, 0))
        frames.append(b)
    encode_frames(frames, f'{S}/work/segs/s{len(segs) - 1:03d}.mp4')


if __name__ == '__main__':
    what = sys.argv[1:]
    seg_by = {i: s for i, s in enumerate(segs)}
    v33 = [s for s in segs if s['clip'] == 'V33']
    heart_t0 = v33[0]['m0'] + 5.0
    heart_n = round((v33[-1]['m1'] - heart_t0) * FPS)
    v07g = [s for s in segs if s['clip'] == 'V07'][-2]
    v08g = [s for s in segs if s['clip'] == 'V08'][-1]
    conf_t0, conf_t1 = v07g['m0'], v08g['m1']
    tr = {s['trans'][2]: s['m0'] for s in segs if s.get('trans') and s['trans'][2] in ('flower', 'spoon', 'ball')}
    v05 = [s for s in segs if s['clip'] == 'V05'][0]
    sched = {'title': segs[1]['m0'], 'card': v05['m1'] - 2.5, 'flower': tr['flower'] - 0.1,
             'spoon': tr['spoon'] - 0.05, 'ball': tr['ball'] - 0.05, 'heart': heart_t0, 'confetti': conf_t0}
    json.dump(sched, open(f'{OV}_sched.json', 'w'), indent=1)
    jobs = dict(A1=make_A1, title=make_title, card=make_card, flower=make_flower, spoon=make_spoon,
                ball=make_ball, heart=lambda: make_heart(heart_n),
                confetti=lambda: make_confetti(round((conf_t1 - conf_t0) * FPS)), H=make_H)
    for k in (what or [k for k in jobs if k != 'H']):
        jobs[k]()
        print('done', k, flush=True)
