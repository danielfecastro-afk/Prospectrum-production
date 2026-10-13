# MiMi Casa E03 — "Thank You, God, for My Family!" build

Scripts expect a scratch root with `dl/` (V01–V39, PRESENTS, AMEN, FF1–FF5), `work/SONG.mp3`,
`work/VOX.mp3` (lead-vocal stem), `fonts/Fredoka-Bold.ttf` and `../images/1.webp` (avatar).

Order: `sync.py` (find each sung clip's song anchor) → `flux.py VOX onsets.npy` → `timeline.py` →
`render_segs.py` → `overlays.py` (then `overlays.py H` once shots exist) → `mix.py` → `subs.py` →
`final.py master.mp4` → `verify_sync.py` (frame-match lip-sync check).

Lip-sync rule: a sung clip's source time = song time − anchor, where the anchor is measured by
cross-correlating the clip's own audio against the lead-vocal stem (re-used chorus shots use the
vocal-envelope match). Shots keep their cut points; only the in-point inside the clip moves.
