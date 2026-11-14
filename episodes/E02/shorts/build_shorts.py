#!/usr/bin/env python3
"""Corta 3 Shorts verticales (1080x1920) del video largo E02 sin gastar créditos.

Cada tramo es (inicio, fin, x_recorte) sobre el master 1920x1080. x_recorte puede ser
un número o una expresión de ffmpeg en función de t (segundos del tramo) para hacer paneos.
"""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "MiMiCasa_E02_SanaSana_LARGO.mp4")
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
CW = 608  # ancho del recorte 9:16 sobre 1080 de alto

SHORTS = {
    "S2_ay_mi_dedito": {
        "hook": ["¡AY!", "¡MI DEDITO!"],
        "segs": [(43.4, 50.4, 950), (50.4, 60.9, 1100), (60.9, 69.0, 560)],
    },
    "S3_perrito_espinita": {
        "hook": ["¡POBRE", "PERRITO!"],
        "segs": [(69.0, 76.0, 480), (76.0, 84.0, 700), (84.0, 90.0, 656)],
    },
    "S4_ranita_bailarina": {
        "hook": ["¡LA RANITA", "BAILARINA!"],
        # en L15 la cámara va de la rana a la abuela
        "segs": [(84.0, 90.0, 656), (90.0, 98.0, "250+100*t"), (98.0, 105.0, 650)],
    },
}


def build(name, cfg):
    out = os.path.join(HERE, f"MiMiCasa_E02_{name}.mp4")
    ins, f, labels = [], [], []
    for n, (a, b, x) in enumerate(cfg["segs"]):
        ins += ["-ss", f"{a}", "-t", f"{b - a}", "-i", SRC]
        xe = f"'min(max({x},0),{1920 - CW})'"
        f.append(f"[{n}:v]crop={CW}:1080:{xe}:0,scale=1080:1920:flags=lanczos,"
                 f"unsharp=5:5:0.6,setsar=1,fps=24[v{n}]")
        f.append(f"[{n}:a]aresample=48000[a{n}]")
        labels.append(f"[v{n}][a{n}]")
    total = sum(b - a for a, b, _ in cfg["segs"])
    l1, l2 = cfg["hook"]
    f.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=1[vc][ac]")
    f.append(
        f"[vc]drawtext=fontfile={FONT}:text='{l1}':fontsize=130:fontcolor=#FFD93B:borderw=11:"
        f"bordercolor=#7A1F3D:x=(w-tw)/2:y=230:enable='lt(t,3.5)',"
        f"drawtext=fontfile={FONT}:text='{l2}':fontsize=130:fontcolor=#FFD93B:borderw=11:"
        f"bordercolor=#7A1F3D:x=(w-tw)/2:y=380:enable='lt(t,3.5)',"
        f"drawtext=fontfile={FONT}:text='¡Sana, sana,':fontsize=92:fontcolor=white:borderw=8:"
        f"bordercolor=#1E7A3A:x=(w-tw)/2:y=1460:enable='gte(t,3.5)',"
        f"drawtext=fontfile={FONT}:text='colita de rana!':fontsize=92:fontcolor=#B6F36B:borderw=8:"
        f"bordercolor=#1E7A3A:x=(w-tw)/2:y=1570:enable='gte(t,3.5)'[vout]")
    f.append(f"[ac]afade=t=in:d=0.3,afade=t=out:st={total - 0.8:.2f}:d=0.8[aout]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(f),
                    "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", out], check=True)
    print(f"OK {out} {total:.1f}s")


if __name__ == "__main__":
    for k, v in SHORTS.items():
        build(k, v)
