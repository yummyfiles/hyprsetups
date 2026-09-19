#!/bin/bash
# Render the media player HUD (B&W, pixel-exact), print new path for eww refresh.
set -e
CACHE="$HOME/.cache/eww-media.json"

if [ ! -f "$CACHE" ]; then
  "$HOME/.config/eww/scripts/media.sh" >/dev/null 2>&1 || true
fi

if [ -f "$CACHE" ]; then
  TITLE=$(jq -r '.title' "$CACHE")
  ARTIST=$(jq -r '.artline' "$CACHE")
  TIMES=$(jq -r '.times' "$CACHE")
  STATUS=$(jq -r '.status' "$CACHE")
  PTS=$(jq -r '.pos' "$CACHE" 2>/dev/null | tr -d '"')
  LEN=$(jq -r '.dur' "$CACHE" 2>/dev/null | tr -d '"')
else
  TITLE="NOTHING PLAYING"; ARTIST="playerctl HUD ready"; TIMES="0:00 / 0:00"
  STATUS="stopped"; PTS=0; LEN=0
fi

PTS=${PTS:-0}; LEN=${LEN:-0}
if [ -n "$LEN" ] && [ "$LEN" -gt 0 ] 2>/dev/null; then
  PCT=$(( PTS * 100 / LEN ))
else
  PCT=0
fi
[ "$PCT" -gt 100 ] && PCT=100

case "$STATUS" in
  playing) ICON=">";;
  paused)  ICON="||";;
  *)       ICON="#";;
esac

B=0; W=255
OUT="/tmp"
VER=$(( $(ls "$OUT"/mediahd.*.png 2>/dev/null | wc -l) + 1 ))
FILE="$OUT/mediahd.$VER.png"
FONT="/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
FBOLD="/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"

# truncate to fit width (approximate px per char at pointsize)
[ ${#TITLE}  -gt 34 ] && TITLE="${TITLE:0:33}…"
[ ${#ARTIST} -gt 48 ] && ARTIST="${ARTIST:0:47}…"

magick -size 500x88 xc:none "$FILE"

# outer border
magick "$FILE" -fill none -stroke "gray($W)" -strokewidth 2 \
  -draw "rectangle 1,1 498,86" "$FILE"

# art square + icon
magick "$FILE" -fill "gray($W)" -draw "rectangle 14,12 44,42" \
  -fill "gray($B)" -font "$FONT" -pointsize 16 -gravity NorthWest -annotate +23+19 "$ICON" \
  -fill "gray($W)" -font "$FBOLD" -pointsize 15 -gravity NorthWest -annotate +56+13 "$TITLE" \
  -font "$FONT" -pointsize 10 -gravity NorthWest -annotate +57+35 "$ARTIST" \
  "$FILE"

# status tag right
STATUS_TXT=$(echo "$STATUS" | tr 'a-z' 'A-Z')
STW=$(magick -font "$FONT" -pointsize 9 "label:$STATUS_TXT" -format "%w" info:)
SBX=$((488 - STW - 12))
magick "$FILE" -fill "gray($W)" -font "$FONT" -pointsize 9 -gravity NorthWest \
  -annotate +$((SBX))+12 "$STATUS_TXT" \
  -fill "gray($W)" -draw "rectangle 14,52 486,54" "$FILE"

# progress track (black = disabled) + fill (solid white)
TRACK_X=14; TRACK_W=486
FILL_W=$(( TRACK_W * PCT / 100 ))
magick "$FILE" -fill "gray($B)" \
  -draw "rectangle $TRACK_X,62 $((TRACK_X+TRACK_W)),65" \
  -fill "gray($W)" \
  -draw "rectangle $TRACK_X,62 $((TRACK_X+FILL_W)),65" \
  -font "$FONT" -pointsize 10 -gravity NorthWest -annotate +14+70 "$TIMES" \
  "$FILE"

echo "$FILE"
# keep /tmp tidy
ls -t "$OUT"/mediahd.*.png 2>/dev/null | tail -n +8 | xargs -r rm -f
ls -t "$OUT"/ghdh.*.png 2>/dev/null | tail -n +8 | xargs -r rm -f