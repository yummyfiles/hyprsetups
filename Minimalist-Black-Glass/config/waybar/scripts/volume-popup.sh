#!/bin/bash

# Volume slider popup - slides down from top right

get_volume() {
    wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{print int($2 * 100)}'
}

get_mute() {
    wpctl get-volume @DEFAULT_AUDIO_SINK@ | grep -c "MUTED"
}

VOL=$(get_volume)
MUTE=$(get_mute)

if [ "$MUTE" -eq 1 ]; then
    ICON="󰝟"
    STATUS="MUTED"
else
    if [ "$VOL" -gt 66 ]; then ICON="󰕾"; elif [ "$VOL" -gt 33 ]; then ICON="󰖀"; else ICON="󰕿"; fi
    STATUS="${VOL}%"
fi

# Get current output device
DEVICE=$(wpctl status | grep -A 20 "Audio" | grep -A 10 "Sinks" | grep "\*" | head -1 | sed 's/.*[0-9]\. //' | sed 's/ \[vol:.*//')

OPTIONS="󰝟  Toggle Mute\n󰕾  Volume: ${VOL}%\n󰋋  Output: ${DEVICE}\n󰁄  Set 100%\n󰁃  Set 50%\n󰁂  Set 0%"

CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -p "VOLUME ($STATUS)" -theme ~/.config/rofi/themes/bw.rasi -location 3 -xoffset -20 -yoffset 30 -width 300 -lines 7)

case "$CHOICE" in
    *"Toggle Mute"*) wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle ;;
    *"Volume:"*) 
        # Use a slider-like input
        NEW_VOL=$(seq 0 5 100 | rofi -dmenu -p "Set Volume (${VOL}%)" -theme ~/.config/rofi/themes/bw.rasi -location 3 -xoffset -20 -yoffset 70 -width 200 -lines 10)
        if [ -n "$NEW_VOL" ]; then
            wpctl set-volume @DEFAULT_AUDIO_SINK@ "${NEW_VOL}%"
        fi
        ;;
    *"Set 100%"*) wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 ;;
    *"Set 50%"*) wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.5 ;;
    *"Set 0%"*) wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.0 ;;
esac