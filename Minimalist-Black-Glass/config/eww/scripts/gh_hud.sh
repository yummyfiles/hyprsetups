#!/bin/bash
# GitHub HUD renderer - monochrome, uses real avatar from gh cache
# Usage: ~/.config/eww/scripts/gh_hud.sh

set -e
CFG="$HOME/.config/eww/scripts"
CACHE="$HOME/.cache/eww-gh.json"

# Load GitHub data from cache or fallback
if [ -f "$CACHE" ]; then
    LOGIN=$(jq -r '.login' "$CACHE")
    NAME=$(jq -r '.name' "$CACHE")
    FOLLOWERS=$(jq -r '.followers' "$CACHE")
    FOLLOWING=$(jq -r '.following' "$CACHE")
    REPOS=$(jq -r '.repos' "$CACHE")
    STARS=$(jq -r '.stars' "$CACHE")
    STREAK=$(jq -r '.streak' "$CACHE")
    CONTRIB=$(jq -r '.contributions' "$CACHE")
    AVATAR_URL=$(jq -r '.avatar' "$CACHE")
else
    LOGIN="yummyfiles"
    NAME="YUMMYFILES // DEV"
    FOLLOWERS=19; FOLLOWING=37; REPOS=18; STARS=6
    STREAK=0; CONTRIB=369
    AVATAR_URL="https://avatars.githubusercontent.com/u/147447349?v=4"
fi

# Font paths
FONT_REGULAR="/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
FONT_BOLD="/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"

OUT_DIR="/tmp"
VER=$(( $(ls "$OUT_DIR"/ghdh.*.png 2>/dev/null | wc -l) + 1 ))
OUT_FILE="$OUT_DIR/ghdh.$VER.png"

# Helper: download avatar (full-size square)
AVATAR_PATH="/tmp/github_avatar.png"
if command -v curl >/dev/null 2>&1; then
    curl -s -o "$AVATAR_PATH" "$AVATAR_URL"
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$AVATAR_PATH" "$AVATAR_URL"
else
    AVATAR_PATH="/tmp/dummy_avatar.png"
    magick -size 128x128 xc:#FFFFFF "$AVATAR_PATH"
fi

# Monochrome avatar (convert to grayscale, then to 1-bit)
magick "$AVATAR_PATH" -colorspace Gray -resize 44x44! "$OUT_FILE"

# Helper: text width measurement using magick
tw() {
    magick -font "$1" -pointsize "$2" "label:$3" -format "%w" info: 2>/dev/null
}

# === HEADER ===
# Avatar (real grayscale avatar with white border)
magick "$OUT_FILE" \
    -fill "rgb(255,255,255)" -draw "rectangle 3,3 49,49" \
    "$OUT_FILE"

# Name and login (monospace, bold for name, regular for login)
NAME_WIDTH=$(tw "$FONT_BOLD" 18 "$NAME")
LOGIN_WIDTH=$(tw "$FONT_REGULAR" 10 "@$LOGIN")
magick "$OUT_FILE" \
    -fill "rgb(255,255,255)" -font "$FONT_BOLD" -pointsize 18 -gravity West -annotate +0+0 "$NAME" \
    -fill "rgb(255,255,255)" -font "$FONT_REGULAR" -pointsize 10 -gravity West -annotate +$((NAME_WIDTH+6))+9 "@$LOGIN" \
    "$OUT_FILE"

# Right tag: GH · DEV HUD (monospace, centered in 84px box)
TAG_TEXT="GH · DEV HUD"
TAG_WIDTH=$(tw "$FONT_REGULAR" 10 "$TAG_TEXT")
TAG_X=$((640 - TAG_WIDTH - 28))
magick "$OUT_FILE" \
    -fill "rgb(255,255,255)" -stroke "rgb(255,255,255)" -strokewidth 1 -fill none \
    -draw "rectangle $((TAG_X-6)),4 $((TAG_X+TAG_WIDTH+6)),22" \
    -fill "rgb(255,255,255)" -font "$FONT_REGULAR" -pointsize 10 -gravity Center -annotate +0+12 "$TAG_TEXT" \
    "$OUT_FILE"

# Header underline
magick "$OUT_FILE" \
    -fill "rgb(255,255,255)" -draw "rectangle 4,54 636,56" "$OUT_FILE"

# === STATS COLUMN (followers/following/repos/stars) ===
COL_W=160
COL_X=8
for i in 0 1 2 3; do
    case $i in
        0) VAL="$FOLLOWERS"; LBL="FOLLOWERS";;
        1) VAL="$FOLLOWING"; LBL="FOLLOWING";;
        2) VAL="$REPOS"; LBL="REPOS";;
        3) VAL="$STARS"; LBL="STARS";;
    esac
    CX=$((COL_X + i*COL_W + COL_W/2))
    VAL_W=$(tw "$FONT_BOLD" 20 "$VAL")
    LBL_W=$(tw "$FONT_REGULAR" 9 "$LBL")
    magick "$OUT_FILE" \
        -fill "rgb(255,255,255)" -font "$FONT_BOLD" -pointsize 20 -gravity Center -annotate +$((CX - VAL_W/2))+60 "$VAL" \
        -fill "rgb(255,255,255)" -font "$FONT_REGULAR" -pointsize 9 -gravity Center -annotate +$((CX - LBL_W/2))+88 "$LBL" \
        "$OUT_FILE"
    if [ $i -gt 0 ]; then
        DX=$((COL_X + i*COL_W))
        magick "$OUT_FILE" -fill "rgb(255,255,255)" -draw "rectangle $DX,54 $((DX+1)),104" "$OUT_FILE"
    fi
done

# === FOOTER (streak/year) ===
magick "$OUT_FILE" \
    -fill "rgb(255,255,255)" -draw "rectangle 8,110 632,112" \
    -fill "rgb(255,255,255)" -font "$FONT_BOLD" -pointsize 10 -gravity West -annotate +12+114 "STREAK: $STREAK DAYS" \
    -fill "rgb(255,255,255)" -font "$FONT_REGULAR" -pointsize 10 -gravity East -annotate -12+114 "YEAR: $CONTRIB CONTRIBUTIONS" \
    "$OUT_FILE"

echo "$OUT_FILE"