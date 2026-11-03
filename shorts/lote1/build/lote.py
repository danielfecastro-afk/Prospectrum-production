"""Build one vertical Short (1080x1920/30) from the E03 master.
usage: lote.py <scratch> <name> [stage...]   stages: video gfx subs audio final qc"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S, NAME = sys.argv[1], sys.argv[2]
sys.path.insert(0, f"{S}/tools")
from lote_cfg import SHORTS
C = SHORTS[NAME]
SRC = f"{S}/lote/src/MiMiCasa_E03_master.mp4"
SEGS = json.load(open(f"{S}/e03b/work/timeline.json"))["segs"]
AVATAR = "/tmp/claude-0/-home-user-Prospectrum-production/50d1e345-c8df-5f1e-9821-a163fd0d5c61/images/1.webp"
FONT = f"{S}/fonts/Fredoka-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
W, H, FPS, SFPS = 1080, 1920, 30, 24
ORANGE = (0xFF, 0x8A, 0x1F)
WD = f"{S}/lote/{NAME}"; os.makedirs(WD, exist_ok=True)
F0, F1 = round(C["t0"] * SFPS), round(C["t1"] * SFPS)
T0, DUR = F0 / SFPS, (F1 - F0) / SFPS


def run(cmd):
    subprocess.run(cmd, check=True)


# ------------------------------------------------------------------ shots
def shot_spans():
    out = []
    for k, (si, mode, kf, ext, burn, hold) in enumerate(C["shots"]):
        s = SEGS[si]
        a, b = max(s["f0"], F0), min(s["f1"], F1)
        if hold or k == len(C["shots"]) - 1:
            b_src, b = b, F1
        else:
            b_src = b
        out.append(dict(seg=si, clip=s["clip"], mode=mode, kf=kf, ext=ext, burn=burn, a=a, b=b, b_src=b_src,
                        loc0=(a - s["f0"]) / SFPS))
    for x, y in zip(out, out[1:]):
        assert x["b"] == y["a"], (x, y)
    assert out[0]["a"] == F0 and out[-1]["b"] == F1
    return out


def xexpr(kf, loc0):
    # piecewise-linear centre x over shot-local time (seg time = loc0 + t)
    pts = [(t - loc0, x) for t, x in kf]
    if len(pts) == 1:
        return str(pts[0][1])
    e = str(pts[-1][1])
    for (ta, xa), (tb, xb) in reversed(list(zip(pts, pts[1:]))):
        seg = f"({xa}+({xb}-{xa})*(t-({ta}))/({tb}-({ta})))"
        e = f"if(lt(t\\,{tb})\\,{seg}\\,{e})"
    return f"if(lt(t\\,{pts[0][0]})\\,{pts[0][1]}\\,{e})"


def video():
    os.makedirs(f"{WD}/seg", exist_ok=True)
    lst = []
    for i, sp in enumerate(shot_spans()):
        h0 = sp["burn"] if isinstance(sp["burn"], int) and not isinstance(sp["burn"], bool) else (940 if sp["burn"] else 1080)
        n_src, n = sp["b_src"] - sp["a"], sp["b"] - sp["a"]
        pre = f"crop=1920:{h0}:0:0,"
        if sp["mode"] == "crop":
            w = int(round(h0 * 9 / 16 / 2) * 2)
            x = xexpr(sp["kf"], sp["loc0"])
            fc = f"[0:v]{pre}crop={w}:{h0}:'max(0\\,min(1920-{w}\\,{x}-{w}/2))':0,scale={W}:{H}:flags=lanczos[v0]"
        else:
            fc = (f"[0:v]{pre}split[a][b];[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
                  f"gblur=sigma=9,eq=brightness=-0.05:saturation=1.15,scale={W}:{H}:flags=bicubic[bg];"
                  f"[b]scale={W}:-2:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]")
        pad = f",tpad=stop_mode=clone:stop={n - n_src}" if n > n_src else ""
        fc += f";[v0]trim=end_frame={n_src}{pad},setsar=1,format=yuv420p[v]"
        out = f"{WD}/seg/{i:02d}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{sp['a'] / SFPS:.5f}", "-i", SRC, "-filter_complex", fc,
             "-map", "[v]", "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "12",
             "-r", str(SFPS), out])
        lst.append(f"file '{out}'")
        print(i, sp["clip"], sp["mode"], n, flush=True)
    open(f"{WD}/seg/list.txt", "w").write("\n".join(lst) + "\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{WD}/seg/list.txt", "-c", "copy",
         f"{WD}/base24.mp4"])


# ------------------------------------------------------------------ graphics
def ease_back(t):
    c1 = 1.9; c3 = c1 + 1; t = min(max(t, 0), 1)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160)); ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)


def word_img(text, size, fill, stroke, sw):
    f = ImageFont.truetype(FONT, size)
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    pad = 24
    im = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad))
    sh = Image.new("RGBA", im.size)
    ImageDraw.Draw(sh).text((pad - l + 6, pad - t + 10), text, font=f, fill=(90, 35, 0, 150),
                            stroke_width=sw, stroke_fill=(90, 35, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    return im


def paste_scaled(c, im, cx, cy, s, alpha=1.0):
    if s <= 0.01 or alpha <= 0: return
    w, h = max(1, int(im.width * s)), max(1, int(im.height * s))
    r = im.resize((w, h), Image.LANCZOS)
    if alpha < 1: r.putalpha(r.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(r, (int(cx - w / 2), int(cy - h / 2)))


def seq(name, n, fn):
    d = f"{WD}/{name}"; os.makedirs(d, exist_ok=True)
    for i in range(n): fn(i / FPS).save(f"{d}/{i:04d}.png", compress_level=1)


def intro():  # 0.0-1.0 s, opaque: avatar pop + flash (title is its own layer on top)
    av = Image.open(AVATAR).convert("RGB"); sz = av.width
    r0, r1 = 4 * (sz / 2 - 618), 4 * (sz / 2 + 618)
    m = Image.new("L", (sz * 4, sz * 4)); ImageDraw.Draw(m).ellipse((r0, r0, r1, r1), fill=255)
    logo = av.convert("RGBA"); logo.putalpha(m.resize((sz, sz), Image.LANCZOS)); logo = logo.crop(logo.getbbox())
    bg = av.resize((H, H), Image.LANCZOS).crop(((H - W) // 2, 0, (H - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(38))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (255, 150, 60)), 0.28).convert("RGBA")
    glow = Image.new("RGBA", (W, H)); ImageDraw.Draw(glow).ellipse((W / 2 - 430, 900 - 430, W / 2 + 430, 900 + 430),
                                                                  fill=(255, 235, 170, 170))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    base = 720 / logo.width

    def fr(t):
        c = bg.copy(); c.alpha_composite(glow)
        paste_scaled(c, logo, W / 2, 900, base * max(0.35, ease_back(t / 0.42)) * (1 + 0.04 * max(0, t - 0.42)))
        fa = max(0.0, 1 - abs(t - 0.30) / 0.16)
        if fa > 0:
            fl = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(fl); cx, cy = W / 2, 900
            for k in range(14):
                a = 2 * math.pi * k / 14 + 0.2
                d.polygon([(cx + 40 * math.cos(a + 1.57), cy + 40 * math.sin(a + 1.57)),
                           (cx + 1100 * math.cos(a), cy + 1100 * math.sin(a)),
                           (cx - 40 * math.cos(a + 1.57), cy - 40 * math.sin(a + 1.57))], fill=(255, 250, 225, int(150 * fa)))
            d.ellipse((cx - 480, cy - 480, cx + 480, cy + 480), fill=(255, 255, 240, int(140 * fa)))
            c.alpha_composite(fl.filter(ImageFilter.GaussianBlur(18)))
        return c

    seq("intro", FPS, fr)


def title():  # 0.0-2.5 s, word by word with bounce, wrapped to <= 960 px
    txt = C["title"]
    emo = txt.split()[-1] if not txt.split()[-1][0].isalnum() and not txt.split()[-1][0] in "'\"" else None
    words = txt.split()[:-1] if emo else txt.split()
    size = 150
    while True:
        imgs = [word_img(w, size, ORANGE, (255, 255, 255), 16) for w in words]
        e_img = emoji_img(emo, int(size * 0.85)) if emo else None
        space = int(size * 0.18)
        lines, cur, cw = [], [], 0
        items = list(range(len(words))) + (["E"] if emo else [])
        wid = lambda it: (e_img.width + 10 if it == "E" else imgs[it].width - 48)
        for it in items:
            w = wid(it)
            if cur and cw + space + w > 980: lines.append(cur); cur, cw = [], 0
            cw += (space if cur else 0) + w; cur.append(it)
        lines.append(cur)
        if len(lines) <= 3 or size < 100: break
        size -= 10
    lh = int(size * 1.05)
    y0 = 215 + lh // 2 + 10
    place = []
    for li, ln in enumerate(lines):
        tw = sum(wid(it) for it in ln) + space * (len(ln) - 1); x = W / 2 - tw / 2
        for it in ln:
            place.append((it, x + wid(it) / 2, y0 + li * lh)); x += wid(it) + space

    def fr(t):
        c = Image.new("RGBA", (W, H))
        out = max(0.0, (t - 2.25) / 0.25)
        for k, (it, x, y) in enumerate(place):
            t0 = 0.08 + 0.16 * k
            p = (t - t0) / 0.34
            if p <= 0: continue
            im = e_img if it == "E" else imgs[it]
            s = ease_back(p) * (1 + (0.025 * math.sin(2 * math.pi * (t - t0) * 1.8) if p >= 1 else 0))
            paste_scaled(c, im, x, y - 22 * math.sin(min(p, 1) * math.pi), s * (1 - 0.2 * out), 1 - min(out, 1))
        return c

    seq("title", int(2.5 * FPS), fr)


LEAF_COLS = [(232, 106, 23), (214, 64, 30), (246, 170, 40), (190, 80, 30), (250, 196, 70)]


def leaves():  # seamless 6 s loop: every motion term has a whole number of periods in P
    P, n = 6.0, 16
    rnd = random.Random(7)
    L = []
    for _ in range(n):
        sz = rnd.randint(22, 42); col = rnd.choice(LEAF_COLS)
        im = Image.new("RGBA", (sz * 2, sz * 2)); d = ImageDraw.Draw(im); pts = []
        for i in range(40):
            a = 2 * math.pi * i / 40
            r = sz * (0.55 + 0.45 * abs(math.cos(a)) ** 0.6) * (1 - 0.25 * abs(math.sin(3 * a)))
            pts.append((sz + r * math.cos(a), sz + 0.55 * r * math.sin(a)))
        d.polygon(pts, fill=col + (225,))
        d.line([(sz * 0.15, sz), (sz * 1.85, sz)], fill=tuple(int(c * 0.7) for c in col) + (225,), width=max(2, sz // 12))
        L.append(dict(spr=im, x=rnd.uniform(0, W), y0=rnd.uniform(0, H + 200), k=rnd.choice([1, 1, 2]),
                      sway=rnd.uniform(30, 80), m=rnd.choice([1, 2, 3]), ph=rnd.uniform(0, 6.28),
                      rot=rnd.uniform(0, 360), j=rnd.choice([-2, -1, 1, 2])))

    def fr(t):
        c = Image.new("RGBA", (W, H))
        for l in L:
            y = (l["y0"] + l["k"] * (H + 200) * t / P) % (H + 200) - 100
            x = l["x"] + l["sway"] * math.sin(2 * math.pi * l["m"] * t / P + l["ph"])
            spr = l["spr"].rotate(l["rot"] + 360 * l["j"] * t / P, resample=Image.BICUBIC, expand=True)
            c.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height / 2)))
        return c

    seq("leaves", int(P * FPS), fr)


# ------------------------------------------------------------------ subtitles
SYL = {"family": 3, "every": 2, "thunder's": 2, "mija": 2, "sunshine": 2, "morning": 2, "raindrops": 2,
       "flowers": 2, "around": 2, "garden": 2, "hours": 2, "sunbathe": 2, "brother": 2, "sister": 2,
       "behind": 2, "seek": 1, "small": 1, "takes": 1, "each": 1, "god": 1, "gray": 1}


def syl(w):
    k = w.lower().strip(",.!?()'\"")
    if k in SYL: return SYL[k]
    return max(1, len([1 for i, ch in enumerate(k) if ch in "aeiouy" and (i == 0 or k[i - 1] not in "aeiouy")]))


def onset_env():
    s = np.fromfile(f"{S}/lote/e03v.raw", np.float32); h = 80; n = len(s) // h
    le = 20 * np.log10(np.sqrt((s[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-5)
    return le, np.convolve(np.maximum(np.diff(le, prepend=le[0]), 0), [0.25, 0.5, 0.25], "same")


def ass_t(t):
    cs = max(0, int(round(t * 100)))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def burned():  # word times read from the master's own burned karaoke (tools/burnk.py)
    out = {}
    for ln in open(f"{S}/lote/burnk.json"):
        st, _, ts = json.loads(ln)
        fixed = []
        for k, t in enumerate(ts):  # keep monotonic; fill gaps by interpolation
            if t is None or (fixed and t <= fixed[-1]):
                nxt = next((x for x in ts[k + 1:] if x is not None and (not fixed or x > fixed[-1])), None)
                t = (fixed[-1] + (nxt if nxt else fixed[-1] + 0.6)) / 2 if fixed else st
            fixed.append(t)
        out[round(st, 2)] = fixed
    return out


def subs():
    le, fl = onset_env()
    BK = burned()
    cues = sorted(C["cues"], key=lambda c: c[1])
    ev, log = [], []
    for i, (kind, st, en, text) in enumerate(cues):
        nxt = cues[i + 1][1] if i + 1 < len(cues) else None
        if en is None:
            en = (nxt - 0.12) if nxt else C["last_end"]
        show0 = st - (0.2 if kind == "K" else 0.05)
        if i > 0 and ev: show0 = max(show0, prev_end)
        show1 = min(en + 0.25, (nxt - (0.2 if cues[i + 1][0] == "K" else 0.05)) if nxt else C["t1"])
        show1 = min(show1, C["t1"])
        prev_end = show1
        a, b = show0 - T0, show1 - T0
        if kind == "D":
            ev.append(f"Dialogue: 0,{ass_t(a)},{ass_t(b)},Sub,,0,0,0,,{text}")
            continue
        words = text.split(); tot = sum(syl(w) for w in words)
        step = (en - st) / tot
        times, cum = [], 0
        for w in words:
            est = st + cum * step
            lo, hi = int((est - 0.1) * 100), int((est + 0.1) * 100)
            j = lo + int(np.argmax(fl[lo:hi + 1]))
            t = j / 100 if fl[j] > 2.5 else est
            if not times: t = st
            elif t <= times[-1] + 0.1: t = max(est, times[-1] + 0.1)
            times.append(t); cum += syl(w)
        if round(st, 2) in BK and len(BK[round(st, 2)]) == len(words):
            times = BK[round(st, 2)]
        log.append(" ".join(f"{w}@{t:.2f}" for w, t in zip(words, times)))
        bounds = [show0] + times + [show1]
        for k in range(len(words) + 1):
            x0, x1 = bounds[k], bounds[k + 1]
            if k == len(words): x1 = show1
            if x1 - x0 < 0.01: continue
            parts = [("{\\1c&H0000D7FF&\\3c&H000E5AE0&}" + w + "{\\1c&H00FFFFFF&\\3c&H001F8AFF&}") if m == k - 1 else w
                     for m, w in enumerate(words)]
            ev.append(f"Dialogue: 0,{ass_t(x0 - T0)},{ass_t(x1 - T0)},Sub,,0,0,0,," + " ".join(parts))
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Fredoka,82,&H00FFFFFF,&H00FFFFFF,&H001F8AFF,&H78301000,-1,0,0,0,100,100,1,0,1,8,3,2,80,80,{int(H * 0.235)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(f"{WD}/subs.ass", "w").write(hdr + "\n".join(ev) + "\n")
    open(f"{WD}/karaoke_words.txt", "w").write("\n".join(log) + "\n")
    print("\n".join(log))


# ------------------------------------------------------------------ audio
def loud(p):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr.split("Summary:")[-1]
    return float(r.split("I:")[1].split("LUFS")[0]), float(r.split("Peak:")[1].split("dBFS")[0])


def audio():
    raw = f"{WD}/a_raw.wav"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{T0:.5f}", "-t", f"{DUR:.5f}", "-i", SRC, "-vn", "-ac", "2",
         "-ar", "48000", "-af", f"afade=t=in:d=0.012,afade=t=out:st={DUR - 0.015:.4f}:d=0.015", "-c:a", "pcm_f32le", raw])
    i, _ = loud(raw)
    g = -14.0 - i
    for _ in range(4):
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
             f"volume={g:.2f}dB,aresample=192000,alimiter=limit=0.87:attack=2:release=60:level=disabled:asc=1,aresample=48000",
             "-c:a", "pcm_f32le", f"{WD}/a.wav"])
        run(["ffmpeg", "-v", "error", "-y", "-i", f"{WD}/a.wav", "-c:a", "aac", "-b:a", "320k", f"{WD}/a_test.m4a"])
        i2, p2 = loud(f"{WD}/a_test.m4a")
        print("audio", round(g, 2), i2, p2)
        if abs(i2 + 14) <= 0.15: break
        g += -14 - i2


# ------------------------------------------------------------------ final
def ext_enable():
    parts = []
    for sp in shot_spans():
        if sp["ext"]:
            a, b = (sp["a"] - F0) / SFPS, (sp["b"] - F0) / SFPS
            parts.append(f"between(t\\,{a:.4f}\\,{b - 0.001:.4f})")
    return "+".join(parts) or "0"


def final():
    out = f"{S}/lote/out/{NAME}.mp4"; os.makedirs(os.path.dirname(out), exist_ok=True)
    fc = (f"[0:v]fps={FPS}[b];[1:v]format=rgba[i];[2:v]format=rgba[t];[3:v]format=rgba[l];"
          f"[b][i]overlay=eof_action=pass:repeatlast=0[v1];"
          f"[v1][l]overlay=enable='{ext_enable()}':shortest=0:eof_action=repeat[v2];"
          f"[v2][t]overlay=eof_action=pass:repeatlast=0[v3];"
          f"[v3]subtitles={WD}/subs.ass:fontsdir={S}/fonts,format=yuv420p[v]")
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{WD}/base24.mp4", "-framerate", str(FPS), "-i", f"{WD}/intro/%04d.png",
         "-framerate", str(FPS), "-i", f"{WD}/title/%04d.png", "-stream_loop", "-1", "-framerate", str(FPS),
         "-i", f"{WD}/leaves/%04d.png", "-i", f"{WD}/a.wav", "-filter_complex", fc, "-map", "[v]", "-map", "4:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{DUR:.5f}", out])
    print(out, subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "csv=p=0", out],
                              capture_output=True, text=True).stdout.strip(), loud(out))


if __name__ == "__main__":
    for st in sys.argv[3:] or ["video", "gfx", "subs", "audio", "final"]:
        if st == "gfx":
            intro(); title(); leaves()
        else:
            globals()[st]()
