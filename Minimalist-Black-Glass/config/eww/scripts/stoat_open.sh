#!/usr/bin/env bash
# OPEN/TOGGLE the stoat chat window.
if ! pgrep -f "stoat-desktop/app.asar" >/dev/null 2>&1; then
    setsid /usr/bin/stoat-desktop >/dev/null 2>&1 < /dev/null &
    exit 0
fi
# Focus the window whose process cmdline mentions stoat-desktop (if mapped).
if command -v hyprctl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    pids=$(pgrep -f "stoat-desktop/app.asar" | tr '\n' ' ')
    target=$(hyprctl clients -j 2>/dev/null | jq -r --arg pids "$pids" '
        [$pids | split(" ") | map(tonumber)] as $list |
        .[] | select((.pid // 0) as $p | $list | index($p)) | .address' | head -1)
    if [ -n "$target" ]; then
        hyprctl dispatch focuswindow "address:$target" 2>/dev/null
        exit 0
    fi
fi
# Window hidden/closed: relaunch.
setsid /usr/bin/stoat-desktop >/dev/null 2>&1 < /dev/null &
exit 0