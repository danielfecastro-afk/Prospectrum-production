#!/bin/bash
# Builds the graded 1080x1920/30 fps base segments and concatenates them (timeline = song seconds).
set -euo pipefail
S=$1; cd "$S"; mkdir -p seg
FILL="scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920"
PUNCH="scale=1242:2208:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920"
GRADE="colorbalance=rs=0.04:gs=0.01:bs=-0.05:rm=0.035:bm=-0.04:rh=0.02:bh=-0.03,eq=saturation=1.06,format=yuv420p"
ENC="-an -c:v libx264 -preset fast -crf 12 -pix_fmt yuv420p -r 30"

# name src start_frame frames scale extra(pre-scale)
seg() {
  local name=$1 src=$2 sf=$3 nf=$4 sc=$5 pre=${6:-}
  ffmpeg -v error -y -i "$src" -vf "${pre}fps=30,trim=start_frame=${sf},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=3,${sc},${GRADE},trim=end_frame=${nf}" \
    $ENC "seg/$name.mp4"
  echo "$name $(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 seg/$name.mp4) / $nf"
}

ffmpeg -v error -y -framerate 30 -i ov/intro/%04d.png -vf "${GRADE}" -frames:v 30 $ENC seg/00_intro.mp4
seg 01_V09a dl/V09.mp4 0   195 "$FILL"                     # 1.0-7.5
seg 02_V01  dl/V01.mp4 0   210 "$FILL"                     # 7.5-14.5
seg 03_V02  dl/V02.mp4 0   210 "$FILL"                     # 14.5-21.5
seg 04_V03  dl/V03.mp4 0   216 "$FILL"                     # 21.5-28.7
seg 05_V04  dl/V04.mp4 0   189 "$FILL"                     # 28.7-35.0
seg 06_V09b dl/V09.mp4 195 18  "$FILL"                     # 35.0-35.6 (clip 6.5-7.0)
seg 07_V05  dl/V05.mp4 0   222 "$FILL"                     # 35.6-43.0
seg 08_V06  dl/V06.mp4 0   111 "$FILL"                     # 43.0-46.7
seg 09_V07  dl/V07.mp4 0   102 "$FILL"                     # 46.7-50.1
seg 10_V08  dl/V08.mp4 0   213 "$FILL"                     # 50.1-57.2
seg 11_V03p dl/V03.mp4 ${V03P_SF:-4} 213 "$PUNCH"          # 57.2-64.3, in-point +0.13 s (sync)
seg 12_V04p dl/V04.mp4 ${V04P_SF:-2} 180 "$PUNCH"          # 64.3-70.3, in-point +0.05 s (sync)
seg 13_V10  dl/V10.mp4 0   255 "$FILL" "setpts=PTS*6.2/6.0417,"  # 70.3-76.5 slowed, freeze to 78.8

(cd seg && ls *.mp4) | sed "s/^/file '/;s/$/'/" > seg/list.txt
ffmpeg -v error -y -f concat -safe 0 -i seg/list.txt -c copy base.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 base.mp4
