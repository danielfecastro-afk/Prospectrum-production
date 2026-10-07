#!/usr/bin/env python3
"""MiMi Casa E02 '¡Mangos para todos!' — build script (ffmpeg + numpy)."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL, W = f"{S}/dl", f"{S}/work"
AVATAR = "/tmp/claude-0/-home-user-Prospectrum-production/fafcce1d-ac75-5ee8-88c2-38637206a31d/images/1.webp"
MUSIC = "/root/.claude/uploads/fafcce1d-ac75-5ee8-88c2-38637206a31d/0e7addc8-Reunion_Familiar_-_Luna_Cantina.mp3"
FONT = f"{S}/fonts/Fredoka-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
FPS, SR, XF = 24, 48000, 7          # xfade = 7 frames (0.29 s, closest to 0.3 s at 24 fps)
SPF = SR // FPS
OUT = sys.argv[1] if len(sys.argv) > 1 else f"{W}/master.mp4"
os.makedirs(f"{W}/seg", exist_ok=True)

# name, has embedded lip-sync audio, extra voice mp3 (when embedded is short), music dB, card
SHOTS = [
    ("P02", False, -20), ("P03", True, -28), ("P04", False, -16), ("P05a", True, -28),
    ("P05b", True, -28), ("P06", False, -16), ("P07", True, -28), ("P08", True, -28),
    ("P09", True, -28), ("P10", False, -20), ("P11", True, -28), ("P12", True, -28),
    ("P13", True, -28), ("P14", True, -28), ("P15", True, -28), ("P16", True, -28),
    ("P17", True, -28), ("P18", True, None), ("P19", False, -20), ("P20a", True, -28),
    ("P20b", False, -28),
]
CARDS = {"P13": "COMPARTIR = SHARE", "P16": "One for you! 🥭",
         "P20a": "Sharing makes it sweeter! · ¡Compartir es más dulce!"}
CARD_START, CARD_DUR = 0.5, 2.5
BOING_AT = 2.94          # mango lands on the iguana's head in P06
CHORUS_AT = 0.8          # P20b: family cheers from ~0.8 s
END_FREEZE = 2.0
VOICE_LUFS = -18.0


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_dur(p, sel="format=duration"):
    r = run(["ffprobe", "-v", "error", "-show_entries", sel, "-of", "csv=p=0", p], capture_output=True, text=True)
    return float(r.stdout.strip().split("\n")[0])


def nframes(p):
    r = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
             "stream=nb_read_frames,r_frame_rate", "-of", "json", p], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return int(s["nb_read_frames"]), num / den


def load_audio(p, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss is not None else []) + ["-i", p] \
        + (["-t", str(t)] if t is not None else []) + ["-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(run(cmd, capture_output=True).stdout, np.float32).reshape(-1, 2).copy()


def lufs(x):
    p = f"{W}/_m.wav"
    write_wav(p, x)
    r = run(["ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True, text=True)
    lines = r.stderr.split("Summary:")[-1]
    i = float(lines.split("I:")[1].split("LUFS")[0])
    tp = float(lines.split("Peak:")[1].split("dBFS")[0])
    return i, tp


def write_wav(p, x):
    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-c:a", "pcm_f32le", p], input=x.astype(np.float32).tobytes())


def onset(x, th_db=-35):
    m = np.abs(x).max(axis=1)
    w = SR // 100
    e = np.array([np.sqrt(np.mean(m[i:i + w] ** 2)) for i in range(0, len(m) - w, w)])
    idx = np.where(20 * np.log10(e / e.max() + 1e-9) > th_db)[0]
    return idx[0] * w


def edge_fade(x, ms=5):
    n = min(len(x) // 2, SR * ms // 1000)
    r = np.linspace(0, 1, n)[:, None]
    x[:n] *= r
    x[-n:] *= r[::-1]
    return x


# ---------------------------------------------------------------- cards
def render_card(text):
    """Returns list of RGBA frames (1920x1080) with a pop-scale animation."""
    maxw, size = 1680, 96
    while True:
        f = ImageFont.truetype(FONT, size)
        txt, emo = (text[:-2], text[-1]) if text.endswith("🥭") else (text, None)
        stroke = max(6, size // 9)
        bb = f.getbbox(txt, stroke_width=stroke)
        tw = bb[2] - bb[0]
        ew = int(size * 1.15) if emo else 0
        if tw + ew + (size // 4 if emo else 0) <= maxw or size <= 40:
            break
        size -= 4
    pad = 40
    cw = tw + ew + (size // 4 if emo else 0) + 2 * pad
    ch = (bb[3] - bb[1]) + 2 * pad + 20
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    x0, y0 = pad - bb[0], pad - bb[1]
    # soft drop shadow
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x0 + 4, y0 + 8), txt, font=f, fill=(90, 30, 20, 150),
                            stroke_width=stroke, stroke_fill=(90, 30, 20, 150))
    card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(card)
    d.text((x0, y0), txt, font=f, fill="white", stroke_width=stroke, stroke_fill="#F27A6B")
    if emo:
        ef = ImageFont.truetype(EMOJI, 109)
        ei = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
        ImageDraw.Draw(ei).text((0, 0), emo, font=ef, embedded_color=True)
        ei = ei.crop(ei.getbbox())
        if ei.getbbox() is None:
            raise RuntimeError("emoji did not render")
        eh = int(size * 1.05)
        ei = ei.resize((int(ei.width * eh / ei.height), eh), Image.LANCZOS)
        ex = x0 + bb[2] + size // 4
        ey = pad + (bb[3] - bb[1]) // 2 - eh // 2 + 4
        card.alpha_composite(ei, (ex, ey))
    frames = []
    n = int(round(CARD_DUR * FPS))
    for i in range(n):
        t = i / FPS
        # pop: easeOutBack from 0.3 to 1.0 in 0.33 s; fade out last 0.25 s
        u = min(1.0, t / 0.33)
        c1, c3 = 1.9, 2.9
        s = 0.3 + 0.7 * (1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2)
        a = min(1.0, t / 0.08) * min(1.0, (CARD_DUR - t) / 0.25)
        cw2, ch2 = max(1, int(cw * s)), max(1, int(ch * s))
        im = card.resize((cw2, ch2), Image.LANCZOS)
        if a < 1:
            al = im.getchannel("A").point(lambda v: int(v * a))
            im.putalpha(al)
        fr = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        cy = 1080 - 70 - ch // 2          # anchor: centre of the card, bottom area
        fr.alpha_composite(im, ((1920 - cw2) // 2, cy - ch2 // 2))
        frames.append(fr)
    return frames


# ---------------------------------------------------------------- intro P01
def build_intro(path, n=72):
    av = Image.open(AVATAR).convert("RGB")
    S0 = av.width
    # circular crop (inside the yellow ring is kept; outside -> transparent)
    big = 4
    mask = Image.new("L", (S0 * big, S0 * big), 0)
    cx, cy, r = 625 * big, 619 * big, 605 * big       # outer edge of the yellow ring (measured)
    ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    mask = mask.resize((S0, S0), Image.LANCZOS)
    fg = av.convert("RGBA")
    fg.putalpha(mask)
    fg = fg.crop((625 - 606, 619 - 606, 625 + 606, 619 + 606))
    S0 = fg.width
    # blurred background from the avatar art itself
    bg = av.crop((80, 80, S0 - 80, S0 - 80)).resize((1920, 1920), Image.LANCZOS).crop((0, 420, 1920, 1500))
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (40, 20, 10)), 0.25).convert("RGBA")
    shadow = Image.new("RGBA", (S0 + 200, S0 + 200), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((100, 120, S0 + 100, S0 + 120), fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    base_d = 900
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "10",
                          "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                          "-colorspace", "bt709", path], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / (n - 1)
        e = 0.5 - 0.5 * math.cos(math.pi * t)          # ease-in-out
        z = 1.0 + 0.08 * e
        d = int(round(base_d * z))
        fr = bg.copy()
        shd = shadow.resize((int(d * (S0 + 200) / S0),) * 2, Image.LANCZOS)
        fr.alpha_composite(shd, ((1920 - shd.width) // 2, (1080 - shd.height) // 2))
        im = fg.resize((d, d), Image.LANCZOS)
        fr.alpha_composite(im, ((1920 - d) // 2, (1080 - d) // 2))
        fade = min(1.0, i / (0.8 * FPS))                 # from black
        fade = fade * fade * (3 - 2 * fade)
        rgb = Image.blend(Image.new("RGB", (1920, 1080), 0), fr.convert("RGB"), fade)
        p.stdin.write(rgb.tobytes())
    p.stdin.close()
    p.wait()


# ---------------------------------------------------------------- per-shot plan
def plan():
    shots = [dict(name="P01", src=None, N=72, music=-20, audio=None)]
    for name, wan, mdb in SHOTS:
        src = f"{DL}/{name}_v.mp4"
        nf, fps = nframes(src)
        clip_dur = nf / fps
        N = int(round(clip_dur * FPS))
        audio, voice_dur = None, 0.0
        if wan:
            emb = probe_dur(src, "stream=duration")  # first stream is video; use audio below
            emb = float(run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                             "stream=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
            mp3 = f"{DL}/{name}_a.mp3"
            voice_dur = probe_dur(mp3)
            # embedded audio == voice at offset 0.000 (verified by cross-correlation);
            # use it, unless it is shorter than the voice (truncated) -> same voice from the mp3 at 0.0
            audio = src if emb >= voice_dur - 0.005 else mp3
            if voice_dur > clip_dur:
                N = int(math.ceil((voice_dur + 0.4) * FPS))
        shots.append(dict(name=name, src=src, N=N, clip_frames=int(round(clip_dur * FPS)), music=mdb,
                          audio=audio, voice_dur=voice_dur, clip_dur=clip_dur, fps=fps))
    shots[-1]["N"] += int(END_FREEZE * FPS)
    s = 0
    for sh in shots:
        sh["start"] = s
        s += sh["N"] - XF
    total = s + XF
    return shots, total


def build_segment(sh):
    out = f"{W}/seg/{sh['name']}.mp4"
    name, N = sh["name"], sh["N"]
    vf = []
    if abs(sh["fps"] - FPS) > 0.01:
        vf.append(f"fps={FPS}")
    vf += ["scale=-2:1080:flags=lanczos+accurate_rnd+full_chroma_int", "crop=1920:1080", "setsar=1"]
    pad = N - sh["clip_frames"]
    if pad > 0:
        vf.append(f"tpad=stop_mode=clone:stop={pad}")
    if name == "P20b":
        vf.append(f"fade=t=out:st={(N - END_FREEZE * FPS) / FPS:.4f}:d={END_FREEZE}")
    vf.append(f"trim=end_frame={N},setpts=PTS-STARTPTS,format=yuv420p")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", sh["src"]]
    if name in CARDS:
        cdir = f"{W}/card_{name}"
        os.makedirs(cdir, exist_ok=True)
        for i, fr in enumerate(render_card(CARDS[name])):
            fr.save(f"{cdir}/{i:03d}.png")
        cmd += ["-framerate", str(FPS), "-i", f"{cdir}/%03d.png"]
        fc = (f"[0:v]{','.join(vf[:-1])}[b];[1:v]format=rgba,setpts=PTS+{CARD_START}/TB[c];"
              f"[b][c]overlay=eof_action=pass:format=auto,{vf[-1]}[v]")
    else:
        fc = f"[0:v]{','.join(vf)}[v]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "10",
            "-r", str(FPS), "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", out]
    run(cmd)
    got, _ = nframes(out)
    assert got == N, (name, got, N)
    return out


def xfade_all(shots, segs, out):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in segs:
        cmd += ["-i", p]
    fc, prev = [], "[0:v]"
    for k in range(1, len(segs)):
        off = shots[k]["start"] / FPS
        lab = f"[x{k}]" if k < len(segs) - 1 else "[v]"
        fc.append(f"{prev}[{k}:v]xfade=transition=fade:duration={XF / FPS:.6f}:offset={off:.6f}{lab}")
        prev = lab
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "10",
            "-r", str(FPS), "-pix_fmt", "yuv420p", out]
    run(cmd)


# ---------------------------------------------------------------- audio
def boing():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 190 + 110 * np.exp(-3.5 * t) + 70 * np.exp(-6 * t) * np.sin(2 * np.pi * 10 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph))
    env = np.minimum(1, t / 0.004) * np.exp(-6 * t)
    y = y * env
    y = y / np.abs(y).max() * 10 ** (-14 / 20)
    return np.stack([y, y], 1).astype(np.float32)


def build_audio(shots, total):
    L = total * SPF
    dia = np.zeros((L, 2), np.float32)
    log = {}
    for sh in shots:
        if not sh["audio"]:
            continue
        x = load_audio(sh["audio"])
        x = x[: sh["N"] * SPF]
        i, _ = lufs(x)
        g = VOICE_LUFS - i
        x = edge_fade(x * 10 ** (g / 20))
        a = sh["start"] * SPF
        dia[a:a + len(x)] += x
        log[sh["name"]] = dict(src=os.path.basename(sh["audio"]), offset_s=0.0, lufs_in=round(i, 1), gain_db=round(g, 1))
    # P06 boing
    p06 = next(s for s in shots if s["name"] == "P06")
    b = boing()
    a = p06["start"] * SPF + int(BOING_AT * SR)
    dia[a:a + len(b)] += b
    # P20b chorus: 5 voices, aligned by their onsets, each normalised then -6 dB
    p20b = next(s for s in shots if s["name"] == "P20b")
    base = p20b["start"] * SPF + int(CHORUS_AT * SR)
    ch = []
    for k in range(1, 6):
        x = load_audio(f"{DL}/P20b_c{k}.mp3")
        o = onset(x)
        i, _ = lufs(x)
        x = edge_fade(x[o:] * 10 ** ((VOICE_LUFS - i) / 20) * 10 ** (-6 / 20))
        dia[base:base + len(x)] += x
        ch.append(dict(voice=k, onset_s=round(o / SR, 3), lufs_in=round(i, 1)))
    log["P20b_chorus"] = ch

    # music: section 1 from 0 until P18; muted on P18; section 2 resumes on P19 and ends with the song's end
    mus_full = load_audio(MUSIC)
    p18 = next(s for s in shots if s["name"] == "P18")
    p19 = next(s for s in shots if s["name"] == "P19")
    mus = np.zeros((L, 2), np.float32)
    s18 = (p18["start"] + XF) * SPF
    mus[:s18] = mus_full[:s18]
    s19 = p19["start"] * SPF
    tail = L - s19
    song_end = int(93.9 * SR)
    mus[s19:] = mus_full[song_end - tail:song_end]
    # gain envelope (dB) per shot with 0.5 s ramps, completed before a voice starts
    pts = []
    for k, sh in enumerate(shots):
        g = sh["music"] if sh["music"] is not None else -90
        t0 = sh["start"] / FPS
        if k == 0:
            pts.append((0.0, g))
            continue
        gp = pts[-1][1]
        if g < gp:      # going down: finish at start of the shot
            pts += [(t0 - 0.5, gp), (t0, g)]
        else:           # going up: start once the shot begins
            pts += [(t0, gp), (t0 + 0.5, g)]
    tt = np.arange(L) / SR
    env_db = np.interp(tt, [p[0] for p in pts], [p[1] for p in pts])
    env = 10 ** (env_db / 20)
    env *= np.clip(tt / 0.4, 0, 1)                       # tiny fade-in from black
    env *= np.clip((total / FPS - tt) / 3.0, 0, 1)       # 3 s fade out
    mus *= env[:, None].astype(np.float32)
    mix = dia + mus
    log["music_points"] = pts
    return mix, log


def master_audio(mix, path):
    raw = f"{W}/mix_raw.wav"
    write_wav(raw, mix)
    i0, _ = lufs(mix)
    g = -14.0 - i0
    for it in range(6):
        out = f"{W}/mix_master.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
             f"volume={g:.3f}dB,aresample=192000,alimiter=limit={10 ** (-1.6 / 20):.5f}:attack=2:release=80:level=false:asc=1,"
             f"aresample={SR}", "-c:a", "pcm_f32le", out])
        r = run(["ffmpeg", "-nostats", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"],
                capture_output=True, text=True).stderr.split("Summary:")[-1]
        I = float(r.split("I:")[1].split("LUFS")[0])
        if abs(I + 14.0) < 0.05:
            break
        g += -14.0 - I
    return out


def main():
    shots, total = plan()
    for sh in shots:
        print(f"{sh['name']:5s} start {sh['start'] / FPS:7.3f}s  N {sh['N']:4d} ({sh['N'] / FPS:.2f}s)  "
              f"audio {os.path.basename(sh['audio']) if sh['audio'] else '-'}", flush=True)
    print("TOTAL", total, total / FPS, flush=True)
    segs = []
    intro = f"{W}/seg/P01.mp4"
    if not os.path.exists(intro):
        build_intro(intro)
    segs.append(intro)
    for sh in shots[1:]:
        p = f"{W}/seg/{sh['name']}.mp4"
        if not os.path.exists(p) or os.environ.get("REBUILD") in ("all", sh["name"]):
            p = build_segment(sh)
        segs.append(p)
        print("seg", sh["name"], flush=True)
    vid = f"{W}/video.mp4"
    if not os.path.exists(vid) or os.environ.get("REBUILD"):
        xfade_all(shots, segs, vid)
    mix, log = build_audio(shots, total)
    aud = master_audio(mix, f"{W}/mix_master.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", aud, "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.1",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", "48", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-colorspace", "bt709", "-c:a", "aac", "-b:a", "256k", "-ar", str(SR),
         "-movflags", "+faststart", "-shortest", OUT])
    json.dump(dict(shots=[{k: v for k, v in s.items()} for s in shots], total_frames=total, audio=log),
              open(f"{W}/plan.json", "w"), indent=1, default=str)
    print("done", OUT)


if __name__ == "__main__":
    main()
