#!/usr/bin/env python3
"""QC: duration, LUFS, true peak, contact sheet (one frame per shot)."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = f"{S}/work"
master, sheet = sys.argv[1], sys.argv[2]
plan = json.load(open(f"{W}/plan.json"))
FPS, XF = 24, 7

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", master],
                           capture_output=True, text=True).stdout)
r = subprocess.run(["ffmpeg", "-nostats", "-i", master, "-map", "0:a", "-af", "ebur128=peak=true:framelog=quiet",
                    "-f", "null", "-"], capture_output=True, text=True).stderr.split("Summary:")[-1]
I = float(r.split("I:")[1].split("LUFS")[0])
LRA = float(r.split("LRA:")[1].split("LU")[0])
TP = float(r.split("Peak:")[1].split("dBFS")[0])
print(f"duration {dur:.3f}s  integrated {I:.1f} LUFS  true-peak {TP:.1f} dBTP  LRA {LRA:.1f} LU")

font = ImageFont.truetype(f"{S}/fonts/Fredoka-Bold.ttf", 22)
tw, th, cols = 384, 216, 6
shots = plan["shots"]
rows = (len(shots) + cols - 1) // cols
pad, lab = 8, 30
img = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad + 50), (24, 22, 28))
d = ImageDraw.Draw(img)
d.text((pad, 12), f"MiMi Casa E02 · ¡Mangos para todos!   {dur:.2f} s · {I:.1f} LUFS · {TP:.1f} dBTP",
       font=font, fill="white")
for k, sh in enumerate(shots):
    st = int(sh["start"]) + (XF if k else 0)
    en = int(sh["start"]) + int(sh["N"]) - (XF if k < len(shots) - 1 else 48)
    t = (st + en) / 2 / FPS
    if sh["name"] in ("P13", "P16", "P20a"):
        t = (int(sh["start"]) / FPS) + 1.2          # show the card
    fr = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", master, "-frames:v", "1",
                         "-vf", f"scale={tw}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        capture_output=True).stdout
    im = Image.frombytes("RGB", (tw, th), fr)
    x = pad + (k % cols) * (tw + pad)
    y = 50 + (k // cols) * (th + lab + pad)
    img.paste(im, (x, y))
    d.text((x + 2, y + th + 3), f"{sh['name']}  @{t:6.2f}s  ({int(sh['N']) / FPS:.2f}s)", font=font, fill=(242, 122, 107))
img.save(sheet, quality=90)
print("sheet", sheet)
