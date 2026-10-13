"""Single source of truth for the E03 edit. All times in seconds.
Song-section shots are given in SONG time and converted to master time."""
import json, os

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL = os.path.join(S, 'dl')
FPS = 24
BEAT0, BEAT = 5.16, 60 / 108

# measured clip durations (video)
DUR = {
 'V01': 4.0417, 'V02': 5.0, 'V03': 4.0, 'V04': 4.0, 'V05': 5.0, 'V06': 4.0417, 'V07': 7.0, 'V08': 7.0,
 'V09': 4.0, 'V10': 6.0, 'V11': 5.0, 'V12': 4.0, 'V13': 5.0417, 'V14': 8.0, 'V15': 5.0, 'V16': 6.0417,
 'V17': 3.0, 'V18': 3.0, 'V19': 3.0417, 'V20': 5.0, 'V21': 5.0, 'V22': 5.0, 'V23': 5.0, 'V24': 5.0,
 'V25': 3.0417, 'V26': 6.0417, 'V27': 4.0417, 'V28': 4.0, 'V29': 4.0, 'V30': 5.0417, 'V31': 10.0,
 'V32': 9.0, 'V33': 7.0, 'V34': 4.0417, 'V35': 9.0, 'V36': 8.0, 'V37': 4.0417, 'V38': 6.0417, 'V39': 6.0417}

# Song time at which each sung clip's t=0 falls (cross-correlation of clip audio
# vs. lead-vocal stem for first use; vocal-envelope match for re-used choruses).
ANCHOR = {'V07': 5.300, 'V08': 12.900, 'V09': 22.300, 'V10': 26.500, 'V11': 30.400, 'V12': 35.400,
          'V14': 44.800, 'V15': 53.200, 'V17': 75.600, 'V18': 78.150, 'V20': 81.400, 'V21': 85.800,
          'V22': 89.850, 'V23': 94.400, 'V24': 98.700, 'V31': 120.200, 'V32': 129.500}
SUNG = set(ANCHOR) | {'V07', 'V08'}


def shot(clip, a, b, src_in=0.0, speed=1.0, zoom=1.0, flip=False, warm=0.0, trans=None, punch=None,
         anchor=None, fade=None, label=None):
    if anchor is not None:  # lip-synced: source time = song time - anchor (speed 1)
        src_in = a - anchor
    return dict(clip=clip, a=a, b=b, src_in=round(src_in, 4), speed=speed, zoom=zoom, flip=flip,
                warm=warm, trans=trans, punch=punch, anchor=anchor, fade=fade, label=label)


def fill(clip, a, b, src_in=0.0, src_out=None):
    src_out = DUR[clip] if src_out is None else src_out
    return (src_out - src_in) / (b - a)


# ---------------- song part 1 (song time) ----------------
C = [
 shot('V06', 0.00, 5.30, speed=fill('V06', 0, 5.30), trans=('circleopen', 0.5, 'whoosh')),
 shot('V07', 5.30, 12.90, anchor=5.300, punch=9.05),
 shot('V08', 12.90, 19.30, anchor=12.900, punch=16.27),
 shot('V13', 19.30, 22.30),
 shot('V09', 22.30, 26.50, anchor=22.300),
 shot('V10', 26.50, 30.40, anchor=26.500, trans=('radial', 0.4, 'flower')),
 shot('V11', 30.40, 35.40, anchor=30.400),
 shot('V12', 35.40, 39.20, anchor=35.400),
 shot('V13', 39.20, 44.80, speed=fill('V13', 39.20, 44.80), flip=True),
 shot('V14', 44.80, 53.20, anchor=44.800, trans=('slideleft', 0.4, 'spoon'), punch=48.50),
 shot('V15', 53.20, 58.00, anchor=53.200),
 shot('V16', 58.00, 58.70, src_in=0.0),
 shot('V07', 58.70, 65.10, anchor=58.12, zoom=1.15, warm=0.03, punch=61.83),
 shot('V16', 65.10, 65.70, src_in=0.7),
 shot('V08', 65.70, 72.10, anchor=65.70, zoom=1.15, punch=69.05),
 shot('V16', 72.10, 75.60, src_in=1.3),
 shot('V17', 75.60, 78.15, anchor=75.600, trans=('zoomin', 0.4, 'ball')),
 shot('V18', 78.15, 80.90, anchor=78.150),
 shot('V19', 80.90, 81.40, src_in=0.0),
 shot('V20', 81.40, 85.80, anchor=81.400),
 shot('V21', 85.80, 89.85, anchor=85.800, trans=('wiperight', 0.4, None)),
 shot('V22', 89.85, 94.40, anchor=89.850),
 shot('V23', 94.40, 98.70, anchor=94.400),
 shot('V24', 98.70, 103.10, anchor=98.700),
 shot('V25', 103.10, 106.10),
 shot('V26', 106.10, 110.70, src_in=0.0),
 shot('V08', 110.70, 117.10, anchor=110.67, zoom=1.20, punch=114.06),
 shot('V19', 117.10, 120.20, src_in=0.5, speed=fill('V19', 117.10, 120.20, 0.5), fade=('out', 2.5, 0.6)),
]
E = [
 shot('V31', 120.20, 129.50, anchor=120.200, punch=124.80),
 shot('V32', 129.50, 138.30, anchor=129.500, punch=133.90),
 shot('V33', 138.30, 145.20, punch=141.10, label='dialog'),
]
G = [
 shot('V38', 145.20, 147.24, src_in=0.0, trans=('circleopen', 0.4, None)),
 shot('V07', 147.24, 153.64, anchor=146.80, zoom=1.10, punch=150.73),
 shot('V38', 153.64, 154.34, src_in=2.04),
 shot('V08', 154.34, 160.74, anchor=154.32, zoom=1.10, punch=157.39),
 shot('V38', 160.74, 163.90, src_in=2.74, speed=0.8),
 shot('V26', 163.90, 169.40, speed=0.9, flip=True),
 shot('V39', 169.40, 176.40, speed=fill('V39', 169.40, 176.40), punch=172.40),
]

# ---------------- master layout ----------------
T_A1, T_A2, T_B = 0.0, 3.0, 7.0
B = [('V02', 5.0), ('V03', 4.0), ('V04', 4.0), ('V05', 5.0)]
T_C = T_B + sum(d for _, d in B)               # 25.0 : song 0.0
OFF_C = T_C
T_D = OFF_C + 120.20                            # 145.2
D = [('V27', DUR['V27']), ('V28', 4.0), ('V29', 4.0)]
T_V30 = T_D + sum(d for _, d in D)
SONG_BACK = T_V30 + 3.6                         # song 119.8 returns here
OFF_E = SONG_BACK - 119.8
T_F = OFF_E + 145.20
F = [('V34', DUR['V34']), ('V35', 9.0), ('V36', 8.0)]
T_V37 = T_F + sum(d for _, d in F)
V37_LEN = 6.30
OFF_G = T_V37 + V37_LEN - 145.20
T_H = OFF_G + 176.40
TOTAL = T_H + 4.0


def build():
    segs = []  # master-time segments
    def add(clip, m0, m1, **kw):
        segs.append(dict(clip=clip, m0=m0, m1=m1, **kw))
    add('A1', T_A1, T_A2, special='A1')
    add('V01', T_A2, T_B, src_in=0.0, speed=1.0)
    t = T_B
    for c, d in B:
        add(c, t, t + d, src_in=0.0, speed=1.0, label='dialog')
        t += d
    def song_shots(lst, off):
        for s in lst:
            pieces = [(s['a'], s['punch'])] if s['punch'] else []
            cuts = [s['a']] + ([s['punch']] if s['punch'] else []) + [s['b']]
            for k in range(len(cuts) - 1):
                a, b = cuts[k], cuts[k + 1]
                sp = s['speed']
                src = s['src_in'] + (a - s['a']) * sp
                z = s['zoom'] if k == 0 else (s['zoom'] * 1.10 if s['zoom'] < 1.12 else s['zoom'] - 0.10)
                fade = s['fade'] if k == len(cuts) - 2 else None
                add(s['clip'], off + a, off + b, src_in=src, speed=sp, zoom=z, flip=s['flip'],
                    warm=s['warm'], trans=s['trans'] if k == 0 else None, fade=fade,
                    sung=s['anchor'] is not None, anchor=s['anchor'], song_a=a, song_b=b, label=s['label'])
    song_shots(C, OFF_C)
    t = T_D
    for c, d in D:
        add(c, t, t + d, src_in=0.0, speed=1.0, label='dialog' if c != 'V27' else None,
            fade=('in', 0.0, 0.6) if c == 'V27' else None)
        t += d
    add('V30', T_V30, OFF_E + 120.20, src_in=0.0, speed=1.0)
    song_shots(E, OFF_E)
    t = T_F
    for c, d in F:
        add(c, t, t + d, src_in=0.0, speed=1.0, label='dialog' if c != 'V34' else None,
            fade=('inwhite', 0.0, 0.4) if c == 'V34' else None)
        t += d
    add('V37', T_V37, T_V37 + V37_LEN, src_in=0.0, speed=0.8)
    song_shots(G, OFF_G)
    add('H', T_H, TOTAL, special='H')
    # frame rounding
    for s in segs:
        s['f0'] = round(s['m0'] * FPS)
        s['f1'] = round(s['m1'] * FPS)
        s['n'] = s['f1'] - s['f0']
    for i in range(1, len(segs)):
        assert segs[i]['f0'] == segs[i - 1]['f1'], (i, segs[i])
    return segs


TL = dict(T_A1=T_A1, T_A2=T_A2, T_B=T_B, T_C=T_C, OFF_C=OFF_C, T_D=T_D, T_V30=T_V30, SONG_BACK=SONG_BACK,
          OFF_E=OFF_E, T_F=T_F, T_V37=T_V37, V37_LEN=V37_LEN, OFF_G=OFF_G, T_H=T_H, TOTAL=TOTAL,
          B=B, D=D, F=F)

if __name__ == '__main__':
    segs = build()
    json.dump(dict(tl=TL, segs=segs), open(os.path.join(S, 'work', 'timeline.json'), 'w'), indent=1)
    for i, s in enumerate(segs):
        print(f"{i:2d} {s['clip']:4s} {s['m0']:8.3f}-{s['m1']:8.3f} n={s['n']:4d} in={s.get('src_in',0):6.3f} "
              f"sp={s.get('speed',1):.3f} z={s.get('zoom',1):.2f} {'F' if s.get('flip') else ' '} "
              f"{s.get('trans') or ''} {s.get('fade') or ''}")
    print(TL)
