#!/bin/bash

SSID=$(nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2)
[ -z "$SSID" ] && SSID="Disconnected"

OPTIONS="Toggle WiFi\nRescan Networks\nDisconnect\n"
NETWORKS=$(nmcli -t -f SSID,SIGNAL dev wifi | sed 's/:/  -  /g' | sort -u)

CHOICE=$(echo -e "$OPTIONS$NETWORKS" | rofi -dmenu -p "WIFI ($SSID)" -theme ~/.config/rofi/themes/bw.rasi)

if [ -z "$CHOICE" ]; then exit; fi

if [ "$CHOICE" == "Toggle WiFi" ]; then
    STATE=$(nmcli radio wifi)
    if [ "$STATE" == "enabled" ]; then
        nmcli radio wifi off
    else
        nmcli radio wifi on
    fi
elif [ "$CHOICE" == "Rescan Networks" ]; then
    nmcli dev wifi rescan
elif [ "$CHOICE" == "Disconnect" ]; then
    nmcli dev disconnect wlan0
else
    # Extract SSID
    TARGET_SSID=$(echo "$CHOICE" | awk -F '  -  ' '{print $1}')
    # Ask for password if needed
    PASS=$(rofi -dmenu -p "Password for $TARGET_SSID" -password -theme ~/.config/rofi/themes/bw.rasi)
    if [ -z "$PASS" ]; then
        nmcli dev wifi connect "$TARGET_SSID"
    else
        nmcli dev wifi connect "$TARGET_SSID" password "$PASS"
    fi
fi
