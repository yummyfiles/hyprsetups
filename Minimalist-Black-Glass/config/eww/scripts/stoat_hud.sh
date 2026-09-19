#!/usr/bin/env bash
# stoat widget — status + profile overview pulled from its Chromium Local Storage
LS="$HOME/.config/stoat-desktop/Local Storage/leveldb"
if pgrep -f "stoat-desktop/app.asar" >/dev/null 2>&1; then
  RUN="RUNNING"
else
  RUN="CLOSED"
fi

DUMP=""
for DIR in \
  "$LS" \
  "$HOME/.config/stoat-desktop/IndexedDB"/*/ \
  "$HOME/.config/stoat-desktop/Session Storage" ; do
  [ -d "$DIR" ] || continue
  DUMP="$DUMP"$'\n'"$( { strings -a "$DIR"/*.log "$DIR"/*.ldb 2>/dev/null; strings -el "$DIR"/*.log "$DIR"/*.ldb 2>/dev/null; } | sort -u )"
done

USER=$(printf '%s\n' "$DUMP" | grep -oE '"username"[: ]*"[^"]+"' | head -1 | sed -E 's/.*"username"[: ]*"([^"]+)"/\1/')
[ -z "$USER" ] && USER=$(printf '%s\n' "$DUMP" | grep -oE '"username"[: ]*[a-zA-Z0-9_-]+' | head -1 | sed -E 's/.*: *//')

PRES=$(printf '%s\n' "$DUMP" | grep -oE '"status"[: ]*"[^"]+"' | head -1 | sed -E 's/.*"status"[: ]*"([^"]+)"/\1/')
[ -z "$PRES" ] && PRES="ONLINE"

echo "STOAT  ·  $RUN  ·  $PRES"
echo "@${USER:-profile not cached}"