#!/bin/bash

# Get current volume and mute status
VOLUME=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{print $2 * 100}')
MUTE=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ | grep -c "MUTED")

if [ "$MUTE" -eq 1 ]; then
    STATUS="MUTED"
else
    STATUS="$VOLUME%"
fi

OPTIONS="Toggle Mute\nVolume Up (+5%)\nVolume Down (-5%)\nSet 100%\nSet 50%\nSet 0%"

CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -p "VOLUME ($STATUS)" -theme ~/.config/rofi/themes/bw.rasi)

case "$CHOICE" in
    "Toggle Mute") wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle ;;
    "Volume Up (+5%)") wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+ ;;
    "Volume Down (-5%)") wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%- ;;
    "Set 100%") wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 ;;
    "Set 50%") wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.5 ;;
    "Set 0%") wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.0 ;;
esac
