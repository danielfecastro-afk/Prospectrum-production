"""Read word-sung times from the E03 master's burned karaoke (each word turns yellow when sung)."""
import subprocess, sys, json
import numpy as np
S = sys.argv[1]; SRC = f"{S}/lote/src/MiMiCasa_E03_master.mp4"


def frames(a, d):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', SRC, '-vf',
                        'crop=1920:70:0:958', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(p, np.uint8).reshape(-1, 70, 1920, 3).astype(int)


def masks(fr):
    R, G, B = fr[..., 0], fr[..., 1], fr[..., 2]
    return (R > 215) & (G > 170) & (G < 230) & (B < 120), (R > 228) & (G > 228) & (B > 228)


HDR = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Fredoka,74,&H003CC9FF,&H00FFFFFF,&H006B7AF2,&H96142850,-1,0,0,0,100,100,1,0,1,0,0,2,80,80,58,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def clean_cols(text):
    import tempfile, os
    d = tempfile.mkdtemp(dir=f"{S}/lote")
    open(f"{d}/l.ass", "w").write(HDR + "Dialogue: 0,0:00:00.00,0:00:05.00,Karaoke,,0,0,0,," + text + "\n")
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=black:s=1920x1080:d=1', '-vf',
                        f'subtitles={d}/l.ass:fontsdir={S}/fonts,crop=1920:70:0:958', '-frames:v', '1', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    im = np.frombuffer(p, np.uint8).reshape(70, 1920, 3)
    return im.max(2).max(0) > 100


def scan(st, en, nwords, text):
    a = st - 0.15; fr = frames(a, en - a + 0.2)
    yel, wht = masks(fr)
    ref = 0
    xs = np.where(clean_cols(text))[0]
    for gap in range(26, 6, -1):
        groups, s0 = [], xs[0]
        for p, q in zip(xs, xs[1:]):
            if q - p > gap: groups.append((s0, p)); s0 = q
        groups.append((s0, xs[-1]))
        if len(groups) == nwords: break
    if len(groups) != nwords: return None, ref
    res = []
    for x0, x1 in groups:
        y = yel[:, :, x0:x1 + 1].sum((1, 2)); w = wht[:, :, x0:x1 + 1].sum((1, 2))
        seen_white = False; t = None
        for i in range(len(y)):
            if w[i] > y[i] and w[i] > 30: seen_white = True
            elif seen_white and y[i] > w[i] and y[i] > 30: t = round(a + i / 24, 3); break
        if t is None:  # word already yellow when the line fades in
            idx = np.where((y > w) & (y > 30))[0]
            t = round(a + idx[0] / 24, 3) if len(idx) else None
        res.append(t)
    return res, ref


if __name__ == '__main__':
    for st, en, text in json.loads(sys.argv[2]):
        r, ref = scan(st, en, len(text.split()), text)
        print(json.dumps([st, text, r]))
