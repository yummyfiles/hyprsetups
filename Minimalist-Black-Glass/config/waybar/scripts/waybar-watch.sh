#!/bin/bash
# Watch waybar configs and keep exactly one waybar + one watcher alive.
# A newer instance wins: it retires any previous watcher it finds.

set -e

CONFIG_FILE="$HOME/.config/waybar/config"
STYLE_FILE="$HOME/.config/waybar/style.css"
PIDFILE=/tmp/waybar-watch.pid

if [ -f "$PIDFILE" ]; then
    old=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "$old" ] && [ "$old" != "$$" ] && kill -0 "$old" 2>/dev/null; then
        pkill -TERM -P "$old" 2>/dev/null || true
        kill "$old" 2>/dev/null || true
        sleep 0.5
    fi
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"; pkill -TERM waybar 2>/dev/null || true' EXIT

restart_bar() {
    pkill -TERM waybar 2>/dev/null || true
    sleep 0.5
    waybar &
}

restart_bar

inotifywait -m -e modify,create,delete,move "$CONFIG_FILE" "$STYLE_FILE" 2>/dev/null |
while read -r directory event file; do
    restart_bar
done