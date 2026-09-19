#!/bin/bash
STATE=/tmp/arch_desktop_state
SPECIAL="special:showdesktop"

lua_eval() {
    hyprctl eval "$1" 2>/dev/null
}

move_window() {
    lua_eval "hl.dispatch(hl.dsp.window.move({ workspace = \"$1\", window = \"address:$2\", follow = false }))"
}

if [ -f "$STATE" ]; then
    # ---- RESTORE ----
    window_count=0
    addr=(); ws=(); w=()
    focus_addr=""
    while read -r key a b c d e; do
        case "$key" in
            F) focus_addr="$a" ;;
            w)
                addr[$window_count]="$a"
                ws[$window_count]="$b"
                w[$window_count]="$e"
                window_count=$((window_count + 1))
                ;;
        esac
    done < "$STATE"

    if [ "$window_count" -gt 0 ]; then
        # restore the first (leftmost) window
        move_window "${ws[0]}" "${addr[0]}"

        if [ "$window_count" -eq 2 ] && [ "${ws[0]}" = "${ws[1]}" ]; then
            # Make the split deterministic (new window right of the restored one)
            lua_eval 'hl.dispatch(hl.dsp.layout("preselect right"))'
            # child0 gets box/2 * splitRatio; we want left = w0/(w0+w1)
            frac=$(awk -v a="${w[0]}" -v b="${w[1]}" 'BEGIN{printf "%.6f", a/(a+b)}')
            ratio=$(awk -v f="$frac" 'BEGIN{r=2*f; if(r<0.1)r=0.1; if(r>1.9)r=1.9; printf "%.4f", r}')
            lua_eval "hl.config({ dwindle = { default_split_ratio = $ratio } })"
            move_window "${ws[1]}" "${addr[1]}"
            lua_eval 'hl.config({ dwindle = { default_split_ratio = 1.0 } })'
        elif [ "$window_count" -gt 1 ]; then
            for i in $(seq 1 $((window_count - 1))); do
                move_window "${ws[$i]}" "${addr[$i]}"
            done
        fi
    fi

    if [ -n "$focus_addr" ]; then
        lua_eval "hl.dispatch(hl.dsp.focus({ window = \"address:$focus_addr\" }))"
    fi
    rm -f "$STATE"
else
    # ---- HIDE ----
    : > "$STATE"
    hyprctl clients -j 2>/dev/null | jq -r '
        [.[] | select(.mapped==true and ((.hidden // false) | not) and .workspace.id >= 0 and .fullscreen==0 and .pinned==false)]
        | sort_by(.at[0], .at[1])
        | .[] | "w \(.address) \(.workspace.id) \(.at[0]) \(.at[1]) \(.size[0])"' > "$STATE" 2>/dev/null

    FOCUS=$(hyprctl activewindow -j 2>/dev/null | jq -r 'if type == "array" then (.[0].address // empty) else (.address // empty) end')
    if [ -n "$FOCUS" ]; then
        { echo "F $FOCUS"; cat "$STATE"; } > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
    fi

    while read -r kw addr rest; do
        [ "$kw" = "w" ] && move_window "$SPECIAL" "$addr"
    done < <(grep -E "^w " "$STATE")
    count=$(grep -cE "^w " "$STATE" 2>/dev/null)
    [ "$count" -eq 0 ] && rm -f "$STATE"
fi