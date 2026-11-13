#!/usr/bin/env python3
"""Arma el video largo E02 "Sana Sana Colita de Rana" (16:9, 1920x1080).

Uso: python3 build_long.py   (desde episodes/E02/long, con clips/L*.mp4 descargados)
"""
import subprocess, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
E02 = os.path.dirname(HERE)
CLIPS = os.path.join(HERE, "clips")
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
SONG = os.path.join(E02, "audio", "long_song_full.wav")
OUTRO_BED = os.path.join(E02, "audio", "long_part1.mp3")
END_CARD = os.path.join(HERE, "frames", "L21.png")
OUT = os.path.join(E02, "MiMiCasa_E02_SanaSana_LARGO.mp4")

COLD_OPEN = ["L01", "L02", "L03"]  # se usan con su audio nativo, 4 s c/u
# (clip, inicio, fin) dentro del clip; se estira cada mitad para cubrir su tramo de la canción
HALF1 = [("L04", 0, 5), ("L05", 0, 9), ("L06", 0, 8), ("L12", 0, 5),
         ("L07", 0, 6), ("L08", 0, 9), ("L11", 0, 7)]
HALF2 = [("L09", 0, 6), ("L10", 0, 7), ("L12", 0, 5), ("L15", 0, 7),
         ("L17", 0, 6), ("L16", 0, 7), ("L18", 0, 6), ("L19", 0, 5)]
SONG_LEN = 113.7
HALF1_LEN = 57.3 - 0.4
HALF2_LEN = SONG_LEN - HALF1_LEN
OUTRO_FROG = ("L20", 0, 4)
END_CARD_LEN = 12.0

V = "scale=1920:1080:flags=lanczos,fps=24,format=yuv420p,setsar=1"


def dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


def main():
    filters = []
    idx = 0
    in_args = []

    def inp(path, pre=()):
        nonlocal idx
        in_args.extend(list(pre) + ["-i", path])
        idx += 1
        return idx - 1

    # 1) Apertura con audio nativo
    cold_v, cold_a = [], []
    for name in COLD_OPEN:
        i = inp(os.path.join(CLIPS, f"{name}.mp4"))
        filters.append(f"[{i}:v]trim=0:4,setpts=PTS-STARTPTS,{V}[cv{i}]")
        filters.append(f"[{i}:a]atrim=0:4,asetpts=PTS-STARTPTS,aresample=48000[ca{i}]")
        cold_v.append(f"[cv{i}]"); cold_a.append(f"[ca{i}]")
    cold_len = 4.0 * len(COLD_OPEN)

    # 2) Canción: cada mitad se estira para encajar en su tramo
    def still(name, seconds, out_label, direction):
        """Fotograma fijo con zoom lento (Ken Burns) si la escena aún no está animada."""
        i = inp(os.path.join(HERE, "frames", f"{name}.png"))
        frames = int(round(seconds * 24))
        z = "min(zoom+0.0009,1.18)" if direction else "if(eq(on,0),1.18,max(zoom-0.0009,1.0))"
        filters.append(f"[{i}:v]scale=2400:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
                       f"y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=24,format=yuv420p,setsar=1"
                       f"{out_label}")

    def half(segs, target, tag):
        raw = sum(e - s for _, s, e in segs)
        k = target / raw
        labels = []
        for n, (name, s, e) in enumerate(segs):
            lab = f"[{tag}{n}]"
            clip = os.path.join(CLIPS, f"{name}.mp4")
            if os.path.exists(clip):
                i = inp(clip)
                filters.append(f"[{i}:v]trim={s}:{e},setpts=(PTS-STARTPTS)*{k:.4f},{V}{lab}")
            else:
                print(f"  (sin animar) {name}: fotograma con zoom")
                still(name, (e - s) * k, lab, n % 2 == 0)
            labels.append(lab)
        return labels

    song_v = half(HALF1, HALF1_LEN, "h1_") + half(HALF2, HALF2_LEN, "h2_")

    # 3) Rana "¿Otra vez?" + tarjeta final
    frog_clip = os.path.join(CLIPS, f"{OUTRO_FROG[0]}.mp4")
    if os.path.exists(frog_clip):
        i = inp(frog_clip)
        filters.append(f"[{i}:v]trim={OUTRO_FROG[1]}:{OUTRO_FROG[2]},setpts=PTS-STARTPTS,{V}[frog0]")
    else:
        print(f"  (sin animar) {OUTRO_FROG[0]}: fotograma con zoom")
        still(OUTRO_FROG[0], OUTRO_FROG[2] - OUTRO_FROG[1], "[frog0]", True)
    filters.append(f"[frog0]drawtext=fontfile={FONT}:text='¿Otra vez?  One more time!':fontsize=110:"
                   f"fontcolor=#FFD93B:borderw=10:bordercolor=#1E7A3A:x=(w-tw)/2:y=90[frog]")
    i = inp(END_CARD)
    filters.append(
        f"[{i}:v]scale=2400:-1,zoompan=z='min(zoom+0.0006,1.15)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={int(END_CARD_LEN*24)}:s=1920x1080:fps=24,format=yuv420p,setsar=1,"
        f"drawtext=fontfile={FONT}:text='¡Suscríbete a MiMi Casa!':fontsize=96:fontcolor=white:"
        f"borderw=9:bordercolor=#7A1F3D:x=(w-tw)/2:y=80[card]")

    allv = cold_v + song_v + ["[frog]", "[card]"]
    filters.append("".join(allv) + f"concat=n={len(allv)}:v=1:a=0[vout]")

    # Audio: apertura nativa -> canción -> cama suave en el cierre
    s = inp(SONG)
    o = inp(OUTRO_BED)
    outro_len = (OUTRO_FROG[2] - OUTRO_FROG[1]) + END_CARD_LEN
    filters.append("".join(cold_a) + f"concat=n={len(cold_a)}:v=0:a=1[cold]")
    filters.append(f"[{s}:a]aresample=48000,atrim=0:{SONG_LEN}[song]")
    filters.append(f"[{o}:a]aresample=48000,atrim=13:{13+outro_len},asetpts=PTS-STARTPTS,"
                   f"volume=0.35,afade=t=in:d=1,afade=t=out:st={outro_len-3}:d=3[bed]")
    filters.append("[cold][song][bed]concat=n=3:v=0:a=1,alimiter=limit=0.95[aout]")

    total = cold_len + SONG_LEN + outro_len
    cmd = ["ffmpeg", "-v", "error", "-y", *in_args, "-filter_complex", ";".join(filters),
           "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print(f"OK {OUT} ~{total:.1f}s")


if __name__ == "__main__":
    main()
