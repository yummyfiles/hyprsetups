#!/usr/bin/env bash
# eww weather widget — wttr.in, auto location, black/white text
D=$(curl -s -m 8 "https://wttr.in/?format=j1" 2>/dev/null)
if [ -z "$D" ]; then
  echo "OFFLINE"
  exit 0
fi
python3 - "$D" <<'EOF'
import sys, json
try:
    d = json.loads(sys.argv[1])
except Exception:
    print("WEATHER UNAVAILABLE")
    sys.exit(0)
c = d["current_condition"][0]
t = c["temp_C"]
f = c["FeelsLikeC"]
w = c["windspeedKmph"]
desc = (c["weatherDesc"][0]["value"] or "").upper()
today = d["weather"][0]
hi, lo = today["maxtempC"], today["mintempC"]
print(desc[:20])
print(f"{t}\u00b0C   FEELS {f}\u00b0C")
print(f"H {hi}\u00b0    L {lo}\u00b0    {w}KM/H WIND")
EOF