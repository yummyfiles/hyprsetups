#!/usr/bin/env bash
# Fullscreen overlay power menu (dimmed background, big centered icons)

OPTIONS=("󰐥  Shut Down" "󰜉  Reboot" "󰤄  Suspend" "󰀣  Lock")

CHOICE=$(printf '%s\n' "${OPTIONS[@]}" | rofi -dmenu -theme ~/.config/rofi/themes/power.rasi -p "" 2>/dev/null)
[ -z "$CHOICE" ] && exit 0

case "$CHOICE" in
  *Shut*) sudo -n systemctl poweroff ;;
  *Reboot*) sudo -n systemctl reboot ;;
  *Suspend*) sudo -n systemctl suspend ;;
  *Lock*) hyprlock >/dev/null 2>&1 & ;;
esac

exit 0