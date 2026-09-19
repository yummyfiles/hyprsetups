#!/bin/sh
# Keep Spotify audio on the Spotify-only sink so cava only visualizes it.
# Runs forever; safe to restart. Works regardless of how Spotify was launched.
# Single instance: a newer copy takes over from any previous one.

PIDFILE=/tmp/spotify-watch.pid
if [ -f "$PIDFILE" ]; then
    old=$(cat "$PIDFILE" 2>/dev/null) || old=""
    if [ -n "$old" ] && [ "$old" != "$$" ] && kill -0 "$old" 2>/dev/null; then
        pkill -TERM -P "$old" 2>/dev/null
        kill "$old" 2>/dev/null
        sleep 0.2
    fi
fi
echo "$$" > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

pactl subscribe | while read -r line; do
    pactl list sink-inputs | python3 -c '
import re, subprocess, sys
text = sys.stdin.read()
for block in re.split(r"\n(?=Sink Input #)", text):
    m = re.search(r"Sink Input #(\d+)", block)
    if not m:
        continue
    idx = m.group(1)
    name = re.search(
        r"application\.(?:process\.binary|name) = \"([^\"]+)\"", block)
    if name and "spotify" in name.group(1).lower():
        subprocess.run(["pactl", "move-sink-input", idx, "Spotify"])
'
done