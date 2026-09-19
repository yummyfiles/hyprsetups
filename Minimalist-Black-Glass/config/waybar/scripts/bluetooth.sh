#!/bin/bash

STATUS=$(bluetoothctl show | grep "Powered:" | awk '{print $2}')
DEVICES=$(bluetoothctl devices Paired | awk '{print $2, $3}')

OPTIONS="Toggle Power\nScan\nPair Device\nTrust Device\nConnect Device\nDisconnect Device\nRemove Device"

CHOICE=$(echo -e "$OPTIONS" | rofi -dmenu -p "BLUETOOTH ($STATUS)" -theme ~/.config/rofi/themes/bw.rasi)

case "$CHOICE" in
    "Toggle Power")
        if [ "$STATUS" == "yes" ]; then
            bluetoothctl power off
        else
            bluetoothctl power on
        fi
        ;;
    "Scan")
        bluetoothctl scan on &
        sleep 5
        bluetoothctl scan off
        ;;
    "Connect Device")
        DEV=$(bluetoothctl devices | awk '{$1=""; print $0}' | rofi -dmenu -p "Connect" -theme ~/.config/rofi/themes/bw.rasi)
        MAC=$(bluetoothctl devices | grep "$DEV" | awk '{print $2}')
        bluetoothctl connect "$MAC"
        ;;
    "Disconnect Device")
        DEV=$(bluetoothctl info | grep "Name:" | awk '{$1=""; print $0}')
        MAC=$(bluetoothctl info | grep "Device" | awk '{print $2}')
        bluetoothctl disconnect "$MAC"
        ;;
esac
