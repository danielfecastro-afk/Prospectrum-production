#!/usr/bin/env python3
"""Arma el video largo 02 de WorthWired (surveillance pricing) a partir de:
  audio/N1..N8.wav  (narración por sección)
  img/I01..I24.png  (b-roll generado)
Las tarjetas con cifras se dibujan aquí con PIL (texto exacto, sin IA).
Salida: WorthWired_LONG02_surveillance_pricing.mp4 (1920x1080, 30 fps)
"""
import os, subprocess, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
IMG, AUD = os.path.join(HERE, "img"), os.path.join(HERE, "audio")
BUILD = os.path.join(HERE, "build")
OUT = os.path.join(HERE, "WorthWired_LONG02_surveillance_pricing.mp4")
F = "/usr/share/fonts/opentype/inter/"
BLACK, XB, SB = F + "InterDisplay-Black.otf", F + "Inter-ExtraBold.otf", F + "Inter-SemiBold.otf"
W, H, FPS = 1920, 1080, 30
GOLD, WHITE, RED, GREY, BG = (245, 197, 24), (255, 255, 255), (229, 57, 53), (170, 176, 186), (11, 15, 20)


def font(p, s):
    return ImageFont.truetype(p, s)


def bg_from(img_name, dim=0.28, blur=6):
    if img_name:
        im = Image.open(os.path.join(IMG, img_name)).convert("RGB").resize((W, H), Image.LANCZOS)
        im = im.filter(ImageFilter.GaussianBlur(blur))
        im = ImageEnhance.Brightness(im).enhance(dim)
    else:
        im = Image.new("RGB", (W, H), BG)
    return im


def centered(d, y, text, fnt, fill, stroke=0):
    w = d.textlength(text, font=fnt)
    d.text(((W - w) / 2, y), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def card(name, lines, source=None, bg=None, kicker=None):
    """lines: list of (text, size, color, font)."""
    im = bg_from(bg)
    d = ImageDraw.Draw(im)
    total = sum(int(s * 1.25) for _, s, _, _ in lines) + (90 if kicker else 0)
    y = (H - total) / 2 - (30 if source else 0)
    if kicker:
        centered(d, y, kicker, font(XB, 44), GOLD)
        y += 90
    for text, size, color, fp in lines:
        centered(d, y, text, font(fp, size), color, stroke=3 if size > 90 else 0)
        y += int(size * 1.25)
    if source:
        centered(d, H - 90, "Source: " + source, font(SB, 28), GREY)
    # sello del canal
    d.text((110, 80), "WORTHWIRED", font=font(XB, 30), fill=GOLD)
    path = os.path.join(BUILD, f"card_{name}.png")
    im.save(path)
    return path


def overlay(img_name, name, top=None, bottom=None, tag=None):
    """Imagen con texto grande encima (estilo Shorts)."""
    im = Image.open(os.path.join(IMG, img_name)).convert("RGB").resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")
    if bottom:
        d.rectangle([0, H - 260, W, H], fill=(0, 0, 0, 150))
        centered(d, H - 215, bottom[0], font(BLACK, bottom[1]), bottom[2], stroke=4)
    if top:
        centered(d, 70, top[0], font(BLACK, top[1]), top[2], stroke=6)
    if tag:
        d.rounded_rectangle([110, 90, 110 + d.textlength(tag, font=font(XB, 40)) + 50, 160], 18, fill=(245, 197, 24, 235))
        d.text((135, 100), tag, font=font(XB, 40), fill=(0, 0, 0))
    path = os.path.join(BUILD, f"ov_{name}.png")
    im.save(path)
    return path


def img(n):
    return os.path.join(IMG, f"I{n:02d}.png")


def plan():
    G, Wh, R = GOLD, WHITE, RED
    C = card
    return {
        "N1": [
            (overlay("I01.png", "five", bottom=("$3.99 · $4.28 · $4.59 · $4.69 · $4.79", 88, G)), 3),
            (C("same", [("SAME EGGS.", 120, Wh, BLACK), ("SAME STORE. SAME TIME.", 84, Wh, BLACK), ("5 DIFFERENT PRICES.", 120, R, BLACK)], bg="I01.png"), 2),
            (img(3), 2),
            (C("437", [("437 SHOPPERS", 130, G, BLACK), ("3 OUT OF 4 ITEMS", 90, Wh, BLACK), ("had more than one price", 60, Wh, SB)],
               source="Groundwork Collaborative / Consumer Reports / More Perfect Union, Dec. 2025", bg="I03.png"), 2.5),
            (C("yourprice", [("YOUR PRICE", 150, Wh, BLACK), ("≠ MY PRICE", 150, R, BLACK)], bg="I02.png"), 2),
            (img(2), 2),
        ],
        "N2": [
            (img(3), 2),
            (C("stats", [("~75%", 120, G, BLACK), ("of items had more than one price", 54, Wh, SB),
                         ("UP TO 23% MORE", 100, R, BLACK), ("for the same item", 54, Wh, SB),
                         ("≈ $1,200 / YEAR", 100, G, BLACK), ("estimated extra cost for a family of four", 50, Wh, SB)],
               source="Groundwork Collaborative / Consumer Reports / More Perfect Union, Dec. 2025", bg="I03.png"), 4),
            (overlay("I04.png", "saltines", bottom=("$3.99  vs  $4.69", 120, G), tag="SAME SALTINES · SAME TARGET · OHIO"), 2.5),
            (img(13), 2),
            (C("instacart", [("INSTACART'S RESPONSE", 80, G, BLACK), ("“Random tests, not personal data”", 62, Wh, SB),
                             ("→ ENDED ALL ITEM PRICE TESTS", 78, Wh, BLACK), ("FTC + NY Attorney General started asking questions", 48, GREY, SB)],
               source="CNBC, Dec. 22, 2025 · NY Attorney General, 2026", bg="I13.png"), 3.5),
            (img(5), 2),
            (img(6), 2),
        ],
        "N3": [
            (overlay("I06.png", "surv", top=("SURVEILLANCE PRICING", 120, G)), 3),
            (img(5), 1.5),
            (C("tracked", [("WHAT CAN BE TRACKED", 90, G, BLACK), ("• Your location", 70, Wh, XB), ("• Browsing & purchase history", 70, Wh, XB),
                           ("• Mouse movements", 70, Wh, XB), ("• What you leave in your cart", 70, Wh, XB)],
               source="FTC Surveillance Pricing Study, preliminary staff findings, Jan. 2025", bg="I06.png"), 4),
            (img(7), 2),
            (img(18), 1.5),
            (img(9), 2),
            (img(8), 1.5),
            (C("prelim", [("IMPORTANT", 70, G, BLACK), ("Findings were preliminary.", 72, Wh, XB), ("Examples were hypothetical.", 72, Wh, XB),
                          ("The tools exist — and they're being sold.", 60, GREY, SB)],
               source="FTC, Jan. 17, 2025", bg="I08.png"), 3),
        ],
        "N4": [
            (overlay("I11.png", "fought", top=("2026: STATES FIGHT BACK", 110, G)), 2.5),
            (C("md", [("BANNED", 140, R, BLACK), ("Personal-data pricing at large grocery stores", 54, Wh, SB),
                      ("& grocery delivery apps · in effect Oct. 1, 2026", 54, Wh, SB), ("Store prices must hold ≥ 1 business day", 54, Wh, SB),
                      ("Loophole: loyalty-program pricing", 54, G, XB)],
               source="Maryland HB 895, Protection From Predatory Pricing Act", bg="I10.png", kicker="MARYLAND"), 5),
            (img(10), 2),
            (C("ct", [("BANNED", 140, R, BLACK), ("Surveillance pricing by retail sellers", 56, Wh, SB), ("& food-delivery services", 56, Wh, SB),
                      ("+ online label when personal data raises a price", 54, G, XB)],
               source="Connecticut, law signed in 2026", bg="I11.png", kicker="CONNECTICUT"), 4),
        ],
        "N5": [
            (C("nj", [("SHOPPERS CAN SUE", 120, R, BLACK), ("Grocery stores & delivery apps · signed July 23, 2026", 52, Wh, SB),
                      ("Up to $50,000 per violation", 70, G, BLACK), ("Comply by Aug. 1, 2027 · pause on new electronic shelf labels", 46, Wh, SB)],
               source="NJ Fair Price Protection Act, P.L.2026, c.55", bg="I12.png", kicker="NEW JERSEY"), 5),
            (img(12), 1.5),
            (img(14), 1.5),
            (C("ny", [("“THIS PRICE WAS SET", 88, Wh, BLACK), ("BY AN ALGORITHM USING", 88, Wh, BLACK), ("YOUR PERSONAL DATA.”", 88, G, BLACK),
                      ("Required disclosure since Nov. 2025", 50, GREY, SB)],
               source="NY Algorithmic Pricing Disclosure Act", bg="I14.png", kicker="NEW YORK"), 4),
            (C("bills", [("40+ BILLS", 150, G, BLACK), ("in 24+ states (summer 2026)", 70, Wh, XB)],
               source="Greenberg Traurig, Sep. 2026", bg="I11.png"), 2.5),
            (img(5), 1.5),
            (C("ftc", [("FTC · AUG. 2026", 90, G, BLACK), ("Hidden personalized pricing can be", 60, Wh, SB), ("deceptive or unfair", 80, R, BLACK),
                       ("A proposal — not a ban", 60, Wh, XB)],
               source="FTC Proposed Enforcement Policy Statement, Aug. 19, 2026", bg="I05.png"), 4),
        ],
        "N6": [
            (overlay("I15.png", "esl", top=("DIGITAL PRICE TAGS", 110, G)), 3),
            (img(16), 2),
            (C("esl", [("PRICES THAT CHANGE IN SECONDS", 72, Wh, BLACK), ("Maryland: grocery prices must hold ≥ 1 business day", 52, G, XB),
                       ("New Jersey: pause on new installations", 52, G, XB)],
               source="Maryland HB 895 · NJ P.L.2026, c.55", bg="I15.png"), 3),
            (img(10), 1.5),
        ],
        "N7": [
            (C("5ways", [("5 WAYS", 170, G, BLACK), ("to protect your wallet", 80, Wh, XB)], bg="I21.png"), 2),
            (overlay("I17.png", "t1", bottom=("1 · COMPARE BEFORE YOU BUY", 90, G)), 3),
            (overlay("I24.png", "t1b", bottom=("Logged out · private window · other device", 64, Wh)), 2),
            (overlay("I18.png", "t2", bottom=("2 · WATCH THE CART GAME", 90, G)), 3),
            (overlay("I19.png", "t3", bottom=("3 · KNOW WHAT YOUR LOYALTY CARD COSTS", 76, G)), 3),
            (overlay("I14.png", "t4", bottom=("4 · LOOK FOR THE LABEL", 90, G)), 2.5),
            (overlay("I20.png", "t5", bottom=("5 · REPORT IT TO YOUR STATE AG", 84, G)), 3),
        ],
        "N8": [
            (img(22), 2),
            (img(21), 2),
            (C("end", [("WORTHWIRED", 140, G, BLACK), ("Decoding the American money system", 64, Wh, XB), ("SUBSCRIBE", 90, R, BLACK)],
               source=None, bg="I23.png"), 2.5),
        ],
    }


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))


def kenburns(src, out, seconds, zin):
    frames = max(int(round(seconds * FPS)), 2)
    # tarjetas y overlays (generados en build/) casi sin zoom para no cortar el texto
    zmax = 1.03 if os.path.dirname(src) == BUILD else 1.12
    step = (zmax - 1.0) / frames
    z = f"min(zoom+{step:.6f},{zmax})" if zin else f"if(eq(on,0),{zmax},max(zoom-{step:.6f},1.0))"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf",
                    f"scale=2880:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p,setsar=1",
                    "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out], check=True)


def main():
    os.makedirs(BUILD, exist_ok=True)
    p = plan()
    sections = []
    k = 0
    for sec in ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"]:
        a = os.path.join(AUD, f"{sec}.wav")
        L = dur(a) + 0.6  # pequeña pausa entre secciones
        weights = sum(w for _, w in p[sec])
        clips = []
        for src, w in p[sec]:
            out = os.path.join(BUILD, f"seg_{k:03d}.mp4")
            kenburns(src, out, L * w / weights, k % 2 == 0)
            clips.append(out); k += 1
        lst = os.path.join(BUILD, f"{sec}.txt")
        open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
        sv = os.path.join(BUILD, f"{sec}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", a,
                        "-filter_complex", f"[1:a]apad=pad_dur=0.6,aresample=48000[a]", "-map", "0:v", "-map", "[a]",
                        "-t", f"{L:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", sv], check=True)
        sections.append(sv)
        print(sec, f"{L:.1f}s", len(clips), "clips")
    lst = os.path.join(BUILD, "all.txt")
    open(lst, "w").write("".join(f"file '{s}'\n" for s in sections))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True)
    print("OK", OUT, f"{dur(OUT):.1f}s")


if __name__ == "__main__":
    main()
