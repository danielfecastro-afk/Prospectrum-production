import json, os, subprocess, re, tempfile
import numpy as np

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = f'{S}/work'
DL = f'{S}/dl'
SR = 48000
J = json.load(open(f'{W}/timeline.json'))
segs, TL = J['segs'], J['tl']
rng = np.random.default_rng(3)


def load(p, ss=None, t=None, af=None):
    cmd = ['ffmpeg', '-nostdin', '-v', 'error']
    if ss is not None: cmd += ['-ss', f'{ss:.4f}']
    if t is not None: cmd += ['-t', f'{t:.4f}']
    cmd += ['-i', p, '-vn'] + (['-af', af] if af else []) + ['-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).reshape(-1, 2).copy()


def write_wav(x, p):
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-c:a', 'pcm_f32le', p], input=x.astype(np.float32).tobytes())


def lufs(x):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        write_wav(x, f.name)
        r = subprocess.run(['ffmpeg', '-nostdin', '-i', f.name, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
    I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
    tp = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r)[-1])
    return I, tp


def norm(x, target):
    I, _ = lufs(x)
    return x * 10 ** ((target - I) / 20)


def db(g): return 10 ** (g / 20)


def ramp_env(n, pts):
    """pts: list of (time_s, gain_db) breakpoints, linear in dB."""
    t = np.arange(n) / SR
    tt = [p[0] for p in pts]; gg = [p[1] for p in pts]
    return db(np.interp(t, tt, gg))[:, None]


def fade(x, fi=0.0, fo=0.0):
    x = x.copy()
    if fi > 0:
        k = int(fi * SR); x[:k] *= np.linspace(0, 1, k)[:, None]
    if fo > 0:
        k = int(fo * SR); x[-k:] *= np.linspace(1, 0, k)[:, None]
    return x


TOTAL = TL['TOTAL']
mix = np.zeros((int(TOTAL * SR) + SR, 2), np.float32)
stems = {k: np.zeros_like(mix) for k in ('music', 'voice', 'fx')}


def place(x, t, stem):
    i = int(round(t * SR))
    x = x[:max(0, len(mix) - i)]
    stems[stem][i:i + len(x)] += x


# ---------------- synth fx
def bell(level=-18):
    n = int(2.2 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 2.6) + 0.45 * np.sin(2 * np.pi * 3000 * t) * np.exp(-t * 4.5)
         + 0.25 * np.sin(2 * np.pi * 4130 * t) * np.exp(-t * 7) + 0.3 * np.sin(2 * np.pi * 1500 * 2.76 * t) * np.exp(-t * 9))
    y *= np.minimum(1, t / 0.003)
    return norm(np.stack([y, y], 1), level)


def filt(x, lo=None, hi=None):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if hi: m *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo: m *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * m[:, None], n=len(x), axis=0)


def pink(n):
    w = rng.standard_normal((n, 2))
    X = np.fft.rfft(w, axis=0); f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1
    return np.fft.irfft(X / np.sqrt(f)[:, None], n=n, axis=0)


def whoosh(level=-20, dur=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.standard_normal((n, 2))
    # sweeping band-pass via short-time blocks
    out = np.zeros_like(noise); blk = 1024
    for i in range(0, n, blk):
        p = i / n
        fc = 400 + 3200 * np.sin(np.pi * p) ** 2
        seg = noise[i:i + blk * 2] if i + blk * 2 <= n else noise[i:]
        y = filt(seg, lo=fc * 0.6, hi=fc * 1.6)
        out[i:i + blk] += y[:min(blk, n - i)]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    out *= env[:, None]
    out[:, 0] *= 1 - 0.4 * t / dur; out[:, 1] *= 0.6 + 0.4 * t / dur
    return norm(out, level)


def rain(dur, level=-30):
    n = int(dur * SR)
    x = filt(pink(n), lo=250, hi=3500)
    # sparse drops
    for _ in range(int(dur * 25)):
        i = rng.integers(0, n - 2000); a = rng.uniform(0.5, 2.0)
        d = np.exp(-np.arange(1500) / 120) * rng.standard_normal(1500)
        x[i:i + 1500, rng.integers(0, 2)] += a * d * x.std()
    return norm(x, level)


def thunder(level=-21):
    n = int(4.0 * SR); t = np.arange(n) / SR
    x = filt(rng.standard_normal((n, 2)), hi=110)
    env = np.minimum(1, t / 0.08) * np.exp(-t / 1.1) * (1 + 0.5 * np.sin(2 * np.pi * 3.1 * t + 1) * np.exp(-t))
    return norm(x * env[:, None], level)


def loop(x, dur, xf=1.0):
    out = x.copy(); k = int(xf * SR)
    w = np.linspace(0, 1, k)[:, None]
    while len(out) < dur * SR:
        out = np.concatenate([out[:-k], out[-k:] * (1 - w) + x[:k] * w, x[k:]])
    return out[:int(dur * SR)]


VAF = 'highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=1'
def limit(x, lin):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f, tempfile.NamedTemporaryFile(suffix='.wav') as g:
        write_wav(x, f.name)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', f.name, '-af',
                        f'alimiter=limit={lin}:attack=1:release=50:level=disabled', '-c:a', 'pcm_f32le', g.name])
        return load(g.name)[:len(x)]


def vload(p, target=-14.0):
    x = load(p, af=VAF)
    for _ in range(2):
        x = limit(norm(x, target), 0.63)
    return x

# ---------------- sources
SONG = norm(load(f'{W}/SONG.mp3'), -14.0)
PIANO = SONG[int(138.3 * SR):int(147.0 * SR)]
PI = lufs(PIANO)[0]
piano = lambda target: PIANO * db(target - PI)
seg_by_clip = {}
for s in segs: seg_by_clip.setdefault(s['clip'], []).append(s)

# A: bell + presents
place(bell(-17), 0.0, 'fx')
place(vload(f'{DL}/PRESENTS.mp3'), 0.3, 'voice')

# A2 + B piano bed: -22 in A2, -28 under dialogues
t0, t1 = TL['T_A2'], TL['T_C']
bed = loop(piano(0), t1 - t0 + 0.6)
env = ramp_env(len(bed), [(0, -40), (0.4, -22), (TL['T_B'] - t0 - 0.2, -22), (TL['T_B'] - t0 + 0.3, -28),
                          (t1 - t0, -28), (t1 - t0 + 0.6, -60)])
place(bed * env, t0, 'music')

# dialogues (full clip audio, cut at shot end where trailing silence)
VOICE_TARGET = -14.0
for c in ['V02', 'V03', 'V04', 'V05', 'V28', 'V29', 'V33', 'V35', 'V36']:
    s0 = seg_by_clip[c][0]; s1 = seg_by_clip[c][-1]
    x = vload(f'{DL}/{c}.mp4')
    x = fade(x[:int((s1['m1'] - s0['m0']) * SR)], 0.005, 0.03)
    place(x, s0['m0'], 'voice')

# whooshes on object transitions (+ B->C circle)
for s in segs:
    tr = s.get('trans')
    if tr and tr[2] in ('whoosh', 'flower', 'spoon', 'ball'):
        place(whoosh(-20), s['m0'] - 0.15, 'fx')

# C: song 0 - 120.2 (fade out 119.6-120.2)
x = SONG[:int(120.2 * SR)].copy()
x[int(119.6 * SR):] *= np.linspace(1, 0, len(x) - int(119.6 * SR))[:, None]
place(x, TL['OFF_C'], 'music')

# D: storm
tD, back = TL['T_D'], TL['SONG_BACK']
place(fade(rain(back - tD + 1.5), 0.6, 1.5), tD, 'fx')
place(thunder(-21), tD + 0.05, 'fx')

# E: song 119.8 - 145.6, fade in 0.3, duck -10 under V33, fade out 145.2-145.6
a, b = 119.8, 145.6
x = SONG[int(a * SR):int(b * SR)].copy()
env = ramp_env(len(x), [(0, -60), (0.3, 0), (138.3 - a - 0.2, 0), (138.3 - a, -10), (145.2 - a, -10), (b - a, -60)])
place(x * env, TL['OFF_E'] + a, 'music')

# F: piano loop -26 under prayer, AMEN over V37
tF, tG = TL['T_F'], TL['OFF_G'] + 145.2
bed = loop(piano(0), tG - tF + 0.4)
place(bed * ramp_env(len(bed), [(0, -50), (0.4, -26), (tG - tF - 0.2, -26), (tG - tF + 0.4, -60)]), tF, 'music')
place(vload(f'{DL}/AMEN.mp3'), TL['T_V37'], 'voice')

# G: song 145.2 - 176.4, duck -8 under FAMILY FIRST chorus at song 171.0
FF_ON = [0.17, 0.15, 0.14, 0.13, 0.14]
ffs = [vload(f'{DL}/FF{i + 1}.mp3') * db(-6) for i in range(5)]
ff_end = 171.0 + max(len(f) / SR - o for f, o in zip(ffs, FF_ON))
a = 145.2
x = SONG[int(a * SR):].copy()
env = ramp_env(len(x), [(0, -40), (0.03, 0), (171.0 - a - 0.25, 0), (171.0 - a - 0.05, -8), (ff_end - a, -8),
                        (ff_end - a + 0.4, 0), (len(x) / SR, 0)])
place(x * env, TL['OFF_G'] + a, 'music')
for f, o in zip(ffs, FF_ON):
    place(f, TL['OFF_G'] + 171.0 - o, 'voice')

# H: soft chime as the logo pops
place(bell(-24), TL['T_H'] + 0.35, 'fx')

mix = stems['music'] + stems['voice'] + stems['fx']
mix = mix[:int(TOTAL * SR)]
write_wav(mix, f'{W}/mix_raw.wav')
print('raw', lufs(mix), 'ff_end', ff_end)
# master: gain to -14 LUFS, true-peak-safe limiter at -1.5 dBFS (4x oversampled), re-trim gain
for it in range(3):
    I, _ = lufs(mix)
    mix = mix * db(-14.0 - I)
    write_wav(mix, f'{W}/mix_pre.wav')
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', f'{W}/mix_pre.wav', '-af',
                    'aresample=192000,alimiter=limit=0.83:attack=1:release=60:level=disabled:asc=1,aresample=48000',
                    '-c:a', 'pcm_f32le', f'{W}/mix_lim.wav'])
    mix = load(f'{W}/mix_lim.wav')[:len(mix)]
    print('pass', it, lufs(mix))
write_wav(mix, f'{W}/mix_final.wav')
json.dump(dict(ff_end=ff_end), open(f'{W}/mix_meta.json', 'w'))
