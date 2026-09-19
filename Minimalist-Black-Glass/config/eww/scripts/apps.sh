#!/usr/bin/env bash
# app-dock driver: prev/next/set page, repopulate eww slot vars
PAGESTATE="$HOME/.config/eww/scripts/.apps_page"
PAGE=$(cat "$PAGESTATE" 2>/dev/null || echo 1)
[ -z "$PAGE" ] && PAGE=1
case "${1:-}" in
  prev) PAGE=$((PAGE - 1)); [ "$PAGE" -lt 1 ] && PAGE=1 ;;
  next) PAGE=$((PAGE + 1)) ;;
  set) PAGE=${2:-1} ;;
  *) PAGE=${1:-$PAGE} ;;
esac
echo "$PAGE" > "$PAGESTATE"
OUT=$(python3 "$HOME/.config/eww/scripts/apps_backend.py" "$PAGE")
[ -n "$OUT" ] && eval "$OUT"
exit 0