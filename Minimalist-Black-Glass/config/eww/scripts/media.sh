#!/bin/bash
# eww media HUD data provider - outputs JSON consumed by the media widget.

OUT=$(playerctl -a metadata -f '{"status":"{{status}}","artist":"{{artist}}","title":"{{title}}","album":"{{album}}","pos":"{{position}}","dur":"{{mpris:length}}","player":"{{playerName}}"}' 2>/dev/null | head -1)

PLAY_ICON="\uf04b"   # 󰐊 play
PAUSE_ICON="\uf04c"  # 󰏤 pause
STOP_ICON="\uf049"   # 󰓛 stopped
BLANK="\uf03a"       # 󰎆

if [ -z "$OUT" ]; then
    python3 -c "
import json
print(json.dumps({
    'status': 'stopped',
    'title': 'NOTHING PLAYING',
    'artline': 'playerctl HUD ready',
    'icon': '$STOP_ICON',
    'bar': '\u2591' * 18,
    'times': '0:00 / 0:00',
    'pos': 0,
    'dur': 0,
}))"
    exit 0
fi

python3 - "$OUT" <<'PYEOF'
import json, sys

try:
    d = json.loads(sys.argv[1])
except Exception:
    d = {"status": "Stopped"}

if d.get("status") == "Stopped":
    print(json.dumps({
        "status": "stopped",
        "title": "NOTHING PLAYING",
        "artline": "playerctl HUD ready",
        "icon": "\uf049",
        "bar": "\u2591" * 18,
        "times": "0:00 / 0:00",
        "pos": 0,
        "dur": 0,
    }))
    sys.exit(0)

def secs(v):
    try:
        return int(int(v or 0) / 1_000_000)
    except Exception:
        return 0

pos = secs(d.get("pos"))
dur = secs(d.get("dur"))
artist = d.get("artist") or "Unknown Artist"
title = d.get("title") or "Unknown Title"
album = d.get("album") or ""
artline = (artist + " - " + album) if album else artist

BARS = 18
filled = int(BARS * (pos / dur)) if dur else 0
bar = "\u2588" * filled + "\u2591" * (BARS - filled)

def fmt(s):
    return f"{s // 60}:{s % 60:02d}"

icon = "\uf04b" if d.get("status") == "Playing" else "\uf04c"
times = f"{fmt(pos)} / {fmt(dur)}" if dur else "live stream"

print(json.dumps({
    "status": d.get("status", "").lower(),
    "title": title,
    "artline": artline,
    "icon": icon,
    "bar": bar,
    "times": times,
    "pos": pos,
    "dur": dur,
}))
PYEOF