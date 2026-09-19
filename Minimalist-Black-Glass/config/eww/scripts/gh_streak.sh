#!/bin/bash
# GitHub contribution streak + graph data provider for eww.
# Fetches the public yearly contributions page (no auth), which contains a
# per-day `data-level` (0-4) for every day of the last year.  We turn that into:
#   graph    ~/.cache/gh_graph.png  (monochrome contribution graph, cached daily)
#   streak   current consecutive contribution day streak (as of the latest data)
#   longest  longest streak in the last year
#   total    contributions in the last year (text shown on the GH page)
# Output is a JSON object consumed by the gh-dashboard window.

set -u

USER="yummyfiles"
CONTRIB="$HOME/.cache/gh_contrib.html"
GRAPH="$HOME/.cache/gh_graph.png"
TTL=86400   # 1 day
URL="https://github.com/users/$USER/contributions"

mkdir -p "$(dirname "$CONTRIB")"

fetch_page() { # refresh the html if stale/missing
  [ -s "$CONTRIB" ] || return 1
  local now last
  now=$(date +%s); last=$(stat -c %Y "$CONTRIB")
  [ $((now - last)) -le $TTL ] && return 0
  return 1
}
if ! fetch_page; then
  curl -sf --max-time 20 "$URL" -o "$CONTRIB" || :  # keep stale copy on failure
fi

# Parse "430 contributions in the last year": the number sits on the line
# right after the h2 opening tag (avoids tabindex="-1" etc.)
TOTAL=$(rg -A1 'id="js-contribution-activity-description"' "$CONTRIB" | tail -1 | rg -o '[0-9,]+' | head -1 | tr -d ',')

# Per-day levels, used for both the streak math and the graph rendering.
rg -o 'data-date="[0-9-]+"[^>]*?data-level="[0-9]+"' "$CONTRIB" \
  | sed -E 's/.*data-date="([0-9-]+)".*data-level="([0-9]+)"/\1 \2/' \
  | sort -u > /tmp/gh_levels.txt

python3 - "$TOTAL" "$GRAPH" <<'PYEOF'
import sys, datetime, subprocess, os

total_raw = sys.argv[1] if len(sys.argv) > 1 else ""
graph_path = sys.argv[2] if len(sys.argv) > 2 else ""

try:
    total = int(total_raw) if total_raw.isdigit() else 0
except Exception:
    total = 0

levels = {}
with open("/tmp/gh_levels.txt") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d, lv = line.split()
        levels[d] = int(lv)

if not levels:
    print('{"graph":"","streak":"--","longest":"--","total":"--"}')
    sys.exit(0)

lo = min(levels)
hi = max(levels)
d0 = datetime.date.fromisoformat(lo)
d1 = datetime.date.fromisoformat(hi)

# ---- streaks ----
cur = best = 0
day = d0
while day <= d1:
    lv = levels.get(day.isoformat(), 0)
    if lv > 0:
        cur += 1
        best = max(best, cur)
    else:
        cur = 0
    day += datetime.timedelta(days=1)

# ---- contribution graph (monochrome), GitHub layout: columns = weeks,
#      rows = Sun..Sat, each column starts at a Sunday. ----
def render():
    try:
        # find the Sunday that starts the first column (at or before d0)
        start = d0 - datetime.timedelta(days=d0.isoweekday() % 7)  # Sun=7 -> back 0, Mon=1 -> back 1

        weeks = []
        col = start
        while col <= d1:
            wk = [(col + datetime.timedelta(days=i)).isoformat() for i in range(7)]
            weeks.append(wk)
            col += datetime.timedelta(days=7)
        ncols = len(weeks)
        nrows = 7

        cell = 10
        gap = 2
        pad = 4
        W = pad * 2 + ncols * (cell + gap) - gap
        H = pad * 2 + nrows * (cell + gap) - gap

        # pure black/white: any contribution = solid white cell
        alpha = {1: "1.0", 2: "1.0", 3: "1.0", 4: "1.0"}
        draws = ["-size", f"{W}x{H}", "canvas:none"]
        for c, wk in enumerate(weeks):
            for r, d in enumerate(wk):
                lv = levels.get(d, 0)
                a = alpha.get(lv)
                if a is None:
                    continue
                x = pad + c * (cell + gap)
                y = pad + r * (cell + gap)
                draws += [
                    "-fill", f"rgba(255,255,255,{a})",
                    "-draw", f"rectangle {x},{y} {x + cell - 1},{y + cell - 1}",
                ]
        draws += [graph_path]
        subprocess.run(["magick", *draws], check=True, capture_output=True)
        return graph_path if os.path.isfile(graph_path) else ""
    except Exception as e:
        print("graph error", e, file=sys.stderr)
        return ""

graph = render()

# ---- JSON for eww: keep followers/stars/repos passed through? no: this
#      script only owns streak/graph/total; the main dashboard owns the rest.
print('{"graph":"%s","streak":"%d","longest":"%d","total":"%d"}' % (graph, cur, best, total))
PYEOF