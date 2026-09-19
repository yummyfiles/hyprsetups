#!/bin/bash
# Desktop widget visibility controller
# Shows widgets ONLY on the desktop, hides them the moment any normal window
# covers or fullscreens over the active workspace.

set -e

# Single instance: a newer copy takes over from any previous one
PIDFILE=/tmp/desktop-watcher.pid
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

EWW_SCRIPT_DIR="$HOME/.config/eww/scripts"
ALL_WIDGETS="github media gh-dashboard clock weather stoat calendar sysinfo appdock"

# Only open/close on state transitions, to avoid spamming eww every second.
LAST_STATE=""
DOCK_TICKS=0
update_widgets() {
    # The desktop widget only belongs on the desktop: it is covered as soon as
    # the currently visible workspace has any normal (unpinned) window, or any
    # fullscreen window is present on this monitor.
    local active_ws=$(hyprctl monitors -j 2>/dev/null | jq -r '.[0].activeWorkspace.id')
    local covered=$(hyprctl clients -j 2>/dev/null | jq --argjson ws "$active_ws" '[.[] | select(.mapped == true and .workspace.id == $ws and .pinned == false) | .address] | length')
    local fullscreen=$(hyprctl clients -j 2>/dev/null | jq --argjson ws "$active_ws" '[.[] | select(.fullscreen == 1 and .workspace.id == $ws) | .address] | length')

    local state
    if [ "${covered:-0}" -gt 0 ] || [ "${fullscreen:-0}" -gt 0 ]; then
        state="covered"
    else
        state="clear"
    fi

    # Keep the :visible flag in sync (normal windows honour it if they use it).
    eww update show_desktop_widgets="$([ "$state" = "clear" ] && echo true || echo false)" 2>/dev/null || true

    if [ "$state" != "$LAST_STATE" ]; then
        if [ "$state" = "covered" ]; then
            for w in $ALL_WIDGETS; do eww close "$w" 2>/dev/null || true; done
        else
            for w in $ALL_WIDGETS; do eww open "$w" 2>/dev/null || true; done
        fi
        LAST_STATE="$state"
    fi

    # Keep the app-dock populated while widgets are visible (deflisten was flaky).
    if [ "$state" = "clear" ]; then
        DOCK_TICKS=$((DOCK_TICKS + 1))
        if [ $((DOCK_TICKS % 15)) -eq 0 ]; then
            sh "$EWW_SCRIPT_DIR/apps.sh" 2>/dev/null || true
        fi
    else
        DOCK_TICKS=0
    fi
}

# Initial check
update_widgets

# Watch for workspace changes
echo "Desktop widget visibility watcher started"
DOCK_TICK=0
while true; do
    sleep 1
    update_widgets
    DOCK_TICK=$((DOCK_TICK + 1))
    if [ $((DOCK_TICK % 15)) -eq 0 ] && [ "$(eww get show_desktop_widgets 2>/dev/null)" = "true" ]; then
        sh "$EWW_SCRIPT_DIR/apps.sh" >/dev/null 2>&1 || true
    fi
done