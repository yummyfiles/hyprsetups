#!/usr/bin/env python3
# app-dock backend: enumerate installed .desktop apps, resolve icons, emit eww updates
import os, sys, configparser, glob, hashlib

SEARCH_DIRS = [
    "/usr/share/applications",
    "/usr/local/share/applications",
    os.path.expanduser("~/.local/share/applications"),
    "/var/lib/flatpak/exports/share/applications",
    os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
    "/usr/share/applications/kde4",
]

ICON_DIRS = [
    "/usr/share/icons/hicolor/512x512/apps",
    "/usr/share/icons/hicolor/256x256/apps",
    "/usr/share/icons/hicolor/128x128/apps",
    "/usr/share/icons/hicolor/96x96/apps",
    "/usr/share/icons/hicolor/64x64/apps",
    "/usr/share/icons/hicolor/48x48/apps",
    "/usr/share/icons/hicolor/32x32/apps",
    "/usr/share/icons/hicolor/24x24/apps",
    "/usr/share/icons/hicolor/scalable/apps",
    "/usr/share/icons/Adwaita/scalable/apps",
    "/usr/share/icons/Adwaita/512x512/apps",
    "/usr/share/icons/Adwaita/48x48/apps",
    "/usr/share/icons/breeze-dark/scalable/apps",
    "/usr/share/icons/breeze-dark/48x48/apps",
    "/usr/share/icons/breeze/scalable/apps",
    "/usr/share/icons/breeze/48x48/apps",
    "/usr/share/icons/Papirus/48x48/apps",
    "/usr/share/pixmaps",
]

PRIORITY = [
    "firefox", "spotify", "dolphin", "stoat", "kitty",
    "files", "nautilus", "discord", "vesktop", "cava",
    "code", "obsidian", "font-manager", "system-settings", "settings",
]

BLOCK_SUBSTR = (
    "uninstall", "installer", "setup", "app.asar", "demo",
    "manual", "electron", "authors", "bookworm", "waydroid-installer",
)

FALLBACK_ICON = "/home/yummy.dev/.config/eww/assets/icons/app.svg"
CACHE = os.path.expanduser("~/.config/eww/scripts/.iconcache")
os.makedirs(CACHE, exist_ok=True)


def mono(path, key):
    """Greyscale a source icon onto a black square, cached for eww."""
    out = os.path.join(CACHE, key + ".png")
    if os.path.exists(out):
        return out
    try:
        import subprocess
        # Compress into near-pure black/white for a true mono look.
        r = subprocess.run(
["convert", path, "-background", "black", "-flatten",
             "-alpha", "off", "-colorspace", "gray", "-level", "30%,75%",
             "-resize", "48x48^", "-extent", "48x48", out],
            capture_output=True, timeout=10)
        if r.returncode == 0 and os.path.exists(out):
            return out
    except Exception:
        pass
    return path

def parse(entry):
    cp = configparser.ConfigParser(interpolation=None)
    try:
        cp.read(entry, encoding="utf-8")
    except Exception:
        return None
    if not cp.has_section("Desktop Entry"):
        return None
    s = cp["Desktop Entry"]
    if s.get("Type", "Application") not in ("Application",):
        return None
    if s.get("NoDisplay", "false").lower() in ("true", "1"):
        return None
    if s.get("Hidden", "false").lower() in ("true", "1"):
        return None
    name = s.get("Name") or os.path.basename(entry).replace(".desktop", "")
    if s.get("Terminal", "false").lower() in ("true", "1"):
        return None
    exec_ = s.get("Exec", "")
    lower = (name + " " + exec_).lower()
    if any(b in lower for b in BLOCK_SUBSTR):
        return None
    icon = s.get("Icon", "")
    return {"name": name, "icon": icon, "id": os.path.basename(entry)}

def resolve_icon(icon):
    if not icon:
        return None
    if icon.startswith("/"):
        return icon if os.path.exists(icon) else None
    base = os.path.basename(icon)
    # prefer scalable svg then largest png/svg
    for d in ICON_DIRS:
        for ext in ("svg", "png", "xpm"):
            p = os.path.join(d, base + "." + ext)
            if os.path.exists(p):
                return p
    return None

def shq(v):
    return "'" + v.replace("'", "'\\''") + "'"

def main():
    page = max(1, int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    seen, apps = set(), []
    for d in SEARCH_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.desktop"))):
            if f in seen:
                continue
            seen.add(f)
            a = parse(f)
            if a:
                apps.append(a)

    def rank(a):
        low = a["id"].lower()
        for i, p in enumerate(PRIORITY):
            if p in low:
                return (0, i)
        return (1, a["name"].lower())

    apps.sort(key=rank)

    pages = max(1, (len(apps) + per - 1) // per)
    page = min(page, pages)
    start = (page - 1) * per
    chunk = apps[start:start + per]

    updates = [f"app_page={page}", f"app_pages={pages}", f"app_total={len(apps)}"]
    for i in range(per):
        if i < len(chunk):
            a = chunk[i]
            icon = resolve_icon(a["icon"])
            if icon and icon != FALLBACK_ICON:
                icon = mono(icon, hashlib.sha1(a["id"].encode()).hexdigest()[:12])
            else:
                icon = FALLBACK_ICON
            name = a["name"].replace(" ", " ").replace("\"", "'")
            cmd = f"gtk-launch {a['id']} &"
        else:
            icon, name, cmd = FALLBACK_ICON, "", "true"
        updates.append(f"app_p{i}={shq(icon)}")
        updates.append(f"app_n{i}={shq(name)}")
        updates.append(f"app_c{i}={shq(cmd)}")
    print("eww update " + " ".join(updates))

if __name__ == "__main__":
    main()