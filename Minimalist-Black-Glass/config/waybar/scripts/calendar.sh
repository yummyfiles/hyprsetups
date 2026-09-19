#!/bin/bash

# Simple calendar popup using rofi

cal_output=$(cal -3 | sed 's/^/  /')

echo "$cal_output" | rofi -dmenu -p "CALENDAR" -theme ~/.config/rofi/themes/bw.rasi -location 3 -xoffset -20 -yoffset 30 -width 400 -lines 15 -no-custom