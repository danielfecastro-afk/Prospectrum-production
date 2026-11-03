"""Draw each crop shot's 9:16 window on source frames (start / 1/3 / 2/3 / end) for review."""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
S, NAME = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], S, NAME]
exec(open(f"{S}/tools/lote.py").read().split('if __name__ == "__main__":')[0])
Fn = ImageFont.truetype(FONT, 22)
def xat(kf, loc0, t):
    pts = [(a - loc0, x) for a, x in kf]
    if t <= pts[0][0]: return pts[0][1]
    for (ta, xa), (tb, xb) in zip(pts, pts[1:]):
        if t < tb: return xa + (xb - xa) * (t - ta) / (tb - ta)
    return pts[-1][1]
rows = []
for i, sp in enumerate(shot_spans()):
    if sp["mode"] != "crop": continue
    h0 = sp["burn"] if isinstance(sp["burn"], int) and not isinstance(sp["burn"], bool) else (940 if sp["burn"] else 1080)
    w = int(round(h0 * 9 / 16 / 2) * 2)
    d = (sp["b_src"] - sp["a"]) / SFPS
    ims = []
    for f in (0.02, 0.35, 0.68, 0.98):
        t = d * f
        p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{sp["a"] / SFPS + t:.3f}', '-i', SRC, '-frames:v', '1',
                            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        im = Image.frombytes('RGB', (1920, 1080), p)
        x = max(0, min(1920 - w, xat(sp["kf"], sp["loc0"], t) - w / 2))
        dr = ImageDraw.Draw(im)
        dark = Image.new('RGBA', (1920, 1080), (0, 0, 0, 150)); m = Image.new('L', (1920, 1080), 255)
        ImageDraw.Draw(m).rectangle((x, 0, x + w, h0), fill=0)
        im.paste(Image.new('RGB', (1920, 1080), (0, 0, 0)), (0, 0), m.point(lambda v: v * 150 // 255))
        ImageDraw.Draw(im).rectangle((x, 0, x + w, h0), outline=(0, 255, 0), width=6)
        im = im.resize((480, 270)); ImageDraw.Draw(im).text((6, 240), f'shot{i} seg{sp["seg"]} t={t:.1f}', font=Fn,
                                                             fill='white', stroke_width=2, stroke_fill='black')
        ims.append(im)
    rows.append(ims)
c = Image.new('RGB', (4 * 484, len(rows) * 274), (40, 40, 40))
for r, ims in enumerate(rows):
    for k, im in enumerate(ims): c.paste(im, (k * 484, r * 274))
c.save(f"{S}/lote/crop_{NAME}.jpg", quality=85)
