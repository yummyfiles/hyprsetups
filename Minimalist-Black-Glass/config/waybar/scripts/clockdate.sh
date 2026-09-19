#!/bin/sh
case "$(playerctl -p spotify status 2>/dev/null)" in
    Playing|Paused) date '+%I:%M %p | %B %d, %Y' ;;
    *)              date '+%I:%M %p \    / %B %d, %Y' ;;
esac