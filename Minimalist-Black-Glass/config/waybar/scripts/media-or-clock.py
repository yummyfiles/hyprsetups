#!/usr/bin/env python3
import subprocess
import time

def status():
    try:
        r = subprocess.run(["playerctl", "-p", "spotify", "status"],
            capture_output=True, text=True, timeout=2)
        return r.stdout.strip()
    except Exception:
        return ""

def metadata():
    try:
        r = subprocess.run(["playerctl", "-p", "spotify", "metadata", "--format",
            "{{title}} - {{artist}}"],
            capture_output=True, text=True, timeout=2)
        return r.stdout.strip()
    except Exception:
        return ""

st = status()
if st == "Playing":
    print(metadata() or "Playing")
elif st == "Paused":
    print("(paused) " + metadata() if metadata() else "(paused)")
else:
    print(time.strftime("%I:%M %p  |  %B %d, %Y"))