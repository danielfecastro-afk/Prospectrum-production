"""Graphics for the MiMi Casa Pumpkin Patch short: intro frames, title/leaves/end
overlays (RGBA PNG sequences) and the karaoke ASS file."""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = sys.argv[1]
AVATAR = sys.argv[2]
W, H, FPS = 1080, 1920, 30
FONT = f"{S}/fonts/Fredoka-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
ORANGE = (0xFF, 0x8A, 0x1F)


def ease_back(t):  # 0..1 -> overshooting 0..1
    c1 = 1.9; c3 = c1 + 1
    t = min(max(t, 0), 1)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160)); ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)


def word_img(text, size, fill, stroke, sw, shadow=True):
    f = ImageFont.truetype(FONT, size)
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    pad = 24
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad))
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new("RGBA", im.size)
        ImageDraw.Draw(sh).text((pad - l + 6, pad - t + 10), text, font=f, fill=(90, 35, 0, 150),
                                stroke_width=sw, stroke_fill=(90, 35, 0, 150))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d.text((pad - l, pad - t), text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    return im


def paste_scaled(canvas, im, cx, cy, s, alpha=1.0):
    if s <= 0.01 or alpha <= 0: return
    w, h = max(1, int(im.width * s)), max(1, int(im.height * s))
    r = im.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        a = r.getchannel("A").point(lambda v: int(v * alpha)); r.putalpha(a)
    canvas.alpha_composite(r, (int(cx - w / 2), int(cy - h / 2)))


# ---------- falling leaves ----------
LEAF_COLS = [(232, 106, 23), (214, 64, 30), (246, 170, 40), (190, 80, 30), (250, 196, 70)]


def leaf_sprite(col, size):
    im = Image.new("RGBA", (size * 2, size * 2)); d = ImageDraw.Draw(im)
    pts = []
    for i in range(40):  # pointed leaf outline
        a = 2 * math.pi * i / 40
        r = size * (0.55 + 0.45 * abs(math.cos(a)) ** 0.6) * (1 - 0.25 * abs(math.sin(3 * a)))
        pts.append((size + r * math.cos(a), size + 0.55 * r * math.sin(a)))
    d.polygon(pts, fill=col + (235,))
    d.line([(size * 0.15, size), (size * 1.85, size)], fill=tuple(int(c * 0.7) for c in col) + (235,), width=max(2, size // 12))
    return im


class Leaves:
    def __init__(self, n, seed):
        rnd = random.Random(seed)
        self.l = []
        for _ in range(n):
            sz = rnd.randint(22, 44)
            self.l.append(dict(spr=leaf_sprite(rnd.choice(LEAF_COLS), sz), x=rnd.uniform(0, W),
                               y0=rnd.uniform(-H, H), v=rnd.uniform(170, 300), sway=rnd.uniform(30, 90),
                               fw=rnd.uniform(0.6, 1.4), ph=rnd.uniform(0, 6.28), rot=rnd.uniform(-90, 90),
                               rv=rnd.uniform(-120, 120)))

    def draw(self, canvas, t, alpha=1.0):
        for L in self.l:
            y = (L["y0"] + L["v"] * t) % (H + 200) - 100
            x = L["x"] + L["sway"] * math.sin(L["fw"] * t * 2 + L["ph"])
            spr = L["spr"].rotate(L["rot"] + L["rv"] * t, resample=Image.BICUBIC, expand=True)
            if alpha < 1:
                spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
            canvas.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height / 2)))


def render_seq(name, n, fn):
    d = f"{S}/ov/{name}"; os.makedirs(d, exist_ok=True)
    for i in range(n):
        fn(i / FPS).save(f"{d}/{i:04d}.png", compress_level=1)


# ---------- intro (0.0-1.0, opaque) ----------
def intro():
    av = Image.open(AVATAR).convert("RGB")
    sz = av.width
    r0, r1 = 4 * (sz / 2 - 618), 4 * (sz / 2 + 618)  # 4x supersampled circle inside the yellow ring
    mask = Image.new("L", (sz * 4, sz * 4)); ImageDraw.Draw(mask).ellipse((r0, r0, r1, r1), fill=255)
    mask = mask.resize((sz, sz), Image.LANCZOS)
    logo = av.convert("RGBA"); logo.putalpha(mask)
    logo = logo.crop(logo.getbbox())
    bg = av.resize((H, H), Image.LANCZOS).crop(((H - W) // 2, 0, (H - W) // 2 + W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(38))
    warm = Image.new("RGB", (W, H), (255, 150, 60))
    bg = Image.blend(bg, warm, 0.28).convert("RGBA")
    # soft vignette
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    vig = Image.fromarray((np.clip(r - 0.55, 0, 1) * 200).astype(np.uint8))
    bg.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 90), Image.new("L", (W, H), 30),
                                             Image.new("L", (W, H), 0), vig)))
    # glow behind logo
    glow = Image.new("RGBA", (W, H)); ImageDraw.Draw(glow).ellipse((W / 2 - 520, H / 2 - 520, W / 2 + 520, H / 2 + 520),
                                                                  fill=(255, 235, 170, 170))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    base = 940 / logo.width

    def frame(t):
        c = bg.copy()
        p = t / 0.42
        s = base * ease_back(p) * (1 + 0.04 * max(0, t - 0.42))  # pop, then slow push
        c.alpha_composite(glow)
        paste_scaled(c, logo, W / 2, H / 2, s)
        # flash: bright burst peaking at 0.30 s
        fa = max(0.0, 1 - abs(t - 0.30) / 0.16)
        if fa > 0:
            fl = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(fl)
            cx, cy = W / 2, H / 2
            for k in range(14):  # star rays
                a = 2 * math.pi * k / 14 + 0.2
                d.polygon([(cx + 40 * math.cos(a + 1.57), cy + 40 * math.sin(a + 1.57)),
                           (cx + 1100 * math.cos(a), cy + 1100 * math.sin(a)),
                           (cx - 40 * math.cos(a + 1.57), cy - 40 * math.sin(a + 1.57))], fill=(255, 250, 225, int(150 * fa)))
            d.ellipse((cx - 600, cy - 600, cx + 600, cy + 600), fill=(255, 255, 240, int(150 * fa)))
            c.alpha_composite(fl.filter(ImageFilter.GaussianBlur(18)))
        return c.convert("RGB")

    d = f"{S}/ov/intro"; os.makedirs(d, exist_ok=True)
    for i in range(FPS):
        frame(i / FPS).save(f"{d}/{i:04d}.png", compress_level=1)


# ---------- title + leaves (timeline 1.0-7.5) ----------
def title():
    words = [("PUMPKIN", 470, 0.10), ("PATCH", 650, 0.42), ("SONG", 830, 0.74)]
    imgs = [word_img(w, 200, ORANGE, (255, 255, 255), 18) for w, _, _ in words]
    pump = emoji_img("🎃", 150)
    leaves = Leaves(16, 1)

    def frame(t):
        c = Image.new("RGBA", (W, H))
        leaves.draw(c, t + 3)
        out = max(0.0, (t - 6.15) / 0.3)  # exit before the cut
        for (w, y, t0), im in zip(words, imgs):
            p = (t - t0) / 0.38
            if p <= 0: continue
            s = ease_back(p) * (1 + 0.025 * math.sin(2 * math.pi * (t - t0) * 116 / 60)) if p >= 1 else ease_back(p)
            x = W / 2 - (95 if w == "SONG" else 0)
            paste_scaled(c, im, x, y - 25 * math.sin(min(p, 1) * math.pi), s * (1 - 0.2 * out), 1 - min(out, 1))
        p = (t - 1.06) / 0.38
        if p > 0:
            sx = W / 2 + imgs[2].width / 2 - 95 + 40
            paste_scaled(c, pump, sx, 830, ease_back(p) * (1 - 0.2 * out), 1 - min(out, 1))
        return c

    render_seq("title", int(6.5 * FPS), frame)


def bridge():
    leaves = Leaves(16, 2)
    render_seq("bridge", int(0.6 * FPS), lambda t: (lambda c: (leaves.draw(c, t + 9), c)[1])(Image.new("RGBA", (W, H))))


def ending():  # timeline 70.3-78.8: leaves throughout, end card from 76.5
    leaves = Leaves(18, 3)
    l1 = word_img("Family first,", 132, (255, 255, 255), ORANGE, 14)
    l2 = word_img("siempre!", 150, (255, 214, 0), ORANGE, 15)
    heart = emoji_img("❤️", 130)

    def frame(t):
        c = Image.new("RGBA", (W, H))
        leaves.draw(c, t + 5)
        te = t - 6.2  # 76.5
        if te > 0:
            band = Image.new("RGBA", (W, H)); ImageDraw.Draw(band).rounded_rectangle(
                (60, 1040, W - 60, 1420), 60, fill=(120, 50, 10, int(110 * min(1, te / 0.3))))
            c.alpha_composite(band.filter(ImageFilter.GaussianBlur(10)))
            paste_scaled(c, l1, W / 2, 1140, ease_back((te - 0.05) / 0.35))
            paste_scaled(c, l2, W / 2 - 75, 1310, ease_back((te - 0.30) / 0.35))
            hp = ease_back((te - 0.55) / 0.35) * (1 + 0.08 * max(0, math.sin(2 * math.pi * max(0, te - 0.9) * 1.93)))
            paste_scaled(c, heart, W / 2 + l2.width / 2 - 75 + 60, 1305, hp)
        return c

    render_seq("end", int(8.5 * FPS), frame)


# ---------- karaoke ASS ----------
LYRICS = [
    (8.0, "Off we go to the pumpkin patch,"), (10.9, "big ones, small ones, find a match!"),
    (14.6, "Crunchy leaves beneath our feet,"), (18.1, "autumn days are oh so sweet!"),
    (21.6, "Pumpkin, pumpkin, big and bright,"), (25.1, "God made the harvest, what a sight!"),
    (28.7, "Thank You, God, for the food we share,"), (32.3, "and for the love that's everywhere!"),
    (35.8, "This one's tall and this one's round,"), (39.4, "this one's sitting on the ground!"),
    (43.1, "I can't lift it, help me please!"), (46.9, "Papi lifts it up with ease!"),
    (50.2, "Mimi's baking pumpkin pie,"), (53.7, "smell it, smell it, oh my, my!"),
    (57.3, "Pumpkin, pumpkin, big and bright,"), (60.7, "God made the harvest, what a sight!"),
    (64.3, "Thank You, God, for the food we share,"), (67.9, "and for the love that's everywhere!"),
]
LINE_END = 70.3
CHORUS2_OFFSET = 35.57
SYL = {"pumpkin": 2, "crunchy": 2, "beneath": 2, "autumn": 2, "harvest": 2, "everywhere": 3,
       "sitting": 2, "papi": 2, "mimi's": 2, "baking": 2, "ease": 1, "please": 1}


def syl(w):
    k = w.lower().strip(",.!?")
    return SYL.get(k, 1)


def onset_env(path):
    s = np.fromfile(path, np.float32); h = 80; n = len(s) // h
    le = 20 * np.log10(np.sqrt((s[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-5)
    d = np.convolve(np.maximum(np.diff(le, prepend=le[0]), 0), [0.25, 0.5, 0.25], "same")
    return d


def ass_time(t):
    cs = int(round(t * 100)); return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def karaoke():
    env = onset_env(f"{S}/songv.raw")
    ev = []
    timing = []
    for i, (t0, line) in enumerate(LYRICS):
        t1 = LYRICS[i + 1][0] if i + 1 < len(LYRICS) else LINE_END
        words = line.split()
        tot = sum(syl(w) for w in words)
        step = min(0.30, (t1 - t0 - 0.45) / tot)
        starts, cum = [], 0
        for w in words:
            est = t0 + cum * step
            a, b = int((est - 0.09) * 100), int((est + 0.09) * 100)
            j = a + int(np.argmax(env[a:b + 1]))
            snapped = j / 100 if env[j] > 3 and (not starts or j / 100 > starts[-1] + 0.12) else est
            starts.append(snapped if cum else t0)  # first word = given line time
            cum += syl(w)
        if i >= 14:  # final chorus repeats chorus 1; measured offset song[57.07]~song[21.5]
            starts = [x + CHORUS2_OFFSET for x in timing[i - 10][1]]
        timing.append((line, starts))
        show0, show1 = t0 - 0.25, (t1 - 0.25 if i + 1 < len(LYRICS) else t1 - 0.06)  # no overlap with next line
        bounds = [show0] + starts + [show1]
        for k in range(len(words) + 1):
            a, b = bounds[k], bounds[k + 1]
            if b - a < 0.01: continue
            parts = []
            for m, w in enumerate(words):
                parts.append(("{\\1c&H0000D7FF&\\3c&H000E5AE0&}" + w + "{\\1c&H00FFFFFF&\\3c&H001F8AFF&}") if m == k - 1 else w)
            ev.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Lyric,,0,0,0,,{{\\fad(0,0)}}" + " ".join(parts))
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyric,Fredoka,84,&H00FFFFFF,&H00FFFFFF,&H001F8AFF,&H78301000,-1,0,0,0,100,100,1,0,1,8,3,2,80,80,{int(H * 0.235)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(f"{S}/lyrics.ass", "w").write(hdr + "\n".join(ev) + "\n")
    for line, st in timing:
        print(" ".join(f"{w}@{t:.2f}" for w, t in zip(line.split(), st)))


if __name__ == "__main__":
    what = sys.argv[3:] or ["intro", "title", "bridge", "ending", "karaoke"]
    for w in what: globals()[w]()
