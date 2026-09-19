#!/usr/bin/env bash
# BOOST: drop caches + compact memory (needs root, passwordless sudo configured)
if pgrep -x sudo >/dev/null 2>&1; then
    notify-send -u low "boost" "still busy with an earlier task" 2>/dev/null
    exit 0
fi
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches; echo 1 > /proc/sys/vm/compact_memory'
if [ $? -eq 0 ]; then
    eww update sys_boost="BOOSTED" 2>/dev/null
    ( sleep 8; eww update sys_boost="BOOST" ) >/dev/null 2>&1 &
else
    eww update sys_boost="FAILED" 2>/dev/null
    ( sleep 8; eww update sys_boost="BOOST" ) >/dev/null 2>&1 &
fi