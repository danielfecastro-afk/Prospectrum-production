import json, os, subprocess, sys
import numpy as np

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = f'{S}/work'; DL = f'{S}/dl'
J = json.load(open(f'{W}/timeline.json'))
segs, TL = J['segs'], J['tl']
ONS = np.load(f'{W}/onsets.npy')


def voiced(path, thr=-40, ss=None, t=None):
    SR, H = 8000, 80
    cmd = ['ffmpeg', '-nostdin', '-v', 'error']
    if ss is not None: cmd += ['-ss', str(ss), '-t', str(t)]
    x = np.frombuffer(subprocess.run(cmd + ['-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True).stdout, np.float32)
    n = len(x) // H
    e = 20 * np.log10(np.sqrt((x[:n * H].reshape(n, H) ** 2).mean(1)) + 1e-6)
    on = np.where(e > thr)[0]
    return [], (on[0] / 100, on[-1] / 100 + 0.01) if len(on) else (0, 0)


VOX = f'{W}/VOX.mp3'
_vox_cache = None


def vox_env():
    global _vox_cache
    if _vox_cache is None:
        SR, H = 8000, 80
        x = np.frombuffer(subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', VOX, '-ac', '1', '-ar', str(SR),
                                          '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
        n = len(x) // H
        _vox_cache = 20 * np.log10(np.sqrt((x[:n * H].reshape(n, H) ** 2).mean(1)) + 1e-6)
    return _vox_cache


# ---- lyrics: words with syllable counts
CHORUS = [
    "Thank|1 you,|1 God,|1 for|1 my|1 family|3 (my|1 family!)|3",
    "Thank|1 you|1 for|1 the|1 love|1 I|1 see|1 (I|1 see!)|1",
    "Every|2 hug,|1 every|2 smile,|1 every|2 good|1 gift|1",
    "all|1 the|1 while|1 comes|1 from|1 You...|1",
    "Thank|1 you,|1 God,|1 for|1 my|1 family!|3",
]
LINES = []  # (song_start, song_end, line_idx, section_offset)
def chorus(starts, last_end, off, extra=None):
    for i, st in enumerate(starts):
        en = starts[i + 1] - 0.05 if i + 1 < len(starts) else last_end
        LINES.append((st, en, i, off))
    if extra:
        LINES.append((*extra, 4, off))

chorus([5.16, 9.66, 13.44, 17.20, 19.32], 22.0, TL['OFF_C'])
LINES.append((39.20, 44.96, 0, TL['OFF_C']))
chorus([58.56, 62.56, 66.24, 70.04, 72.12], 74.9, TL['OFF_C'])
chorus([103.16, 107.58, 111.20, 115.00, 117.08], 119.6, TL['OFF_C'])
chorus([147.10, 151.28, 154.88, 158.60, 160.72], 163.2, TL['OFF_G'], extra=(163.94, 169.2))


def word_times(st, en, words):
    env = vox_env()
    a, b = int((st - 0.1) * 100), int(en * 100)
    v = np.where(env[a:b] > -40)[0]
    if len(v):
        vs, ve = max(st, (a + v[0]) / 100), (a + v[-1]) / 100
    else:
        vs, ve = st, en
    ve = max(ve, vs + 0.5)
    syl = [int(w.split('|')[1]) for w in words]
    tot = sum(syl)
    step = (ve - vs) / tot
    times, acc = [], 0
    for s in syl:
        nominal = vs + acc * step
        near = ONS[(ONS > nominal - 0.18) & (ONS < nominal + 0.18)]
        t = float(near[np.argmin(abs(near - nominal))]) if len(near) else nominal
        if times and t <= times[-1] + 0.12:
            t = max(nominal, times[-1] + 0.12)
        times.append(t)
        acc += s
    return times, ve


def ass_time(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'


def srt_time(t):
    t = max(0, t)
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def make_ass():
    hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Fredoka,74,&H003CC9FF,&H00FFFFFF,&H006B7AF2,&H96142850,-1,0,0,0,100,100,1,0,1,6,3,2,80,80,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    srt_lyrics = []
    prev_end = -1
    for st, en, li, off in LINES:
        words = CHORUS[li].split()
        times, ve = word_times(st, en, words)
        show0 = min(st, times[0]) - 0.25
        if off + show0 < prev_end + 0.02:
            show0 = prev_end + 0.02 - off
        prev_end = off + en
        txt = '{\\fad(150,200)}'
        cs = int(round((times[0] - show0) * 100))
        txt += f'{{\\k{cs}}}'
        for k, w in enumerate(words):
            nxt = times[k + 1] if k + 1 < len(times) else max(ve, times[k] + 0.4)
            d = int(round((nxt - times[k]) * 100))
            txt += f'{{\\k{d}}}' + w.split('|')[0] + (' ' if k + 1 < len(words) else '')
        ev.append(f'Dialogue: 0,{ass_time(off + show0)},{ass_time(off + en)},Karaoke,,0,0,0,,{txt}')
        plain = ' '.join(w.split('|')[0] for w in words)
        srt_lyrics.append((off + show0 + 0.1, off + en, f'♪ {plain} ♪', li, times))
    open(f'{W}/karaoke.ass', 'w').write(hdr + '\n'.join(ev) + '\n')
    return srt_lyrics


def seg(clip, k=0):
    return [s for s in segs if s['clip'] == clip][k]


def make_srt(srt_lyrics):
    cues = []
    def spoken(clip, text, parts=None, ss_src=None, k=0):
        s0 = seg(clip, k)
        path = f'{DL}/{clip}.mp4' if clip.startswith('V') else f'{DL}/{clip}.mp3'
        _, (a, b) = voiced(path)
        base = s0['m0'] if ss_src is None else ss_src
        if parts:
            for (pa, pb, t) in parts:
                cues.append((base + pa, base + pb, t))
        else:
            cues.append((base + a, base + b + 0.25, text))
    cues.append((0.3, 3.4, 'MiMi Casa... presents!'))
    spoken('V02', 'Luna, tonight... YOU get to lead our dinner prayer!')
    spoken('V03', 'Me? But... what do I say?')
    spoken('V04', "Just say 'thank you for the food'... and let's eat!")
    spoken('V05', 'Look around, mija. Every good gift... comes from God!')
    spoken('V28', "Whoa! The lights went out! I can't see anything!")
    spoken('V29', "Mimi... I'm scared. It's so dark.")
    spoken('V33', None, parts=[(0.2, 2.6, 'Mimi, I know what to say now!'),
                               (2.8, 6.85, 'Every good gift comes from God...\nand the best one is us!')])
    spoken('V35', None, parts=[(0.26, 3.7, "Dear God... thank You for Papi's strong hands..."),
                               (4.2, 8.1, "for Mami's yummy food...\nfor Mateo and our puppy...")])
    spoken('V36', None, parts=[(0.2, 3.7, "for all our friends in the garden...\nand for Mimi's hugs."),
                               (4.1, 7.2, 'Every good gift comes from You. Amen!')])
    tA = TL['T_V37']
    cues.append((tA + 0.1, tA + 3.75, 'Amen! Amen! Amen!'))
    cues.append((tA + 3.95, tA + 6.2, "Amen! Now let's eat!"))
    ffm = json.load(open(f'{W}/mix_meta.json'))['ff_end']
    cues.append((TL['OFF_G'] + 171.0, TL['OFF_G'] + ffm + 0.2, 'Family first, siempre!'))
    # verse openings (known first words of each sung verse)
    verses = [('V09', 'My hands are big...'), ('V10', 'I work and plant...'), ('V11', 'You fix my bike...'),
              ('V14', 'My kitchen smells...'), ('V15', 'I hum a song...'), ('V17', 'Run and jump...'),
              ('V18', 'Hide and seek...'), ('V20', 'Brother, sister...'), ('V21', 'Sunshine in the morning...'),
              ('V22', 'I zoom around the garden...'), ('V23', 'And I just sunbathe...'), ('V24', 'Big or small...'),
              ('V31', 'When the night is dark...'), ('V32', 'Hold my hand, mija...')]
    env = vox_env()
    for clip, txt in verses:
        s0 = seg(clip)
        song_a = s0['song_a']
        off = s0['m0'] - song_a
        a = int(song_a * 100)
        v = np.where(env[a:a + 400] > -40)[0]
        st = song_a + (v[0] / 100 if len(v) else 0)
        end_song = [s for s in segs if s['clip'] == clip][-1]['song_b'] if clip in ('V31', 'V32', 'V14') else s0['song_b']
        cues.append((off + st, off + min(st + 3.2, end_song - 0.05), f'♪ {txt} ♪'))
    for a, b, t, *_ in srt_lyrics:
        cues.append((a, b, t))
    cues.sort()
    # no overlaps
    out = []
    for i, (a, b, t) in enumerate(cues):
        if i + 1 < len(cues):
            b = min(b, cues[i + 1][0] - 0.04)
        out.append(f'{len(out) + 1}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n')
    open(f'{W}/MiMiCasa_E03_en.srt', 'w').write('\n'.join(out))
    return cues


if __name__ == '__main__':
    lyr = make_ass()
    cues = make_srt(lyr)
    for a, b, t in cues:
        print(f'{a:8.2f} {b:8.2f} {t!r}')
