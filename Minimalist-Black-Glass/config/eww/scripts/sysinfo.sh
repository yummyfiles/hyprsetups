#!/usr/bin/env bash
# eww system-info widget — cpu/ram/swap/storage/uptime, monochrome
python3 - <<'EOF'
import os, re, time, shutil

rc = re.compile(r"^(\w+):\s*(.*)$")
def meminfo():
    out = {}
    for line in open("/proc/meminfo", errors="ignore"):
        k, v = line.split(":", 1)
        out[k] = int(v.split()[0])
    return out

def cpu_use():
    a = [int(x) for x in open("/proc/stat").readline().split()[1:]]
    time.sleep(0.25)
    b = [int(x) for x in open("/proc/stat").readline().split()[1:]]
    tot_a, tot_b = sum(a), sum(b)
    idle_a, idle_b = a[3] + a[4], b[3] + b[4]
    d = max(1, tot_b - tot_a)
    return round(100 * (1 - (idle_b - idle_a) / d))

m = meminfo()
tot = m.get("MemTotal", 0) / 1048576
avail = m.get("MemAvailable", m.get("MemFree", 0)) / 1048576
stot = m.get("SwapTotal", 0) / 1048576
sfree = m.get("SwapFree", 0) / 1048576

def df(p):
    try:
        u = shutil.disk_usage(p)
        return u.total / 1e9, u.used / 1e9
    except Exception:
        return None, None

dt, du = df("/")
ht, hu = dt, du
for p in ("/home",):
    if os.path.ismount(p):
        ht, hu = df(p)

with open("/proc/uptime") as f:
    up = int(float(f.read().split()[0]))
h, mm = divmod(up, 3600); mm //= 60

print(f"CPU {cpu_use():>3}%")
print(f"RAM {avail:.1f}/{tot:.1f}GB")
print(f"SWAP {max(0, stot-sfree)/1000:.1f}/{stot/1000:.1f}GB")
print(f"DISK {hu:.0f}/{ht:.0f}GB")
print(f"UP {h}h {mm:02d}m")
EOF