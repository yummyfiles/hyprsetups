#!/bin/sh
set -e

# ensure the Spotify-only sink exists
if ! pactl list short sinks | grep -qE '[[:space:]]Spotify[[:space:]]'; then
    pactl load-module module-null-sink sink_name=Spotify \
        sink_properties=device.description="Spotify" >/dev/null
fi

# route Spotify's audio back to the real output so it stays audible
if ! pactl list short modules | grep -q 'source=Spotify.monitor'; then
    pactl load-module module-loopback source=Spotify.monitor \
        sink=@DEFAULT_SINK@ >/dev/null
fi

# heal: move any already-running Spotify streams onto the Spotify sink
# so cava keeps seeing only Spotify regardless of launch method
pactl list sink-inputs | python3 - <<'PY'
import re, subprocess, sys

text = sys.stdin.read()
for block in re.split(r"\n(?=Sink Input #)", text):
    m = re.search(r"Sink Input #(\d+)", block)
    if not m:
        continue
    name = re.search(
        r"application\.(?:process\.binary|name) = \"([^\"]+)\"", block)
    if name and "spotify" in name.group(1).lower():
        subprocess.run(["pactl", "move-sink-input", m.group(1), "Spotify"])
PY

# persistent watcher: catches Spotify streams that appear after startup
if ! pgrep -f "cava/scripts/spotify-watch.sh" >/dev/null; then
    nohup sh /home/yummy.dev/.config/cava/scripts/spotify-watch.sh >/dev/null 2>&1 &
fi