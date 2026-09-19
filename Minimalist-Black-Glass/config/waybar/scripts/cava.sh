#!/bin/bash
# Launch cava as a full-width bar pinned to the bottom of the screen
CONFIG="$HOME/.config/cava/config"
KITTY_CONFIG="$HOME/.config/kitty/cava.conf"

if pgrep -f "app-id cava-bar" >/dev/null; then
    pkill -f "app-id cava-bar"
    sleep 0.3
fi

exec kitty --app-id cava-bar --title cava --class cava-bar \
    -c "$KITTY_CONFIG" \
    -- cava -p "$CONFIG"