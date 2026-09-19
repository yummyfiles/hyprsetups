#!/bin/sh
# Click handler for the center module: media popup when playing, calendar when idle.
status=$(playerctl -p spotify status 2>/dev/null)
case "$status" in
    Playing|Paused) sh "$HOME/.config/waybar/scripts/media-popup.py" ;;
    *)              sh "$HOME/.config/waybar/scripts/calendar.sh" ;;
esac