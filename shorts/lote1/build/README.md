# MiMi Casa Shorts — batch 1 (M1–M4, from E03 master)

All footage and audio are cut from `episodes/E03/MiMiCasa_E03_master.mp4` (branch `claude/dreamy-sagan-w5fzty`); nothing generated.

- `lote_cfg.py` — per Short: master in/out, per-shot framing (`crop` 9:16 with x keyframes, or `fit` = full frame on blurred copy),
  exterior flag (falling leaves), burned-text flag (the master has burned-in chorus karaoke at rows ≥ 955 and a text card at
  22.5–24.75 s, rows ≥ 875; those shots only use rows above it), and subtitle cues (K = karaoke, D = spoken).
- `burnk.py` — reads each chorus word's sung time from the master's own burned karaoke (word turns yellow) → `burnk.json`.
- `lote.py <scratch> <name>` — stages `video gfx subs audio final`. `cropchk.py` draws the crop windows on source frames for review.
- `*.ass` — the subtitle/karaoke files burned into each Short.

Scratch layout: `lote/src/` (masters), `lote/e03v.raw` (vocal-band 8 kHz mono of E03), `e03b/work/timeline.json`
(from E03 `build/timeline.py`), `fonts/Fredoka-Bold.ttf`, avatar PNG.
