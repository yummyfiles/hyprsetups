#!/usr/bin/env bash
# hyprsetups installer — installs ONE rice folder as your live dotfiles.
#
# Usage:
#   sh install.sh            # pick a setup from the collection
#   sh install.sh --force    # replace existing configs (backs them up first)
#   sh install.sh Green-Hacker
#
# Each rice lives in its own folder at the repo root (e.g. Minimalist-Black-Glass/)
# with config/, home/, local-share/, firefox/ and a README.md.

set -e

# --- Resolve the repo root (clone if we're a bare piped one-liner) ----------
if [ -d "$(dirname "$0")/Minimalist-Black-Glass" ]; then
    REPO="$(cd "$(dirname "$0")" && pwd)"
else
    DEST="${DOTFILES_DIR:-$HOME/hyprsetups}"
    REPO_URL="${DOTFILES_REPO:-https://github.com/yummyfiles/hyprsetups}"
    echo "==> Cloning $REPO_URL into $DEST"
    if [ ! -d "$DEST/.git" ]; then
        command -v git >/dev/null || { echo "ERROR: git is required to bootstrap install."; exit 1; }
        git clone --depth 1 "$REPO_URL" "$DEST"
    fi
    REPO="$DEST"
fi

HOME_DIR="$HOME"
BACKUP="$HOME/.dotfiles-backup"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

# --- Pick the rice -----------------------------------------------------------
pick() {
    local d
    for d in "$REPO"/*/; do
        [ -f "$d/.info" ] || continue
        local id; id="$(basename "$d")"
        local name; name="$(sed -n 's/^name: *//p' "$d/.info")"
        local desc; desc="$(sed -n 's/^desc: *//p' "$d/.info")"
        printf '%-28s %-22s %s\n' "$id" "$name" "$desc"
    done
}

SETUP="${1:-}"
if [ "$SETUP" = "--force" ]; then SETUP="${2:-}"; FORCE=1; fi
if [ -z "$SETUP" ]; then
    pick
    printf 'enter a setup name: '; read -r SETUP
fi
CFG_ROOT="$REPO/$SETUP"
[ -d "$CFG_ROOT/config" ] || [ -d "$CFG_ROOT/home" ] || {
    echo "!! \"$SETUP\" is a placeholder — it has nothing to install yet." >&2
    echo "   Add config/ + home/ to '$CFG_ROOT' first, then re-run." >&2
    exit 1
}
echo "==> installing setup: $SETUP"

link() { # link <absolute-source> <target>
    local src="$1" dst="$2"
    [ -e "$src" ] || return 0
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        [ "$FORCE" = 1 ] || { echo "skip  $dst (exists, use --force to replace)"; return 0; }
        mkdir -p "$BACKUP"
        mv "$dst" "$BACKUP/$(basename "$dst")"
        echo "backed up $dst -> $BACKUP"
    fi
    [ -L "$dst" ] && rm -f "$dst"
    mkdir -p "$(dirname "$dst")"
    ln -s "$src" "$dst"
    echo "linked $dst"
}

echo "== home dotfiles =="
for f in .zshrc .bashrc .bash_profile .bash_logout .profile .zprofile .gitconfig .gtkrc-2.0; do
    link "$CFG_ROOT/home/$f" "$HOME_DIR/$f"
done

echo "== ~/.config =="
while IFS= read -r d; do
    base="$(basename "$d")"
    link "$d" "$HOME_DIR/.config/$base"
done < <(find "$CFG_ROOT/config" -maxdepth 1 -mindepth 1 2>/dev/null | sort)

echo "== ~/.local/share =="
while IFS= read -r d; do
    base="$(basename "$d")"
    link "$d" "$HOME_DIR/.local/share/$base"
done < <(find "$CFG_ROOT/local-share" -maxdepth 2 -mindepth 2 2>/dev/null | sort)

echo "== firefox theme (best-effort) =="
FF_DIR="$HOME/.config/mozilla/firefox"
PROFILE=""
if [ -f "$FF_DIR/profiles.ini" ]; then
    PROFID=$(awk -F= '/^Default=/{print $2; exit}' "$FF_DIR/profiles.ini" 2>/dev/null)
    if [ -z "$PROFID" ]; then
        PROFID=$(awk -F= '/\[Profile|^Path=/{if ($1=="Path"){print $2; exit}}' "$FF_DIR/profiles.ini" 2>/dev/null)
    fi
    [ -n "$PROFID" ] && PROFILE="$FF_DIR/$PROFID"
fi
if [ -n "$PROFILE" ] && [ -d "$PROFILE" ] && [ -d "$CFG_ROOT/firefox" ]; then
    mkdir -p "$PROFILE/chrome"
    cp -a "$CFG_ROOT/firefox/user.js" "$PROFILE/user.js" 2>/dev/null || true
    cp -a "$CFG_ROOT/firefox/chrome/userChrome.css" "$PROFILE/chrome/userChrome.css" 2>/dev/null || true
    cp -a "$CFG_ROOT/firefox/chrome/userContent.css" "$PROFILE/chrome/userContent.css" 2>/dev/null || true
    echo "deployed firefox theme -> $PROFILE"
else
    echo "no firefox profile or no firefox/ in this setup; skipping"
fi

echo "== systemd user units =="
if [ -d "$CFG_ROOT/config/systemd/user" 2>/dev/null ]; then
    systemctl --user daemon-reload 2>/dev/null || true
    for u in "$CFG_ROOT"/config/systemd/user/*.service; do
        [ -e "$u" ] || continue
        unit="$(basename "$u")"
        systemctl --user enable "$unit" >/dev/null 2>&1 || true
        echo "enabled $unit"
    done
fi

echo
echo "Done (setup: $SETUP)."